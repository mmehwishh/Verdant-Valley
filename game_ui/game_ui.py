# ── Blocked Tile Cross Overlay ─────────────────────────────────────────────

def draw_blocked_tile_cross(surface, col, row, grid, color=(220, 40, 40), size=32, thickness=4):
    """Draw a red cross on the specified tile (blocked movement indicator)."""
    import pygame
    x, y = grid_to_px(col, row)
    cx = x + grid.tiles[col][row].rect().width // 2
    cy = y + grid.tiles[col][row].rect().height // 2
    half = size // 2
    pygame.draw.line(surface, color, (cx - half, cy - half), (cx + half, cy + half), thickness)
    pygame.draw.line(surface, color, (cx - half, cy + half), (cx + half, cy - half), thickness)

# Usage: Call draw_blocked_tile_cross in your main game loop or agent logic when movement is denied.
"""
game_ui.py — all Pygame rendering: loading, menu, HUD, sidebar, CSP panel.
"""

import pygame
import math
import random
from utils.helpers import grid_to_px
from utils.constants import *
from utils.helpers import draw_rounded_rect, draw_text, lerp_color


# ── Font cache ────────────────────────────────────────────────────────────────


class FontCache:
    _cache = {}

    @classmethod
    def get(cls, size, bold=False):
        key = (size, bold)
        if key not in cls._cache:
            try:
                cls._cache[key] = pygame.font.Font(None, size)
            except Exception:
                cls._cache[key] = pygame.font.SysFont("monospace", size, bold=bold)
        return cls._cache[key]


# ── Loading screen ────────────────────────────────────────────────────────────


class LoadingScreen:
    def __init__(self, screen):
        self.screen = screen
        self.progress = 0.0  # 0.0 – 1.0
        self.done = False

        # Particle seeds for decorative leaves
        rng = random.Random(42)
        self.particles = [
            {
                "x": rng.randint(0, SCREEN_W),
                "y": rng.randint(0, SCREEN_H),
                "r": rng.randint(3, 8),
                "vx": rng.uniform(-0.3, 0.3),
                "vy": rng.uniform(-0.5, -0.15),
                "alpha": rng.randint(60, 160),
            }
            for _ in range(60)
        ]
        self._tick = 0

    def update(self, dt=1):
        self._tick += 1
        # Simulate load (replace with real load steps if needed)
        self.progress = min(1.0, self._tick / 120)
        if self.progress >= 1.0:
            self.done = True

        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["y"] < -20:
                p["y"] = SCREEN_H + 10
                p["x"] = random.randint(0, SCREEN_W)

    def draw(self):
        s = self.screen
        s.fill(C_BG_DARK)

        # Floating leaf particles
        leaf_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        for p in self.particles:
            leaf_surf.fill((0, 0, 0, 0))
            pygame.draw.ellipse(leaf_surf, (*C_GRASS, p["alpha"]), (0, 4, 12, 8))
            s.blit(leaf_surf, (int(p["x"]), int(p["y"])))

        # Title
        f_title = FontCache.get(FONT_HUGE, bold=True)
        f_sub = FontCache.get(FONT_LARGE)
        draw_text(
            s,
            "VERDANT VALLEY",
            f_title,
            C_TEXT_GOLD,
            SCREEN_W // 2,
            SCREEN_H // 2 - 80,
            "center",
        )
        draw_text(
            s,
            "Multi-Agent AI Farming Simulation",
            f_sub,
            C_TEXT_DIM,
            SCREEN_W // 2,
            SCREEN_H // 2,
            "center",
        )

        # Progress bar
        bar_w = 400
        bar_h = 10
        bx = SCREEN_W // 2 - bar_w // 2
        by = SCREEN_H // 2 + 60
        pygame.draw.rect(s, C_BG_MID, (bx, by, bar_w, bar_h), border_radius=5)
        fill = int(bar_w * self.progress)
        if fill > 0:
            pygame.draw.rect(s, C_GRASS, (bx, by, fill, bar_h), border_radius=5)
        pygame.draw.rect(s, C_PANEL_BORD, (bx, by, bar_w, bar_h), 1, border_radius=5)

        pct = FontCache.get(FONT_SMALL)
        draw_text(
            s,
            f"Loading... {int(self.progress*100)}%",
            pct,
            C_TEXT_DIM,
            SCREEN_W // 2,
            by + 20,
            "center",
        )


# ── Main Menu ─────────────────────────────────────────────────────────────────


class Button:
    def __init__(self, label, rect, color_normal, color_hover, color_text=None):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.color_normal = color_normal
        self.color_hover = color_hover
        self.color_text = color_text or C_TEXT_MAIN
        self.hovered = False

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface):
        col = self.color_hover if self.hovered else self.color_normal
        draw_rounded_rect(
            surface, col, self.rect, radius=10, border=1, border_color=C_PANEL_BORD
        )
        f = FontCache.get(FONT_MEDIUM)
        draw_text(
            surface,
            self.label,
            f,
            self.color_text,
            self.rect.centerx,
            self.rect.centery,
            "center",
        )


class MainMenu:
    def __init__(self, screen):
        self.screen = screen
        cx = SCREEN_W // 2
        bw, bh = 260, 52
        gap = 16

        y0 = SCREEN_H // 2 + 20
        self.btn_start = Button(
            "▶  Start Game", (cx - bw // 2, y0, bw, bh), (38, 70, 38), (55, 100, 55)
        )
        self.btn_how = Button(
            "?  How to Play",
            (cx - bw // 2, y0 + bh + gap, bw, bh),
            (30, 50, 60),
            (40, 75, 90),
        )
        self.btn_quit = Button(
            "✕  Quit",
            (cx - bw // 2, y0 + 2 * (bh + gap), bw, bh),
            (60, 30, 30),
            (90, 45, 45),
        )

        self.buttons = [self.btn_start, self.btn_how, self.btn_quit]
        self._t = 0

        # decorative leaf particles
        rng = random.Random(7)
        self.leaves = [
            {
                "x": rng.randint(0, SCREEN_W),
                "y": rng.randint(0, SCREEN_H),
                "r": rng.uniform(0, math.pi * 2),
                "s": rng.uniform(1.5, 4),
            }
            for _ in range(80)
        ]

    def handle(self, event):
        """Returns 'start', 'howto', 'quit', or None."""
        for btn in self.buttons:
            if btn.handle(event):
                if btn is self.btn_start:
                    return "start"
                if btn is self.btn_how:
                    return "howto"
                if btn is self.btn_quit:
                    return "quit"
        return None

    def update(self):
        self._t += 1
        for l in self.leaves:
            l["r"] += 0.008
            l["y"] -= l["s"] * 0.4
            if l["y"] < -30:
                l["y"] = SCREEN_H + 10
                l["x"] = random.randint(0, SCREEN_W)

    def draw(self):
        s = self.screen
        s.fill(C_BG_DARK)

        # Drifting leaves background
        for l in self.leaves:
            a = int(abs(math.sin(l["r"])) * 100 + 30)
            pygame.draw.ellipse(
                s, (*C_GRASS, min(255, a)), (int(l["x"]), int(l["y"]), 12, 7)
            )

        # Dark vignette overlay
        vign = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(6):
            alpha = 12
            margin = i * 60
            pygame.draw.rect(
                vign,
                (0, 0, 0, alpha),
                (margin, margin, SCREEN_W - 2 * margin, SCREEN_H - 2 * margin),
                margin,
                border_radius=0,
            )
        s.blit(vign, (0, 0))

        # Title with glow-pulse
        pulse = 0.5 + 0.5 * math.sin(self._t * 0.04)
        glow_col = lerp_color(C_TEXT_GOLD, (255, 255, 255), pulse * 0.3)
        f_huge = FontCache.get(FONT_HUGE, bold=True)
        f_sub = FontCache.get(FONT_MEDIUM)
        f_tiny = FontCache.get(FONT_SMALL)

        draw_text(
            s,
            "VERDANT VALLEY",
            f_huge,
            glow_col,
            SCREEN_W // 2,
            SCREEN_H // 2 - 130,
            "center",
        )
        draw_text(
            s,
            "Multi-Agent AI Farming Simulation",
            f_sub,
            C_TEXT_DIM,
            SCREEN_W // 2,
            SCREEN_H // 2 - 60,
            "center",
        )

        # Subtitle tags
        tags = ["A* Pathfinding", "CSP Layout", "Genetic Evolution"]
        total_w = (
            sum(FontCache.get(FONT_TINY).size(f"  {t}  ")[0] + 10 for t in tags) + 20
        )
        tx = SCREEN_W // 2 - total_w // 2
        ty = SCREEN_H // 2 - 25
        for tag in tags:
            label = f"  {tag}  "
            tw, th = FontCache.get(FONT_TINY).size(label)
            draw_rounded_rect(
                s,
                C_BG_MID,
                (tx, ty, tw + 8, th + 8),
                radius=5,
                border=1,
                border_color=C_PANEL_BORD,
            )
            draw_text(s, label, FontCache.get(FONT_TINY), C_TEXT_DIM, tx + 4, ty + 4)
            tx += tw + 18

        for btn in self.buttons:
            btn.draw(s)

        draw_text(
            s,
            "FAST-NUCES  ·  Spring 2026  ·  BCS-6C",
            f_tiny,
            C_TEXT_DIM,
            SCREEN_W // 2,
            SCREEN_H - 30,
            "center",
        )


# ── HUD (top bar) ─────────────────────────────────────────────────────────────


def draw_hud(surface, season_mgr, agents, paused=False):
    pygame.draw.rect(surface, C_HUD_BG, (0, 0, SCREEN_W, GRID_OFFSET_Y))
    pygame.draw.line(
        surface, C_HUD_BORD, (0, GRID_OFFSET_Y - 1), (SCREEN_W, GRID_OFFSET_Y - 1)
    )

    f = FontCache.get(FONT_MEDIUM)
    fs = FontCache.get(FONT_SMALL)

    # Season & time
    draw_text(surface, f"⟡ {season_mgr.name}", f, C_TEXT_GOLD, 16, 18)
    draw_text(surface, season_mgr.time_label(), fs, C_TEXT_DIM, 16, 38)

    # Season progress bar (mini)
    bx, by, bw, bh = 130, 22, 100, 8
    pygame.draw.rect(surface, C_BG_MID, (bx, by, bw, bh), border_radius=3)
    fill = int(bw * season_mgr.progress)
    pygame.draw.rect(surface, C_TEXT_GOLD, (bx, by, fill, bh), border_radius=3)
    pygame.draw.rect(surface, C_PANEL_BORD, (bx, by, bw, bh), 1, border_radius=3)

    # Agent scores
    x = 280
    agent_icons = {
        "Farmer": ("●", C_FARMER),
        "Guard": ("●", C_GUARD),
        "Animal": ("●", C_ANIMAL),
    }
    for agent in agents:
        icon, col = agent_icons.get(agent.__class__.__name__, ("●", C_TEXT_DIM))
        draw_text(surface, f"{icon} {agent.name}: {agent.score}", fs, col, x, 22)
        x += 180

    # Rain indicator
    if season_mgr.rain_active:
        draw_text(surface, "🌧 Rain!", f, C_TEXT_WARN, SCREEN_W // 2 - 40, 16)

    # Pause
    if paused:
        draw_text(
            surface,
            "⏸ PAUSED — press P to resume",
            f,
            C_TEXT_GOLD,
            SCREEN_W // 2,
            SCREEN_H // 2,
            "center",
        )


# ── Sidebar panel ─────────────────────────────────────────────────────────────


def draw_sidebar(surface, grid, season_mgr, agents, selected_agent=None):
    """Right-hand info panel."""
    sx = SCREEN_W - SIDEBAR_W
    sy = GRID_OFFSET_Y
    sw = SIDEBAR_W
    sh = SCREEN_H - sy

    draw_rounded_rect(
        surface,
        C_BG_PANEL,
        (sx, sy, sw, sh),
        radius=0,
        border=1,
        border_color=C_PANEL_BORD,
    )

    f = FontCache.get(FONT_MEDIUM)
    fs = FontCache.get(FONT_SMALL)
    ft = FontCache.get(FONT_TINY)

    y = sy + 14
    draw_text(surface, "SIMULATION INFO", f, C_TEXT_GOLD, sx + 12, y)
    y += 28
    pygame.draw.line(surface, C_PANEL_BORD, (sx + 8, y), (sx + sw - 8, y))
    y += 10

    # Season
    draw_text(surface, f"Season : {season_mgr.name}", fs, C_TEXT_MAIN, sx + 12, y)
    y += 22
    prog_pct = int(season_mgr.progress * 100)
    draw_text(surface, f"Progress: {prog_pct}%", ft, C_TEXT_DIM, sx + 12, y)
    y += 20
    # mini bar
    bw = sw - 24
    pygame.draw.rect(surface, C_BG_MID, (sx + 12, y, bw, 6), border_radius=3)
    pygame.draw.rect(
        surface,
        C_TEXT_GOLD,
        (sx + 12, y, int(bw * season_mgr.progress), 6),
        border_radius=3,
    )
    y += 20

    # Agents
    pygame.draw.line(surface, C_PANEL_BORD, (sx + 8, y), (sx + sw - 8, y))
    y += 8
    draw_text(surface, "AGENTS", f, C_TEXT_GOLD, sx + 12, y)
    y += 26

    for ag in agents:
        name = ag.__class__.__name__
        col = {"Farmer": C_FARMER, "Guard": C_GUARD, "Animal": C_ANIMAL}.get(
            name, C_TEXT_DIM
        )
        pygame.draw.circle(surface, col, (sx + 22, y + 8), 7)
        draw_text(surface, f"{ag.name}", fs, C_TEXT_MAIN, sx + 36, y)
        draw_text(
            surface,
            f"({ag.col},{ag.row})  state: {ag.state}",
            ft,
            C_TEXT_DIM,
            sx + 36,
            y + 16,
        )
        draw_text(surface, f"score: {ag.score}", ft, C_TEXT_DIM, sx + 36, y + 30)
        y += 52

    # A* stats
    pygame.draw.line(surface, C_PANEL_BORD, (sx + 8, y), (sx + sw - 8, y))
    y += 8
    draw_text(surface, "A* LIVE", f, C_TEXT_GOLD, sx + 12, y)
    y += 26

    for ag in agents:
        if hasattr(ag, "explored") and ag.explored:
            draw_text(
                surface,
                f"{ag.name}: {len(ag.explored)} nodes explored",
                ft,
                C_TEXT_DIM,
                sx + 12,
                y,
            )
            y += 18

    # Crop counts
    pygame.draw.line(surface, C_PANEL_BORD, (sx + 8, y), (sx + sw - 8, y))
    y += 8
    draw_text(surface, "CROPS", f, C_TEXT_GOLD, sx + 12, y)
    y += 26

    counts = {CROP_WHEAT: 0, CROP_SUNFLOWER: 0, CROP_CORN: 0, CROP_TOMATO: 0, CROP_CARROT: 0, CROP_POTATO: 0}
    for c in range(grid.cols):
        for r in range(grid.rows):
            t = grid.tiles[c][r]
            if t.crop in counts:
                counts[t.crop] += 1

    for crop_id, cnt in counts.items():
        cc = CROP_COLOR[crop_id]
        pygame.draw.rect(surface, cc, (sx + 12, y + 2, 10, 10), border_radius=2)
        draw_text(surface, f"{CROP_NAMES[crop_id]}: {cnt}", fs, C_TEXT_MAIN, sx + 28, y)
        y += 20

    # Controls
    y = SCREEN_H - 90
    pygame.draw.line(surface, C_PANEL_BORD, (sx + 8, y), (sx + sw - 8, y))
    y += 8
    controls = ["P  — Pause/Resume", "R  — Restart", "ESC — Menu"]
    for c in controls:
        draw_text(surface, c, ft, C_TEXT_DIM, sx + 12, y)
        y += 16


# ── CSP visualisation panel ───────────────────────────────────────────────────


def draw_csp_overlay(surface, log_entry, all_vars, assignment):
    """
    Shown during CSP solving phase.
    log_entry: (col, row, crop, action) most recent step
    """
    ow, oh = 600, 400
    ox = SCREEN_W // 2 - ow // 2
    oy = SCREEN_H // 2 - oh // 2

    # Panel background
    draw_rounded_rect(
        surface,
        C_BG_PANEL,
        (ox, oy, ow, oh),
        radius=12,
        border=2,
        border_color=C_PANEL_BORD,
    )

    f = FontCache.get(FONT_LARGE)
    fs = FontCache.get(FONT_SMALL)
    ft = FontCache.get(FONT_TINY)

    draw_text(
        surface,
        "CSP FARM LAYOUT PLANNER",
        f,
        C_TEXT_GOLD,
        SCREEN_W // 2,
        oy + 20,
        "center",
    )
    draw_text(
        surface,
        "Assigning crops via Backtracking + Forward Checking",
        fs,
        C_TEXT_DIM,
        SCREEN_W // 2,
        oy + 48,
        "center",
    )

    # Assignment grid mini-view (crops as colored squares)
    cell = 14
    cols_shown = min(GRID_COLS, 18)
    rows_shown = min(GRID_ROWS, 14)
    gx = ox + 20
    gy = oy + 75
    for c in range(cols_shown):
        for r in range(rows_shown):
            color = C_BG_MID
            crop = assignment.get((c, r))
            if crop is not None:
                color = CROP_COLOR[crop]
            pygame.draw.rect(
                surface,
                color,
                (gx + c * cell, gy + r * cell, cell - 1, cell - 1),
                border_radius=1,
            )

    # Legend
    lx = ox + 20
    ly = gy + rows_shown * cell + 12
    for crop_id, name in CROP_NAMES.items():
        if crop_id == CROP_NONE:
            continue
        pygame.draw.rect(
            surface, CROP_COLOR[crop_id], (lx, ly, 12, 12), border_radius=2
        )
        draw_text(surface, name, ft, C_TEXT_MAIN, lx + 16, ly)
        lx += 80

    # Last action log
    if log_entry:
        c, r, crop, action = log_entry
        col_map = {"assign": C_FARMER, "backtrack": C_TEXT_WARN, "final": C_TEXT_GOLD}
        msg = f"{action.upper()}  ({c},{r}) → {CROP_NAMES[crop]}"
        draw_text(
            surface,
            msg,
            fs,
            col_map.get(action, C_TEXT_MAIN),
            SCREEN_W // 2,
            oy + oh - 40,
            "center",
        )

    assigned = len([v for v, cr in assignment.items() if cr != CROP_NONE])
    draw_text(
        surface,
        f"Assigned {assigned} / {len(all_vars)} tiles",
        ft,
        C_TEXT_DIM,
        SCREEN_W // 2,
        oy + oh - 20,
        "center",
    )
