"""
src/agents/animal.py - Animal Agent with two types: Bear (destroyer) and Rabbit (eater)
  - Bear: destroys crops entirely (removes them)
  - Rabbit: eats crops (reduces crop_stage by 1)
  - Includes fleeing, wandering and stamina mechanics
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan, tile_center


class Animal(Agent):
    FLEE_DISTANCE = 5  # Distance to start fleeing from guard
    STAMINA_MAX = 100
    STAMINA_DRAIN = 0.5  # Less drain for animal

    def __init__(self, col, row, animal_type="bear"):
        # Auto-detect frame size
        import os
        import pygame

        self.animal_type = animal_type

        if animal_type == "rabbit":
            path = "assets/agents/animal/rabbit.png"
            name = "Rabbit"
            color = (180, 140, 220)  # light purple for rabbit
            speed = 1.8
        else:
            path = "assets/agents/animal/bear.png"
            name = "Bear"
            color = C_ANIMAL
            speed = 1.5

        frame_w, frame_h = 16, 16

        if os.path.exists(path):
            img = pygame.image.load(path)
            w, h = img.get_size()
            frame_w = w // 4
            frame_h = h // 4
            print(f"✅ {name} sheet: {w}x{h}, frames: {frame_w}x{frame_h}")
        else:
            print(f"⚠️ {name} sheet not found at: {path}, will use fallback")
            path = None

        super().__init__(
            col,
            row,
            color,
            speed=speed,
            name=name,
            sprite_sheet_path=path,
            frame_size=(frame_w, frame_h),
            animation_rows=4,
            animation_cols=4,
            scale=2,
        )
        self.alive = True
        self.crops_eaten = 0
        self.recent_crop_damage_timer = 0
        self.replan_cd = 0
        self.w_crop_value = 1.0
        self.w_guard_avoid = 1.5 if animal_type == "bear" else 1.0
        self._ate_this_tile = False
        self.state = "hungry"  # hungry, scared, wandering
        self.stamina = self.STAMINA_MAX
        self.original_color = color

    def get_color(self):
        if self.state == "scared":
            return (255, 0, 0)  # Red when scared
        elif self.state == "wandering":
            return (128, 128, 128)  # Gray when wandering
        return self.original_color

    def draw(self, surface, font=None):
        # Add shaking effect when scared
        offset_x, offset_y = 0, 0
        if self.state == "scared":
            import random
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)

        # Temporarily adjust position for drawing
        original_x, original_y = self.x, self.y
        self.x += offset_x
        self.y += offset_y

        super().draw(surface, font)

        # Restore position
        self.x, self.y = original_x, original_y

        if self.state == "scared" and font:
            scared_text = font.render("Scared!", True, (255, 0, 0))
            surface.blit(
                scared_text,
                (int(self.x) - scared_text.get_width() // 2, int(self.y) - TILE_SIZE // 2 - 32),
            )

    def caught(self):
        self.alive = False
        self.state = "caught"
        self.moving = False
        self.path = []
        print(f"{self.name} was caught!")

    def _is_valid_step(self, tile):
        if tile is None:
            return False
        return ANIMAL_COSTS.get(tile.type, float("inf")) != float("inf")

    def _can_step(self, grid, col, row):
        """Override: animal cannot step on water, stone, snow_stone."""
        return self._is_valid_step(grid.get(col, row))

    def _nearest_valid_tile(self, grid, col, row):
        start = grid.get(col, row)
        if self._is_valid_step(start):
            return col, row

        for radius in range(1, 6):
            for dc in range(-radius, radius + 1):
                for dr in range(-radius, radius + 1):
                    if abs(dc) + abs(dr) != radius:
                        continue
                    nc = max(0, min(grid.cols - 1, col + dc))
                    nr = max(0, min(grid.rows - 1, row + dr))
                    if self._is_valid_step(grid.get(nc, nr)):
                        return nc, nr

        return col, row

    def respawn(self, col, row, grid=None):
        if grid is not None:
            col, row = self._nearest_valid_tile(grid, col, row)

        self.alive = True
        self.col = col
        self.row = row
        self.crops_eaten = 0
        self.recent_crop_damage_timer = 0
        from utils.helpers import tile_center
        cx, cy = tile_center(col, row)
        self.x = float(cx)
        self.y = float(cy)
        self.state = "idle"
        self.path = []
        self.path_idx = 0
        self.moving = False
        self._ate_this_tile = False
        self.replan_cd = 0
        print(f"{self.name} respawned at ({col}, {row})")

    def _plan_wander(self, grid):
        """Wander using _is_valid_step"""
        for _ in range(5):
            nc = self.col + random.randint(-3, 3)
            nr = self.row + random.randint(-3, 3)
            nc = max(0, min(grid.cols - 1, nc))
            nr = max(0, min(grid.rows - 1, nr))
            t = grid.get(nc, nr)
            if not self._is_valid_step(t):
                continue

            result = astar(grid, (self.col, self.row), (nc, nr), cost_dict=ANIMAL_COSTS, agent_type="Animal", rain_active=False)
            if result.path:
                self.set_path(result.path)
                return True

        return False

    def _ensure_valid_position(self, grid):
        current_tile = grid.get(self.col, self.row)
        if self._is_valid_step(current_tile):
            return

        nc, nr = self._nearest_valid_tile(grid, self.col, self.row)
        self.col, self.row = nc, nr
        cx, cy = tile_center(self.col, self.row)
        self.x = float(cx)
        self.y = float(cy)
        self.path = []
        self.path_idx = 0
        self.moving = False

    def _pick_target(self, grid, agents):
        guard = next((a for a in agents if a.__class__.__name__ == "Guard"), None)

        best_score = -1
        best_tile = None

        for c, r in grid.crop_tiles():
            tile = grid.get(c, r)
            if tile is None or tile.crop == CROP_NONE:
                continue
            value = CROP_VALUE[tile.crop] * self.w_crop_value
            dist = manhattan((self.col, self.row), (c, r)) + 1

            guard_penalty = 0
            if guard:
                gd = manhattan((c, r), (guard.col, guard.row)) + 1
                guard_penalty = self.w_guard_avoid * (10 / gd)

            score = (value / dist) - guard_penalty
            if score > best_score:
                best_score = score
                best_tile = (c, r)

        return best_tile

    def _eat(self, grid):
        """Eat only when fully arrived at tile (not mid-movement)."""
        if self.moving:
            return
        tile = grid.get(self.col, self.row)
        if tile and tile.crop != CROP_NONE:
            crop_name = CROP_NAMES[tile.crop]

            if not self._ate_this_tile:
                if self.animal_type == "rabbit":
                    # Rabbit eats: reduces crop stage by 1, doesn't destroy
                    if tile.crop_stage > 0:
                        tile.crop_stage -= 1
                        self.crops_eaten += 1
                        self.recent_crop_damage_timer = 8 * FPS
                        self.score += CROP_VALUE[tile.crop]
                        print(f"Rabbit nibbled {crop_name} (stage now {tile.crop_stage})! Score: {self.score}")
                        self._ate_this_tile = True
                        if tile.crop_stage <= 0:
                            tile.crop = CROP_NONE
                            tile.crop_stage = 0
                            print(f"Rabbit fully consumed {crop_name}!")
                else:
                    # Bear destroys: removes crop entirely
                    self.crops_eaten += 1
                    self.recent_crop_damage_timer = 8 * FPS
                    self.score += CROP_VALUE[tile.crop] * max(1, tile.crop_stage)
                    print(f"Bear destroyed {crop_name}! Score: {self.score}")
                    tile.crop = CROP_NONE
                    tile.crop_stage = 0
                    self._ate_this_tile = True
        else:
            self._ate_this_tile = False

    def _wander(self, grid):
        """Move to a random nearby tile that the animal can traverse, within farming boundaries."""
        min_col, max_col = 4, 13
        min_row, max_row = 2, 11
        for _ in range(15):
            nc = self.col + random.randint(-4, 4)
            nr = self.row + random.randint(-4, 4)
            nc = max(min_col, min(max_col, nc))
            nr = max(min_row, min(max_row, nr))
            t = grid.get(nc, nr)
            if not self._is_valid_step(t):
                continue
            if (nc, nr) != (self.col, self.row):
                result = astar(grid, (self.col, self.row), (nc, nr), cost_dict=ANIMAL_COSTS, agent_type="Animal", rain_active=False)
                if result.path:
                    self.set_path(result.path, result.explored)
                    return True
        return False

    def _flee_from_guard(self, grid, guard):
        """Move away from the guard, within farming boundaries."""
        if not guard:
            return
        min_col, max_col = 4, 13
        min_row, max_row = 2, 11
        # Find direction away from guard
        dx = self.col - guard.col
        dy = self.row - guard.row
        # Normalize and extend
        dist = max(1, abs(dx) + abs(dy))
        target_col = self.col + int(dx / dist * 5)
        target_row = self.row + int(dy / dist * 5)
        # Clamp to farming grid
        target_col = max(min_col, min(max_col, target_col))
        target_row = max(min_row, min(max_row, target_row))
        # Try to path to that tile
        result = astar(grid, (self.col, self.row), (target_col, target_row), cost_dict=ANIMAL_COSTS, agent_type="Animal", rain_active=False)
        if result.path:
            self.set_path(result.path, result.explored)
        else:
            # Fallback to wander
            self._wander(grid)

    def update(self, grid, agents, season_mgr=None):
        if not self.alive:
            return
        self._ensure_valid_position(grid)
        super().update(grid, agents, season_mgr)
        self.replan_cd = max(0, self.replan_cd - 1)
        self.recent_crop_damage_timer = max(0, self.recent_crop_damage_timer - 1)

        # Update color based on state
        self.color = self.get_color()
        self._eat(grid)

        # Check for guard proximity
        guard = next((a for a in agents if a.__class__.__name__ == "Guard"), None)
        if guard:
            dist_to_guard = manhattan((self.col, self.row), (guard.col, guard.row))
            if dist_to_guard <= self.FLEE_DISTANCE:
                self.state = "scared"
                self.stamina = max(0, self.stamina - self.STAMINA_DRAIN)
                if self.stamina == 0:
                    self.speed = 1.0  # Slow down when tired
                else:
                    self.speed = 2.2  # Speed up when scared
            else:
                self.state = "hungry"
                self.stamina = min(self.STAMINA_MAX, self.stamina + 1)  # Recover
                self.speed = 1.7

        # Only replan when not moving OR cooldown expired
        if self.moving:
            return

        # Reset eat flag when starting a new move
        self._ate_this_tile = False

        if self.replan_cd > 0:
            return

        if self.state == "scared":
            # Flee from guard
            self._flee_from_guard(grid, guard)
            self.replan_cd = 5  # More frequent when scared
        elif self.state == "hungry":
            target = self._pick_target(grid, agents)
            if target:
                result = astar(grid, (self.col, self.row), target, cost_dict=ANIMAL_COSTS, agent_type="Animal", rain_active=False)
                if result.path:
                    self.set_path(result.path, result.explored)
                    self.replan_cd = 60
                else:
                    self.state = "wandering"
                    self._plan_wander(grid)
                    self.replan_cd = 45
            else:
                self.state = "wandering"
                self._plan_wander(grid)
                self.replan_cd = 90
        else:  # wandering
            self._plan_wander(grid)
            self.replan_cd = 45
