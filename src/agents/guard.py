"""
src/agents/guard.py - Guard Agent
"""

import random
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan, tile_center



class Guard(Agent):
    ALERT_RADIUS = 10
    RETURN_RADIUS = 15
    CHASE_REPLAN_FRAMES = 5  # More frequent replanning
    PATROL_REPLAN_FRAMES = 30
    GIVE_UP_TIME = 30 * 60  # 30 seconds at 60 FPS
    STAMINA_MAX = 100
    STAMINA_DRAIN = 1  # Per frame during chase
    STAMINA_RECOVER = 2  # Per frame during patrol

    def draw_failed_move_indicator(self, surface, grid):
        self.show_blocked_cross(surface, grid)

    def show_blocked_cross(self, surface, grid):
        """Draw a cross on the last failed tile if timer is active."""
        if getattr(self, '_failed_move_tile', None) is not None and getattr(self, '_failed_move_timer', 0) > 0:
            from game_ui.game_ui import draw_blocked_tile_cross
            tile = self._failed_move_tile
            if isinstance(tile, tuple) and len(tile) == 2:
                col, row = tile
                draw_blocked_tile_cross(surface, col, row, grid)

    def _show_failed_move(self, tile_pos=None):
        self._failed_move_tile = tile_pos if tile_pos is not None else (self.col, self.row)
        self._failed_move_timer = 60

    def update_failed_move_timer(self):
        if hasattr(self, '_failed_move_timer') and self._failed_move_timer > 0:
            self._failed_move_timer -= 1
        if hasattr(self, '_failed_move_timer') and self._failed_move_timer == 0:
            self._failed_move_tile = None

    def __init__(self, col, row, color=C_GUARD):
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

        Agent.__init__(
            self, col, row, color,
            speed=2.2,
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
        self.chase_start_time = 0
        self.stamina = self.STAMINA_MAX
        self.original_color = C_GUARD

    def get_color(self):
        if self.state == "chase":
            if self.stamina < self.STAMINA_MAX // 2:
                return (255, 100, 100)  # Red when tired
            return (255, 165, 0)  # Orange when chasing
        elif self.state == "alert":
            return (255, 255, 0)  # Yellow when alert
        return self.original_color  # Default blue

    def set_waypoints(self, waypoints):
        self.waypoints = waypoints
        self.wp_index = 0

    def _nearest_animal(self, agents):
        animals = [a for a in agents if a.__class__.__name__ == "Animal" and a.alive]
        if not animals:
            return None
        return min(animals, key=lambda a: manhattan((self.col, self.row), (a.col, a.row)))

    def _plan_to(self, grid, goal, season_mgr=None):
        goal = self._resolve_goal(grid, goal)
        if goal is None:
            return False
        rain_active = season_mgr.rain_active if season_mgr else False
        result = astar(grid, (self.col, self.row), goal, agent_type="Guard", rain_active=rain_active)
        if getattr(result, 'path', None):
            self.set_path(result.path, result.explored)
            self.moving = True
            return True
        return False

    def _is_valid_step(self, tile):
        if tile is None:
            return False
        return GUARD_COSTS.get(tile.type, float("inf")) != float("inf")

    def _can_step(self, grid, col, row):
        """Override: guard cannot step on water, stone, snow_stone."""
        return self._is_valid_step(grid.get(col, row))

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
        if self._is_valid_step(tile):
            self.set_path([(next_col, next_row)], set())
        else:
            # Try other direction
            if abs(dx) > abs(dy):
                next_row = self.row + (1 if dy > 0 else -1)
            else:
                next_col = self.col + (1 if dx > 0 else -1)
            tile = grid.get(next_col, next_row)
            if self._is_valid_step(tile):
                self.set_path([(next_col, next_row)], set())

    def update(self, grid, agents, season_mgr=None):
        self._ensure_valid_position(grid)
        Agent.update(self, grid, agents, season_mgr)
        self.replan_cd = max(0, self.replan_cd - 1)

        # Stuck detection: if position hasn't changed for 60 ticks, force replan
        if (self.col, self.row) == self._last_pos:
            self._stuck_ticks += 1
        else:
            self._stuck_ticks = 0
            self._last_pos = (self.col, self.row)

        # Update color based on state
        self.color = self.get_color()

        nearest = self._nearest_animal(agents)

        # ── State transitions ─────────────────────────────────────────────────
        if nearest and nearest.alive:
            dist = manhattan((self.col, self.row), (nearest.col, nearest.row))
            crop_damage = getattr(nearest, "recent_crop_damage_timer", 0) > 0
            crop_alert_radius = self.RETURN_RADIUS + 4
            near_enough = dist <= self.ALERT_RADIUS or (crop_damage and dist <= crop_alert_radius)
            if near_enough:
                if self.state == "patrol":
                    self.state = "alert"
                    self.replan_cd = 0
                    print("Guard alerted!")
                elif self.state == "alert" and dist <= 5:  # Closer for chase
                    self.state = "chase"
                    self.chase_target = nearest
                    import pygame
                    self.chase_start_time = pygame.time.get_ticks()
                    self.replan_cd = 0
                    print("Guard chasing!")
                elif self.state == "chase":
                    self.chase_target = nearest
            elif self.state in ["alert", "chase"] and dist > self.RETURN_RADIUS and not crop_damage:
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
                    self._plan_to(grid, (nearest.col, nearest.row), season_mgr)
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

            # If on the same tile as Bear, catch it
            if self.col == self.chase_target.col and self.row == self.chase_target.row:
                if hasattr(self.chase_target, 'animal_type') and self.chase_target.animal_type == 'bear':
                    self.chase_target.alive = False
                    self.score = getattr(self, 'score', 0) + 1
                    print("🛡️ Guard caught the Bear!")
                    self.state = "patrol"
                    self.chase_target = None
                    return

            import pygame
            # Give up if chase too long
            if pygame.time.get_ticks() - self.chase_start_time > self.GIVE_UP_TIME:
                self.state = "patrol"
                self.chase_target = None
                self.replan_cd = 0
                print("Guard gave up chase")
                return

            # Immediate catch check — always runs, even mid-path
            if manhattan((self.col, self.row), (self.chase_target.col, self.chase_target.row)) <= 1:
                self.chase_target.caught()
                self.score += 50
                self.state = "patrol"
                self.chase_target = None
                self._stuck_ticks = 0
                self.replan_cd = 0
                print("Guard caught the animal!")
                return
            else:
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
                    ok = self._plan_to(grid, (self.chase_target.col, self.chase_target.row), season_mgr)
                    if not ok:
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
            current_goal = self.waypoints[self.wp_index % len(self.waypoints)]
            ok = self._plan_to(grid, current_goal, season_mgr)
            self.replan_cd = self.PATROL_REPLAN_FRAMES if ok else 10
        elif self.replan_cd == 0 and (
            not self.moving or not self.path or self.path_idx >= max(0, len(self.path) - 1)
        ):
            ok = self._plan_to(grid, current_goal, season_mgr)
            if ok:
                self.replan_cd = self.PATROL_REPLAN_FRAMES
            else:
                self.wp_index = (self.wp_index + 1) % len(self.waypoints)
                self.replan_cd = 10
