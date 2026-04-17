"""
main.py — Verdant Valley
Run: python main.py
"""

import sys
import pygame
import random

# Add parent directory to path for imports
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.constants import *
from utils.helpers import tile_center
from src.world.environment.grid import Grid
from src.world.environment.season import SeasonManager
from src.agents.farmer import Farmer
from src.agents.guard import Guard
from src.agents.animal import Animal
from src.algorithms.csp import CSPSolver
from game_ui import UIManager, FontCache
from game_ui.csp_panel import CSPPanel
from game_ui.metrics_panel import MetricsPanel

# Initialize font cache
from game_ui.fonts import FontCache

FontCache.clear()


class LoadingScreen:
    def __init__(self, screen):
        self.screen = screen
        self.progress = 0.0
        self.done = False
        self._tick = 0

    def update(self, dt=1):
        self._tick += 1
        self.progress = min(1.0, self._tick / 120)
        if self.progress >= 1.0:
            self.done = True

    def draw(self):
        s = self.screen
        s.fill(C_BG_DARK)

        f_title = FontCache.get(FONT_HUGE, bold=True)
        f_sub = FontCache.get(FONT_LARGE)

        from utils.helpers import draw_text

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
        from utils.helpers import draw_rounded_rect, draw_text

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
        self.animation_frame = 0
        self.particles = []

        # Create floating particles
        for _ in range(100):
            self.particles.append(
                {
                    "x": random.randint(0, SCREEN_W),
                    "y": random.randint(0, SCREEN_H),
                    "vx": random.uniform(-0.5, 0.5),
                    "vy": random.uniform(-0.5, 0.5),
                    "size": random.randint(2, 5),
                    "color": random.choice(
                        [(80, 160, 60), (60, 120, 40), (100, 180, 80)]
                    ),
                }
            )

        # Create buttons
        bw, bh = 280, 60
        cx = SCREEN_W // 2 - bw // 2
        y_start = SCREEN_H // 2 + 50

        self.buttons = [
            {
                "label": "🌾 START GAME",
                "rect": pygame.Rect(cx, y_start, bw, bh),
                "action": "start",
            },
            {
                "label": "ℹ️ HOW TO PLAY",
                "rect": pygame.Rect(cx, y_start + bh + 15, bw, bh),
                "action": "howto",
            },
            {
                "label": "🚪 QUIT",
                "rect": pygame.Rect(cx, y_start + (bh + 15) * 2, bw, bh),
                "action": "quit",
            },
        ]

        self.hovered_button = None

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    self.hovered_button = btn
                    return None
            self.hovered_button = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    return btn["action"]
        return None

    def update(self):
        self.animation_frame += 1
        # Update particles
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0 or p["x"] > SCREEN_W or p["y"] < 0 or p["y"] > SCREEN_H:
                p["x"] = random.randint(0, SCREEN_W)
                p["y"] = random.randint(0, SCREEN_H)

    def draw(self):
        self.screen.fill(C_BG_DARK)

        # Draw gradient background
        for i in range(SCREEN_H):
            ratio = i / SCREEN_H
            color = (
                int(C_BG_DARK[0] * (1 - ratio) + 20 * ratio),
                int(C_BG_DARK[1] * (1 - ratio) + 40 * ratio),
                int(C_BG_DARK[2] * (1 - ratio) + 20 * ratio),
            )
            pygame.draw.line(self.screen, color, (0, i), (SCREEN_W, i))

        # Draw particles
        for p in self.particles:
            alpha = int(abs(p["vx"]) * 100 + 50)
            color = (p["color"][0], p["color"][1], p["color"][2], min(255, alpha))
            pygame.draw.circle(
                self.screen, p["color"], (int(p["x"]), int(p["y"])), p["size"]
            )

        # Title with glow effect
        f_title = FontCache.get(FONT_HUGE, bold=True)
        f_sub = FontCache.get(FONT_LARGE)

        # Draw shadow
        title_shadow = f_title.render("VERDANT VALLEY", True, (0, 0, 0))
        shadow_rect = title_shadow.get_rect(
            center=(SCREEN_W // 2 + 4, SCREEN_H // 2 - 100 + 4)
        )
        self.screen.blit(title_shadow, shadow_rect)

        # Draw title with gradient
        title = f_title.render("VERDANT VALLEY", True, C_TEXT_TITLE)
        title_rect = title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 100))
        self.screen.blit(title, title_rect)

        # Draw subtitle
        subtitle = f_sub.render("Multi-Agent AI Farming Simulation", True, C_TEXT_GOLD)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 40))
        self.screen.blit(subtitle, subtitle_rect)

        # Draw buttons
        f_button = FontCache.get(FONT_MEDIUM, bold=True)
        for btn in self.buttons:
            rect = btn["rect"]
            is_hover = self.hovered_button == btn

            # Button background
            color = C_BUTTON_HOVER if is_hover else C_BUTTON_NORMAL
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            pygame.draw.rect(self.screen, C_TEXT_GOLD, rect, 2, border_radius=12)

            # Button text
            text_color = C_TEXT_GOLD if is_hover else C_TEXT_MAIN
            text = f_button.render(btn["label"], True, text_color)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)


def make_agents(grid):
    """Spawn agents at sensible starting positions."""
    farmer = Farmer(6, 6)
    guard = Guard(10, 10)
    animal = Animal(16, 1)

    # Guard patrol waypoints
    guard.set_waypoints([(4, 2), (13, 2), (13, 11), (4, 11)])

    return farmer, guard, animal


def run_csp(grid):
    """Solve CSP and return the solver."""
    solver = CSPSolver(grid)
    solver.solve()
    return solver


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        self.state = STATE_LOADING
        self.paused = False

        self.loading = LoadingScreen(self.screen)
        self.menu = None
        self.ui = None
        self.grid = None
        self.season = None
        self.agents = []
        self.farmer = self.guard = self.animal = None

        # CSP animation state
        self.csp_solver = None
        self.csp_log_idx = 0
        self.csp_assignment = {}
        self.csp_tick = 0
        self.game_tick = 0

    # ── Setup helpers ─────────────────────────────────────────────────────────

    def _setup_game(self):
        self.grid = Grid()
        self.season = SeasonManager()
        self.farmer, self.guard, self.animal = make_agents(self.grid)
        self.agents = [self.farmer, self.guard, self.animal]
        self.ui = UIManager(self.screen)
        self.csp_panel = CSPPanel(self.screen)
        self.metrics_panel = MetricsPanel(self.screen)

        # Run CSP
        self.csp_solver = run_csp(self.grid)
        self.csp_log_idx = 0
        self.csp_assignment = {}
        self.csp_tick = 0
        self.state = STATE_CSP_VIZ

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS)

            # ── Events ────────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if self.state == STATE_MENU:
                    result = self.menu.handle(event)
                    if result == "start":
                        self._setup_game()
                    elif result == "quit":
                        pygame.quit()
                        sys.exit()

                if self.state == STATE_PLAYING:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_p:
                            self.paused = not self.paused
                        if event.key == pygame.K_r:
                            self._setup_game()
                        if event.key == pygame.K_ESCAPE:
                            self.state = STATE_MENU
                            self.menu = MainMenu(self.screen)

                if self.state == STATE_CSP_VIZ:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        self._finish_csp()

            # ── Update ────────────────────────────────────────────────────────
            if self.state == STATE_LOADING:
                self.loading.update()
                if self.loading.done:
                    self.state = STATE_MENU
                    self.menu = MainMenu(self.screen)

            elif self.state == STATE_MENU:
                self.menu.update()

            elif self.state == STATE_CSP_VIZ:
                self._update_csp_anim()

            elif self.state == STATE_PLAYING and not self.paused:
                self.season.update(self.grid)
                for agent in self.agents:
                    agent.update(self.grid, self.agents)
                # Respawn animal if caught
                if not self.animal.alive:
                    self.animal.respawn(16, 1)
                self.game_tick += 1

            # ── Draw ──────────────────────────────────────────────────────────
            if self.state == STATE_LOADING:
                self.loading.draw()

            elif self.state == STATE_MENU:
                self.menu.draw()

            elif self.state == STATE_CSP_VIZ:
                self._draw_csp_anim()

            elif self.state == STATE_PLAYING:
                self._draw_game()

            pygame.display.flip()

    # ── CSP animation ─────────────────────────────────────────────────────────

    def _update_csp_anim(self):
        self.csp_tick += 1

        # Show each assignment step by step
        steps_per_frame = 2

        for _ in range(steps_per_frame):
            if self.csp_log_idx < len(self.csp_solver.log):
                entry = self.csp_solver.log[self.csp_log_idx]
                c, r, crop, action = entry
                if action in ("assign", "final"):
                    self.csp_assignment[(c, r)] = crop
                self.csp_log_idx += 1
            else:
                # Finished all CSP steps
                self._finish_csp()
                return

    def _finish_csp(self):
        self.csp_solver.apply_to_grid()
        self.state = STATE_PLAYING

    def _draw_csp_anim(self):
        self.screen.fill(C_BG_DARK)
        self.grid.draw(self.screen)

        # Current log entry
        entry = None
        if self.csp_log_idx > 0 and self.csp_log_idx <= len(self.csp_solver.log):
            entry = self.csp_solver.log[self.csp_log_idx - 1]

        self.csp_panel.draw(entry, self.csp_solver.vars, self.csp_assignment)

        from utils.helpers import draw_text

        f = FontCache.get(FONT_SMALL)
        draw_text(
            self.screen,
            "SPACE — skip to gameplay",
            f,
            C_TEXT_DIM,
            SCREEN_W // 2,
            SCREEN_H - 20,
            "center",
        )

    # ── Game draw ─────────────────────────────────────────────────────────────

    def _draw_game(self):
        self.screen.fill(C_BG_DARK)

        # Grid area
        self.grid.draw(self.screen, self.game_tick)

        # Path overlays
        self.farmer.draw_path_overlay(self.screen, C_PATH_FARMER)
        self.guard.draw_path_overlay(self.screen, C_PATH_GUARD)
        if self.animal.alive:
            self.animal.draw_path_overlay(self.screen, C_PATH_ANIMAL)

        # Agents
        f_tiny = FontCache.get(FONT_TINY)
        for ag in self.agents:
            if hasattr(ag, "alive") and not ag.alive:
                continue
            ag.draw(self.screen, f_tiny)

        # UI chrome
        self.ui.draw_hud(self.season, self.agents, self.paused, self.game_tick)
        self.ui.draw_sidebar(self.grid, self.season, self.agents)
        self.metrics_panel.draw(self.grid, self.agents)

        # Seasonal atmosphere
        season_tints = {
            "🌱 Spring": (20, 40, 20, 30),
            "☀️ Summer": (40, 20, 0, 40),
            "🍂 Autumn": (40, 20, 0, 40),
            "❄️ Winter": (0, 20, 40, 30),
        }
        if self.season.name in season_tints:
            tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            tint.fill(season_tints[self.season.name])
            self.screen.blit(tint, (0, 0))

        # Weather overlay
        if self.season.rain_active:
            rain_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            rain_overlay.fill((100, 120, 150, 20))
            # Rain particles
            for i in range(30):
                rx = (self.game_tick * 3 + i * 25) % SCREEN_W
                ry = (self.game_tick * 5 + i * 15) % (SCREEN_H + 20)
                pygame.draw.line(rain_overlay, (150, 170, 200, 150), (rx, ry), (rx + 8, ry + 16), 1)
            self.screen.blit(rain_overlay, (0, 0))

        if self.paused:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 90))
            self.screen.blit(overlay, (0, 0))
            from utils.helpers import draw_text

            f = FontCache.get(FONT_HUGE)
            draw_text(
                self.screen,
                "PAUSED",
                f,
                C_TEXT_GOLD,
                SCREEN_W // 2,
                SCREEN_H // 2,
                "center",
            )


if __name__ == "__main__":
    game = Game()
    game.run()
