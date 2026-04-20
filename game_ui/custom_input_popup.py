"""
game_ui/custom_input_popup.py - Popup for selecting exact crop counts
"""

import pygame

from utils.constants import *


class CustomInputPopup:
    """Popup for choosing exact crop counts with +/- controls."""

    def __init__(self, screen, max_crops=50, initial_counts=None, allowed_crops=None):
        self.screen = screen
        self.visible = True
        self.max_crops = max_crops
        self.selected = False

        self.width = 560
        self.height = 360
        self.x = (SCREEN_W - self.width) // 2
        self.y = (SCREEN_H - self.height) // 2

        self.font_title = pygame.font.Font(None, 42)
        self.font_message = pygame.font.Font(None, 22)
        self.font_input = pygame.font.Font(None, 30)
        self.font_button = pygame.font.Font(None, 26)

        self.panel_bg = (20, 30, 25)
        self.border_color = (150, 220, 130)
        self.title_color = (255, 220, 110)
        self.text_color = (230, 230, 230)
        self.input_bg = (40, 50, 45)
        self.button_normal = (100, 160, 100)
        self.button_hover = (140, 200, 130)
        self.button_text = (255, 255, 255)

        allowed_set = set(allowed_crops) if allowed_crops else None

        default_counts = {
            CROP_WHEAT: 0,
            CROP_SUNFLOWER: 0,
            CROP_CORN: 0,
        }
        if initial_counts:
            for crop in default_counts:
                default_counts[crop] = max(0, int(initial_counts.get(crop, 0)))
        if allowed_set is not None:
            for crop in default_counts:
                if crop not in allowed_set:
                    default_counts[crop] = 0
        self.crop_counts = default_counts

        base_rows = [
            (CROP_WHEAT, "Wheat", (230, 200, 60)),
            (CROP_SUNFLOWER, "Sunflower", (255, 180, 0)),
            (CROP_CORN, "Corn", (160, 210, 60)),
        ]
        if allowed_set is None:
            self.crop_rows = base_rows
        else:
            self.crop_rows = [row for row in base_rows if row[0] in allowed_set]
        self.crop_controls = {}
        self._build_crop_controls()

        self.button_width = 160
        self.button_height = 48
        self.button_x = self.x + (self.width - self.button_width) // 2
        self.button_y = self.y + self.height - 72
        self.button_rect = pygame.Rect(
            self.button_x,
            self.button_y,
            self.button_width,
            self.button_height,
        )

        self.mouse_pos = (0, 0)
        self.submitted = False
        self.error_message = ""
        self.error_timer = 0

    def _build_crop_controls(self):
        row_y = self.y + 120
        row_gap = 58
        for index, (crop, _name, _color) in enumerate(self.crop_rows):
            y = row_y + index * row_gap
            minus_rect = pygame.Rect(self.x + 250, y - 4, 34, 34)
            value_rect = pygame.Rect(self.x + 296, y - 4, 72, 34)
            plus_rect = pygame.Rect(self.x + 380, y - 4, 34, 34)
            self.crop_controls[crop] = {
                "minus": minus_rect,
                "value": value_rect,
                "plus": plus_rect,
            }

    def total_selected(self):
        return sum(self.crop_counts.values())

    def update(self):
        self.mouse_pos = pygame.mouse.get_pos()
        if self.error_timer > 0:
            self.error_timer -= 1
        return False

    def draw(self):
        if not self.visible:
            return

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(self.screen, self.panel_bg, panel_rect, border_radius=22)
        pygame.draw.rect(self.screen, self.border_color, panel_rect, 3, border_radius=22)

        title = self.font_title.render("Custom Crop Generation", True, self.title_color)
        self.screen.blit(title, title.get_rect(center=(self.x + self.width // 2, self.y + 34)))

        message = self.font_message.render(
            f"Select exact crop counts ({self.total_selected()} / {self.max_crops})",
            True,
            self.text_color,
        )
        self.screen.blit(message, message.get_rect(center=(self.x + self.width // 2, self.y + 76)))

        for crop, name, color in self.crop_rows:
            controls = self.crop_controls[crop]
            row_y = controls["value"].y + 4
            pygame.draw.rect(self.screen, color, (self.x + 90, row_y + 6, 16, 16), border_radius=4)
            label = self.font_message.render(name, True, self.text_color)
            self.screen.blit(label, (self.x + 118, row_y + 2))

            for symbol, rect in (("-", controls["minus"]), ("+", controls["plus"])):
                hovered = rect.collidepoint(self.mouse_pos)
                button_color = self.button_hover if hovered else self.button_normal
                pygame.draw.rect(self.screen, button_color, rect, border_radius=8)
                pygame.draw.rect(self.screen, self.border_color, rect, 2, border_radius=8)
                text = self.font_button.render(symbol, True, self.button_text)
                self.screen.blit(text, text.get_rect(center=rect.center))

            value_rect = controls["value"]
            pygame.draw.rect(self.screen, self.input_bg, value_rect, border_radius=8)
            pygame.draw.rect(self.screen, self.border_color, value_rect, 2, border_radius=8)
            value_text = self.font_input.render(str(self.crop_counts[crop]), True, self.text_color)
            self.screen.blit(value_text, value_text.get_rect(center=value_rect.center))

        if self.error_timer > 0:
            error_text = self.font_message.render(self.error_message, True, (255, 100, 100))
            self.screen.blit(
                error_text,
                error_text.get_rect(center=(self.x + self.width // 2, self.y + self.height - 104)),
            )

        button_hover = self.button_rect.collidepoint(self.mouse_pos)
        button_color = self.button_hover if button_hover else self.button_normal
        pygame.draw.rect(self.screen, button_color, self.button_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.border_color, self.button_rect, 2, border_radius=10)
        button_text = self.font_button.render("Generate", True, self.button_text)
        self.screen.blit(button_text, button_text.get_rect(center=self.button_rect.center))

    def handle_keypress(self, key):
        if key == pygame.K_RETURN:
            self.try_submit()

    def _adjust_crop(self, crop, delta):
        new_total = self.total_selected() + delta
        if delta > 0 and new_total > self.max_crops:
            self.error_message = f"Only {self.max_crops} field tiles are available."
            self.error_timer = 120
            return
        next_value = max(0, self.crop_counts[crop] + delta)
        if delta < 0 and self.crop_counts[crop] == 0:
            return
        self.crop_counts[crop] = next_value
        self.error_message = ""
        self.error_timer = 0

    def handle_click(self, pos):
        for crop, controls in self.crop_controls.items():
            if controls["minus"].collidepoint(pos):
                self._adjust_crop(crop, -1)
                return
            if controls["plus"].collidepoint(pos):
                self._adjust_crop(crop, 1)
                return
        if self.button_rect.collidepoint(pos):
            self.try_submit()

    def try_submit(self):
        if self.total_selected() <= 0:
            self.error_message = "Select at least one crop."
            self.error_timer = 120
            return None
        self.submitted = True
        self.visible = False
        return self.get_value()

    def get_value(self):
        if self.submitted:
            return dict(self.crop_counts)
        return None

    def is_visible(self):
        return self.visible
