"""
src/agents/animal.py - Animal Agent (Bear) with 4x4 Animation
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan


class Animal(Agent):
    def __init__(self, col, row):
        # Auto-detect frame size
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
            col,
            row,
            C_ANIMAL,
            speed=1.5,
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

    def caught(self):
        self.alive = False
        self.state = "caught"
        self.moving = False
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
        self.moving = False
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
        tile = grid.get(self.col, self.row)
        if tile and tile.crop != CROP_NONE:
            self.crops_eaten += 1
            self.score += CROP_VALUE[tile.crop] * tile.crop_stage
            print(f"Bear ate {CROP_NAMES[tile.crop]}! Score: {self.score}")
            tile.crop = CROP_NONE
            tile.crop_stage = 0

    def update(self, grid, agents):
        if not self.alive:
            return
        super().update(grid, agents)
        self.replan_cd = max(0, self.replan_cd - 1)
        self._eat(grid)

        if not self.moving or self.replan_cd == 0:
            target = self._pick_target(grid, agents)
            if target:
                result = astar(grid, (self.col, self.row), target, ANIMAL_COSTS)
                if result.path:
                    self.set_path(result.path, result.explored)
                    self.replan_cd = 60
            else:
                for _ in range(5):
                    nc = self.col + random.randint(-3, 3)
                    nr = self.row + random.randint(-3, 3)
                    nc = max(0, min(grid.cols - 1, nc))
                    nr = max(0, min(grid.rows - 1, nr))
                    t = grid.get(nc, nr)
                    if t and t.walkable:
                        result = astar(grid, (self.col, self.row), (nc, nr), ANIMAL_COSTS)
                        if result.path:
                            self.set_path(result.path)
                            break
                self.replan_cd = 90
