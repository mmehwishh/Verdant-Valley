"""
world/grid.py  —  Verdant Valley
Tile grid with baked textures (no per-frame random calls), rounded corners,
top-face highlights, crop shadow glows, hover highlight, and season tint overlay.
"""

import random
import math
import sys
import os
import re
import base64

import pygame
from io import BytesIO

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
)

from utils.constants import (
    TILE_GRASS,
    TILE_DIRT,
    TILE_STONE,
    TILE_MUD,
    TILE_WATER,
    TILE_FIELD,
    TILE_COLOR,
    TILE_HIGHLIGHT,
    TILE_SHADOW,
    TILE_COST,
    TILE_RADIUS,
    TILE_SIZE,
    GRID_COLS,
    GRID_ROWS,
    GRID_OFFSET_X,
    GRID_OFFSET_Y,
    CROP_NONE,
    CROP_WHEAT,
    CROP_SUNFLOWER,
    CROP_CORN,
    CROP_COLOR,
    CROP_GLOW_COLOR,
    C_TILE_HOVER_BORDER,
    C_TILE_HOVER_FILL,
    SEASON_TINTS,
)
from utils.helpers import grid_to_px, draw_rounded_rect


# ── Asset loading ──────────────────────────────────────────────────────────────

REPO_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
)
STONE_ASSET_PATHS = [
    os.path.join(REPO_ROOT, "assets", "images", "final_stone.jpg"),
    os.path.join(REPO_ROOT, "assets", "images", "stones.png"),
    os.path.join(REPO_ROOT, "assets", "images", "stones.svg"),
]
STONE_ASSET = None


def _get_stone_asset():
    """Load and cache the stone tile art from assets/images."""
    global STONE_ASSET

    if STONE_ASSET is not None:
        return STONE_ASSET

    for asset_path in STONE_ASSET_PATHS:
        if not os.path.exists(asset_path):
            continue

        ext = os.path.splitext(asset_path)[1].lower()

        # Prefer regular bitmap assets when available.
        if ext in {".jpg", ".jpeg", ".png"}:
            try:
                img = pygame.image.load(asset_path)
                if pygame.display.get_surface() is not None:
                    img = img.convert_alpha() if ext == ".png" else img.convert()
                STONE_ASSET = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
                if _surface_has_visible_pixels(STONE_ASSET):
                    return STONE_ASSET
            except Exception:
                continue

        # SVG fallback path for older assets.
        try:
            img = pygame.image.load(asset_path)
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            scaled = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
            styled = _stylize_stone_asset(scaled)
            if _surface_has_visible_pixels(styled):
                STONE_ASSET = styled
                return STONE_ASSET
        except Exception:
            pass

        try:
            with open(asset_path, "r", encoding="utf-8", errors="replace") as svg_file:
                svg_text = svg_file.read()

            match = re.search(r"data:image/png;base64,([A-Za-z0-9+/=\n\r]+)", svg_text)
            if not match:
                continue

            png_data = base64.b64decode(match.group(1))
            img = pygame.image.load(BytesIO(png_data), "stones.png")
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            scaled = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
            styled = _stylize_stone_asset(scaled)
            if _surface_has_visible_pixels(styled):
                STONE_ASSET = styled
                return STONE_ASSET
        except Exception:
            continue

    STONE_ASSET = None

    return STONE_ASSET


def _surface_has_visible_pixels(surface):
    """Return True when the surface contains at least one visible pixel."""
    width, height = surface.get_size()
    for x in range(width):
        for y in range(height):
            if surface.get_at((x, y)).a > 0:
                return True
    return False


def _stylize_stone_asset(surface):
    """Remove dark background from the imported asset and tint details as stone."""
    styled = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    width, height = surface.get_size()

    for x in range(width):
        for y in range(height):
            r, g, b, a = surface.get_at((x, y))
            if a == 0:
                continue

            brightness = (r + g + b) // 3

            # Treat near-black pixels as background.
            if brightness < 24:
                continue

            # Map visible detail into a stone-gray gradient.
            shade = max(90, min(220, 90 + int((brightness / 255) * 130)))
            alpha = max(110, min(255, a))
            styled.set_at((x, y), (shade, shade, shade, alpha))

    return styled


# ── Baked texture data per tile ───────────────────────────────────────────────


def _bake_grass(col, row):
    """Return list of (x_off, y_off, height) for grass blades — deterministic."""
    rng = random.Random(col * 1000 + row * 37 + 3)
    blades = []
    for _ in range(6):
        bx = rng.randint(4, TILE_SIZE - 8)
        by = rng.randint(8, TILE_SIZE - 6)
        bh = rng.randint(4, 8)
        blades.append((bx, by, bh))
    # small pebble
    px = rng.randint(6, 14)
    py = rng.randint(8, 16)
    return {"blades": blades, "pebble": (px, py)}


def _bake_dirt(col, row):
    rng = random.Random(col * 999 + row * 53 + 7)
    dots = [
        (rng.randint(3, TILE_SIZE - 3), rng.randint(3, TILE_SIZE - 3)) for _ in range(5)
    ]
    return {"dots": dots}


def _bake_stone(col, row):
    """Generate 3D stone data with shadow and highlight positions."""
    rng = random.Random(col * 777 + row * 41 + 13)
    pebbles = []
    for _ in range(4):
        sx = rng.randint(8, TILE_SIZE - 8)
        sy = rng.randint(8, TILE_SIZE - 8)
        sr = rng.randint(5, 10)  # larger stones
        # Light direction: top-left (-1, -1)
        highlight_offset = (-sr // 3, -sr // 3)
        # Shadow direction: bottom-right (1, 1)
        shadow_offset = (sr // 2, sr // 2)
        color_var = rng.randint(-8, 8)  # slight color variation
        pebbles.append(
            {
                "x": sx,
                "y": sy,
                "r": sr,
                "highlight_offset": highlight_offset,
                "shadow_offset": shadow_offset,
                "color_var": color_var,
            }
        )
    return {"pebbles": pebbles}


def _bake_mud(col, row):
    rng = random.Random(col * 888 + row * 29 + 17)
    streaks = []
    for i in range(0, TILE_SIZE, 6):
        ox = rng.randint(-2, 2)
        streaks.append(i + ox)
    return {"streaks": streaks}


def _bake_field(col, row):
    """Horizontal furrow lines + small clod dots."""
    rng = random.Random(col * 555 + row * 61 + 23)
    clods = [
        (rng.randint(8, TILE_SIZE - 8), rng.randint(8, TILE_SIZE - 8)) for _ in range(3)
    ]
    return {"clods": clods}


def _bake_water(col, row):
    """Wave arc offsets (column/row-offset so adjacent tiles don't repeat identically)."""
    rng = random.Random(col * 333 + row * 19 + 5)
    ripple_offset = rng.randint(0, 20)
    return {"ripple_offset": ripple_offset}


BAKE_FN = {
    TILE_GRASS: _bake_grass,
    TILE_DIRT: _bake_dirt,
    TILE_STONE: _bake_stone,
    TILE_MUD: _bake_mud,
    TILE_FIELD: _bake_field,
    TILE_WATER: _bake_water,
}


# ── Tile ──────────────────────────────────────────────────────────────────────


class Tile:
    def __init__(self, col, row, tile_type=TILE_GRASS):
        self.col = col
        self.row = row
        self.type = tile_type
        self.crop = CROP_NONE
        self.crop_stage = 0  # 0-3
        self.wet = False
        self._texture = None  # baked texture data dict

    def bake(self):
        """Call once after tile type is set (or changed) to pre-compute texture data."""
        fn = BAKE_FN.get(self.type)
        self._texture = fn(self.col, self.row) if fn else {}

    @property
    def texture(self):
        if self._texture is None:
            self.bake()
        return self._texture

    @property
    def cost(self):
        return TILE_COST[self.type]

    @property
    def walkable(self):
        return self.cost < 500

    def rect(self):
        x, y = grid_to_px(self.col, self.row)
        return pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)


# ── Grid ──────────────────────────────────────────────────────────────────────


class Grid:
    def __init__(self):
        self.cols = GRID_COLS
        self.rows = GRID_ROWS
        self.tiles = [[Tile(c, r) for r in range(self.rows)] for c in range(self.cols)]

        # NEW: Add buildings list
        self.buildings = []

        # NEW: Load house sprite
        self.house_sprite = None
        self.load_house_sprite()

        self._build_map()
        self._bake_all()
        # Cache for the season tint surface (resized only when season changes)
        self._tint_surf_cache: dict[int, pygame.Surface] = {}
        # Hovered tile (col, row) — set by caller each frame
        self.hovered: tuple[int, int] | None = None

    # NEW: Method to load house sprite
    def load_house_sprite(self):
        """Load the house sprite from assets"""
        try:
            self.house_sprite = pygame.image.load(
                "assets/farm/house.png"
            ).convert_alpha()
            # Scale to appropriate size (96x96 for 2x2 tiles)
            self.house_sprite = pygame.transform.scale(self.house_sprite, (96, 96))
            print("House sprite loaded successfully!")
        except Exception as e:
            print(f"Could not load house sprite: {e}")
            self.house_sprite = None

    # NEW: Method to add house at specific position
    def add_house(self, col, row):
        """Add a house at grid position"""
        self.buildings.append(
            {"col": col, "row": row, "type": "house", "sprite": self.house_sprite}
        )
        print(f"House added at ({col}, {row})")

    # NEW: Method to draw all buildings
    def draw_buildings(self, surface):
        """Draw all buildings on top of tiles"""
        for building in self.buildings:
            if building["sprite"] is None:
                continue

            x, y = grid_to_px(building["col"], building["row"])

            # Adjust position for larger sprite (96x96 house on 48x48 grid)
            sprite_width = building["sprite"].get_width()
            sprite_height = building["sprite"].get_height()

            if sprite_width > TILE_SIZE:
                # Center the larger sprite
                x = x - (sprite_width - TILE_SIZE) // 2
                y = y - (sprite_height - TILE_SIZE)

            surface.blit(building["sprite"], (x, y))

    # ── Map generation ────────────────────────────────────────────────────────

    def _build_map(self):
        """Generate random terrain layout (water fixed at col 0-1, everything else random)"""

        # FIRST: Water - ALWAYS FIXED at columns 0-1
        for r in range(self.rows):
            if 0 < self.cols:
                self.tiles[0][r].type = TILE_WATER
            if 1 < self.cols:
                self.tiles[1][r].type = TILE_WATER

        # SECOND: Random terrain for all other tiles
        for c in range(self.cols):
            for r in range(self.rows):
                # Skip water columns (0 and 1)
                if c <= 1:
                    continue

                # Random number between 0 and 1
                rand = random.random()

                # Assign random tile types with probabilities
                if rand < 0.35:  # 35% Grass
                    self.tiles[c][r].type = TILE_GRASS
                elif rand < 0.55:  # 20% Dirt
                    self.tiles[c][r].type = TILE_DIRT
                elif rand < 0.70:  # 15% Field
                    self.tiles[c][r].type = TILE_FIELD
                elif rand < 0.82:  # 12% Stone
                    self.tiles[c][r].type = TILE_STONE
                else:  # 18% Mud
                    self.tiles[c][r].type = TILE_MUD

        # THIRD: Stone path at bottom (fixed)
        for c in range(2, self.cols):
            if 12 < self.rows:
                self.tiles[c][12].type = TILE_STONE
            if 13 < self.rows:
                self.tiles[c][13].type = TILE_STONE

    def _bake_all(self):
        """Pre-compute texture data for every tile."""
        for c in range(self.cols):
            for r in range(self.rows):
                self.tiles[c][r].bake()

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get(self, col, row):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.tiles[col][row]
        return None

    def water_sources(self):
        return [
            (c, r)
            for c in range(self.cols)
            for r in range(self.rows)
            if self.tiles[c][r].type == TILE_WATER
        ]

    def field_tiles(self):
        return [
            (c, r)
            for c in range(self.cols)
            for r in range(self.rows)
            if self.tiles[c][r].type == TILE_FIELD
        ]

    def crop_tiles(self):
        return [
            (c, r)
            for c in range(self.cols)
            for r in range(self.rows)
            if self.tiles[c][r].crop != CROP_NONE
        ]

    # ── Rain event ────────────────────────────────────────────────────────────

    def apply_rain(self):
        new_mud = []
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                if t.type == TILE_MUD:
                    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        n = self.get(c + dc, r + dr)
                        if n and n.type in (TILE_DIRT, TILE_GRASS):
                            new_mud.append((c + dc, r + dr))
                if t.type in (TILE_FIELD, TILE_GRASS):
                    t.wet = True
        for c, r in new_mud:
            if 0 <= c < self.cols and 0 <= r < self.rows:
                self.tiles[c][r].type = TILE_MUD
                self.tiles[c][r].bake()

    # ── Hover helper ──────────────────────────────────────────────────────────

    def update_hover(self, mouse_pos):
        """Call each frame with pygame.mouse.get_pos()."""
        mx, my = mouse_pos
        col = (mx - GRID_OFFSET_X) // TILE_SIZE
        row = (my - GRID_OFFSET_Y) // TILE_SIZE
        if 0 <= col < self.cols and 0 <= row < self.rows:
            self.hovered = (col, row)
        else:
            self.hovered = None

    # ── Rendering ─────────────────────────────────────────────────────────────

    def draw(self, surface, tick=0, font_tiny=None, season_index=0):
        # ── Farm plot background panel ────────────────────────────────────────
        plot_rect = pygame.Rect(
            GRID_OFFSET_X - 10,
            GRID_OFFSET_Y - 10,
            self.cols * TILE_SIZE + 20,
            self.rows * TILE_SIZE + 20,
        )
        draw_rounded_rect(surface, (20, 28, 18, 230), plot_rect, radius=20)
        draw_rounded_rect(
            surface,
            (255, 255, 255, 40),
            plot_rect,
            radius=20,
            border=2,
            border_color=(90, 120, 90),
        )

        # Soft panel shadow
        shadow_rect = plot_rect.inflate(12, 12)
        shadow_surf = pygame.Surface(
            (shadow_rect.width, shadow_rect.height), pygame.SRCALPHA
        )
        pygame.draw.rect(
            shadow_surf, (0, 0, 0, 40), shadow_surf.get_rect(), border_radius=24
        )
        surface.blit(shadow_surf, (shadow_rect.x, shadow_rect.y))

        # ── Draw tiles ────────────────────────────────────────────────────────
        for c in range(self.cols):
            for r in range(self.rows):
                self._draw_tile(surface, self.tiles[c][r], tick)

        # ── Hover highlight (drawn on top of tiles) ───────────────────────────
        if self.hovered:
            hc, hr = self.hovered
            hx, hy = grid_to_px(hc, hr)
            hover_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(
                hover_surf,
                C_TILE_HOVER_FILL,
                hover_surf.get_rect(),
                border_radius=TILE_RADIUS,
            )
            surface.blit(hover_surf, (hx, hy))
            pygame.draw.rect(
                surface,
                C_TILE_HOVER_BORDER,
                pygame.Rect(hx, hy, TILE_SIZE, TILE_SIZE),
                width=2,
                border_radius=TILE_RADIUS,
            )

        # ── Season tint overlay ───────────────────────────────────────────────
        self._draw_season_tint(surface, season_index)

    # ── Single tile drawing ───────────────────────────────────────────────────

    def _draw_tile(self, surface, t: Tile, tick: int):
        x, y = grid_to_px(t.col, t.row)
        tx = t.texture

        base = TILE_COLOR[t.type]
        hi = TILE_HIGHLIGHT[t.type]
        sh = TILE_SHADOW[t.type]

        # Darken when wet
        if t.wet and t.type != TILE_WATER:
            base = tuple(max(0, v - 22) for v in base)
            hi = tuple(max(0, v - 22) for v in hi)

        tile_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)

        # ── Base fill ─────────────────────────────────────────────────────────
        pygame.draw.rect(surface, base, tile_rect, border_radius=TILE_RADIUS)

        # ── Top-face highlight strip (baked, not random) ──────────────────────
        hi_surf = pygame.Surface((TILE_SIZE, 10), pygame.SRCALPHA)
        hi_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(
            hi_surf, (*hi, 100), hi_surf.get_rect(), border_radius=TILE_RADIUS
        )
        surface.blit(hi_surf, (x, y))

        # ── Bottom shadow strip ────────────────────────────────────────────────
        sh_surf = pygame.Surface((TILE_SIZE, 8), pygame.SRCALPHA)
        sh_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(sh_surf, (*sh, 80), sh_surf.get_rect())
        surface.blit(sh_surf, (x, y + TILE_SIZE - 8))

        # ── Type-specific textures (all baked, no random calls here) ──────────
        if t.type == TILE_GRASS:
            for bx, by, bh in tx.get("blades", []):
                pygame.draw.line(
                    surface, (44, 155, 44), (x + bx, y + by), (x + bx, y + by - bh), 1
                )
            px, py = tx.get("pebble", (10, 12))
            pygame.draw.circle(surface, (200, 200, 165), (x + px, y + py), 2)

        elif t.type == TILE_WATER:
            ripple = tx.get("ripple_offset", 0)
            for i in range(-4, TILE_SIZE + 4, 6):
                wave = int(3 * math.sin((tick * 0.07 + ripple + i) * 0.2))
                pygame.draw.arc(
                    surface,
                    (50, 130, 210),
                    (x + i, y + 9 + wave, 12, 8),
                    math.pi,
                    2 * math.pi,
                    2,
                )
            # Shimmer dot
            shimmer_alpha = int(80 + 60 * math.sin(tick * 0.13 + t.col))
            sh_dot = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(sh_dot, (200, 230, 255, shimmer_alpha), (2, 2), 2)
            surface.blit(sh_dot, (x + 20, y + 6))

        elif t.type == TILE_FIELD:
            # Furrow lines (fixed positions)
            for line_y_off in range(7, TILE_SIZE, 8):
                pygame.draw.line(
                    surface,
                    (90, 52, 16),
                    (x + 5, y + line_y_off),
                    (x + TILE_SIZE - 5, y + line_y_off),
                    2,
                )
            for cx, cy in tx.get("clods", []):
                pygame.draw.circle(surface, (98, 46, 12), (x + cx, y + cy), 2)

        elif t.type == TILE_DIRT:
            for dx, dy in tx.get("dots", []):
                pygame.draw.circle(surface, (100, 52, 18), (x + dx, y + dy), 1)

        elif t.type == TILE_STONE:
<<<<<<< Updated upstream
            stone_asset = _get_stone_asset()
            if stone_asset:
                surface.blit(stone_asset, (x, y))
            else:
                for pebble in tx.get("pebbles", []):
                    sx = pebble["x"]
                    sy = pebble["y"]
                    sr = pebble["r"]
                    h_off = pebble["highlight_offset"]
                    s_off = pebble["shadow_offset"]
                    c_var = pebble["color_var"]
                    
                    # Base stone color with variation
                    base = TILE_COLOR[TILE_STONE]
                    stone_color = (
                        max(40, min(200, base[0] + c_var)),
                        max(40, min(200, base[1] + c_var)),
                        max(40, min(200, base[2] + c_var))
                    )
                    
                    # Deep shadow (darkest inner ring)
                    shadow_color = (
                        max(40, stone_color[0] - 30),
                        max(40, stone_color[1] - 30),
                        max(40, stone_color[2] - 30)
                    )
                    pygame.draw.circle(surface, shadow_color, (x + sx + s_off[0], y + sy + s_off[1]), sr + 1)
                    
                    # Main stone body
                    pygame.draw.circle(surface, stone_color, (x + sx, y + sy), sr)
                    
                    # Subtle mid-tone ring for depth
                    mid_color = (
                        (stone_color[0] + shadow_color[0]) // 2,
                        (stone_color[1] + shadow_color[1]) // 2,
                        (stone_color[2] + shadow_color[2]) // 2
                    )
                    pygame.draw.circle(surface, mid_color, (x + sx, y + sy), sr, 1)
                    
                    # Top highlight (bright edge)
                    highlight_color = (
                        min(255, stone_color[0] + 40),
                        min(255, stone_color[1] + 40),
                        min(255, stone_color[2] + 40)
                    )
                    h_size = max(1, sr // 3)
                    pygame.draw.circle(surface, highlight_color, 
                                     (x + sx + h_off[0], y + sy + h_off[1]), h_size)
                    
                    # Micro-shine dot on highlight
                    pygame.draw.circle(surface, (255, 255, 255),
                                     (x + sx + h_off[0], y + sy + h_off[1]), max(1, h_size - 1))
=======
            for pebble in tx.get("pebbles", []):
                sx = pebble["x"]
                sy = pebble["y"]
                sr = pebble["r"]
                h_off = pebble["highlight_offset"]
                s_off = pebble["shadow_offset"]
                c_var = pebble["color_var"]

                # Base stone color with variation
                base = TILE_COLOR[TILE_STONE]
                stone_color = (
                    max(40, min(200, base[0] + c_var)),
                    max(40, min(200, base[1] + c_var)),
                    max(40, min(200, base[2] + c_var)),
                )

                # Deep shadow (darkest inner ring)
                shadow_color = (
                    max(40, stone_color[0] - 30),
                    max(40, stone_color[1] - 30),
                    max(40, stone_color[2] - 30),
                )
                pygame.draw.circle(
                    surface,
                    shadow_color,
                    (x + sx + s_off[0], y + sy + s_off[1]),
                    sr + 1,
                )

                # Main stone body
                pygame.draw.circle(surface, stone_color, (x + sx, y + sy), sr)

                # Subtle mid-tone ring for depth
                mid_color = (
                    (stone_color[0] + shadow_color[0]) // 2,
                    (stone_color[1] + shadow_color[1]) // 2,
                    (stone_color[2] + shadow_color[2]) // 2,
                )
                pygame.draw.circle(surface, mid_color, (x + sx, y + sy), sr, 1)

                # Top highlight (bright edge)
                highlight_color = (
                    min(255, stone_color[0] + 40),
                    min(255, stone_color[1] + 40),
                    min(255, stone_color[2] + 40),
                )
                h_size = max(1, sr // 3)
                pygame.draw.circle(
                    surface,
                    highlight_color,
                    (x + sx + h_off[0], y + sy + h_off[1]),
                    h_size,
                )

                # Micro-shine dot on highlight
                pygame.draw.circle(
                    surface,
                    (255, 255, 255),
                    (x + sx + h_off[0], y + sy + h_off[1]),
                    max(1, h_size - 1),
                )
>>>>>>> Stashed changes

        elif t.type == TILE_MUD:
            for streak_x in tx.get("streaks", []):
                pygame.draw.line(
                    surface,
                    (88, 54, 26),
                    (x + streak_x, y + 8),
                    (x + streak_x + 4, y + 14),
                    1,
                )

        # ── Water edge blending ────────────────────────────────────────────────
        if t.type == TILE_WATER:
            for dc, dr, rx, ry, rw, rh in [
                (-1, 0, 0, 0, 6, TILE_SIZE),
                (1, 0, TILE_SIZE - 6, 0, 6, TILE_SIZE),
                (0, -1, 0, 0, TILE_SIZE, 6),
                (0, 1, 0, TILE_SIZE - 6, TILE_SIZE, 6),
            ]:
                n = self.get(t.col + dc, t.row + dr)
                if n and n.type != TILE_WATER:
                    es = pygame.Surface((rw, rh), pygame.SRCALPHA)
                    pygame.draw.rect(
                        es, (60, 150, 220, 70), es.get_rect(), border_radius=3
                    )
                    surface.blit(es, (x + rx, y + ry))

        # ── Field edge blending ────────────────────────────────────────────────
        if t.type == TILE_FIELD:
            for dc, dr, rx, ry, rw, rh in [
                (-1, 0, 0, 0, 4, TILE_SIZE),
                (1, 0, TILE_SIZE - 4, 0, 4, TILE_SIZE),
                (0, -1, 0, 0, TILE_SIZE, 4),
                (0, 1, 0, TILE_SIZE - 4, TILE_SIZE, 4),
            ]:
                n = self.get(t.col + dc, t.row + dr)
                if n and n.type in (TILE_DIRT, TILE_GRASS):
                    es = pygame.Surface((rw, rh), pygame.SRCALPHA)
                    pygame.draw.rect(es, (130, 88, 50, 70), es.get_rect())
                    surface.blit(es, (x + rx, y + ry))

        # ── Crop rendering ─────────────────────────────────────────────────────
        if t.type == TILE_FIELD and t.crop != CROP_NONE:
            self._draw_crop(surface, t, x, y, tick)

        # ── Tile border (subtle) ──────────────────────────────────────────────
        pygame.draw.rect(
            surface, (0, 0, 0, 55), tile_rect, 1, border_radius=TILE_RADIUS
        )

    # ── Crop drawing ──────────────────────────────────────────────────────────

    def _draw_crop(self, surface, t: Tile, x: int, y: int, tick: int):
        cc = CROP_COLOR[t.crop]
        cx = x + TILE_SIZE // 2
        cy = y + TILE_SIZE // 2

        if t.crop_stage == 0:
            # Seed — small round dot with highlight
            pygame.draw.circle(surface, (195, 160, 95), (cx, cy), 4)
            pygame.draw.circle(surface, (220, 195, 135), (cx - 1, cy - 1), 2)

        elif t.crop_stage == 1:
            # Sprout — thin stem + two leaves
            stem_top = (cx, cy - 8)
            pygame.draw.line(surface, (90, 165, 55), (cx, cy + 5), stem_top, 2)
            pygame.draw.line(surface, (90, 165, 55), stem_top, (cx - 6, cy - 1), 2)
            pygame.draw.line(surface, (90, 165, 55), stem_top, (cx + 6, cy - 1), 2)

        elif t.crop_stage == 2:
            # Mid-growth — thicker stem + bud
            stem_top = (cx, cy - 12)
            pygame.draw.line(surface, (75, 148, 42), (cx, cy + 6), stem_top, 3)
            pygame.draw.circle(surface, cc, stem_top, 5)
            pygame.draw.circle(
                surface,
                tuple(min(255, v + 50) for v in cc),
                (stem_top[0] - 1, stem_top[1] - 1),
                2,
            )

        else:
            # Stage 3 — fully grown, type-specific
            self._draw_mature_crop(surface, t, x, y, cx, cy, tick)

    def _draw_mature_crop(self, surface, t: Tile, x, y, cx, cy, tick):
        cc = CROP_COLOR[t.crop]

        # Glow shadow ellipse under every mature crop
        if t.crop in CROP_GLOW_COLOR:
            glow_surf = pygame.Surface((TILE_SIZE, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(
                glow_surf, CROP_GLOW_COLOR[t.crop], glow_surf.get_rect()
            )
            surface.blit(glow_surf, (x, y + TILE_SIZE - 12))

        if t.crop == CROP_WHEAT:
            # Three wheat stalks
            for i, ox in enumerate((-7, 0, 7)):
                sx = cx + ox
                sy_bot = y + TILE_SIZE - 6
                sy_top = y + TILE_SIZE - 24
                pygame.draw.line(surface, (165, 128, 40), (sx, sy_bot), (sx, sy_top), 3)
                # Wheat head (oval)
                pygame.draw.ellipse(surface, cc, (sx - 4, sy_top - 6, 8, 10))
                pygame.draw.ellipse(surface, (255, 220, 90), (sx - 3, sy_top - 5, 5, 6))
                # Awns
                for j in range(-1, 2):
                    pygame.draw.line(
                        surface,
                        cc,
                        (sx, sy_top - 3 + j * 3),
                        (sx + 6, sy_top - 5 + j * 3),
                        1,
                    )

        elif t.crop == CROP_SUNFLOWER:
            stem_top = (cx, cy - 14)
            pygame.draw.line(surface, (75, 148, 42), (cx, cy + 8), stem_top, 3)
            # Petals (8 petals)
            for angle in range(0, 360, 45):
                rad = math.radians(angle + tick * 0.5)  # very slow rotation
                px = stem_top[0] + int(10 * math.cos(rad))
                py = stem_top[1] + int(10 * math.sin(rad))
                pygame.draw.ellipse(surface, cc, (px - 4, py - 3, 8, 6))
            # Centre disc
            pygame.draw.circle(surface, (60, 30, 8), stem_top, 6)
            pygame.draw.circle(surface, (90, 50, 15), stem_top, 4)

        elif t.crop == CROP_CORN:
            stem_top = (cx, cy - 16)
            pygame.draw.line(surface, (65, 128, 35), (cx, cy + 8), stem_top, 4)
            # Two leaves
            pygame.draw.line(surface, (90, 165, 50), (cx, cy), (cx - 10, cy - 8), 2)
            pygame.draw.line(
                surface, (90, 165, 50), (cx, cy - 6), (cx + 10, cy - 14), 2
            )
            # Cob
            pygame.draw.rect(
                surface, (200, 165, 50), (cx - 5, cy - 14, 10, 18), border_radius=4
            )
            # Corn kernel rows (dots)
            for kr in range(3):
                for kc in range(2):
                    pygame.draw.circle(
                        surface, (230, 200, 80), (cx - 3 + kc * 6, cy - 11 + kr * 5), 2
                    )

        # Shimmer sparkle on all mature crops (tick-driven, not random)
        shimmer_alpha = int(20 + 18 * math.sin(tick * 0.18 + t.col * 0.5))
        sp_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(sp_surf, (255, 255, 210, shimmer_alpha), (2, 2), 2)
        surface.blit(sp_surf, (cx - 8, cy - 8))
        surface.blit(sp_surf, (cx + 4, cy - 4))

    # ── Season tint ───────────────────────────────────────────────────────────

    def _draw_season_tint(self, surface, season_index: int):
        tint_color = SEASON_TINTS.get(season_index)
        if not tint_color:
            return
        grid_w = self.cols * TILE_SIZE
        grid_h = self.rows * TILE_SIZE
        if season_index not in self._tint_surf_cache:
            tint = pygame.Surface((grid_w, grid_h), pygame.SRCALPHA)
            tint.fill(tint_color)
            self._tint_surf_cache[season_index] = tint
<<<<<<< Updated upstream
        surface.blit(self._tint_surf_cache[season_index],
                     (GRID_OFFSET_X, GRID_OFFSET_Y))
=======
        surface.blit(
            self._tint_surf_cache[season_index], (GRID_OFFSET_X, GRID_OFFSET_Y)
        )
>>>>>>> Stashed changes
