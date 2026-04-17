"""
UIManager - Enhanced UI with better visuals
"""

import pygame
import random
from utils.constants import *
from utils.helpers import draw_rounded_rect, draw_text
from game_ui.fonts import FontCache


class UIManager:
    def __init__(self, screen):
        self.screen = screen

    def draw_hud(self, season_mgr, agents, paused=False, tick=0):
        # Glassy HUD strip
        hud_surface = pygame.Surface((SCREEN_W, GRID_OFFSET_Y), pygame.SRCALPHA)
        hud_surface.fill((20, 28, 22, 210))
        pygame.draw.rect(
            hud_surface,
            (255, 255, 255, 30),
            (10, 10, SCREEN_W - 20, GRID_OFFSET_Y - 20),
            border_radius=18,
        )
        pygame.draw.rect(
            hud_surface,
            (255, 255, 255, 60),
            (10, 10, SCREEN_W - 20, GRID_OFFSET_Y - 20),
            1,
            border_radius=18,
        )
        self.screen.blit(hud_surface, (0, 0))

        f_title = FontCache.get(FONT_MEDIUM, bold=True)
        f_normal = FontCache.get(FONT_SMALL)
        f_tiny = FontCache.get(FONT_TINY)

        # Season card
        card_rect = pygame.Rect(20, 15, 280, 70)
        draw_rounded_rect(
            self.screen,
            (18, 34, 28, 210),
            card_rect,
            radius=16,
            border=2,
            border_color=(120, 185, 110),
        )

        season_text = f_title.render(season_mgr.name, True, C_TEXT_GOLD)
        self.screen.blit(season_text, (card_rect.x + 16, card_rect.y + 12))

        time_text = f_normal.render(
            f"⏱ {season_mgr.time_label()}", True, C_TEXT_MAIN
        )
        self.screen.blit(time_text, (card_rect.x + 16, card_rect.y + 42))

        # Seasonal bloom glow
        glow_radius = 28 + int(season_mgr.bloom * 6)
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            glow_surf,
            (255, 215, 120, 80),
            (glow_radius, glow_radius),
            glow_radius,
        )
        self.screen.blit(glow_surf, (card_rect.right - glow_radius - 10, card_rect.y + 12))

        # Season progress bar
        bar_x, bar_y, bar_w, bar_h = 320, 35, 260, 12
        pygame.draw.rect(
            self.screen,
            (20, 30, 24),
            (bar_x, bar_y, bar_w, bar_h),
            border_radius=6,
        )
        fill_w = int(bar_w * season_mgr.progress)
        if fill_w > 0:
            fill_color = (
                min(255, C_PROGRESS_FILL[0] + 20),
                min(255, C_PROGRESS_FILL[1] + 20),
                min(255, C_PROGRESS_FILL[2] + 20),
            )
            pygame.draw.rect(
                self.screen,
                fill_color,
                (bar_x, bar_y, fill_w, bar_h),
                border_radius=6,
            )
        pygame.draw.rect(
            self.screen,
            (255, 255, 255, 100),
            (bar_x, bar_y, bar_w, bar_h),
            1,
            border_radius=6,
        )

        progress_label = f_tiny.render(
            f"Season progress {int(season_mgr.progress * 100)}%", True, C_TEXT_DIM
        )
        self.screen.blit(progress_label, (bar_x, bar_y + bar_h + 6))

        # Rain indicator inside HUD
        if season_mgr.rain_active:
            rain_rect = pygame.Rect(580, 26, 200, 46)
            draw_rounded_rect(
                self.screen,
                (18, 30, 40, 220),
                rain_rect,
                radius=16,
                border=1,
                border_color=C_TEXT_WARN,
            )
            rain_text = f_normal.render("🌧 Rain active", True, C_TEXT_WARN)
            self.screen.blit(rain_text, (rain_rect.x + 18, rain_rect.y + 12))

            for i in range(12):
                rx = (rain_rect.x + 18 + i * 16 + tick * 3) % (rain_rect.x + rain_rect.width - 8)
                ry = rain_rect.y + 26 + (i % 3) * 4
                pygame.draw.line(
                    self.screen,
                    (150, 190, 220, 180),
                    (rx, ry),
                    (rx + 5, ry + 12),
                    2,
                )

        # Agent cards and rest of HUD with icon-rich farm look
        score_x = 20
        card_y = 15
        for agent in agents:
            if hasattr(agent, "alive") and not agent.alive:
                continue

            if "Farmer" in agent.name:
                color = C_FARMER
                icon = "🌾"
            elif "Guard" in agent.name:
                color = C_GUARD
                icon = "🛡️"
            else:
                color = C_ANIMAL
                icon = "🐮"

            card_rect = pygame.Rect(score_x, card_y, 190, 70)
            draw_rounded_rect(
                self.screen,
                (25, 35, 28, 220),
                card_rect,
                radius=14,
                border=1,
                border_color=(color[0], color[1], color[2], 180),
            )
            pygame.draw.rect(
                self.screen,
                (color[0], color[1], color[2], 40),
                (card_rect.x + 10, card_rect.y + 42, 160, 18),
                border_radius=8,
            )

            icon_text = f_normal.render(icon, True, color)
            self.screen.blit(icon_text, (score_x + 14, card_y + 12))

            name_text = f_normal.render(f"{agent.name}", True, C_TEXT_MAIN)
            self.screen.blit(name_text, (score_x + 40, card_y + 10))

            state_text = f_tiny.render(agent.state, True, C_TEXT_DIM)
            self.screen.blit(state_text, (score_x + 40, card_y + 34))

            score_text = f_title.render(f"{agent.score}", True, C_TEXT_GOLD)
            self.screen.blit(score_text, (score_x + 14, card_y + 46))

            score_x += 200

        # Pause overlay
        if paused:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            pause_text = f_title.render("⏸ GAME PAUSED", True, C_TEXT_GOLD)
            pause_rect = pause_text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
            self.screen.blit(pause_text, pause_rect)

            resume_text = f_normal.render("Press P to resume", True, C_TEXT_DIM)
            resume_rect = resume_text.get_rect(
                center=(SCREEN_W // 2, SCREEN_H // 2 + 50)
            )
            self.screen.blit(resume_text, resume_rect)

    def draw_sidebar(self, grid, season_mgr, agents):
        """Enhanced right-hand info panel"""
        sx = SCREEN_W - SIDEBAR_W
        sy = GRID_OFFSET_Y
        sw = SIDEBAR_W
        sh = SCREEN_H - sy

        sidebar_surface = pygame.Surface((sw, sh), pygame.SRCALPHA)
        sidebar_surface.fill((18, 28, 22, 220))
        draw_rounded_rect(
            sidebar_surface,
            (24, 38, 28, 220),
            pygame.Rect(4, 4, sw - 8, sh - 8),
            radius=18,
            border=2,
            border_color=(90, 120, 90),
        )

        for i in range(sh - 16):
            ratio = i / (sh - 16)
            color = (
                int(30 * (1 - ratio) + 20 * ratio),
                int(46 * (1 - ratio) + 30 * ratio),
                int(36 * (1 - ratio) + 28 * ratio),
                18,
            )
            pygame.draw.line(sidebar_surface, color, (14, 12 + i), (sw - 14, 12 + i))

        self.screen.blit(sidebar_surface, (sx, sy))

        f_title = FontCache.get(FONT_MEDIUM, bold=True)
        f_normal = FontCache.get(FONT_SMALL)
        f_tiny = FontCache.get(FONT_TINY)

        y = sy + 15

        # Section headers with icons
        sections = [
            ("📊 STATISTICS", C_TEXT_GOLD),
            ("👥 AGENTS", C_TEXT_GOLD),
            ("🌾 CROP STATUS", C_TEXT_GOLD),
            ("🎮 CONTROLS", C_TEXT_GOLD),
        ]

        for section, color in sections:
            section_text = f_title.render(section, True, color)
            self.screen.blit(section_text, (sx + 15, y))
            y += 30
            pygame.draw.line(
                self.screen, C_PANEL_BORD, (sx + 10, y), (sx + sw - 10, y), 1
            )
            y += 15

            if section == "📊 STATISTICS":
                # Season stats
                season_text = f_normal.render(
                    f"Season: {season_mgr.name}", True, C_TEXT_MAIN
                )
                self.screen.blit(season_text, (sx + 15, y))
                y += 22

                progress = int(season_mgr.progress * 100)
                progress_text = f_tiny.render(
                    f"Progress: {progress}%", True, C_TEXT_DIM
                )
                self.screen.blit(progress_text, (sx + 15, y))
                y += 15

                # Mini progress bar
                bar_w = sw - 30
                pygame.draw.rect(
                    self.screen, C_PROGRESS_BG, (sx + 15, y, bar_w, 6), border_radius=3
                )
                fill_w = int(bar_w * season_mgr.progress)
                pygame.draw.rect(
                    self.screen,
                    C_PROGRESS_FILL,
                    (sx + 15, y, fill_w, 6),
                    border_radius=3,
                )
                y += 25

                # Rain status
                if season_mgr.rain_active:
                    rain_text = f_tiny.render("🌧 Rain active!", True, C_TEXT_WARN)
                    self.screen.blit(rain_text, (sx + 15, y))
                    y += 20

            elif section == "👥 AGENTS":
                for ag in agents:
                    if hasattr(ag, "alive") and not ag.alive:
                        continue

                    # Agent card background
                    card_rect = pygame.Rect(sx + 10, y, sw - 20, 65)
                    pygame.draw.rect(
                        self.screen, (30, 40, 30), card_rect, border_radius=6
                    )

                    # Determine icon and color
                    if "Farmer" in ag.name:
                        icon = "🌾"
                        color = C_FARMER
                    elif "Guard" in ag.name:
                        icon = "🛡️"
                        color = C_GUARD
                    else:
                        icon = "🐮"
                        color = C_ANIMAL

                    # Agent icon
                    icon_text = f_title.render(icon, True, color)
                    self.screen.blit(icon_text, (sx + 20, y + 10))

                    # Agent name and state
                    name_text = f_normal.render(ag.name, True, C_TEXT_MAIN)
                    self.screen.blit(name_text, (sx + 50, y + 10))

                    state_text = f_tiny.render(f"State: {ag.state}", True, C_TEXT_DIM)
                    self.screen.blit(state_text, (sx + 50, y + 30))

                    pos_text = f_tiny.render(
                        f"Position: ({ag.col},{ag.row})", True, C_TEXT_DIM
                    )
                    self.screen.blit(pos_text, (sx + 50, y + 45))

                    # Score
                    score_text = f_title.render(f"{ag.score}", True, C_TEXT_GOLD)
                    self.screen.blit(score_text, (sx + sw - 60, y + 25))

                    y += 75

            elif section == "🌾 CROP STATUS":
                counts = {CROP_WHEAT: 0, CROP_SUNFLOWER: 0, CROP_CORN: 0}
                for c in range(grid.cols):
                    for r in range(grid.rows):
                        t = grid.tiles[c][r]
                        if t.crop in counts:
                            counts[t.crop] += 1

                crop_icons = {CROP_WHEAT: "🌾", CROP_SUNFLOWER: "🌻", CROP_CORN: "🌽"}
                for crop_id, cnt in counts.items():
                    icon = crop_icons.get(crop_id, "❓")
                    crop_text = f_normal.render(
                        f"{icon} {CROP_NAMES[crop_id]}: {cnt}", True, C_TEXT_MAIN
                    )
                    self.screen.blit(crop_text, (sx + 15, y))
                    y += 25

            elif section == "🎮 CONTROLS":
                controls = [
                    "P - Pause/Resume",
                    "R - Restart Game",
                    "ESC - Main Menu",
                    "SPACE - Skip CSP",
                ]
                for control in controls:
                    control_text = f_tiny.render(control, True, C_TEXT_DIM)
                    self.screen.blit(control_text, (sx + 15, y))
                    y += 20

        # Version info
        version_text = f_tiny.render("v1.0 | AI Simulation", True, C_TEXT_DIM)
        self.screen.blit(version_text, (sx + 15, SCREEN_H - 25))
