"""
src/agents/base_agent.py - Base Agent Class with Animation Support
"""

import pygame
from utils.constants import *
from utils.helpers import tile_center, grid_to_px
from utils.animation import Animation


class Agent:
    """Base class for all NPC agents with animation support."""

    def __init__(
        self,
        col,
        row,
        color,
        speed=2.5,
        name="Agent",
        sprite_sheet_path=None,
        frame_size=(48, 48),
        animation_rows=4,
        animation_cols=4,
        scale=1,
    ):
        self.col = col
        self.row = row
        self.color = color
        self.name = name
        self.speed = speed

        self.animation = None
        self.last_direction = 0
        self.last_pos = (col, row)

        if sprite_sheet_path:
            try:
                import os
                if os.path.exists(sprite_sheet_path):
                    self.animation = Animation(
                        sprite_sheet_path,
                        frame_size[0],
                        frame_size[1],
                        animation_rows,
                        animation_cols,
                        scale,
                    )
                    print(f"✓ Loaded animation for {name}")
                else:
                    print(f"⚠️ Sprite sheet not found for {name}: {sprite_sheet_path}")
            except Exception as e:
                print(f"Could not load animation for {name}: {e}")

        cx, cy = tile_center(col, row)
        self.x = float(cx)
        self.y = float(cy)

        self.path = []
        self.path_idx = 0
        self.explored = set()
        self.moving = False

        self.score = 0
        self.state = "idle"

    # ── Animation ─────────────────────────────────────────────────────────────

    def update_animation_direction(self):
        if not self.animation:
            return

        dx = self.col - self.last_pos[0]
        dy = self.row - self.last_pos[1]

        if dx > 0:
            self.animation.set_direction(3)
        elif dx < 0:
            self.animation.set_direction(2)
        elif dy > 0:
            self.animation.set_direction(0)
        elif dy < 0:
            self.animation.set_direction(1)

        self.last_pos = (self.col, self.row)

        if self.moving:
            self.animation.update()
        else:
            if self.animation:
                self.animation.current_frame = 0
                self.animation.animation_timer = 0

    # ── Movement ──────────────────────────────────────────────────────────────

    def set_path(self, path, explored=None):
        """
        A* returns a path that INCLUDES the start node as path[0].
        We skip it here so the agent doesn't waste a frame "moving"
        to the tile it's already standing on.
        """
        if path and len(path) > 1:
            # Strip the start node — agent is already there
            self.path = path[1:]
        else:
            # Path is empty or only contains start (already at goal)
            self.path = []

        self.path_idx = 0
        self.explored = explored or set()
        # Only mark moving if there are actual steps to take
        self.moving = len(self.path) > 0

        if self.animation and self.moving:
            self.animation.reset()

    def _move_along_path(self):
        """
        Move one step toward the next tile in the path.
        Sets self.moving = False when the path is fully walked.
        """
        # ── Guard: nothing to do ──────────────────────────────────────────────
        if not self.path or self.path_idx >= len(self.path):
            self.moving = False   # ← THE CRITICAL FIX: was never set False before
            self.path = []
            self.path_idx = 0
            return

        target_col, target_row = self.path[self.path_idx]
        tx, ty = tile_center(target_col, target_row)

        dx = tx - self.x
        dy = ty - self.y
        dist = (dx ** 2 + dy ** 2) ** 0.5

        if dist <= self.speed:
            # Snap to tile center and advance
            self.x = float(tx)
            self.y = float(ty)
            self.col = target_col
            self.row = target_row
            self.path_idx += 1

            # Check if we just finished the last step
            if self.path_idx >= len(self.path):
                self.moving = False   # ← also THE CRITICAL FIX
                self.path = []
                self.path_idx = 0
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

    # ── Update / Draw ─────────────────────────────────────────────────────────

    def update(self, grid, agents):
        self._move_along_path()

    def draw(self, surface, font=None):
        self.update_animation_direction()

        if self.animation:
            sprite = self.animation.get_frame()
            if sprite:
                sprite_rect = sprite.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(sprite, sprite_rect)
            else:
                radius = TILE_SIZE // 2 - 4
                pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), radius)
                pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), radius, 2)
        else:
            radius = TILE_SIZE // 2 - 4
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), radius)
            pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), radius, 2)

        if font:
            label = font.render(self.name, True, C_TEXT_MAIN)
            surface.blit(
                label,
                (int(self.x) - label.get_width() // 2, int(self.y) - TILE_SIZE // 2 - 16),
            )

    def draw_path_overlay(self, surface, path_color):
        if not self.path and not self.explored:
            return

        overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)

        if self.explored:
            overlay.fill(C_EXPLORED)
            for col, row in self.explored:
                x, y = grid_to_px(col, row)
                surface.blit(overlay, (x, y))

        if self.path:
            overlay.fill((*path_color[:3], 160))
            for col, row in self.path[self.path_idx:]:
                x, y = grid_to_px(col, row)
                surface.blit(overlay, (x, y))