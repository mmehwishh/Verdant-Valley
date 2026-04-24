"""
CSP Popup - Farm Layout Generation with Wood Theme
Left: Farm grid preview + terrain info
Right: Statistics panel with crop counts and generation options
"""

import pygame
from utils.constants import *


class CSPPopup:
    """Popup window for CSP-based farm layout generation"""

    def __init__(self, screen, grid, csp_solver):
        self.screen = screen
        self.grid = grid
        self.csp_solver = csp_solver
        self.visible = True
        self.confirmed = False

        # Panel dimensions
        self.width = 1100
        self.height = 750
        self.x = (SCREEN_W - self.width) // 2
        self.y = (SCREEN_H - self.height) // 2

        # Layout sections
        self.grid_area_width = int(self.width * 0.55)
        self.terrain_area_height = 180
        self.grid_preview_height = self.height - self.terrain_area_height - 100
        self.stats_area_width = self.width - self.grid_area_width - 50

        # Buttons
        btn_width = 170
        btn_height = 46
        btn_y = self.y + self.height - 62
        btn_gap = 10
        total_btn_w = btn_width * 2 + btn_gap
        btn_start_x = self.x + self.width - total_btn_w - 22
        self.regenerate_button = pygame.Rect(
            btn_start_x, btn_y, btn_width, btn_height
        )
        self.confirm_button = pygame.Rect(
            btn_start_x + btn_width + btn_gap, btn_y, btn_width, btn_height
        )

        # Fonts
        self.font_title = pygame.font.Font(None, 38)
        self.font_header = pygame.font.Font(None, 22)
        self.font_stat = pygame.font.Font(None, 20)
        self.font_btn = pygame.font.Font(None, 22)
        self.font_btn_small = pygame.font.Font(None, 18)
        self.font_legend = pygame.font.Font(None, 16)
        self.font_input = pygame.font.Font(None, 24)

        # Colors
        self.wood_base = (139, 90, 43)
        self.wood_dark = (100, 65, 30)
        self.wood_light = (170, 115, 55)
        self.panel_bg = (28, 22, 16)
        self.inner_bg = (38, 30, 20)

        # Crop counts from solver
        requested = self.csp_solver.get_requested_counts()
        self.crop_counts = {
            CROP_WHEAT: requested.get(CROP_WHEAT, 0),
            CROP_SUNFLOWER: requested.get(CROP_SUNFLOWER, 0),
            CROP_CORN: requested.get(CROP_CORN, 0),
            CROP_TOMATO: requested.get(CROP_TOMATO, 0),
            CROP_CARROT: requested.get(CROP_CARROT, 0),
        }
        self.mode = self.csp_solver.get_mode()
        self.crop_controls = {}
        self.mode_buttons = {}
        self.message = ""
        self.last_generation_adjusted = False
        self._build_layout_controls()

    # ============================================================
    # UI CONSTRUCTION
    # ============================================================

    def _build_layout_controls(self):
        """Create mode selection and crop adjustment controls"""
        stats_x = self.x + self.grid_area_width + 8
        stats_y = self.y + 64 + 14
        inner_x = stats_x + 14
        inner_w = self.stats_area_width - 28

        # Mode buttons (Auto / Manual)
        mode_y = stats_y + 30
        gap = 10
        mode_w = (inner_w - gap) // 2
        self.mode_buttons["auto"] = pygame.Rect(inner_x, mode_y, mode_w, 34)
        self.mode_buttons["manual"] = pygame.Rect(
            inner_x + mode_w + gap, mode_y, inner_w - mode_w - gap, 34
        )

        # Crop adjustment buttons (+ / -)
        crop_y = mode_y + 84
        row_gap = 42
        btn_size = 28
        value_w = 72

        for idx, crop in enumerate(
            [CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_TOMATO, CROP_CARROT]
        ):
            row_y = crop_y + idx * row_gap
            self.crop_controls[crop] = {
                "minus": pygame.Rect(inner_x + 132, row_y - 4, btn_size, btn_size),
                "value": pygame.Rect(inner_x + 168, row_y - 4, value_w, btn_size),
                "plus": pygame.Rect(inner_x + 248, row_y - 4, btn_size, btn_size),
            }

    # ============================================================
    # DATA MANAGEMENT
    # ============================================================

    def _field_limit(self):
        return self.csp_solver.available_field_count()

    def _selected_total(self):
        return sum(self.crop_counts.values())

    def _sync_solver_counts(self):
        """Push current crop counts to CSP solver"""
        try:
            self.csp_solver.set_mode(self.mode)
            self.csp_solver.set_requested_counts(self.crop_counts)
            self.message = ""
            return True
        except ValueError as e:
            self.message = str(e)
            return False

    def _adjust_crop(self, crop, delta):
        """Increase or decrease crop count within field limits"""
        new_value = max(0, self.crop_counts[crop] + delta)
        new_counts = dict(self.crop_counts)
        new_counts[crop] = new_value

        if sum(new_counts.values()) > self._field_limit():
            self.message = (
                f"Total crops cannot exceed {self._field_limit()} available field tiles"
            )
            return

        self.crop_counts = new_counts
        self._sync_solver_counts()

    def _set_mode(self, mode):
        self.mode = mode
        self._sync_solver_counts()

    def _current_assignment_count(self):
        """Return the number of currently assigned non-empty crops."""
        return sum(
            1
            for crop in getattr(self.csp_solver, "assign", {}).values()
            if crop != CROP_NONE
        )

    def _current_assignment_breakdown(self):
        """Return the assigned crop counts from the current solver state."""
        counts = {
            CROP_WHEAT: 0,
            CROP_SUNFLOWER: 0,
            CROP_CORN: 0,
            CROP_TOMATO: 0,
            CROP_CARROT: 0,
        }
        for crop in getattr(self.csp_solver, "assign", {}).values():
            if crop in counts:
                counts[crop] += 1
        return counts

    def _try_generate_with_counts(self, counts):
        """Try generating a layout with the provided counts."""
        self.grid._build_map()
        self.grid._bake_all()
        self.csp_solver.refresh_grid_context()
        self.csp_solver.set_mode(self.mode)
        self.csp_solver.set_requested_counts(counts)

        solved = self.csp_solver.solve(counts)
        assigned_count = self._current_assignment_count()
        return solved and assigned_count > 0

    def _reduce_to_feasible_counts(self, counts):
        """Reduce an invalid manual crop mix until a valid layout is found."""
        trial_counts = dict(counts)
        original_total = sum(trial_counts.values())

        while sum(trial_counts.values()) > 0:
            if self._try_generate_with_counts(trial_counts):
                placed_counts = self._current_assignment_breakdown()
                placed_total = sum(placed_counts.values())
                self.csp_solver.apply_to_grid()
                self.crop_counts = placed_counts
                self.message = (
                    f"Invalid combo detected. Requested {original_total} crops, so only {placed_total} valid assignments were generated automatically."
                )
                self.last_generation_adjusted = True
                return True

            reducible = [crop for crop, value in trial_counts.items() if value > 0]
            if not reducible:
                break

            crop_to_reduce = max(
                reducible,
                key=lambda crop: (trial_counts[crop], self.crop_counts.get(crop, 0)),
            )
            trial_counts[crop_to_reduce] -= 1

        return False

    def regenerate_everything(self):
        """Regenerate entire farm layout using CSP, refusing zero-assignment results."""
        self.last_generation_adjusted = False

        attempts = 6 if self.mode == "auto" else 1
        last_reason = "No valid crop layout could be generated."

        for _ in range(attempts):
            self._sync_solver_counts()
            if self._try_generate_with_counts(self.crop_counts):
                assigned_count = self._current_assignment_count()
                self.csp_solver.apply_to_grid()

                if self.mode == "auto":
                    self.crop_counts = self._current_assignment_breakdown()

                self.message = ""
                return "success"

            last_reason = (
                getattr(self.csp_solver, "last_failure_reason", "") or last_reason
            )

        if self.mode == "manual" and self._reduce_to_feasible_counts(self.crop_counts):
            return "adjusted"

        self.message = (
            f"No valid assignment found. {last_reason} Adjust crop counts and try again."
            if self.mode == "manual"
            else "Auto mode could not find a valid crop layout. Please regenerate again."
        )
        return False

    # ============================================================
    # DRAWING HELPERS
    # ============================================================

    def _draw_section_header(self, text, x, y, width):
        label = self.font_header.render(text, True, (255, 215, 0))
        self.screen.blit(label, (x, y))
        line_y = y + label.get_height() + 4
        pygame.draw.line(
            self.screen, self.wood_base, (x, line_y), (x + width, line_y), 1
        )
        return line_y + 8

    def _draw_bar(self, x, y, w, h, fraction, color, bg_color=(60, 50, 40)):
        pygame.draw.rect(self.screen, bg_color, (x, y, w, h), border_radius=3)
        fill_w = max(2, int(w * min(fraction, 1.0)))
        pygame.draw.rect(self.screen, color, (x, y, fill_w, h), border_radius=3)

    def draw_wood_button(
        self, rect, text, is_hover=False, accent=False, compact=False, text_font=None
    ):
        """Draw wooden-styled button"""
        if accent:
            base = (60, 140, 80) if not is_hover else (75, 165, 95)
            dark = (35, 90, 50)
        else:
            base = self.wood_light if is_hover else self.wood_base
            dark = self.wood_dark

        radius = 8 if compact else 10
        pygame.draw.rect(self.screen, base, rect, border_radius=radius)

        # Wood grain lines
        if not compact and rect.height >= 42:
            for i in range(3):
                line_y = rect.y + 11 + i * 14
                pygame.draw.line(
                    self.screen,
                    dark,
                    (rect.x + 10, line_y),
                    (rect.x + rect.width - 10, line_y),
                    1,
                )

        pygame.draw.rect(self.screen, dark, rect, 2, border_radius=radius)

        font = text_font or (self.font_btn_small if compact else self.font_btn)
        label = font.render(text, True, (255, 255, 255))
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw_grid_preview(self, start_x, start_y, area_w, area_h):
        """Draw mini grid preview with current crop assignments"""
        cell_size = min(area_w // GRID_COLS, area_h // GRID_ROWS, 20)
        total_w = GRID_COLS * cell_size
        total_h = GRID_ROWS * cell_size
        grid_x = start_x + (area_w - total_w) // 2
        grid_y = start_y + (area_h - total_h) // 2

        # Color maps
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
        }

        for col in range(GRID_COLS):
            for row in range(GRID_ROWS):
                x = grid_x + col * cell_size
                y = grid_y + row * cell_size
                crop = self.csp_solver.assign.get((col, row), CROP_NONE)

                if crop in crop_colors:
                    color = crop_colors[crop]
                else:
                    tile = self.grid.get(col, row)
                    color = (
                        terrain_colors.get(tile.type, (80, 80, 80))
                        if tile
                        else (80, 80, 80)
                    )

                pygame.draw.rect(
                    self.screen, color, (x, y, cell_size - 1, cell_size - 1)
                )

        pygame.draw.rect(
            self.screen, self.wood_dark, (grid_x, grid_y, total_w, total_h), 1
        )

    # ============================================================
    # TERRAIN SECTION
    # ============================================================

    def _draw_terrain_section(self, x, y, width):
        """Draw terrain type statistics and mini bars"""
        header_y = self._draw_section_header("TERRAIN TYPES", x, y, width - 28)

        terrain_meta = {
            TILE_WATER: ("Water", (40, 90, 160)),
            TILE_FIELD: ("Field", (101, 67, 33)),
            TILE_GRASS: ("Grass", (56, 95, 40)),
            TILE_DIRT: ("Dirt", (94, 68, 42)),
            TILE_STONE: ("Stone", (100, 100, 110)),
            TILE_MUD: ("Mud", (85, 62, 40)),
        }

        # Count terrain tiles
        terrain_counts = {t: 0 for t in terrain_meta}
        total_tiles = 0
        for col in range(GRID_COLS):
            for row in range(GRID_ROWS):
                tile = self.grid.get(col, row)
                if tile and tile.type in terrain_counts:
                    terrain_counts[tile.type] += 1
                    total_tiles += 1
        total_tiles = max(total_tiles, 1)

        # Two-column layout
        col1_x = x
        col2_x = x + (width - 28) // 2 + 20
        row_y = header_y
        items = list(terrain_meta.items())
        half = len(items) // 2

        for i, (tile_type, (name, color)) in enumerate(items):
            draw_x = col1_x if i < half else col2_x
            if i == half:
                row_y = header_y

            count = terrain_counts[tile_type]

            # Color swatch
            pygame.draw.rect(
                self.screen, color, (draw_x, row_y + 2, 14, 14), border_radius=3
            )

            # Labels
            name_label = self.font_stat.render(name, True, (210, 210, 200))
            count_label = self.font_stat.render(str(count), True, (200, 200, 180))
            self.screen.blit(name_label, (draw_x + 20, row_y))
            self.screen.blit(count_label, (draw_x + 120, row_y))

            # Progress bar
            self._draw_bar(draw_x + 20, row_y + 18, 100, 5, count / total_tiles, color)
            row_y += 32

        return row_y

    # ============================================================
    # STATS PANEL
    # ============================================================

    def _draw_stats_panel(self, x, y, width):
        """Draw right-side statistics panel"""
        inner_x = x + 14
        inner_y = y + 14
        inner_w = width - 28

        # Generation mode selection
        cy = self._draw_section_header("GENERATION MODE", inner_x, inner_y, inner_w)

        for mode, rect in self.mode_buttons.items():
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            active = self.mode == mode
            self.draw_wood_button(
                rect,
                mode.upper(),
                hovered or active,
                accent=active,
                compact=True,
                text_font=self.font_btn_small,
            )

        cy += 56

        # Crop selection
        cy = self._draw_section_header("SELECT CROPS", inner_x, cy, inner_w)

        crop_rows = [
            (CROP_WHEAT, "Wheat", (230, 200, 60)),
            (CROP_SUNFLOWER, "Sunflower", (255, 180, 0)),
            (CROP_CORN, "Corn", (160, 210, 60)),
            (CROP_TOMATO, "Tomato", (220, 40, 40)),
            (CROP_CARROT, "Carrot", (255, 140, 40)),
        ]

        for crop, name, color in crop_rows:
            controls = self.crop_controls[crop]

            # Crop color swatch
            pygame.draw.rect(
                self.screen, color, (inner_x, cy + 4, 14, 14), border_radius=3
            )

            # Crop name
            label_color = (210, 210, 200) if self.mode == "manual" else (140, 140, 140)
            label = self.font_stat.render(name, True, label_color)
            self.screen.blit(label, (inner_x + 22, cy))

            # Minus button
            hovered = controls["minus"].collidepoint(pygame.mouse.get_pos())
            self.draw_wood_button(
                controls["minus"],
                "-",
                hovered and self.mode == "manual",
                compact=True,
                text_font=self.font_btn,
            )

            # Plus button
            hovered = controls["plus"].collidepoint(pygame.mouse.get_pos())
            self.draw_wood_button(
                controls["plus"],
                "+",
                hovered and self.mode == "manual",
                compact=True,
                text_font=self.font_btn,
            )

            # Value display
            value_rect = controls["value"]
            pygame.draw.rect(self.screen, (55, 44, 30), value_rect, border_radius=6)
            pygame.draw.rect(
                self.screen, self.wood_dark, value_rect, 1, border_radius=6
            )

            value_color = (255, 215, 0) if self.mode == "manual" else (150, 150, 150)
            value_surf = self.font_input.render(
                str(self.crop_counts[crop]), True, value_color
            )
            self.screen.blit(value_surf, value_surf.get_rect(center=value_rect.center))

            cy += 42

        # Total selection display
        total_limit = self._field_limit()
        if self.mode == "manual":
            total_label = (
                f"Selected: {self._selected_total()} / {total_limit} field tiles"
            )
            total_color = (
                (100, 220, 120)
                if self._selected_total() <= total_limit
                else (220, 120, 100)
            )
        else:
            total_label = "Auto mode uses original random CSP layout"
            total_color = (170, 190, 220)

        total_text = self.font_stat.render(total_label, True, total_color)
        self.screen.blit(total_text, (inner_x, cy))
        cy += 20

        # Error message
        if self.message:
            words = self.message.split()
            line, lines = "", []
            for word in words:
                test = (line + " " + word).strip()
                if self.font_legend.size(test)[0] <= inner_w:
                    line = test
                else:
                    if line: lines.append(line)
                    line = word
            if line: lines.append(line)
            for l in lines:
                self.screen.blit(self.font_legend.render(l, True, (255, 160, 120)), (inner_x, cy))
                cy += 16
            cy += 2

        # Crops placed section
        cy += 2
        cy = self._draw_section_header("CROPS PLACED", inner_x, cy, inner_w)

        # Count crops from solver
        crop_counts = {
            c: 0
            for c in [CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_TOMATO, CROP_CARROT]
        }
        for crop in self.csp_solver.assign.values():
            if crop in crop_counts:
                crop_counts[crop] += 1

        total_crops = sum(crop_counts.values())
        total_fields = max(len(self.csp_solver.vars), 1)
        bar_w = inner_w

        # Display each crop count with bar
        crop_meta = {
            CROP_WHEAT: ("Wheat", (230, 200, 60)),
            CROP_SUNFLOWER: ("Sunflower", (255, 180, 0)),
            CROP_CORN: ("Corn", (160, 210, 60)),
            CROP_TOMATO: ("Tomato", (220, 40, 40)),
            CROP_CARROT: ("Carrot", (255, 140, 40)),
        }

        for crop_type, (name, color) in crop_meta.items():
            count = crop_counts[crop_type]
            pygame.draw.rect(
                self.screen, color, (inner_x, cy + 2, 14, 14), border_radius=3
            )

            name_label = self.font_stat.render(name, True, (210, 210, 200))
            count_label = self.font_stat.render(str(count), True, (255, 215, 0))
            self.screen.blit(name_label, (inner_x + 20, cy))
            self.screen.blit(
                count_label, (inner_x + bar_w - count_label.get_width(), cy)
            )

            cy += 20
            self._draw_bar(inner_x, cy, bar_w, 7, count / total_fields, color)
            cy += 16

        # Fill rate
        fill_pct = int(100 * total_crops / total_fields)
        fill_text = self.font_stat.render(
            f"Fill rate {total_crops}/{total_fields} ({fill_pct}%)",
            True,
            (100, 220, 120),
        )
        self.screen.blit(fill_text, (inner_x, cy + 2))
        cy += 20
        self._draw_bar(
            inner_x,
            cy,
            bar_w,
            9,
            total_crops / total_fields,
            (80, 200, 100),
            (50, 45, 35),
        )

        return cy + 18

    # ============================================================
    # MAIN DRAW METHOD
    # ============================================================

    def draw(self):
        """Render the CSP popup window"""
        if not self.visible:
            return

        # Background dim
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        # Main panel
        panel = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(self.screen, self.wood_dark, panel, border_radius=18)
        pygame.draw.rect(
            self.screen, self.wood_light, panel.inflate(-4, -4), border_radius=16
        )
        pygame.draw.rect(
            self.screen, self.panel_bg, panel.inflate(-10, -10), border_radius=13
        )

        # Title strip
        title_strip = pygame.Rect(self.x + 5, self.y + 5, self.width - 10, 52)
        pygame.draw.rect(self.screen, self.wood_dark, title_strip, border_radius=13)
        title = self.font_title.render("FARM LAYOUT GENERATOR", True, (255, 215, 0))
        self.screen.blit(
            title, title.get_rect(center=(self.x + self.width // 2, self.y + 32))
        )

        content_y = self.y + 64
        left_x = self.x + 12
        left_w = self.grid_area_width - 18

        # Grid preview
        grid_h = self.grid_preview_height
        pygame.draw.rect(
            self.screen,
            self.inner_bg,
            (left_x, content_y, left_w, grid_h),
            border_radius=10,
        )
        pygame.draw.rect(
            self.screen,
            self.wood_dark,
            (left_x, content_y, left_w, grid_h),
            1,
            border_radius=10,
        )
        self.draw_grid_preview(left_x + 6, content_y + 6, left_w - 12, grid_h - 12)

        # Terrain section
        terrain_y = content_y + grid_h + 10
        pygame.draw.rect(
            self.screen,
            self.inner_bg,
            (left_x, terrain_y, left_w, self.terrain_area_height),
            border_radius=10,
        )
        pygame.draw.rect(
            self.screen,
            self.wood_dark,
            (left_x, terrain_y, left_w, self.terrain_area_height),
            1,
            border_radius=10,
        )
        self._draw_terrain_section(left_x + 14, terrain_y + 10, left_w - 28)

        # Stats panel (right side)
        stats_x = self.x + self.grid_area_width + 8
        stats_w = self.stats_area_width
        stats_h = self.height - 74
        pygame.draw.rect(
            self.screen,
            self.inner_bg,
            (stats_x, content_y, stats_w, stats_h),
            border_radius=10,
        )
        pygame.draw.rect(
            self.screen,
            self.wood_dark,
            (stats_x, content_y, stats_w, stats_h),
            1,
            border_radius=10,
        )

        self._draw_stats_panel(stats_x, content_y, stats_w)

        # Buttons
        mouse_pos = pygame.mouse.get_pos()
        self.draw_wood_button(
            self.regenerate_button,
            "REGENERATE",
            self.regenerate_button.collidepoint(mouse_pos),
        )
        self.draw_wood_button(
            self.confirm_button,
            "START FARMING",
            self.confirm_button.collidepoint(mouse_pos),
            accent=True,
        )

    # ============================================================
    # EVENT HANDLING
    # ============================================================

    def handle_event(self, event):
        """Process mouse clicks on popup controls"""
        if not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos

            # Mode selection
            for mode, rect in self.mode_buttons.items():
                if rect.collidepoint(pos):
                    self._set_mode(mode)
                    return True

            # Crop count adjustment (manual mode only)
            if self.mode == "manual":
                for crop, controls in self.crop_controls.items():
                    if controls["minus"].collidepoint(pos):
                        self._adjust_crop(crop, -1)
                        return True
                    if controls["plus"].collidepoint(pos):
                        self._adjust_crop(crop, 1)
                        return True

            # Confirm button
            if self.confirm_button.collidepoint(pos):
                result = self.regenerate_everything()
                if result == "success":
                    self.visible = False
                    self.confirmed = True
                elif result == "adjusted":
                    # Keep popup open so the user can read the adjustment message,
                    # then allow a second confirm click to proceed.
                    return True
                return True

            # Regenerate button
            if self.regenerate_button.collidepoint(pos):
                self.regenerate_everything()
                return True

        return False

    def is_confirmed(self):
        return self.confirmed