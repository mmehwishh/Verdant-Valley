"""
game_ui/csp_popup.py — CSP Layout Generation Popup (Wood Theme)
- Left side: Large farm layout preview
- Right side: Statistics panel with tile counts + progress bars
"""

import pygame
from utils.constants import *


class CSPPopup:
    def __init__(self, screen, grid, csp_solver):
        self.screen = screen
        self.grid = grid
        self.csp_solver = csp_solver
        self.visible = True
        self.confirmed = False

        self.width = 1020
        self.height = 720
        self.x = (SCREEN_W - self.width) // 2
        self.y = (SCREEN_H - self.height) // 2

        self.grid_area_width = int(self.width * 0.60)
        self.stats_area_width = self.width - self.grid_area_width - 50

        btn_width = 170
        btn_height = 46
        btn_x = self.x + self.width - btn_width - 22
        self.regenerate_button = pygame.Rect(
            btn_x, self.y + self.height - 118, btn_width, btn_height
        )
        self.confirm_button = pygame.Rect(
            btn_x, self.y + self.height - 62, btn_width, btn_height
        )

        self.font_title = pygame.font.Font(None, 38)
        self.font_sec = pygame.font.Font(None, 22)
        self.font_stat = pygame.font.Font(None, 20)
        self.font_btn = pygame.font.Font(None, 22)
        self.font_btn_small = pygame.font.Font(None, 18)
        self.font_legend = pygame.font.Font(None, 16)
        self.font_input = pygame.font.Font(None, 24)

        self.wood_base = (139, 90, 43)
        self.wood_dark = (100, 65, 30)
        self.wood_light = (170, 115, 55)
        self.panel_bg = (28, 22, 16)
        self.inner_bg = (38, 30, 20)
        self.crop_counts = self.csp_solver.get_requested_counts()
        self.mode = self.csp_solver.get_mode()
        self.crop_controls = {}
        self.mode_buttons = {}
        self.message = ""
        self._build_layout_controls()

    def _build_layout_controls(self):
        sx = self.x + self.grid_area_width + 8
        sy = self.y + 64 + 14
        cx = sx + 14
        panel_inner_w = self.stats_area_width - 28
        mode_y = sy + 30
        gap = 10
        mode_w = (panel_inner_w - gap) // 2
        self.mode_buttons["auto"] = pygame.Rect(cx, mode_y, mode_w, 34)
        self.mode_buttons["manual"] = pygame.Rect(
            cx + mode_w + gap, mode_y, panel_inner_w - mode_w - gap, 34
        )

        crop_y = mode_y + 84
        row_gap = 46
        button_size = 28
        value_w = 72

        for index, crop in enumerate((CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN)):
            row_y = crop_y + index * row_gap
            minus_rect = pygame.Rect(cx + 132, row_y - 4, button_size, button_size)
            value_rect = pygame.Rect(cx + 168, row_y - 4, value_w, button_size)
            plus_rect = pygame.Rect(cx + 248, row_y - 4, button_size, button_size)
            self.crop_controls[crop] = {
                "minus": minus_rect,
                "plus": plus_rect,
                "value": value_rect,
            }

    def _field_limit(self):
        return self.csp_solver.available_field_count()

    def _selected_total(self):
        return sum(self.crop_counts.values())

    def _fit_counts_to_limit(self):
        limit = self._field_limit()
        ordered_crops = [CROP_WHEAT, CROP_CORN, CROP_SUNFLOWER]
        while self._selected_total() > limit:
            for crop in ordered_crops:
                if self.crop_counts[crop] > 0 and self._selected_total() > limit:
                    self.crop_counts[crop] -= 1

    def _sync_solver_counts(self):
        try:
            self.csp_solver.set_mode(self.mode)
            self.csp_solver.set_requested_counts(self.crop_counts)
            self.message = ""
            return True
        except ValueError as exc:
            self.message = str(exc)
            return False

    def _adjust_crop(self, crop, delta):
        next_value = max(0, self.crop_counts[crop] + delta)
        next_counts = dict(self.crop_counts)
        next_counts[crop] = next_value
        if sum(next_counts.values()) > self._field_limit():
            self.message = (
                f"Total crops cannot exceed {self._field_limit()} available field tiles."
            )
            return
        self.crop_counts = next_counts
        self._sync_solver_counts()

    def _set_mode(self, mode):
        self.mode = mode
        self._sync_solver_counts()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _draw_section_header(self, text, x, y, width):
        """Draws a section label with a divider line."""
        label = self.font_sec.render(text, True, (255, 215, 0))
        self.screen.blit(label, (x, y))
        line_y = y + label.get_height() + 4
        pygame.draw.line(
            self.screen, self.wood_base, (x, line_y), (x + width, line_y), 1
        )
        return line_y + 8

    def _draw_bar(self, x, y, w, h, fraction, bar_color, bg_color=(60, 50, 40)):
        """Draws a simple horizontal progress bar."""
        pygame.draw.rect(self.screen, bg_color, (x, y, w, h), border_radius=3)
        fill_w = max(2, int(w * min(fraction, 1.0)))
        pygame.draw.rect(self.screen, bar_color, (x, y, fill_w, h), border_radius=3)

    def regenerate_everything(self):
        print("\nRegenerating entire farm layout...")
        self.grid._build_map()
        self.grid._bake_all()
        self.csp_solver.refresh_grid_context()
        self._fit_counts_to_limit()
        self.csp_solver.assign = {}
        self.csp_solver.log = []
        self._sync_solver_counts()
        self.csp_solver.solve(self.crop_counts)
        self.csp_solver.apply_to_grid()
        print("New layout generated.\n")

    def handle_event(self, event):
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mp = pygame.mouse.get_pos()
            for mode, rect in self.mode_buttons.items():
                if rect.collidepoint(mp):
                    self._set_mode(mode)
                    return True
            if self.mode == "manual":
                for crop, controls in self.crop_controls.items():
                    if controls["minus"].collidepoint(mp):
                        self._adjust_crop(crop, -1)
                        return True
                    if controls["plus"].collidepoint(mp):
                        self._adjust_crop(crop, 1)
                        return True
            if self.confirm_button.collidepoint(mp):
                self.regenerate_everything()
                self.visible = False
                self.confirmed = True
                return True
            if self.regenerate_button.collidepoint(mp):
                self.regenerate_everything()
                return True
        return False

    def draw_wood_button(
        self, rect, text, is_hover=False, accent=False, compact=False, text_font=None
    ):
        if accent:
            base = (60, 140, 80) if not is_hover else (75, 165, 95)
            dark = (35, 90, 50)
        else:
            base = self.wood_light if is_hover else self.wood_base
            dark = self.wood_dark

        radius = 8 if compact else 10
        pygame.draw.rect(self.screen, base, rect, border_radius=radius)
        if not compact and rect.height >= 42:
            for i in range(3):
                ly = rect.y + 11 + i * 14
                pygame.draw.line(
                    self.screen,
                    dark,
                    (rect.x + 10, ly),
                    (rect.x + rect.width - 10, ly),
                    1,
                )
        pygame.draw.rect(self.screen, dark, rect, 2, border_radius=10)
        font = text_font or (self.font_btn_small if compact else self.font_btn)
        surf = font.render(text, True, (255, 255, 255))
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    # ── main draw ────────────────────────────────────────────────────────────

    def draw(self):
        if not self.visible:
            return

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        # Outer frame
        panel = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(self.screen, self.wood_dark, panel, border_radius=18)
        pygame.draw.rect(
            self.screen, self.wood_light, panel.inflate(-4, -4), border_radius=16
        )
        pygame.draw.rect(
            self.screen, self.panel_bg, panel.inflate(-10, -10), border_radius=13
        )

        # Title bar strip
        title_strip = pygame.Rect(self.x + 5, self.y + 5, self.width - 10, 52)
        pygame.draw.rect(self.screen, self.wood_dark, title_strip, border_radius=13)
        title = self.font_title.render("FARM LAYOUT GENERATOR", True, (255, 215, 0))
        self.screen.blit(
            title, title.get_rect(center=(self.x + self.width // 2, self.y + 32))
        )

        content_y = self.y + 64
        content_h = self.height - 74

        # ── LEFT: grid preview ────────────────────────────────────────────
        gx = self.x + 12
        gy = content_y
        gw = self.grid_area_width - 18
        gh = content_h - 10

        pygame.draw.rect(self.screen, self.inner_bg, (gx, gy, gw, gh), border_radius=10)
        pygame.draw.rect(
            self.screen, self.wood_dark, (gx, gy, gw, gh), 1, border_radius=10
        )
        self.draw_grid_preview(gx + 6, gy + 6, gw - 12, gh - 12)

        # ── RIGHT: stats panel ────────────────────────────────────────────
        sx = self.x + self.grid_area_width + 8
        sy = content_y
        sw = self.stats_area_width
        sh = content_h - 10

        pygame.draw.rect(self.screen, self.inner_bg, (sx, sy, sw, sh), border_radius=10)
        pygame.draw.rect(
            self.screen, self.wood_dark, (sx, sy, sw, sh), 1, border_radius=10
        )

        cx = sx + 14
        cy = sy + 14

        cy = self._draw_section_header("GENERATION MODE", cx, cy, sw - 28)

        mode_labels = {
            "auto": "AUTO GENERATE",
            "manual": "CUSTOM INPUT",
        }
        for mode, rect in self.mode_buttons.items():
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            active = self.mode == mode
            self.draw_wood_button(
                rect,
                mode_labels[mode],
                hovered or active,
                accent=active,
                compact=True,
                text_font=self.font_btn_small,
            )

        cy += 56
        cy = self._draw_section_header("SELECT CROPS", cx, cy, sw - 28)

        crop_rows = [
            (CROP_WHEAT, "Wheat", (230, 200, 60)),
            (CROP_SUNFLOWER, "Sunflower", (255, 180, 0)),
            (CROP_CORN, "Corn", (160, 210, 60)),
        ]
        for crop, name, color in crop_rows:
            row_y = cy
            controls = self.crop_controls[crop]
            pygame.draw.rect(self.screen, color, (cx, row_y + 4, 14, 14), border_radius=3)
            label_color = (210, 210, 200) if self.mode == "manual" else (140, 140, 140)
            label = self.font_stat.render(name, True, label_color)
            self.screen.blit(label, (cx + 22, row_y))

            for symbol, rect in (
                ("-", controls["minus"]),
                ("+", controls["plus"]),
            ):
                hovered = rect.collidepoint(pygame.mouse.get_pos())
                self.draw_wood_button(
                    rect,
                    symbol,
                    hovered and self.mode == "manual",
                    accent=False,
                    compact=True,
                    text_font=self.font_btn,
                )

            value_rect = controls["value"]
            pygame.draw.rect(self.screen, (55, 44, 30), value_rect, border_radius=6)
            pygame.draw.rect(self.screen, self.wood_dark, value_rect, 1, border_radius=6)
            value_color = (255, 215, 0) if self.mode == "manual" else (150, 150, 150)
            value_surf = self.font_input.render(str(self.crop_counts[crop]), True, value_color)
            self.screen.blit(value_surf, value_surf.get_rect(center=value_rect.center))
            cy += 46

        total_limit = self._field_limit()
        if self.mode == "manual":
            total_label = f"Selected: {self._selected_total()} / {total_limit} field tiles"
            total_color = (
                (100, 220, 120)
                if self._selected_total() <= total_limit
                else (220, 120, 100)
            )
        else:
            total_label = "Auto mode uses the original random CSP layout."
            total_color = (170, 190, 220)
        total_text = self.font_stat.render(total_label, True, total_color)
        self.screen.blit(total_text, (cx, cy))
        cy += 20

        if self.message:
            message_surf = self.font_legend.render(self.message, True, (255, 160, 120))
            self.screen.blit(message_surf, (cx, cy))
            cy += 18

        # --- Crop counts ---
        cy += 2
        cy = self._draw_section_header("CROPS", cx, cy, sw - 28)

        crop_counts = {CROP_WHEAT: 0, CROP_SUNFLOWER: 0, CROP_CORN: 0}
        for crop in self.csp_solver.assign.values():
            if crop in crop_counts:
                crop_counts[crop] += 1
        total_crops = sum(crop_counts.values())
        total_fields = max(len(self.csp_solver.vars), 1)

        crop_meta = {
            CROP_WHEAT: ("Wheat", (230, 200, 60)),
            CROP_SUNFLOWER: ("Sunflower", (255, 180, 0)),
            CROP_CORN: ("Corn", (160, 210, 60)),
        }
        bar_w = sw - 28

        for crop_type, (cname, ccolor) in crop_meta.items():
            count = crop_counts[crop_type]
            # color swatch + name + count
            pygame.draw.rect(self.screen, ccolor, (cx, cy + 2, 14, 14), border_radius=3)
            label = self.font_stat.render(f"{cname}", True, (210, 210, 200))
            count_surf = self.font_stat.render(str(count), True, (255, 215, 0))
            self.screen.blit(label, (cx + 20, cy))
            self.screen.blit(count_surf, (cx + bar_w - count_surf.get_width(), cy))
            cy += 20
            self._draw_bar(cx, cy, bar_w, 7, count / total_fields, ccolor)
            cy += 16

        # total fill rate
        fill_pct = int(100 * total_crops / total_fields)
        total_surf = self.font_stat.render(
            f"Fill rate {total_crops}/{total_fields} ({fill_pct}%)",
            True,
            (100, 220, 120),
        )
        self.screen.blit(total_surf, (cx, cy + 2))
        cy += 20
        self._draw_bar(
            cx, cy, bar_w, 9, total_crops / total_fields, (80, 200, 100), (50, 45, 35)
        )
        cy += 18

        # --- Terrain counts ---
        cy += 6
        cy = self._draw_section_header("TERRAIN", cx, cy, sw - 28)

        terrain_meta = {
            TILE_WATER: ("Water", (40, 90, 160)),
            TILE_FIELD: ("Field", (101, 67, 33)),
            TILE_GRASS: ("Grass", (56, 95, 40)),
            TILE_DIRT: ("Dirt", (94, 68, 42)),
            TILE_STONE: ("Stone", (100, 100, 110)),
            TILE_MUD: ("Mud", (85, 62, 40)),
        }
        terrain_counts = {t: 0 for t in terrain_meta}
        total_tiles = 0
        for c in range(GRID_COLS):
            for r in range(GRID_ROWS):
                tile = self.grid.get(c, r)
                if tile and tile.type in terrain_counts:
                    terrain_counts[tile.type] += 1
                    total_tiles += 1
        total_tiles = max(total_tiles, 1)

        for tile_type, (tname, tcolor) in terrain_meta.items():
            count = terrain_counts[tile_type]
            pygame.draw.rect(self.screen, tcolor, (cx, cy + 2, 14, 14), border_radius=3)
            label = self.font_stat.render(tname, True, (210, 210, 200))
            cnt_s = self.font_stat.render(str(count), True, (200, 200, 180))
            self.screen.blit(label, (cx + 20, cy))
            self.screen.blit(cnt_s, (cx + bar_w - cnt_s.get_width(), cy))
            cy += 18
            self._draw_bar(cx, cy, bar_w, 5, count / total_tiles, tcolor)
            cy += 10

        # --- Buttons ---
        mp = pygame.mouse.get_pos()
        self.draw_wood_button(
            self.regenerate_button,
            "REGENERATE",
            self.regenerate_button.collidepoint(mp),
        )
        self.draw_wood_button(
            self.confirm_button,
            "START FARMING",
            self.confirm_button.collidepoint(mp),
            accent=True,
        )

    # ── grid preview ─────────────────────────────────────────────────────────

    def draw_grid_preview(self, start_x, start_y, area_w, area_h):
        cell_size = min(area_w // GRID_COLS, area_h // GRID_ROWS, 20)
        total_w = GRID_COLS * cell_size
        total_h = GRID_ROWS * cell_size
        gx = start_x + (area_w - total_w) // 2
        gy = start_y + (area_h - total_h) // 2

        terrain_colors = {
            TILE_WATER: (40, 90, 160),
            TILE_FIELD: (101, 67, 33),
            TILE_GRASS: (56, 95, 40),
            TILE_DIRT: (94, 68, 42),
            TILE_STONE: (100, 100, 110),
            TILE_MUD: (85, 62, 40),
        }
        crop_colors = {
            CROP_WHEAT: (230, 200, 60),
            CROP_SUNFLOWER: (255, 180, 0),
            CROP_CORN: (160, 210, 60),
            CROP_TOMATO: (220, 40, 40),
            CROP_CARROT: (255, 140, 40),
            CROP_POTATO: (180, 140, 80),
        }

        for c in range(GRID_COLS):
            for r in range(GRID_ROWS):
                x = gx + c * cell_size
                y = gy + r * cell_size
                crop = self.csp_solver.assign.get((c, r), CROP_NONE)
                if crop in crop_colors:
                    color = crop_colors[crop]
                else:
                    tile = self.grid.get(c, r)
                    color = (
                        terrain_colors.get(tile.type, (80, 80, 80))
                        if tile
                        else (80, 80, 80)
                    )

                pygame.draw.rect(
                    self.screen, color, (x, y, cell_size - 1, cell_size - 1)
                )

        # thin border around entire preview
        pygame.draw.rect(self.screen, self.wood_dark, (gx, gy, total_w, total_h), 1)

    def is_confirmed(self):
        return self.confirmed
