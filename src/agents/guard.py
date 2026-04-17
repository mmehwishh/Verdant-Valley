"""
src/agents/guard.py - Guard Agent with 4x4 Animation
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan, tile_center


class Guard(Agent):
    ALERT_RADIUS = 8
    RETURN_RADIUS = 12

    def __init__(self, col, row):
        # Auto-detect frame size
        import os
        import pygame

        path = "assets/agents/guard/guard.png"
        frame_w, frame_h = 16, 16

        if os.path.exists(path):
            img = pygame.image.load(path)
            w, h = img.get_size()
            frame_w = w // 4
            frame_h = h // 4
            print(f"✅ Guard sheet: {w}x{h}, frames: {frame_w}x{frame_h}")
        else:
            print(f"⚠️ Guard sheet not found at: {path}")

        super().__init__(
            col,
            row,
            C_GUARD,
            speed=1.8,
            name="Guard",
            sprite_sheet_path=path if os.path.exists(path) else None,
            frame_size=(frame_w, frame_h),
            animation_rows=4,
            animation_cols=4,
            scale=2,
        )
        self.state = "patrol"
        self.waypoints = []
        self.wp_index = 0
        self.chase_target = None
        self.replan_cd = 0
        self._stuck_ticks = 0
        self._last_pos = (col, row)

    def set_waypoints(self, waypoints):
        self.waypoints = waypoints
        self.wp_index = 0

    def _nearest_animal(self, agents):
        animals = [a for a in agents if a.__class__.__name__ == "Animal" and a.alive]
        if not animals:
            return None
        return min(
            animals, key=lambda a: manhattan((self.col, self.row), (a.col, a.row))
        )

    def _plan_to(self, grid, goal):
        goal = self._resolve_goal(grid, goal)
        if goal is None:
            return False

        result = astar(grid, (self.col, self.row), goal, self._move_cost)
        if result.path:
            self.set_path(result.path, result.explored)
            self.moving = True
            return True
        return False

    def _is_valid_step(self, tile):
        if tile is None:
            return False
        return GUARD_COSTS.get(tile.type, float("inf")) != float("inf")

    def _move_cost(self, tile):
        if not self._is_valid_step(tile):
            return float("inf")
        cost = GUARD_COSTS.get(tile.type, 1.0)
        # Small penalty for walking on crop tiles, but never block them
        if tile.crop != CROP_NONE:
            cost += 1.5
        return cost

    def _resolve_goal(self, grid, goal):
        """If goal tile is blocked, pick the nearest walkable alternative."""
        gc, gr = goal
        t = grid.get(gc, gr)
        if self._is_valid_step(t):
            return goal

        for radius in range(1, 5):
            for dc in range(-radius, radius + 1):
                for dr in range(-radius, radius + 1):
                    if abs(dc) + abs(dr) != radius:
                        continue
                    nc, nr = gc + dc, gr + dr
                    n = grid.get(nc, nr)
                    if self._is_valid_step(n):
                        return (nc, nr)

        return None

    def _ensure_valid_position(self, grid):
        current_tile = grid.get(self.col, self.row)
        if self._is_valid_step(current_tile):
            return

        fallback = self._resolve_goal(grid, (self.col, self.row))
        if fallback is None:
            return

        self.col, self.row = fallback
        cx, cy = tile_center(self.col, self.row)
        self.x = float(cx)
        self.y = float(cy)
        self.path = []
        self.path_idx = 0
        self.moving = False

    def ensure_valid_position(self, grid):
        self._ensure_valid_position(grid)

    def update(self, grid, agents):
        self._ensure_valid_position(grid)
        super().update(grid, agents)
        self.replan_cd = max(0, self.replan_cd - 1)

        # Stuck detection: if position hasn't changed for 60 ticks, force replan
        if (self.col, self.row) == self._last_pos:
            self._stuck_ticks += 1
        else:
            self._stuck_ticks = 0
            self._last_pos = (self.col, self.row)

        nearest = self._nearest_animal(agents)

        if nearest:
            dist = manhattan((self.col, self.row), (nearest.col, nearest.row))
            crop_damage = getattr(nearest, "recent_crop_damage_timer", 0) > 0
            crop_alert_radius = self.RETURN_RADIUS + 4
            if dist <= self.ALERT_RADIUS or (crop_damage and dist <= crop_alert_radius):
                self.state = "chase"
                self.chase_target = nearest
            elif self.state == "chase" and dist > self.RETURN_RADIUS and not crop_damage:
                self.state = "patrol"
                self.chase_target = None

        if self.state == "chase" and self.chase_target and self.chase_target.alive:
            # Immediate catch check — always runs, even mid-path
            if manhattan((self.col, self.row), (self.chase_target.col, self.chase_target.row)) <= 1:
                self.chase_target.caught()
                self.score += 10
                self.state = "patrol"
                self.chase_target = None
                self._stuck_ticks = 0
                print(f"Guard caught the animal! +10  total={self.score}")
                return

            force_replan = self._stuck_ticks >= 60
            if force_replan:
                self._stuck_ticks = 0
                self.path = []
                self.path_idx = 0
                self.moving = False
                self.replan_cd = 0

            should_replan = (
                self.replan_cd == 0
                and (
                    not self.moving
                    or not self.path
                    or self.path_idx >= max(0, len(self.path) - 2)
                    or force_replan
                )
            )
            if should_replan:
                planned = self._plan_to(
                    grid, (self.chase_target.col, self.chase_target.row)
                )
                self.replan_cd = 24 if planned else 12
            return

        self.state = "patrol"
        if not self.waypoints:
            return

        current_goal = self.waypoints[self.wp_index % len(self.waypoints)]
        at_goal = (self.col, self.row) == current_goal

        if at_goal:
            self.wp_index += 1
            current_goal = self.waypoints[self.wp_index % len(self.waypoints)]
            planned = self._plan_to(grid, current_goal)
            self.replan_cd = 30 if planned else 10
        elif self.replan_cd == 0 and (
            not self.moving or not self.path or self.path_idx >= max(0, len(self.path) - 1)
        ):
            planned = self._plan_to(grid, current_goal)
            if planned:
                self.replan_cd = 30
            else:
                self.wp_index += 1
                self.replan_cd = 10
