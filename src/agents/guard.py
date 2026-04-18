"""
src/agents/guard.py - Guard Agent
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan


class Guard(Agent):
    ALERT_RADIUS = 10
    RETURN_RADIUS = 15
    CHASE_REPLAN_FRAMES = 5  # More frequent replanning
    PATROL_REPLAN_FRAMES = 30
    GIVE_UP_TIME = 30 * 60  # 30 seconds at 60 FPS
    STAMINA_MAX = 100
    STAMINA_DRAIN = 1  # Per frame during chase
    STAMINA_RECOVER = 2  # Per frame during patrol

    def __init__(self, col, row):
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
            col, row, C_GUARD,
            speed=2.2,
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
        self.chase_start_time = 0
        self.stamina = self.STAMINA_MAX

    def get_color(self):
        if self.state == "chase":
            if self.stamina < self.STAMINA_MAX // 2:
                return (255, 100, 100)  # Red when tired
            return (255, 165, 0)  # Orange when chasing
        elif self.state == "alert":
            return (255, 255, 0)  # Yellow when alert
        return C_GUARD  # Default blue

    def set_waypoints(self, waypoints):
        self.waypoints = waypoints
        self.wp_index = 0

    def _nearest_animal(self, agents):
        animals = [a for a in agents if a.__class__.__name__ == "Animal" and a.alive]
        if not animals:
            return None
        return min(animals, key=lambda a: manhattan((self.col, self.row), (a.col, a.row)))

    def _plan_to(self, grid, goal):
        """Run A* and set path. Returns True if a valid path was found."""
        result = astar(grid, (self.col, self.row), goal, GUARD_COSTS)
        if result.path:
            self.set_path(result.path, result.explored)
            return True
        return False

    def _move_directly_toward(self, grid, target_col, target_row):
        """Fallback: move directly toward target without pathfinding."""
        dx = target_col - self.col
        dy = target_row - self.row
        if abs(dx) > abs(dy):
            next_col = self.col + (1 if dx > 0 else -1)
            next_row = self.row
        else:
            next_col = self.col
            next_row = self.row + (1 if dy > 0 else -1)
        # Check if tile is walkable
        tile = grid.get(next_col, next_row)
        if tile and tile.walkable:
            self.set_path([(next_col, next_row)], set())
        else:
            # Try other direction
            if abs(dx) > abs(dy):
                next_row = self.row + (1 if dy > 0 else -1)
            else:
                next_col = self.col + (1 if dx > 0 else -1)
            tile = grid.get(next_col, next_row)
            if tile and tile.walkable:
                self.set_path([(next_col, next_row)], set())

    def update(self, grid, agents):
        super().update(grid, agents)
        self.replan_cd = max(0, self.replan_cd - 1)

        # Update color based on state
        self.color = self.get_color()

        nearest = self._nearest_animal(agents)

        # ── State transitions ─────────────────────────────────────────────────
        if nearest and nearest.alive:
            dist = manhattan((self.col, self.row), (nearest.col, nearest.row))
            if dist <= self.ALERT_RADIUS:
                if self.state == "patrol":
                    self.state = "alert"
                    self.replan_cd = 0
                    print("Guard alerted!")
                elif self.state == "alert" and dist <= 5:  # Closer for chase
                    self.state = "chase"
                    self.chase_target = nearest
                    self.chase_start_time = pygame.time.get_ticks()
                    self.replan_cd = 0
                    print("Guard chasing!")
            elif self.state in ["alert", "chase"] and dist > self.RETURN_RADIUS:
                self.state = "patrol"
                self.chase_target = None
                self.replan_cd = 0
                print("Guard returning to patrol")

        # ── Alert state ───────────────────────────────────────────────────────
        if self.state == "alert":
            # Scan area, maybe move toward last known position
            if nearest and nearest.alive:
                dist = manhattan((self.col, self.row), (nearest.col, nearest.row))
                if dist > 5 and self.replan_cd == 0:
                    self._plan_to(grid, (nearest.col, nearest.row))
                    self.replan_cd = 10
            # Stay alert for a bit, then patrol if no activity
            return

        # ── Chase ─────────────────────────────────────────────────────────────
        if self.state == "chase" and self.chase_target and self.chase_target.alive:
            # Stamina management
            self.stamina = max(0, self.stamina - self.STAMINA_DRAIN)
            if self.stamina == 0:
                self.speed = 1.0  # Slow down when tired
            else:
                self.speed = 2.2

            # Give up if chase too long
            if pygame.time.get_ticks() - self.chase_start_time > self.GIVE_UP_TIME:
                self.state = "patrol"
                self.chase_target = None
                self.replan_cd = 0
                print("Guard gave up chase")
                return

            if manhattan((self.col, self.row), (self.chase_target.col, self.chase_target.row)) <= 1:
                self.chase_target.caught()
                self.score += 50
                self.state = "patrol"
                self.chase_target = None
                self.replan_cd = 0
                print("Guard caught the animal!")
                return
            else:
                # Frequent replanning
                if self.replan_cd == 0:
                    ok = self._plan_to(grid, (self.chase_target.col, self.chase_target.row))
                    if not ok:
                        # Direct movement fallback
                        self._move_directly_toward(grid, self.chase_target.col, self.chase_target.row)
                    self.replan_cd = self.CHASE_REPLAN_FRAMES
                return

        # ── Patrol ────────────────────────────────────────────────────────────
        self.state = "patrol"
        # Recover stamina
        self.stamina = min(self.STAMINA_MAX, self.stamina + self.STAMINA_RECOVER)
        self.speed = 2.2

        if not self.waypoints:
            return

        current_goal = self.waypoints[self.wp_index % len(self.waypoints)]

        if (self.col, self.row) == current_goal and not self.moving:
            self.wp_index = (self.wp_index + 1) % len(self.waypoints)
            current_goal = self.waypoints[self.wp_index]
            ok = self._plan_to(grid, current_goal)
            self.replan_cd = self.PATROL_REPLAN_FRAMES if ok else 5
        elif self.replan_cd == 0 and not self.moving:
            ok = self._plan_to(grid, current_goal)
            if ok:
                self.replan_cd = self.PATROL_REPLAN_FRAMES
            else:
                self.wp_index = (self.wp_index + 1) % len(self.waypoints)
                self.replan_cd = 5