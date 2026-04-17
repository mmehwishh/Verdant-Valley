"""
src/agents/animal.py - Animal Agent with two types: Bear (destroyer) and Rabbit (eater)
  - Bear: destroys crops entirely (removes them)
  - Rabbit: eats crops (reduces crop_stage by 1)
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan, tile_center


class Animal(Agent):
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

    def caught(self):
        self.alive = False
        self.state = "caught"
        self.moving = False
        print(f"{self.name} was caught!")

    def _is_valid_step(self, tile):
        if tile is None:
            return False
        return ANIMAL_COSTS.get(tile.type, float("inf")) != float("inf")

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
        self.moving = False
        print(f"{self.name} respawned at ({col}, {row})")

    def _plan_wander(self, grid):
        for _ in range(5):
            nc = self.col + random.randint(-3, 3)
            nr = self.row + random.randint(-3, 3)
            nc = max(0, min(grid.cols - 1, nc))
            nr = max(0, min(grid.rows - 1, nr))
            t = grid.get(nc, nr)
            if not self._is_valid_step(t):
                continue

            result = astar(grid, (self.col, self.row), (nc, nr), ANIMAL_COSTS)
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
        tile = grid.get(self.col, self.row)
        if tile and tile.crop != CROP_NONE:
            crop_name = CROP_NAMES[tile.crop]

            if self.animal_type == "rabbit":
                # Rabbit eats: reduces crop stage by 1, doesn't destroy
                if tile.crop_stage > 0:
                    tile.crop_stage -= 1
                    self.crops_eaten += 1
                    self.recent_crop_damage_timer = 8 * FPS
                    self.score += CROP_VALUE[tile.crop]
                    print(f"Rabbit nibbled {crop_name} (stage now {tile.crop_stage})! Score: {self.score}")
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

    def update(self, grid, agents):
        if not self.alive:
            return
        self._ensure_valid_position(grid)
        super().update(grid, agents)
        self.replan_cd = max(0, self.replan_cd - 1)
        self.recent_crop_damage_timer = max(0, self.recent_crop_damage_timer - 1)
        self._eat(grid)

        if not self.moving or self.replan_cd == 0:
            target = self._pick_target(grid, agents)
            if target:
                result = astar(grid, (self.col, self.row), target, ANIMAL_COSTS)
                if result.path:
                    self.set_path(result.path, result.explored)
                    self.replan_cd = 60
                else:
                    self._plan_wander(grid)
                    self.replan_cd = 45
            else:
                self._plan_wander(grid)
                self.replan_cd = 90
