import pygame

# ============================================================================
# SCREEN & GRID DIMENSIONS - FIXED FOR 18 COLUMNS
# ============================================================================

FPS = 60
TILE_SIZE = 48
GRID_COLS, GRID_ROWS = 18, 14
SIDEBAR_W = 320
GRID_OFFSET_X, GRID_OFFSET_Y = 0, 80

# FORCE LARGER SCREEN - THIS IS THE FIX
# 18 columns * 48px = 864px for grid + 320px sidebar = 1184px minimum
SCREEN_W = 1280  # FORCED to show all 18 columns
SCREEN_H = 800  # FORCED for good height

print(f"🔴 FIXED SCREEN SIZE: {SCREEN_W} x {SCREEN_H}")
print(f"🔴 GRID SIZE: {GRID_COLS} x {GRID_ROWS} (18x14)")
print(f"🔴 Grid takes {GRID_COLS * TILE_SIZE}px, Sidebar takes {SIDEBAR_W}px")

# ============================================================================
# COLOR PALETTE
# ============================================================================

C_BG_DARK = (18, 26, 18)
C_BG_MID = (28, 40, 28)
C_BG_PANEL = (22, 33, 22)
C_PANEL_BORD = (80, 120, 80)
C_HUD_BG = (14, 20, 14)
C_HUD_BORD = (60, 100, 60)

C_TEXT_MAIN = (240, 255, 230)
C_TEXT_DIM = (160, 190, 150)
C_TEXT_GOLD = (255, 215, 100)
C_TEXT_WARN = (255, 120, 60)
C_TEXT_SUCCESS = (100, 255, 100)
C_TEXT_TITLE = (255, 220, 150)

C_FARMER = (100, 200, 80)
C_GUARD = (220, 80, 60)
C_ANIMAL = (240, 180, 60)
C_GRASS = (80, 160, 60)

C_BUTTON_NORMAL = (40, 70, 40)
C_BUTTON_HOVER = (60, 100, 60)
C_BUTTON_PRESSED = (30, 50, 30)
C_PROGRESS_BG = (30, 40, 30)
C_PROGRESS_FILL = (100, 200, 80)

C_PATH_FARMER = (100, 255, 100)
C_PATH_GUARD = (255, 100, 80)
C_PATH_ANIMAL = (255, 200, 100)
C_EXPLORED = (255, 255, 100, 60)

# ============================================================================
# TILE TYPES
# ============================================================================

TILE_GRASS, TILE_DIRT, TILE_STONE, TILE_MUD, TILE_WATER, TILE_FIELD = 0, 1, 2, 3, 4, 5
TILE_SNOW_STONE = 6
TILE_WINTER_SNOW = 7
TILE_DARK_MUD = 8

# ============================================================================
# TILE MOVEMENT COSTS
# ============================================================================

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

FARMER_COSTS = {
    TILE_GRASS: 1.0,
    TILE_DIRT: 1.0,
    TILE_FIELD: 1.0,
    TILE_MUD: float("inf"),
    TILE_WATER: float("inf"),
    TILE_STONE: float("inf"),
    TILE_SNOW_STONE: float("inf"),
    TILE_WINTER_SNOW: float("inf"),
    TILE_DARK_MUD: float("inf"),
}

GUARD_COSTS = {
    TILE_GRASS: 1.0,
    TILE_DIRT: 1.0,
    TILE_FIELD: 1.0,
    TILE_MUD: float("inf"),
    TILE_WATER: float("inf"),
    TILE_STONE: float("inf"),
    TILE_SNOW_STONE: float("inf"),
    TILE_WINTER_SNOW: float("inf"),
    TILE_DARK_MUD: float("inf"),
}

ANIMAL_COSTS = {
    TILE_GRASS: 1.0,
    TILE_DIRT: 1.0,
    TILE_FIELD: 1.0,
    TILE_MUD: 2.0,
    TILE_WATER: float("inf"),
    TILE_STONE: float("inf"),
    TILE_SNOW_STONE: float("inf"),
    TILE_WINTER_SNOW: 2.0,
    TILE_DARK_MUD: 2.0,
}

# ============================================================================
# TILE COLORS
# ============================================================================

TILE_COLOR = {
    TILE_GRASS: (38, 120, 38),
    TILE_DIRT: (122, 72, 28),
    TILE_STONE: (142, 140, 132),
    TILE_MUD: (80, 50, 22),
    TILE_WATER: (20, 80, 160),
    TILE_FIELD: (118, 66, 22),
    TILE_SNOW_STONE: (180, 200, 220),
    TILE_WINTER_SNOW: (220, 235, 248),
    TILE_DARK_MUD: (60, 35, 15),
}

TILE_HIGHLIGHT = {
    TILE_GRASS: (70, 170, 55),
    TILE_DIRT: (162, 102, 52),
    TILE_STONE: (188, 186, 178),
    TILE_MUD: (108, 72, 38),
    TILE_WATER: (40, 120, 210),
    TILE_FIELD: (158, 96, 44),
    TILE_SNOW_STONE: (210, 225, 240),
    TILE_WINTER_SNOW: (240, 248, 255),
    TILE_DARK_MUD: (90, 55, 28),
}

TILE_SHADOW = {
    TILE_GRASS: (18, 80, 18),
    TILE_DIRT: (82, 42, 8),
    TILE_STONE: (100, 98, 92),
    TILE_MUD: (50, 28, 8),
    TILE_WATER: (8, 40, 110),
    TILE_FIELD: (78, 36, 8),
    TILE_SNOW_STONE: (140, 155, 175),
    TILE_WINTER_SNOW: (180, 200, 220),
    TILE_DARK_MUD: (40, 20, 8),
}

TILE_RADIUS = 3

# ============================================================================
# CROP SYSTEM
# ============================================================================

(
    CROP_NONE,
    CROP_WHEAT,
    CROP_SUNFLOWER,
    CROP_CORN,
    CROP_TOMATO,
    CROP_CARROT,
    CROP_POTATO,
) = (0, 1, 2, 3, 4, 5, 6)

CROP_NAMES = {
    0: "Empty",
    1: "Wheat",
    2: "Sunflower",
    3: "Corn",
    4: "Tomato",
    5: "Carrot",
    6: "Potato",
}

CROP_COLOR = {
    0: (70, 55, 30),
    1: (230, 200, 60),
    2: (255, 190, 20),
    3: (160, 210, 50),
    4: (220, 40, 40),
    5: (255, 140, 40),
    6: (180, 140, 80),
}

CROP_GLOW_COLOR = {
    CROP_WHEAT: (200, 160, 30, 55),
    CROP_SUNFLOWER: (230, 170, 20, 55),
    CROP_CORN: (160, 200, 40, 55),
    CROP_TOMATO: (200, 30, 30, 55),
    CROP_CARROT: (230, 120, 20, 55),
    CROP_POTATO: (160, 120, 60, 55),
}

CROP_VALUE = {0: 0, 1: 10, 2: 20, 3: 15, 4: 25, 5: 18, 6: 12}

# ============================================================================
# UI & HOVER EFFECTS
# ============================================================================

C_TILE_HOVER_BORDER = (140, 240, 100)
C_TILE_HOVER_FILL = (100, 220, 70, 30)

# ============================================================================
# SEASON SYSTEM
# ============================================================================

SEASON_TINTS = {
    0: (60, 180, 60, 12),
    1: (255, 220, 80, 10),
    2: (200, 100, 20, 18),
    3: (160, 200, 240, 22),
}

SEASONS = ["🌱 Spring", "☀️ Summer", "🍂 Autumn", "❄️ Winter"]
SEASON_DURATION = 15 * FPS

# ============================================================================
# GAME STATES
# ============================================================================

STATE_LOADING, STATE_MENU, STATE_CSP_VIZ, STATE_PLAYING = (
    "loading",
    "menu",
    "csp_viz",
    "playing",
)
STATE_PAUSED, STATE_GA_VIZ, STATE_GAMEOVER = "paused", "ga_viz", "gameover"

# ============================================================================
# FONT SIZES
# ============================================================================

FONT_HUGE, FONT_TITLE, FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY = (
    72,
    48,
    28,
    20,
    15,
    12,
)
FONT_NAME = "Arial"
