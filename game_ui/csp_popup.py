"""
game_ui/csp_popup.py — CSP Layout Generation Popup (Minimal UI)
- Only two buttons: Regenerate and Start Farming
- Shows grid preview with terrain + crop colors
- Shows assigned tiles count
"""

import pygame
from utils.constants import *
from utils.helpers import draw_rounded_rect


class CSPPopup:
    def __init__(self, screen, grid, csp_solver):
        self.screen = screen
        self.grid = grid
        self.csp_solver = csp_solver
        self.visible = True
        self.confirmed = False

        # Popup dimensions
        self.width = 900
        self.height = 650
        self.x = (SCREEN_W - self.width) // 2
        self.y = (SCREEN_H - self.height) // 2

        # Buttons
        self.regenerate_button = pygame.Rect(
            self.x + self.width - 320, self.y + self.height - 70, 140, 48
        )
        self.confirm_button = pygame.Rect(
            self.x + self.width - 160, self.y + self.height - 70, 140, 48
        )

        # Fonts
        self.font_title = pygame.font.Font(None, 28)
        self.font_stats = pygame.font.Font(None, 20)
        self.font_btn = pygame.font.Font(None, 22)
        self.font_label = pygame.font.Font(None, 14)

    def regenerate_everything(self):
        """Regenerate BOTH terrain AND crops"""
        print("\n🔄 Regenerating entire farm layout...")

        self.grid._build_map()
        self.grid._bake_all()

        self.csp_solver.vars = self.grid.field_tiles()
        self.csp_solver.water = self.grid.water_sources()
        self.csp_solver.assign = {}
        self.csp_solver.log = []

        self.csp_solver.solve()
        self.csp_solver.apply_to_grid()

        print("✅ New layout generated!\n")

    def handle_event(self, event):
        if not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            if self.confirm_button.collidepoint(mouse_pos):
                self.visible = False
                self.confirmed = True
                return True

            if self.regenerate_button.collidepoint(mouse_pos):
                self.regenerate_everything()
                return True

        return False

    def draw(self):
        if not self.visible:
            return

        # Dark overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        # Popup panel
        draw_rounded_rect(
            self.screen,
            (30, 35, 45, 250),
            (self.x, self.y, self.width, self.height),
            radius=16,
            border=2,
            border_color=(100, 180, 100),
        )

        # Title
        title = self.font_title.render("🌾 FARM LAYOUT GENERATOR", True, (255, 215, 0))
        title_rect = title.get_rect(center=(self.x + self.width // 2, self.y + 30))
        self.screen.blit(title, title_rect)

        # Draw grid preview
        self.draw_grid_preview()

        # Draw stats (assigned tiles count only)
        planted = sum(
            1 for crop in self.csp_solver.assign.values() if crop != CROP_NONE
        )
        total = len(self.csp_solver.vars)

        stats_text = f"CROPS PLANTED: {planted} / {total}"
        stats_surf = self.font_stats.render(stats_text, True, (100, 255, 100))
        self.screen.blit(stats_surf, (self.x + 30, self.y + self.height - 95))

        # Draw legend (crop and terrain colors)
        self.draw_legend()

        # Draw buttons
        # Regenerate button
        pygame.draw.rect(
            self.screen, (50, 80, 50), self.regenerate_button, border_radius=10
        )
        pygame.draw.rect(
            self.screen, (100, 200, 100), self.regenerate_button, 2, border_radius=10
        )
        regen_text = self.font_btn.render("⟳ REGENERATE", True, (255, 255, 255))
        regen_rect = regen_text.get_rect(center=self.regenerate_button.center)
        self.screen.blit(regen_text, regen_rect)

        # Start Farming button
        pygame.draw.rect(
            self.screen, (50, 100, 50), self.confirm_button, border_radius=10
        )
        pygame.draw.rect(
            self.screen, (100, 220, 100), self.confirm_button, 2, border_radius=10
        )
        confirm_text = self.font_btn.render("✓ START FARMING", True, (255, 255, 255))
        confirm_rect = confirm_text.get_rect(center=self.confirm_button.center)
        self.screen.blit(confirm_text, confirm_rect)

    def draw_grid_preview(self):
        """Draw the grid preview with terrain + crop colors"""

        margin = 20
        preview_w = self.width - (margin * 2)
        preview_h = self.height - 180

        cell_w = preview_w // GRID_COLS
        cell_h = preview_h // GRID_ROWS
        cell_size = min(cell_w, cell_h, 14)

        total_w = GRID_COLS * cell_size
        total_h = GRID_ROWS * cell_size
        start_x = self.x + (self.width - total_w) // 2
        start_y = self.y + 70

        # Background
        bg_rect = pygame.Rect(start_x - 5, start_y - 5, total_w + 10, total_h + 10)
        pygame.draw.rect(self.screen, (20, 25, 30), bg_rect, border_radius=6)
        pygame.draw.rect(self.screen, (80, 120, 80), bg_rect, 2, border_radius=6)

        # Terrain colors
        terrain_colors = {
            TILE_WATER: (40, 90, 160),
            TILE_FIELD: (101, 67, 33),
            TILE_GRASS: (56, 95, 40),
            TILE_DIRT: (94, 68, 42),
            TILE_STONE: (100, 100, 110),
            TILE_MUD: (85, 62, 40),
        }

        # Crop colors
        crop_colors = {
            CROP_WHEAT: (230, 200, 60),
            CROP_SUNFLOWER: (255, 180, 0),
            CROP_CORN: (180, 220, 60),
        }

        for c in range(GRID_COLS):
            for r in range(GRID_ROWS):
                x = start_x + c * cell_size
                y = start_y + r * cell_size

                crop = self.csp_solver.assign.get((c, r), CROP_NONE)

                if crop in crop_colors:
                    color = crop_colors[crop]
                else:
                    tile = self.grid.get(c, r)
                    if tile:
                        color = terrain_colors.get(tile.type, (80, 80, 80))
                    else:
                        color = (80, 80, 80)

                pygame.draw.rect(
                    self.screen, color, (x, y, cell_size - 1, cell_size - 1)
                )
                pygame.draw.rect(
                    self.screen, (50, 50, 60), (x, y, cell_size - 1, cell_size - 1), 1
                )

    def draw_legend(self):
        """Draw color legend at bottom"""
        legend_x = self.x + 30
        legend_y = self.y + self.height - 55

        legend_items = [
            ("🌾 Wheat", (230, 200, 60)),
            ("🌻 Sunflower", (255, 180, 0)),
            ("🌽 Corn", (180, 220, 60)),
            ("💧 Water", (40, 90, 160)),
            ("🌿 Field", (101, 67, 33)),
            ("🍃 Grass", (56, 95, 40)),
            ("🟫 Dirt", (94, 68, 42)),
            ("🪨 Stone", (100, 100, 110)),
            ("💩 Mud", (85, 62, 40)),
        ]

        current_x = legend_x
        for name, color in legend_items:
            # Color box
            pygame.draw.rect(
                self.screen, color, (current_x, legend_y, 14, 14), border_radius=2
            )
            # Name
            text = self.font_label.render(name, True, (180, 180, 180))
            self.screen.blit(text, (current_x + 18, legend_y))
            current_x += text.get_width() + 35

            # Wrap to next line if needed
            if current_x > self.x + self.width - 50:
                current_x = legend_x
                legend_y += 22

    def is_confirmed(self):
        return self.confirmed
