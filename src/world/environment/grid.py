# world/grid.py  —  Verdant Valley
# Tile grid with baked textures (no per-frame random calls), rounded corners,
# top-face highlights, crop shadow glows, hover highlight, and season tint overlay.
#
# Extended with dynamic tile state for CSP-friendly domains:
# - per-tile base_domain / domain
# - flooded / muddy flags and flood_timer
# - utility score (float) used by heuristics
# - helpers: set_flooded, set_muddy, set_type, prune_for_season, prune_for_time_of_day
# - Grid.update_tick to decrement timers and optionally run time/season pruning
# - apply_rain updated to mark wet/muddy/flooded tiles and maintain domains


import random
import math
import sys
import os

import pygame
from utils.constants import SEASON_DURATION

# Load mud puddle sprite (global cache)
MUD_PUDDLE_SPRITE = None
def _get_mud_puddle_sprite():
    global MUD_PUDDLE_SPRITE
    if MUD_PUDDLE_SPRITE is not None:
        return MUD_PUDDLE_SPRITE
    puddle_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "assets", "tiles", "mud_puddle.png"
    )
    if os.path.exists(puddle_path):
        try:
            img = pygame.image.load(puddle_path)
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            # Scale to tile size if needed
            if img.get_width() != TILE_SIZE or img.get_height() != TILE_SIZE:
                img = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
            MUD_PUDDLE_SPRITE = img
            return MUD_PUDDLE_SPRITE
        except Exception:
            pass
    MUD_PUDDLE_SPRITE = None
    return None

# Load snow stone sprite (global cache)
SNOW_STONE_SPRITE = None
def _get_snow_stone_sprite():
    global SNOW_STONE_SPRITE
    if SNOW_STONE_SPRITE is not None:
        return SNOW_STONE_SPRITE
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "assets", "tiles", "Snow_Stone.png"
    )
    if os.path.exists(path):
        try:
            img = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            if img.get_width() != TILE_SIZE or img.get_height() != TILE_SIZE:
                img = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
            SNOW_STONE_SPRITE = img
            return SNOW_STONE_SPRITE
        except Exception:
            pass
    SNOW_STONE_SPRITE = None
    return None

# Load winter snow sprite (global cache)
WINTER_SNOW_SPRITE = None
def _get_winter_snow_sprite():
    global WINTER_SNOW_SPRITE
    if WINTER_SNOW_SPRITE is not None:
        return WINTER_SNOW_SPRITE
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "assets", "tiles", "Winter_Snow.png"
    )
    if os.path.exists(path):
        try:
            img = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            if img.get_width() != TILE_SIZE or img.get_height() != TILE_SIZE:
                img = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
            WINTER_SNOW_SPRITE = img
            return WINTER_SNOW_SPRITE
        except Exception:
            pass
    WINTER_SNOW_SPRITE = None
    return None

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
    TILE_SNOW_STONE,
    TILE_WINTER_SNOW,
    TILE_DARK_MUD,
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
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
SPRING_TILEMAP_PATH = os.path.join(
    REPO_ROOT,
    "assets",
    "Verdant Valley Sprites",
    "Tiny Wonder Farm Free",
    "tilemaps",
    "spring farm tilemap.png",
)
SPRING_TILE_SIZE = 16
STONE_TILE_COORD = (7, 16)
STONE_ASSET_PATHS = [
    os.path.join(REPO_ROOT, "assets", "images", "final_stone.jpg"),
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


def _bake_snow_stone(col, row):
    """Snow stone uses sprite — minimal bake data."""
    return {}

def _bake_dark_mud(col, row):
    """Dark mud: heavier clumps + puddle overlay."""
    rng = random.Random(col * 1234 + row * 89 + 42)
    clumps = []
    for _ in range(8):  # more clumps for dark mud
        cx = rng.randint(3, TILE_SIZE - 5)
        cy = rng.randint(6, TILE_SIZE - 4)
        cw = rng.randint(6, 12)
        ch = rng.randint(4, 8)
        clumps.append((cx, cy, cw, ch))
    streaks = []
    for i in range(0, TILE_SIZE, 7):
        ox = rng.randint(-1, 1)
        streaks.append(i + ox)
    return {"clumps": clumps, "streaks": streaks, "heavy": True}


def _bake_winter_snow(col, row):
    """Winter snow uses sprite — minimal bake data."""
    return {}


BAKE_FN = {
    TILE_GRASS: _bake_grass,
    TILE_DIRT: _bake_dirt,
    TILE_STONE: _bake_stone,
    TILE_MUD: _bake_mud,
    TILE_FIELD: _bake_field,
    TILE_WATER: _bake_water,
    TILE_SNOW_STONE: _bake_snow_stone,
    TILE_WINTER_SNOW: _bake_winter_snow,
    TILE_DARK_MUD: _bake_dark_mud,
}


# ── Tile ──────────────────────────────────────────────────────────────────────


class Tile:
    def __init__(self, col, row, tile_type=TILE_GRASS):
        self.col = col
        self.row = row
        # terrain/type
        self.type = tile_type
        # crop data
        self.crop = CROP_NONE
        self.crop_stage = 0  # 0-3

        # dynamic environmental flags used by CSP heuristics
        self.wet = False
        self.frozen = False
        self.managed_growth = False

        # flooding/muddy state (new)
        self.flooded = False
        self.muddy = False
        # ticks remaining until flood clears (0 or None = not scheduled)
        self.flood_timer = 0

        # Winter freeze: remember original tile type for restoration (store as int, not None)
        self._pre_freeze_type = -1
        self._rain_restore_type = -1
        self._winter_slush = False
        # Thaw stage: 0=normal, 1=mud_puddle, 2=dirt/mud, 3=restoring
        self._thaw_stage = 0
        self._thaw_timer = 0

        # utility multiplier used by heuristics (0.0 - 1.0)
        self.utility = 1.0

        # domain management for CSP:
        # base_domain is derived from self.type (what the tile would allow normally)
        # domain is the currently-pruned list (season, night, flood, manual pruning)
        self.base_domain = self._base_domain_for_type()
        self.domain = list(self.base_domain)

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

    # ── Domain & dynamic state helpers (new) ────────────────────────────────

    def _base_domain_for_type(self):
        """Return the list of crops normally allowed for this tile type."""
        # NOTE: Keep this conservative; CSP/season/time functions prune further.
        if self.type in (TILE_FIELD, TILE_DIRT):
            # Fields and dirt can host core crops
            return [CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_NONE]
        if self.type == TILE_GRASS:
            # Grass supports fewer plant types (for example: flower/herb)
            # We include corn/wheat as disallowed here to encourage CSP to prefer fields.
            return [CROP_SUNFLOWER, CROP_NONE]
        # Water/stone/mud have no plantable crops by default (mud still may be plantable in some rules)
        if self.type == TILE_MUD:
            # Mud is plantable but with lower utility; keep some crops allowed.
            return [CROP_WHEAT, CROP_NONE]
        # Snow tiles are not plantable
        if self.type in (TILE_SNOW_STONE, TILE_WINTER_SNOW):
            return [CROP_NONE]
        return [CROP_NONE]

    def set_type(self, new_type):
        """Change tile type (keeps baked textures in sync and updates base_domain)."""
        self.type = new_type
        # re-bake texture for the new tile type
        self.bake()
        # refresh base domain & reset domain if not flooded
        self.base_domain = self._base_domain_for_type()
        if not self.flooded:
            self.domain = list(self.base_domain)
        # reset some dynamic flags sensibly
        if new_type == TILE_WATER:
            self.wet = True
        else:
            self.wet = False

    def set_flooded(self, flooded: bool, duration_ticks: int | None = None):
        """Set or clear a flooded hard-constraint. Flooded tiles' domain -> [CROP_NONE]."""
        self.flooded = flooded
        if flooded:
            # hard constraint: only CROP_NONE allowed
            self.domain = [CROP_NONE]
            self.utility = 0.0
            self.wet = True
            if duration_ticks:
                self.flood_timer = int(duration_ticks)
        else:
            # clear flooding and restore domain from base (season/time pruning may run later)
            self.flood_timer = 0
            self.flooded = False
            # restore domain from base domain
            self.domain = list(self.base_domain)
            # restore utility heuristic default for type
            if self.type == TILE_GRASS:
                self.utility = 1.0
            elif self.type == TILE_MUD:
                self.utility = 0.5
            else:
                self.utility = 0.9

    def set_muddy(self, muddy: bool):
        """Mark/unmark muddy (non-hard) state. muddy reduces utility but keeps planting allowed."""
        self.muddy = muddy
        if muddy:
            self.utility = 0.5
            # keep domain but deprioritize via utility
            if CROP_NONE not in self.domain:
                # ensure CROP_NONE is always available as fallback
                self.domain.append(CROP_NONE)
        else:
            # restore utility based on type
            if self.type == TILE_GRASS:
                self.utility = 1.0
            elif self.type == TILE_MUD:
                self.utility = 0.6
            else:
                self.utility = 0.9
            # attempt to restore domain to base if not flooded
            if not self.flooded:
                self.domain = list(self.base_domain)

    def restore_domain(self):
        """Restore domain from base_domain unless flooded."""
        if self.flooded:
            self.domain = [CROP_NONE]
        else:
            self.domain = list(self.base_domain)

    def prune_for_season(self, season_index: int):
        """
        Prune domain based on season index.
        Convention: 0=spring, 1=summer, 2=autumn, 3=winter (matches SEASON_TINTS usage).
        Winter removes heat-loving crops (e.g., corn).
        """
        if self.flooded:
            return
        # start from base domain and prune into domain
        allowed = list(self.base_domain)
        # Winter restriction: only corn is plantable.
        if season_index == 3:
            allowed = [v for v in allowed if v in (CROP_NONE, CROP_CORN)]
        # other seasons could re-enable additional crops; here we simply assign allowed
        self.domain = allowed

    def prune_for_time_of_day(self, is_night: bool, distance_from_farmer: int = 0):
        """
        Prune domain for night cycles. Far tiles at night shouldn't host high-light crops.
        Example: remove corn for tiles farther than a threshold at night.
        """
        if self.flooded:
            return
        if not is_night:
            # Keep season-pruned domain during daytime.
            return
        # Night-time pruning:
        allowed = list(self.domain) if self.domain else list(self.base_domain)
        # If far from farmer, remove high-light crop (corn)
        if distance_from_farmer > 6:
            allowed = [v for v in allowed if v != CROP_CORN]
            # reduce utility for distant tiles at night
            self.utility *= 0.6
        self.domain = allowed


# ── Grid ──────────────────────────────────────────────────────────────────────


class Grid:
    def convert_flooded_to_dark_mud(self):
        """Convert all flooded tiles to dark brown mud (TILE_DARK_MUD)."""
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                if getattr(t, 'flooded', False):
                    t.set_flooded(False)
                    t.set_type(TILE_DARK_MUD)
                    t.set_muddy(False)
                    t.wet = False

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
        self._tint_surf_cache = {}
        # Hovered tile (col, row) — set by caller each frame
        self.hovered = None

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
        """Pre-compute texture data for every tile and refresh base/domain state."""
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                t.bake()
                # refresh base domain according to current type
                t.base_domain = t._base_domain_for_type()
                # If tile is flooded, keep domain=[CROP_NONE], otherwise restore
                if t.flooded:
                    t.domain = [CROP_NONE]
                else:
                    t.domain = list(t.base_domain)

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

    def ripe_crop_tiles(self):
        return [
            (c, r)
            for c in range(self.cols)
            for r in range(self.rows)
            if self.tiles[c][r].crop != CROP_NONE and self.tiles[c][r].crop_stage >= 2
        ]

    def generate_random_crops(self, count):
        """Generate 'count' random crops on field tiles (no CSP)"""
        from utils.constants import CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_TOMATO, CROP_CARROT, CROP_POTATO
        
        # Clear all existing crops
        for c in range(self.cols):
            for r in range(self.rows):
                if self.tiles[c][r].crop != CROP_NONE:
                    self.tiles[c][r].crop = CROP_NONE
                    self.tiles[c][r].crop_stage = 0
        
        # Get list of all field tiles
        field_tiles = [
            (c, r)
            for c in range(self.cols)
            for r in range(self.rows)
            if self.tiles[c][r].type == TILE_FIELD
        ]
        
        # Randomly select tiles for crops
        if len(field_tiles) < count:
            count = len(field_tiles)
        
        selected_tiles = random.sample(field_tiles, count)
        crop_types = [CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_TOMATO, CROP_CARROT, CROP_POTATO]
        
        for c, r in selected_tiles:
            crop_type = random.choice(crop_types)
            self.tiles[c][r].crop = crop_type
            self.tiles[c][r].crop_stage = random.randint(1, 2)

        return len(selected_tiles)

    # ── Rain event ────────────────────────────────────────────────────────────

    def apply_rain(self):
        """
        When rain occurs:
        - mark many tiles wet (t.wet=True)
        - convert susceptible Dirt/Field neighbors into MUD (existing behavior)
        - possibly flood low-lying Field/Dirt tiles (set_flooded)
        - set sensible flood_timer so tiles auto-unflood after a number of ticks
        """
        new_mud = []
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                # mark wet for fields and grass (visual effect & potential utility change)
                if t.type in (TILE_FIELD, TILE_GRASS, TILE_DIRT, TILE_MUD):
                    t.wet = True

                # existing mud propagation logic
                if t.type == TILE_MUD:
                    # Mud automatically becomes flooded/impassable during rain.
                    t.set_flooded(True, duration_ticks=600)
                    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        n = self.get(c + dc, r + dr)
                        if n and n.type in (TILE_DIRT, TILE_GRASS):
                            new_mud.append((c + dc, r + dr))
                if t.type == TILE_FIELD and t.crop == CROP_NONE and random.random() < 0.05:
                    new_mud.append((c, r))

                # Flooding heuristic: if tile is Field or Dirt and adjacent to water, chance to flood
                if t.type in (TILE_FIELD, TILE_DIRT):
                    near_water = False
                    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        neighbor = self.get(c + dc, r + dr)
                        if neighbor is not None and neighbor.type == TILE_WATER:
                            near_water = True
                            break
                    flood_chance = 0.06 if near_water else 0.01
                    if random.random() < flood_chance:
                        # mark flooded with a timer of 600 ticks (10 seconds at 60 FPS)
                        t.set_flooded(True, duration_ticks=600)

                # Field/Grass tiles get wet which affects rendering & utility
                if t.type in (TILE_FIELD, TILE_GRASS):
                    t.wet = True

        for c, r in new_mud:
            if 0 <= c < self.cols and 0 <= r < self.rows:
                tile = self.tiles[c][r]
                if tile._rain_restore_type == -1:
                    tile._rain_restore_type = tile.type
                tile.set_type(TILE_MUD)
                tile.set_muddy(True)
                tile.set_flooded(True, duration_ticks=600)

    def apply_winter_freeze(self):
        """Apply winter visuals, then transition winter snow tiles to slushy flood/mud."""
        rng = random.Random(42)  # deterministic snow placement
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                t.frozen = True
                t._thaw_stage = 0
                t._thaw_timer = 0
                t._winter_slush = False

                if t.type == TILE_WATER:
                    pass

                elif t.type == TILE_STONE:
                    near_water = False
                    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        neighbor = self.get(c + dc, r + dr)
                        if neighbor is not None and neighbor.type == TILE_WATER:
                            near_water = True
                            break
                    if near_water:
                        t._pre_freeze_type = TILE_STONE
                        t.set_type(TILE_SNOW_STONE)

                elif t.type in (TILE_FIELD, TILE_GRASS, TILE_DIRT):
                    # Randomly convert farm tiles to winter snow first.
                    if rng.random() < 0.35:
                        t._pre_freeze_type = t.type
                        t.crop = CROP_NONE
                        t.crop_stage = 0
                        t.set_type(TILE_WINTER_SNOW)
                        # Winter_snow then becomes slushy mud/flood terrain.
                        t._winter_slush = True
                        t.set_type(TILE_MUD)
                        t.set_muddy(True)
                        t.set_flooded(True, duration_ticks=SEASON_DURATION)
                        t.wet = True

                # prune domain for winter
                t.prune_for_season(3)

    def clear_winter_freeze(self):
        """Winter end: revert winter-slush/snow tiles to their original regular terrain."""
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                t.frozen = False

                if t.type == TILE_SNOW_STONE:
                    t.set_type(TILE_STONE)
                    t._pre_freeze_type = -1
                    t._winter_slush = False

                else:
                    if t._winter_slush and t._pre_freeze_type != -1:
                        t.set_flooded(False)
                        t.set_type(t._pre_freeze_type)
                        t.set_muddy(False)
                        t.wet = False
                        t._pre_freeze_type = -1
                        t._winter_slush = False
                    elif t._pre_freeze_type != -1:
                        t.set_type(t._pre_freeze_type)
                        t._pre_freeze_type = -1
                        t._winter_slush = False
                    if not t.flooded:
                        t.restore_domain()

    def _update_thaw(self):
        """Tick thaw timers: mud_puddle -> dirt/mud -> original type."""
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                if t._thaw_stage <= 0:
                    continue

                t._thaw_timer -= 1
                if t._thaw_timer > 0:
                    continue

                if t._thaw_stage == 1:
                    # Stage 1 done: mud_puddle -> dirt
                    t._thaw_stage = 2
                    t._thaw_timer = random.randint(200, 400)
                    t.set_type(TILE_DIRT)
                    t.set_muddy(False)
                    t.wet = False

                elif t._thaw_stage == 2:
                    # Stage 2 done: dirt -> original type
                    original = t._pre_freeze_type if t._pre_freeze_type is not None else TILE_GRASS
                    t.set_type(original)
                    t._pre_freeze_type = -1
                    t._thaw_stage = 0
                    t._thaw_timer = 0
                    t.set_muddy(False)
                    t.wet = False
                    if not t.flooded:
                        t.restore_domain()

    # ── Tick / time helpers (new) ─────────────────────────────────────────────

    def update_tick(self, tick: int, is_night: bool = False, season_index: int | None = None, farmer_pos: tuple[int, int] | None = None):
        """
        Call this from the main loop once per simulation tick (or at a coarser rate).
        Responsibilities:
         - decrement flood timers and auto-unflood when timer elapses
         - optionally run prune_for_time_of_day and prune_for_season per tile
        Note: the CSP solver should be invoked from main when you want to recompute planting plan
              after domain changes. This function only updates per-tile domains/flags.
        """
        # Decrement flood timers and auto-convert floods to dark mud when timer expires
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                if getattr(t, "flood_timer", 0):
                    t.flood_timer -= 1
                    if t.flood_timer <= 0 and t.flooded:
                        # Rain flood reverts to original regular tile after 10 seconds.
                        if t._winter_slush:
                            # Winter slush remains blocked until winter ends.
                            t.flood_timer = 1
                            continue
                        t.set_flooded(False)
                        if t._rain_restore_type != -1:
                            t.set_type(t._rain_restore_type)
                            t._rain_restore_type = -1
                        elif t.type == TILE_MUD:
                            t.set_type(TILE_DIRT)
                        t.set_muddy(False)
                        t.wet = False

        # Prune per-tile domains for time-of-day and season if requested
        for c in range(self.cols):
            for r in range(self.rows):
                t = self.tiles[c][r]
                # distance-from-farmer heuristic for night pruning
                dist = 0
                if farmer_pos:
                    fx, fy = farmer_pos
                    dist = abs(fx - c) + abs(fy - r)
                if season_index is not None:
                    t.prune_for_season(season_index)
                t.prune_for_time_of_day(is_night, dist)

    # ─�� Hover helper ──────────────────────────────────────────────────────────

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

        # ── Draw tiles ───────────────────────────────────────────────────────
        for c in range(self.cols):
            for r in range(self.rows):
                self._draw_tile(surface, self.tiles[c][r], tick)

        # draw buildings after tiles (so they appear on top)
        self.draw_buildings(surface)

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
        tx = t.texture or {}

        base = TILE_COLOR[t.type]
        hi = TILE_HIGHLIGHT[t.type]
        sh = TILE_SHADOW[t.type]

        # Darken when wet
        if t.wet and t.type != TILE_WATER:
            base = tuple(max(0, v - 22) for v in base)
            hi = tuple(max(0, v - 22) for v in hi)

        # Winter freeze tint
        if getattr(t, "frozen", False) and t.type != TILE_WATER:
            base = tuple(int(base[i] * 0.55 + (180, 210, 235)[i] * 0.45) for i in range(3))
            hi = tuple(int(hi[i] * 0.50 + (220, 235, 250)[i] * 0.50) for i in range(3))

        tile_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)

        # ── Base fill ─────────────────────────────────────────────────────────
        pygame.draw.rect(surface, base, tile_rect, border_radius=TILE_RADIUS)

        # overlay for flooded tiles (visual cue)
        if getattr(t, "flooded", False):
            flood_overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            flood_overlay.fill((30, 90, 160, 90))
            surface.blit(flood_overlay, (x, y))

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
            if getattr(t, "frozen", False):
                # Ice rendering — light blue solid with cracks
                ice_base = (180, 210, 240)
                ice_hi = (220, 240, 255)
                pygame.draw.rect(surface, ice_base, (x, y, TILE_SIZE, TILE_SIZE), border_radius=TILE_RADIUS)
                # Ice sheen
                sheen = pygame.Surface((TILE_SIZE, TILE_SIZE // 2), pygame.SRCALPHA)
                sheen.fill((255, 255, 255, 30))
                surface.blit(sheen, (x, y))
                # Cracks
                cx, cy = x + TILE_SIZE // 2, y + TILE_SIZE // 2
                pygame.draw.line(surface, ice_hi, (cx - 8, cy - 5), (cx + 6, cy + 3), 1)
                pygame.draw.line(surface, ice_hi, (cx + 2, cy - 7), (cx - 3, cy + 8), 1)
            else:
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

        elif t.type == TILE_MUD:
            for streak_x in tx.get("streaks", []):
                pygame.draw.line(
                    surface,
                    (88, 54, 26),
                    (x + streak_x, y + 8),
                    (x + streak_x + 4, y + 14),
                    1,
                )
            # Use puddle sprite if wet or flooded
            if getattr(t, "wet", False) or getattr(t, "flooded", False):
                puddle_img = _get_mud_puddle_sprite()
                if puddle_img:
                    # Optionally randomize rotation/flip for variety
                    rng = random.Random(t.col * 100 + t.row)
                    img = puddle_img
                    if rng.choice([True, False]):
                        img = pygame.transform.flip(img, True, False)
                    angle = rng.choice([0, 90, 180, 270])
                    if angle:
                        img = pygame.transform.rotate(img, angle)
                    surface.blit(img, (x, y))
                else:
                    # fallback: draw blue puddle as before
                    pud_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    puddle_color = (110, 130, 160, 210)
                    pygame.draw.ellipse(pud_surf, puddle_color, (4, 8, TILE_SIZE-8, TILE_SIZE-12))
                    surface.blit(pud_surf, (x, y))

        elif t.type == TILE_DARK_MUD:
            # Darker streaks + heavy clumps
            tx_dark = t.texture or _bake_dark_mud(t.col, t.row)
            heavy = tx_dark.get("heavy", False)
            # Dark streaks
            for streak_x in tx_dark.get("streaks", []):
                pygame.draw.line(
                    surface,
                    (50, 28, 10),  # darker than mud
                    (x + streak_x, y + 10),
                    (x + streak_x + 5, y + 16),
                    2,
                )
            # Heavy mud clumps
            for cx, cy, cw, ch in tx_dark.get("clumps", []):
                clump_color = (45, 25, 10)
                pygame.draw.ellipse(surface, clump_color, (x + cx, y + cy, cw, ch))
                # Clump highlight
                pygame.draw.ellipse(surface, (70, 45, 25), (x + cx + 1, y + cy + 1, cw//2, ch//2))
            # Always puddle overlay on dark mud (post-flood look)
            puddle_img = _get_mud_puddle_sprite()
            if puddle_img:
                rng = random.Random(t.col * 200 + t.row * 3)
                img = puddle_img
                if rng.choice([True, False]):
                    img = pygame.transform.flip(img, True, False)
                surface.blit(img, (x + 2, y + 4))
            else:
                # Darker puddle fallback
                pud_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                puddle_color = (80, 60, 30, 220)  # dark brown puddle
                pygame.draw.ellipse(pud_surf, puddle_color, (6, 10, TILE_SIZE-12, TILE_SIZE-16))
                surface.blit(pud_surf, (x, y))

        elif t.type == TILE_SNOW_STONE:
            sprite = _get_snow_stone_sprite()
            if sprite:
                surface.blit(sprite, (x, y))
            else:
                # Fallback: white-tinted stone
                pygame.draw.rect(surface, (200, 210, 220), tile_rect, border_radius=TILE_RADIUS)
                pygame.draw.circle(surface, (230, 235, 240), (x + TILE_SIZE // 2, y + TILE_SIZE // 2), 12)

        elif t.type == TILE_WINTER_SNOW:
            sprite = _get_winter_snow_sprite()
            if sprite:
                surface.blit(sprite, (x, y))
            else:
                # Fallback: light snow color
                pygame.draw.rect(surface, (220, 230, 245), tile_rect, border_radius=TILE_RADIUS)
                # Small snow mound
                pygame.draw.ellipse(surface, (240, 245, 255), (x + 8, y + 12, TILE_SIZE - 16, TILE_SIZE - 20))

        # ── Water edge blending ───────────────────────────────────────────────
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
        if t.crop != CROP_NONE:
            self._draw_crop(surface, t, x, y, tick)

        # ── Tile border (subtle) ──────────────────────────────────────────────
        pygame.draw.rect(
            surface, (0, 0, 0, 55), tile_rect, 1, border_radius=TILE_RADIUS
        )

        if getattr(t, "frozen", False) and t.type != TILE_WATER:
            frost = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            frost.fill((210, 235, 255, 50))
            # Snow dots
            import random as _rng
            seed = t.col * 31 + t.row * 17
            for i in range(4):
                sx = (seed * (i + 1) * 7) % (TILE_SIZE - 4) + 2
                sy = (seed * (i + 1) * 13) % (TILE_SIZE - 4) + 2
                pygame.draw.circle(frost, (240, 248, 255, 90), (sx, sy), 2)
            surface.blit(frost, (x, y))

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
        surface.blit(
            self._tint_surf_cache[season_index], (GRID_OFFSET_X, GRID_OFFSET_Y)
        )
