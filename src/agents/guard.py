"""
src/agents/guard.py - Guard Agent with 4x4 Animation
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan


class Guard(Agent):
    ALERT_RADIUS = 5
    RETURN_RADIUS = 8

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
            scale=2.5,
        )
        self.state = "patrol"
        self.waypoints = []
        self.wp_index = 0
        self.chase_target = None
        self.replan_cd = 0

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
        result = astar(grid, (self.col, self.row), goal, GUARD_COSTS)
        if result.path:
            self.set_path(result.path, result.explored)
            self.moving = True

    def update(self, grid, agents):
        super().update(grid, agents)
        self.replan_cd = max(0, self.replan_cd - 1)
        nearest = self._nearest_animal(agents)

        if nearest:
            dist = manhattan((self.col, self.row), (nearest.col, nearest.row))
            if dist <= self.ALERT_RADIUS:
                self.state = "chase"
                self.chase_target = nearest
            elif self.state == "chase" and dist > self.RETURN_RADIUS:
                self.state = "patrol"
                self.chase_target = None

        if self.state == "chase" and self.chase_target and self.chase_target.alive:
            if self.replan_cd == 0:
                self._plan_to(grid, (self.chase_target.col, self.chase_target.row))
                self.replan_cd = 20
            if (self.col, self.row) == (self.chase_target.col, self.chase_target.row):
                self.chase_target.caught()
                self.state = "patrol"
                self.chase_target = None
                print("Guard caught the animal!")
            return

        self.state = "patrol"
        if not self.waypoints:
            return

        current_goal = self.waypoints[self.wp_index % len(self.waypoints)]
        at_goal = (self.col, self.row) == current_goal

        if at_goal:
            self.wp_index += 1
            current_goal = self.waypoints[self.wp_index % len(self.waypoints)]
            self._plan_to(grid, current_goal)
            self.replan_cd = 30
        elif self.replan_cd == 0:
            self._plan_to(grid, current_goal)
            self.replan_cd = 30
