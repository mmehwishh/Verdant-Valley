"""
src/agents/farmer.py - Farmer Agent — full functionality
  - Terrain: walks mud/dirt/grass/field, blocked by water & stone
  - Plant mode: triggered externally via farmer.trigger_planting()
  - Manual planting: farmer.plant_selected_crops(crop_id, count)
      → farmer physically walks to each tile and plants, then auto-harvests
  - Crop growth: ticks over time per planted tile
  - Harvest: auto-harvests stage-2 crops using A*
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan


def _animal_aware_cost(tile, base_cost, agents, animal_avoidance_radius=2):
    """Add cost penalty for tiles near animals."""
    if base_cost == float('inf'):
        return float('inf')
    if not agents:
        return base_cost
    animals = [a for a in agents if hasattr(a, 'name') and 'Animal' in a.name and a.alive]
    if not animals:
        return base_cost
    tile_pos = (tile.col, tile.row)
    min_dist = min(manhattan(tile_pos, (a.col, a.row)) for a in animals)
    if min_dist <= 1:
        return float('inf')
    elif min_dist <= animal_avoidance_radius:
        return base_cost + 20
    return base_cost


# Planting score: how desirable is each tile type for planting?
PLANT_TILE_SCORE = {
    TILE_FIELD: 3.0,
    TILE_MUD:   2.0,
    TILE_DIRT:  1.0,
}

# Crop growth ticks: stage0→1, stage1→2
CROP_GROWTH_TICKS = {
    CROP_WHEAT:     (180, 300),
    CROP_SUNFLOWER: (240, 360),
    CROP_CORN:      (200, 320),
    CROP_TOMATO:    (220, 340),
    CROP_CARROT:    (160, 280),
    CROP_POTATO:    (200, 350),
}


class Farmer(Agent):
    """
    AI Farmer — harvests ripe crops and plants new ones on command.

    External API
    ------------
    farmer.trigger_planting()
        Plant one crop on the farmer's current tile (button / G key).

    farmer.plant_selected_crops(crop_id, count)
        Queue *count* tiles of *crop_id*.  Farmer physically walks to each
        tile, plants, then automatically switches back to harvest mode.
    """

    def __init__(self, col, row):
        import os
        path = "assets/agents/farmer/farmer.png"
        super().__init__(
            col, row, C_FARMER, speed=2.0, name="Farmer",
            sprite_sheet_path=path if os.path.exists(path) else None,
            frame_size=(30, 30), animation_rows=6, animation_cols=6, scale=2,
        )

        self.target      = None
        self.replan_cd   = 0
        self.harvest_count = 0
        self.plant_count   = 0
        self.harvested_count = 0

        # Single-tile plant (G key / button)
        self._plant_requested = False

        # Autonomous multi-tile planting (manual-select mode)
        self._planting_mode   = False
        self._plant_queue: list[tuple[int, int]] = []
        self._plant_crop_id   = CROP_WHEAT      # crop to use in autonomous mode

        # Growth timers: {(col, row): ticks_at_current_stage}
        self._growth_timers: dict[tuple, int] = {}

        # Failed-plant indicator
        self._failed_plant_tile  = None
        self._failed_plant_timer = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def trigger_planting(self):
        """Plant one crop on the farmer's current tile (G key / UI button)."""
        self._plant_requested = True

    def plant_selected_crops(self, crop_id: int, count: int):
        """
        Begin autonomous planting mode.
        The farmer will walk to *count* suitable tiles and plant *crop_id*,
        then automatically resume harvesting.

        Called by main.py after the user confirms Manual Select in the popup.
        """
        self._plant_crop_id = crop_id
        self._plant_queue   = []        # will be populated during first _update_planting call
        self._planting_mode = True
        self._pending_count = count     # how many tiles still to queue
        self._tiles_planted = 0
        self.state = "planting"
        print(f"🌱 Farmer entering manual planting mode: {count}× {CROP_NAMES[crop_id]}")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _tile_passable(self, tile) -> bool:
        return tile is not None and FARMER_COSTS.get(tile.type, 1.0) != float('inf')

    def _pick_harvest_target(self, grid, agents):
        best_score, best_tile = -1, None
        animals = [a for a in agents if hasattr(a, 'name') and 'Animal' in a.name and a.alive]

        for c, r in grid.crop_tiles():
            tile = grid.get(c, r)
            if tile is None or tile.crop == CROP_NONE or tile.crop_stage < 2:
                continue
            if not self._tile_passable(tile):
                continue

            value = CROP_VALUE[tile.crop]
            dist  = manhattan((self.col, self.row), (c, r)) + 1

            animal_penalty = 0
            min_animal_dist = float('inf')
            for a in animals:
                d = manhattan((c, r), (a.col, a.row))
                min_animal_dist = min(min_animal_dist, d)
                if hasattr(a, 'name') and 'Bear' in a.name:
                    animal_penalty += 50 if d <= 3 else (20 if d <= 5 else 0)
            if min_animal_dist <= 2:
                animal_penalty += 30
            elif min_animal_dist <= 4:
                animal_penalty += 10

            score = (value * tile.crop_stage) / dist - animal_penalty
            if score > best_score:
                best_score, best_tile = score, (c, r)
        return best_tile

    def _pick_plant_tiles(self, grid, agents, count: int) -> list[tuple[int, int]]:
        """
        Return up to *count* best plantable tiles sorted by desirability.
        Prefers TILE_FIELD > MUD > DIRT, water adjacency bonus, animal avoidance.
        """
        candidates = []
        animals = [a for a in agents if hasattr(a, 'name') and 'Animal' in a.name and a.alive]

        for c in range(grid.cols):
            for r in range(grid.rows):
                tile = grid.get(c, r)
                if tile is None or tile.type not in PLANT_TILE_SCORE:
                    continue
                if tile.crop != CROP_NONE:
                    continue
                if (c, r) in self._growth_timers:
                    continue

                base = PLANT_TILE_SCORE[tile.type]
                water_bonus = 0.0
                for dc, dr in ((0,1),(0,-1),(1,0),(-1,0)):
                    nb = grid.get(c+dc, r+dr)
                    if nb and nb.type == TILE_WATER:
                        water_bonus = 1.5
                        break

                animal_penalty = 0.0
                for a in animals:
                    d = manhattan((c, r), (a.col, a.row))
                    if d <= 3:
                        animal_penalty = 2.0
                        break
                    elif d <= 5:
                        animal_penalty = 1.0

                dist  = manhattan((self.col, self.row), (c, r)) + 1
                score = (base + water_bonus) / dist - animal_penalty
                candidates.append((score, c, r))

        candidates.sort(reverse=True)
        return [(c, r) for _, c, r in candidates[:count]]

    def _plant_at(self, grid, c, r, crop=None):
        """Actually place a seed on tile (c, r)."""
        tile = grid.get(c, r)
        if tile is None or tile.type not in PLANT_TILE_SCORE:
            return
        if crop is None:
            crop = self._plant_crop_id
        tile.crop       = crop
        tile.crop_stage = 0
        self._growth_timers[(c, r)] = 0
        self.plant_count += 1
        print(f"🌱 Farmer planted {CROP_NAMES[crop]} at ({c},{r})")

    def _harvest(self, grid):
        tile = grid.get(self.col, self.row)
        if tile and tile.crop != CROP_NONE and tile.crop_stage >= 2:
            crop_name = CROP_NAMES[tile.crop]
            value     = CROP_VALUE[tile.crop] * tile.crop_stage
            self.score    += value
            self.harvest_count += 1
            self.harvested_count += 1
            print(f"🌾 Farmer harvested {crop_name}! +{value}  total={self.score}")
            tile.crop       = CROP_NONE
            tile.crop_stage = 0
            self._growth_timers.pop((self.col, self.row), None)
            self.target = None
            self.state  = "harvesting"

    def _tick_growth(self, grid):
        done = []
        for (c, r), ticks in self._growth_timers.items():
            tile = grid.get(c, r)
            if tile is None or tile.crop == CROP_NONE:
                done.append((c, r))
                continue
            ticks += 1
            self._growth_timers[(c, r)] = ticks
            grow = CROP_GROWTH_TICKS.get(tile.crop, (240, 480))
            if tile.crop_stage == 0 and ticks >= grow[0]:
                tile.crop_stage = 1
                print(f"🌿 Crop sprouted at ({c},{r})")
            elif tile.crop_stage == 1 and ticks >= grow[1]:
                tile.crop_stage = 2
                print(f"🌻 Crop ripe at ({c},{r})!")
                done.append((c, r))
        for key in done:
            self._growth_timers.pop(key, None)

    # ── Single-tile plant (G key / button) ───────────────────────────────────

    def _try_plant_current_tile(self, grid):
        self._plant_requested = False
        tile = grid.get(self.col, self.row)
        if tile is None:
            self._show_failed_plant(); return
        if tile.type not in PLANT_TILE_SCORE:
            print(f"🌱 Farmer: cannot plant on {tile.type} tile")
            self._show_failed_plant(); return
        if tile.crop != CROP_NONE:
            print("🌱 Farmer: tile already has a crop")
            self._show_failed_plant(); return
        if (self.col, self.row) in self._growth_timers:
            print("🌱 Farmer: tile already growing something")
            self._show_failed_plant(); return

        crop = random.choice([CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN,
                               CROP_TOMATO, CROP_CARROT, CROP_POTATO])
        self._plant_at(grid, self.col, self.row, crop)

    def _show_failed_plant(self):
        self._failed_plant_tile  = (self.col, self.row)
        self._failed_plant_timer = 60

    # ── Autonomous multi-tile planting ────────────────────────────────────────

    def _update_planting(self, grid, agents):
        """
        Drive the autonomous planting loop:
          1. If queue is empty, pick best tiles (up to _pending_count).
          2. Walk to next tile, plant, pop queue.
          3. When done, switch back to idle / harvest mode.
        """
        # --- Populate queue if empty and we still have tiles to plant ---
        if not self._plant_queue and hasattr(self, '_pending_count') and self._pending_count > 0:
            new_tiles = self._pick_plant_tiles(grid, agents, self._pending_count)
            # Filter out tiles that already have crops or are being grown
            new_tiles = [
                (c, r) for c, r in new_tiles
                if grid.get(c, r) and grid.get(c, r).crop == CROP_NONE
                and (c, r) not in self._growth_timers
            ]
            self._plant_queue = new_tiles
            self._pending_count = 0     # consumed

        # --- Filter stale entries ---
        self._plant_queue = [
            (c, r) for c, r in self._plant_queue
            if grid.get(c, r)
            and grid.get(c, r).crop == CROP_NONE
            and (c, r) not in self._growth_timers
        ]

        # --- Done? ---
        if not self._plant_queue:
            self._planting_mode = False
            self._pending_count = 0
            self.state  = "idle"
            self.target = None
            print(f"✅ Farmer finished manual planting ({self._tiles_planted} tiles)")
            return

        # --- Navigate to next tile ---
        next_tile = self._plant_queue[0]

        if (self.col, self.row) == next_tile:
            self._plant_at(grid, *next_tile, self._plant_crop_id)
            self._tiles_planted += 1
            self._plant_queue.pop(0)
            self.moving = False
            return

        if not self.moving or self.replan_cd == 0:
            path, explored = self._find_path_with_animal_avoidance(grid, agents, next_tile)
            if path:
                self.set_path(path, explored)
                self.replan_cd = 60
            else:
                print(f"⚠️ Farmer can't reach plant tile {next_tile}, skipping")
                self._plant_queue.pop(0)

    def _find_path_with_animal_avoidance(self, grid, agents, target):
        def cost_fn(tile):
            from utils.constants import TILE_COST
            base = TILE_COST.get(tile.type, 1.0)
            return _animal_aware_cost(tile, base, agents, animal_avoidance_radius=2)
        result = astar(grid, (self.col, self.row), target, cost_fn)
        return result.path, (result.explored if result.path else None)

    # ── Main update ───────────────────────────────────────────────────────────

    def update(self, grid, agents):
        super().update(grid, agents)
        self.replan_cd = max(0, self.replan_cd - 1)

        if self._failed_plant_timer > 0:
            self._failed_plant_timer -= 1

        self._tick_growth(grid)
        self._harvest(grid)

        # Single-tile plant (G key / button)
        if self._plant_requested and not self._planting_mode:
            self._try_plant_current_tile(grid)
            return

        # Autonomous planting takes priority over harvesting
        if self._planting_mode:
            self._update_planting(grid, agents)
            return

        # ── Harvest mode ──────────────────────────────────────────────────
        if not self.moving or self.replan_cd == 0:
            new_target = self._pick_harvest_target(grid, agents)
            if new_target and new_target != self.target:
                self.target = new_target
                result = astar(grid, (self.col, self.row), self.target, FARMER_COSTS)
                if result.path:
                    self.set_path(result.path, result.explored)
                    self.replan_cd = 90
                    self.state = "moving"
                else:
                    self.state = "no_path"
            elif not new_target:
                self.moving = False
                self.state  = "idle"
            else:
                self.state = "moving"

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface, font=None):
        super().draw(surface, font)

    def draw_failed_plant_indicator(self, surface):
        """Draw red cross on tile where planting failed."""
        import pygame
        if self._failed_plant_timer <= 0 or self._failed_plant_tile is None:
            return

        from utils.helpers import tile_center
        col, row = self._failed_plant_tile
        px, py   = tile_center(col, row)
        box_size = TILE_SIZE - 16
        box_rect = pygame.Rect(px - box_size//2, py - box_size//2, box_size, box_size)

        bg = pygame.Surface((box_rect.width+8, box_rect.height+8), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0,0,0,180),
                         pygame.Rect(0,0,bg.get_width(),bg.get_height()), border_radius=8)
        surface.blit(bg, (box_rect.x-4, box_rect.y-4))

        bc = (220, 40, 40)
        pygame.draw.rect(surface, bc, box_rect, width=3, border_radius=8)
        pygame.draw.line(surface, bc, (box_rect.left+6,  box_rect.top+6),
                                       (box_rect.right-6, box_rect.bottom-6), 4)
        pygame.draw.line(surface, bc, (box_rect.right-6, box_rect.top+6),
                                       (box_rect.left+6,  box_rect.bottom-6), 4)

        hc = (255, 220, 220)
        pygame.draw.line(surface, hc, (box_rect.left+8,  box_rect.top+6),
                                       (box_rect.right-6, box_rect.bottom-8), 2)
        pygame.draw.line(surface, hc, (box_rect.right-6, box_rect.top+6),
                                       (box_rect.left+8,  box_rect.bottom-8), 2)