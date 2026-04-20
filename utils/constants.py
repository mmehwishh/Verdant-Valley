
import pygame

# ...existing code...


FPS = 60
TILE_SIZE = 48
GRID_COLS, GRID_ROWS = 18, 14
SIDEBAR_W = 320
GRID_OFFSET_X, GRID_OFFSET_Y = 0, 80

SCREEN_W = GRID_COLS * TILE_SIZE + SIDEBAR_W
SCREEN_H = GRID_ROWS * TILE_SIZE + GRID_OFFSET_Y

# Enhanced Color Palette
C_BG_DARK = (18, 26, 18)
C_BG_MID = (28, 40, 28)
C_BG_PANEL = (22, 33, 22)
C_PANEL_BORD = (80, 120, 80)
C_HUD_BG = (14, 20, 14)
C_HUD_BORD = (60, 100, 60)

# Text Colors
C_TEXT_MAIN = (240, 255, 230)
C_TEXT_DIM = (160, 190, 150)
C_TEXT_GOLD = (255, 215, 100)
C_TEXT_WARN = (255, 120, 60)
C_TEXT_SUCCESS = (100, 255, 100)
C_TEXT_TITLE = (255, 220, 150)

# Agent Colors
C_FARMER = (100, 200, 80)
C_GUARD = (220, 80, 60)
C_ANIMAL = (240, 180, 60)
C_GRASS = (80, 160, 60)

# UI Element Colors
C_BUTTON_NORMAL = (40, 70, 40)
C_BUTTON_HOVER = (60, 100, 60)
C_BUTTON_PRESSED = (30, 50, 30)
C_PROGRESS_BG = (30, 40, 30)
C_PROGRESS_FILL = (100, 200, 80)

# Path Colors
C_PATH_FARMER = (100, 255, 100)
C_PATH_GUARD = (255, 100, 80)
C_PATH_ANIMAL = (255, 200, 100)
C_EXPLORED = (255, 255, 100, 60)

TILE_GRASS, TILE_DIRT, TILE_STONE, TILE_MUD, TILE_WATER, TILE_FIELD = 0, 1, 2, 3, 4, 5
TILE_SNOW_STONE = 6   # stone covered in snow (winter)
TILE_WINTER_SNOW = 7  # farm tile covered in snow (winter)
TILE_DARK_MUD = 8     # dark brown mud (post-flood)
TILE_COST = {
    TILE_GRASS: 1.0,
    TILE_DIRT: 1.0,
    TILE_STONE: 0.5,
    TILE_MUD: 3.0,
    TILE_WATER: 999,
    TILE_FIELD: 1.0,
TILE_SNOW_STONE: 1.2,
    TILE_WINTER_SNOW: 2.5,
    TILE_DARK_MUD: 4.0,
}

# Agent Movement Costs
FARMER_COSTS = {
    TILE_GRASS: 1.0,
    TILE_DIRT: 1.0,
    TILE_FIELD: 1.0,
    TILE_MUD: float('inf'),
    TILE_WATER: float('inf'),
    TILE_STONE: float('inf'),
    TILE_SNOW_STONE: float('inf'),
    TILE_WINTER_SNOW: float('inf'),
    TILE_DARK_MUD: float('inf'),  # Dark mud is impassable for Farmer (treated like blocked terrain)
}

GUARD_COSTS = {
    TILE_GRASS: 1.0,
    TILE_DIRT: 1.0,
    TILE_FIELD: 1.0,
    TILE_MUD: float('inf'),
    TILE_WATER: float('inf'),
    TILE_STONE: float('inf'),
    TILE_SNOW_STONE: float('inf'),
    TILE_WINTER_SNOW: float('inf'),
    TILE_DARK_MUD: float('inf'),  # Dark mud is impassable for Guard (treated like blocked terrain)
}

ANIMAL_COSTS = {
    TILE_GRASS: 1.0,
    TILE_DIRT: 1.0,
    TILE_FIELD: 1.0,
    TILE_MUD: 1.0,
    TILE_WATER: 1.0,
    TILE_STONE: 1.0,
    TILE_SNOW_STONE: 1.0,
    TILE_WINTER_SNOW: 1.0,
    TILE_DARK_MUD: 1.0,
}

# ── Tile Base Colors (richer, more saturated) ────────────────────────────────
TILE_COLOR = {
    TILE_GRASS: (38, 120, 38),   # deep forest green
    TILE_DIRT:  (122, 72, 28),   # warm saddle brown
    TILE_STONE: (142, 140, 132), # warm gray stone
    TILE_MUD:   (80, 50, 22),    # dark wet mud
    TILE_WATER: (20, 80, 160),   # rich deep blue
    TILE_FIELD: (118, 66, 22),   # tilled dark sienna
    TILE_SNOW_STONE: (180, 200, 220),  # snowy stone
    TILE_WINTER_SNOW: (220, 235, 248), # winter snow
    TILE_DARK_MUD: (60, 35, 15),    # post-flood dark mud
}

# ── Tile Highlight (top-face lighter shade) ───────────────────────────────────
TILE_HIGHLIGHT = {
    TILE_GRASS: (70, 170, 55),
    TILE_DIRT:  (162, 102, 52),
    TILE_STONE: (188, 186, 178),
    TILE_MUD:   (108, 72, 38),
    TILE_WATER: (40, 120, 210),
    TILE_FIELD: (158, 96, 44),
    TILE_SNOW_STONE: (210, 225, 240),
    TILE_WINTER_SNOW: (240, 248, 255),
    TILE_DARK_MUD: (90, 55, 28),    # darker mud highlight
}

# ── Tile Shadow (bottom-face darker shade) ───────────────────────────────────
TILE_SHADOW = {
    TILE_GRASS: (18, 80, 18),
    TILE_DIRT:  (82, 42, 8),
    TILE_STONE: (100, 98, 92),
    TILE_MUD:   (50, 28, 8),
    TILE_WATER: (8, 40, 110),
    TILE_FIELD: (78, 36, 8),
    TILE_SNOW_STONE: (140, 155, 175),
    TILE_WINTER_SNOW: (180, 200, 220),
    TILE_DARK_MUD: (40, 20, 8),     # darkest mud shadow
}

# ── Tile corner radius ────────────────────────────────────────────────────────
TILE_RADIUS = 3

# ── Crops ─────────────────────────────────────────────────────────────────────
CROP_NONE, CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_TOMATO, CROP_CARROT, CROP_POTATO = 0, 1, 2, 3, 4, 5, 6
CROP_NAMES = {0: "Empty", 1: "Wheat", 2: "Sunflower", 3: "Corn", 4: "Tomato", 5: "Carrot", 6: "Potato"}
CROP_COLOR = {
    0: (70, 55, 30),
    1: (230, 200, 60),    # wheat gold
    2: (255, 190, 20),    # sunflower yellow
    3: (160, 210, 50),    # corn green
    4: (220, 40, 40),     # tomato red
    5: (255, 140, 40),    # carrot orange
    6: (180, 140, 80),    # potato brown
}

# Glow/shadow ellipse color under mature crops
CROP_GLOW_COLOR = {
    CROP_WHEAT:     (200, 160, 30, 55),
    CROP_SUNFLOWER: (230, 170, 20, 55),
    CROP_CORN:      (160, 200, 40, 55),
    CROP_TOMATO:    (200, 30, 30, 55),
    CROP_CARROT:    (230, 120, 20, 55),
    CROP_POTATO:    (160, 120, 60, 55),
}

CROP_VALUE = {0: 0, 1: 10, 2: 20, 3: 15, 4: 25, 5: 18, 6: 12}

# ── Hover tile ────────────────────────────────────────────────────────────────
C_TILE_HOVER_BORDER = (140, 240, 100)
C_TILE_HOVER_FILL   = (100, 220, 70, 30)   # SRCALPHA overlay

# ── Season tints (RGBA overlay on entire grid) ───────────────────────────────
SEASON_TINTS = {
    0: (60, 180, 60,  12),   # Spring: fresh green
    1: (255, 220, 80, 10),   # Summer: warm yellow
    2: (200, 100, 20, 18),   # Autumn: amber orange
    3: (160, 200, 240, 22),  # Winter: cold blue
}

# Game States
STATE_LOADING, STATE_MENU, STATE_CSP_VIZ, STATE_PLAYING = (
    "loading", "menu", "csp_viz", "playing",
)
STATE_PAUSED, STATE_GA_VIZ, STATE_GAMEOVER = "paused", "ga_viz", "gameover"

# Seasons
SEASONS = ["🌱 Spring", "☀️ Summer", "🍂 Autumn", "❄️ Winter"]
SEASON_DURATION = 15 * FPS

# Font Sizes
FONT_HUGE, FONT_TITLE, FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY = (
    72, 48, 28, 20, 15, 12,
)

FONT_NAME = "Arial"