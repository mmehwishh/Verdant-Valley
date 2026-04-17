"""
src/agents/farmer.py - Farmer Agent — full functionality
  - Terrain: walks mud/dirt/grass/field, blocked by water & stone
  - Plant mode: triggered externally via farmer.trigger_planting()
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


# ── Terrain passability ────────────────────────────────────────────────────
# Stone and water are impassable for the farmer.
# This dict is read by your A* cost function — make sure astar() calls
# grid.get(c,r).move_cost and returns float('inf') for impassable tiles.

# Planting score: how desirable is each tile type for planting?
PLANT_TILE_SCORE = {
    TILE_FIELD: 3.0,  # best — purpose-built farmland
    TILE_MUD: 2.0,  # decent
    TILE_DIRT: 1.0,  # okay
}

# Crops cycle through stages 0 (seed) → 1 (sprout) → 2 (ripe)
# Keep both timing profiles so you can switch without losing either behavior.
CROP_GROWTH_TICKS_OLD = {
    CROP_WHEAT: (180, 300),
    CROP_SUNFLOWER: (240, 360),
    CROP_CORN: (200, 320),
    CROP_TOMATO: (220, 340),
    CROP_CARROT: (160, 280),
    CROP_POTATO: (200, 350),
}

CROP_GROWTH_TICKS_NEW = {
    CROP_WHEAT: (900, 1800),
    CROP_SUNFLOWER: (900, 1800),
    CROP_CORN: (900, 1800),
    CROP_TOMATO: (900, 1800),
    CROP_CARROT: (900, 1800),
    CROP_POTATO: (900, 1800),
}

# Switch this between "old" and "new" as needed.
CROP_GROWTH_PROFILE = "old"

if CROP_GROWTH_PROFILE == "new":
    CROP_GROWTH_TICKS = CROP_GROWTH_TICKS_NEW
    DEFAULT_CROP_GROWTH_TICKS = (900, 1800)
else:
    CROP_GROWTH_TICKS = CROP_GROWTH_TICKS_OLD
    DEFAULT_CROP_GROWTH_TICKS = (180, 300)


class Farmer(Agent):
    """
    AI Farmer — harvests ripe crops and plants new ones on command.

    External API:
        farmer.trigger_planting()   — call this from your UI button handler
    """

    def __init__(self, col, row):
        import os
        import pygame

        path = "assets/agents/farmer/Farmer.png"
        frame_w, frame_h = 32, 32
        rows, cols = 10, 6

        if os.path.exists(path):
            try:
                sheet = pygame.image.load(path)
                sw, sh = sheet.get_size()
                cols = max(1, sw // frame_w)
                rows = max(1, sh // frame_h)
                print(f"Farmer sheet: {sw}x{sh}, frames: {cols}x{rows} @ {frame_w}x{frame_h}")
            except Exception:
                pass

        super().__init__(
            col,
            row,
            C_FARMER,
            speed=2.0,
            name="Farmer",
            sprite_sheet_path=path if os.path.exists(path) else None,
            frame_size=(frame_w, frame_h),
            animation_rows=rows,
            animation_cols=cols,
            scale=2,
        )

        # Farmer.png row layout is not the same as 4x4 sheets used by guard/bear.
        # Map movement directions to the walk rows from this sheet.
        self._anim_direction_rows = {
            "down": 0,
            "up": 2 if rows > 2 else 0,
            "left": 4 if rows > 4 else 0,
            "right": 3 if rows > 3 else 0,
        }

        if self.animation:
            self.animation.animation_speed = 0.15

        self.target = None
        self.replan_cd = 0
        self.harvest_count = 0
        self.plant_count = 0

        # Planting mode — set True by trigger_planting(), cleared after done
        self._plant_requested = False
        self._planting_mode = False
        self._plant_queue = []  # list of (col, row) tiles to plant

        # Growth timers: {(col, row): ticks_at_current_stage}
        self._growth_timers: dict[tuple, int] = {}
        
        # Failed planting indicator - shows red cross when planting fails
        self._failed_plant_tile = None
        self._failed_plant_timer = 0  # ticks to show indicator (60 ticks = 1 second)

    # ── Public API ────────────────────────────────────────────────────────────

    def trigger_planting(self):
        """Call from your UI 'Plant Crops' button handler."""
        if self._planting_mode:
            return
        self._plant_requested = True
        print("🌱 Farmer: planting requested")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _tile_passable(self, tile) -> bool:
        """True if the farmer can walk on this tile type."""
        return tile is not None and FARMER_COSTS.get(tile.type, 1.0) != float('inf')

    def _pick_harvest_target(self, grid, agents):
        """Highest-utility ripe (stage=2) crop, weighted by value/distance, avoiding animals."""
        best_score = -1
        best_tile = None

        # Get list of active animals
        animals = [a for a in agents if hasattr(a, 'name') and 'Animal' in a.name and a.alive]

        for c, r in grid.crop_tiles():
            tile = grid.get(c, r)
            if tile is None or tile.crop == CROP_NONE or tile.crop_stage < 2:
                continue
            if not self._tile_passable(tile):
                continue

            value = CROP_VALUE[tile.crop]
            dist = manhattan((self.col, self.row), (c, r)) + 1

            # Calculate animal avoidance penalty
            animal_penalty = 0
            min_animal_dist = float('inf')
            for animal in animals:
                animal_dist = manhattan((c, r), (animal.col, animal.row))
                min_animal_dist = min(min_animal_dist, animal_dist)

                # Extra penalty for being near the bear (destructive animal)
                if hasattr(animal, 'name') and 'Bear' in animal.name:
                    if animal_dist <= 3:  # Bear within 3 tiles
                        animal_penalty += 50  # Heavy penalty
                    elif animal_dist <= 5:  # Bear within 5 tiles
                        animal_penalty += 20  # Moderate penalty

            # General animal avoidance
            if min_animal_dist <= 2:
                animal_penalty += 30  # High penalty for any animal within 2 tiles
            elif min_animal_dist <= 4:
                animal_penalty += 10  # Moderate penalty for any animal within 4 tiles

            score = (value * tile.crop_stage) / dist - animal_penalty

            if score > best_score:
                best_score = score
                best_tile = (c, r)
        return best_tile

    def _pick_plant_tiles(self, grid, agents) -> list[tuple[int, int]]:
        """
        Find plantable tiles sorted by desirability score:
          - tile must be TILE_FIELD / MUD / DIRT
          - no existing crop
          - must be reachable (A* sanity check skipped here — done at path time)
          - bonus for being adjacent to a water tile
          - avoid planting near animals
        Returns all candidates sorted by desirability.
        """
        candidates = []

        # Get list of active animals
        animals = [a for a in agents if hasattr(a, 'name') and 'Animal' in a.name and a.alive]

        for c in range(grid.cols):
            for r in range(grid.rows):
                tile = grid.get(c, r)
                if tile is None:
                    continue
                if tile.type not in PLANT_TILE_SCORE:
                    continue
                if tile.crop != CROP_NONE:
                    continue  # already has a crop
                if (c, r) in self._growth_timers:
                    continue  # seed planted, waiting to emerge

                base = PLANT_TILE_SCORE[tile.type]

                # Water adjacency bonus
                water_bonus = 0.0
                for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nb = grid.get(c + dc, r + dr)
                    if nb and nb.type == TILE_WATER:
                        water_bonus = 1.5
                        break

                # Animal avoidance penalty
                animal_penalty = 0
                for animal in animals:
                    animal_dist = manhattan((c, r), (animal.col, animal.row))
                    if animal_dist <= 3:  # Avoid planting within 3 tiles of any animal
                        animal_penalty = 2.0  # Heavy penalty
                        break
                    elif animal_dist <= 5:  # Moderate penalty within 5 tiles
                        animal_penalty = 1.0

                dist = manhattan((self.col, self.row), (c, r)) + 1
                score = (base + water_bonus) / dist - animal_penalty
                candidates.append((score, c, r))

        candidates.sort(reverse=True)
        return [(c, r) for _, c, r in candidates]

    def _choose_crop_for_tile(self, grid, c, r) -> int:
        """Pick the best crop for this tile (field → sunflower, mud → corn, dirt → wheat)."""
        tile = grid.get(c, r)
        if tile.type == TILE_FIELD:
            return CROP_SUNFLOWER  # highest value on good soil
        if tile.type == TILE_MUD:
            return CROP_CORN
        return CROP_WHEAT

    def _plant_at(self, grid, c, r, crop=None):
        """Actually plant a seed on tile (c, r)."""
        tile = grid.get(c, r)
        if tile is None or tile.type not in PLANT_TILE_SCORE:
            return
        if crop is None:
            crop = self._choose_crop_for_tile(grid, c, r)
        tile.crop = crop
        tile.crop_stage = 0  # stage 0 = seed / just planted
        tile.managed_growth = True
        self._growth_timers[(c, r)] = 0
        self.plant_count += 1
        print(f"🌱 Farmer planted {CROP_NAMES[crop]} at ({c},{r})")

    def _harvest(self, grid):
        """Harvest ripe crop at current tile, if any."""
        tile = grid.get(self.col, self.row)
        if tile and tile.crop != CROP_NONE and tile.crop_stage >= 2:
            crop_name = CROP_NAMES[tile.crop]
            value = 10
            self.score += value
            self.harvest_count += 1
            print(f"🌾 Farmer harvested {crop_name}! +{value}  total={self.score}")
            tile.crop = CROP_NONE
            tile.crop_stage = 0
            tile.managed_growth = False
            self._growth_timers.pop((self.col, self.row), None)
            self.target = None
            self.state = "harvesting"

    def _tick_growth(self, grid):
        """Advance crop growth timers for all planted tiles."""
        done = []
        for (c, r), ticks in self._growth_timers.items():
            tile = grid.get(c, r)
            if tile is None or tile.crop == CROP_NONE:
                if tile is not None:
                    tile.managed_growth = False
                done.append((c, r))
                continue
            ticks += 1
            self._growth_timers[(c, r)] = ticks

            grow = CROP_GROWTH_TICKS.get(tile.crop, DEFAULT_CROP_GROWTH_TICKS)
            if tile.crop_stage == 0 and ticks >= grow[0]:
                tile.crop_stage = 1
                print(f"🌿 Crop sprouted at ({c},{r})")
            elif tile.crop_stage == 1 and ticks >= grow[1]:
                tile.crop_stage = 2
                tile.managed_growth = False
                print(f"🌻 Crop ripe at ({c},{r})!")
                done.append((c, r))  # stop tracking once ripe

        for key in done:
            self._growth_timers.pop(key, None)

    # ── Planting flow ─────────────────────────────────────────────────────────

    def _try_plant_current_tile(self, grid):
        """Try to plant a seed on the tile the farmer is currently standing on."""
        self._plant_requested = False
        
        tile = grid.get(self.col, self.row)
        if tile is None:
            print("🌱 Farmer: no tile here to plant on")
            self._show_failed_plant()
            return
            
        if tile.type not in PLANT_TILE_SCORE:
            print(f"🌱 Farmer: cannot plant on {tile.type} tile")
            self._show_failed_plant()
            return
            
        if tile.crop != CROP_NONE:
            print("🌱 Farmer: tile already has a crop")
            self._show_failed_plant()
            return
            
        if (self.col, self.row) in self._growth_timers:
            print("🌱 Farmer: tile already growing something")
            self._show_failed_plant()
            return
            
        # Plant a random crop on this tile
        crop = random.choice([CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_TOMATO, CROP_CARROT, CROP_POTATO])
        self._plant_at(grid, self.col, self.row, crop)
        print(f"🌱 Farmer planted {CROP_NAMES[crop]} at ({self.col},{self.row})")
    
    def _show_failed_plant(self, tile_pos=None):
        """Mark this tile as failed plant attempt (shows red cross for 1 second)."""
        self._failed_plant_tile = tile_pos if tile_pos is not None else (self.col, self.row)
        self._failed_plant_timer = 60  # Show for 60 ticks at 60fps = 1 second

    def _update_planting(self, grid, agents):
        """Navigate to the next tile in the plant queue and plant it."""
        self._plant_queue = [
            (c, r)
            for c, r in self._plant_queue
            if grid.get(c, r)
            and grid.get(c, r).crop == CROP_NONE
            and (c, r) not in self._growth_timers
        ]

        if not self._plant_queue:
            self._planting_mode = False
            self.target = None
            self.state = "idle"
            print("✅ Farmer finished planting")
            return

        next_tile = self._plant_queue[0]
        next_tile_obj = grid.get(*next_tile)
        if next_tile_obj is None or next_tile_obj.type not in PLANT_TILE_SCORE:
            self._show_failed_plant(next_tile)
            self._plant_queue.pop(0)
            return

        if (self.col, self.row) == next_tile:
            self._plant_at(grid, *next_tile)
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
                self._show_failed_plant(next_tile)
                self._plant_queue.pop(0)
            return

    def _find_path_with_animal_avoidance(self, grid, agents, target):
        """Find path to target, avoiding tiles near animals."""
        def cost_with_animal_avoidance(tile):
            base = FARMER_COSTS.get(tile.type, 1.0)
            return _animal_aware_cost(tile, base, agents, animal_avoidance_radius=2)

        result = astar(grid, (self.col, self.row), target, cost_with_animal_avoidance)
        return result.path, result.explored if result.path else None

    # ── Main update ───────────────────────────────────────────────────────────

    def update(self, grid, agents):
        super().update(grid, agents)
        self.replan_cd = max(0, self.replan_cd - 1)
        
        # Update failed plant timer
        if self._failed_plant_timer > 0:
            self._failed_plant_timer -= 1

        # Always tick growth, harvest if standing on ripe crop
        self._tick_growth(grid)
        self._harvest(grid)

        # Start planting mode only when explicitly requested by the player.
        if self._plant_requested and not self._planting_mode:
            self._plant_requested = False
            self._plant_queue = self._pick_plant_tiles(grid, agents)

            if self._plant_queue:
                self._planting_mode = True
                self.state = "planting"
                self.target = None
                self.path = []
                self.path_idx = 0
                self.moving = False
                self.replan_cd = 0
            else:
                self._try_plant_current_tile(grid)
                return

        # Planting mode takes priority over harvesting
        if self._planting_mode:
            self._update_planting(grid, agents)
            return

        # ── Harvest mode ──────────────────────────────────────────────────
        if not self.moving or self.replan_cd == 0:
            new_target = self._pick_harvest_target(grid, agents)

            if new_target and new_target != self.target:
                self.target = new_target
                path, explored = self._find_path_with_animal_avoidance(grid, agents, self.target)
                if path:
                    self.set_path(path, explored)
                    self.replan_cd = 90
                    self.state = "moving"
                else:
                    self.state = "no_path"

            elif not new_target:
                self.moving = False
                self.state = "idle"
            else:
                self.state = "moving"

    def update_animation_direction(self):
        """Use farmer-specific direction rows from Farmer.png."""
        if not self.animation:
            return

        dx = self.col - self.last_pos[0]
        dy = self.row - self.last_pos[1]

        if dx > 0:
            self.animation.set_direction(self._anim_direction_rows["right"])
        elif dx < 0:
            self.animation.set_direction(self._anim_direction_rows["left"])
        elif dy > 0:
            self.animation.set_direction(self._anim_direction_rows["down"])
        elif dy < 0:
            self.animation.set_direction(self._anim_direction_rows["up"])

        self.last_pos = (self.col, self.row)

        if self.moving:
            self.animation.update()
        else:
            self.animation.current_frame = 0
            self.animation.animation_timer = 0

    def draw(self, surface, font=None):
        """Draw farmer and show red cross on failed plant attempt."""
        super().draw(surface, font)
    
    def draw_failed_plant_indicator(self, surface):
        """Draw red cross on tile where planting failed (separate from farmer sprite)."""
        if self._failed_plant_timer > 0 and self._failed_plant_tile is not None:
            from utils.helpers import grid_to_px, tile_center

            col, row = self._failed_plant_tile
            px, py = tile_center(col, row)
            tile_x, tile_y = grid_to_px(col, row)

            # Use a cross sized to the tile box, with a clear red border
            box_size = TILE_SIZE - 16
            box_rect = pygame.Rect(
                px - box_size // 2,
                py - box_size // 2,
                box_size,
                box_size,
            )

            # Dark translucent background for contrast
            bg = pygame.Surface((box_rect.width + 8, box_rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(
                bg,
                (0, 0, 0, 180),
                pygame.Rect(0, 0, bg.get_width(), bg.get_height()),
                border_radius=8,
            )
            surface.blit(bg, (box_rect.x - 4, box_rect.y - 4))

            # Red outline and cross lines
            border_color = (220, 40, 40)
            pygame.draw.rect(surface, border_color, box_rect, width=3, border_radius=8)
            pygame.draw.line(
                surface,
                border_color,
                (box_rect.left + 6, box_rect.top + 6),
                (box_rect.right - 6, box_rect.bottom - 6),
                4,
            )
            pygame.draw.line(
                surface,
                border_color,
                (box_rect.right - 6, box_rect.top + 6),
                (box_rect.left + 6, box_rect.bottom - 6),
                4,
            )

            # White inner highlight for crispness
            highlight_color = (255, 220, 220)
            pygame.draw.line(
                surface,
                highlight_color,
                (box_rect.left + 8, box_rect.top + 6),
                (box_rect.right - 6, box_rect.bottom - 8),
                2,
            )
            pygame.draw.line(
                surface,
                highlight_color,
                (box_rect.right - 6, box_rect.top + 6),
                (box_rect.left + 8, box_rect.bottom - 8),
                2,
            )
