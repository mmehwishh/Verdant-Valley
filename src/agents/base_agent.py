import pygame
from utils.constants import *
from utils.helpers import grid_to_px, tile_center


class Agent:
    """Base class for all NPC agents."""

    def __init__(self, col, row, color, speed=2.5, name="Agent"):
        self.col = col
        self.row = row
        self.color = color
        self.name = name
        self.speed = speed  # pixels per frame

        # Pixel position (smooth movement)
        cx, cy = tile_center(col, row)
        self.px = float(cx)
        self.py = float(cy)

        # Pathfinding state
        self.path = []  # list of (col, row)
        self.path_idx = 0
        self.explored = set()
        self.moving = False

        # Stats
        self.score = 0
        self.state = "idle"

    # ── Movement ──────────────────────────────────────────────────────────────

    def set_path(self, path, explored=None):
        self.path = path
        self.path_idx = 0
        self.explored = explored or set()
        self.moving = bool(path)

    def _move_along_path(self):
        if not self.path or self.path_idx >= len(self.path):
            self.moving = False
            return

        target_col, target_row = self.path[self.path_idx]
        tx, ty = tile_center(target_col, target_row)

        dx = tx - self.px
        dy = ty - self.py
        dist = (dx**2 + dy**2) ** 0.5

        if dist < self.speed:
            self.px = float(tx)
            self.py = float(ty)
            self.col = target_col
            self.row = target_row
            self.path_idx += 1
        else:
            self.px += (dx / dist) * self.speed
            self.py += (dy / dist) * self.speed

    # ── Update / Draw ────────────────────────────────────────────────

    def update(self, grid, agents):
        self._move_along_path()

    def draw(self, surface, font=None):
        # Shadow
        shadow_color = (0, 0, 0, 80)
        radius = TILE_SIZE // 2 - 4
        pygame.draw.circle(surface, shadow_color, (int(self.px) + 3, int(self.py) + 3), radius)

        # Body circle
        pygame.draw.circle(surface, self.color, (int(self.px), int(self.py)), radius)
        # Dark outline
        pygame.draw.circle(surface, (0, 0, 0), (int(self.px), int(self.py)), radius, 2)

        # Name label
        if font:
            label = font.render(self.name, True, C_TEXT_MAIN)
            surface.blit(
                label,
                (int(self.px) - label.get_width() // 2, int(self.py) - radius - 16),
            )

    def draw_path_overlay(self, surface, path_color):
        """Draw explored nodes + path onto the grid."""
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
            for col, row in self.path[self.path_idx :]:
                x, y = grid_to_px(col, row)
                surface.blit(overlay, (x, y))
