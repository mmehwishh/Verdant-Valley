"""
src/agents/animal.py - Animal Agent (Bear)
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan


class Animal(Agent):
    FLEE_DISTANCE = 5  # Distance to start fleeing from guard
    STAMINA_MAX = 100
    STAMINA_DRAIN = 0.5  # Less drain for animal

    def __init__(self, col, row):
        import os
        import pygame

        path = "assets/agents/animal/bear.png"
        frame_w, frame_h = 16, 16

        if os.path.exists(path):
            img = pygame.image.load(path)
            w, h = img.get_size()
            frame_w = w // 4
            frame_h = h // 4
            print(f"✅ Bear sheet: {w}x{h}, frames: {frame_w}x{frame_h}")
        else:
            print(f"⚠️ Bear sheet not found at: {path}")

        super().__init__(
            col, row, C_ANIMAL,
            speed=1.7,
            name="Bear",
            sprite_sheet_path=path if os.path.exists(path) else None,
            frame_size=(frame_w, frame_h),
            animation_rows=4,
            animation_cols=4,
            scale=2.5,
        )
        self.alive = True
        self.crops_eaten = 0
        self.replan_cd = 0
        self.w_crop_value = 1.0
        self.w_guard_avoid = 1.5
        self._ate_this_tile = False
        self.state = "hungry"  # hungry, scared, wandering
        self.stamina = self.STAMINA_MAX

    def get_color(self):
        if self.state == "scared":
            return (255, 0, 0)  # Red when scared
        elif self.state == "wandering":
            return (128, 128, 128)  # Gray when wandering
        return C_ANIMAL  # Default brown

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
        print("Bear was caught!")

    def respawn(self, col, row):
        self.alive = True
        self.col = col
        self.row = row
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
        print(f"Bear respawned at ({col}, {row})")

    def _pick_target(self, grid, agents):
        guard = next((a for a in agents if a.__class__.__name__ == "Guard"), None)

        best_score = -1
        best_tile = None

        for c, r in grid.crop_tiles():
            tile = grid.get(c, r)
            if tile.crop_stage < 1:
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
        if tile and tile.crop != CROP_NONE and tile.crop_stage > 0:
            if not self._ate_this_tile:
                self.crops_eaten += 1
                self.score += CROP_VALUE[tile.crop] * tile.crop_stage
                print(f"Bear ate {CROP_NAMES[tile.crop]}! Score: {self.score}")
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
            if (
                t
                and ANIMAL_COSTS.get(t.type, float('inf')) < float('inf')
                and (nc, nr) != (self.col, self.row)
            ):
                result = astar(grid, (self.col, self.row), (nc, nr), ANIMAL_COSTS)
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
        result = astar(grid, (self.col, self.row), (target_col, target_row), ANIMAL_COSTS)
        if result.path:
            self.set_path(result.path, result.explored)
        else:
            # Fallback to wander
            self._wander(grid)

    def update(self, grid, agents):
        if not self.alive:
            return

        super().update(grid, agents)
        self.replan_cd = max(0, self.replan_cd - 1)

        # Update color based on state
        self.color = self.get_color()

        # Eat only when stationary on a crop tile
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
                result = astar(grid, (self.col, self.row), target, ANIMAL_COSTS)
                if result.path:
                    self.set_path(result.path, result.explored)
                    self.replan_cd = 10
                    return
            # No crops or A* failed — wander
            self.state = "wandering"
            self._wander(grid)
            self.replan_cd = 20
        else:  # wandering
            self._wander(grid)
            self.replan_cd = 20