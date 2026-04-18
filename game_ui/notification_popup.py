"""
game_ui/notification_popup.py — Simple notification popup for messages
"""

import pygame
from utils.constants import *


class NotificationPopup:
    def __init__(self, screen, message, duration=180):  # 3 seconds at 60 FPS
        self.screen = screen
        self.message = message
        self.duration = duration
        self.timer = 0
        self.visible = True

        self.width = 520
        self.height = 190
        self.x = (SCREEN_W - self.width) // 2
        self.y = (SCREEN_H - self.height) // 2

        self.font_title = pygame.font.Font(None, 40)
        self.font_message = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

        self.panel_bg = (20, 30, 25)
        self.border_color = (150, 220, 130)
        self.title_color = (255, 220, 110)
        self.text_color = (230, 230, 230)
        self.progress_bg = (40, 50, 45)
        self.progress_fill = (120, 245, 140)

    def update(self):
        if self.visible:
            self.timer += 1
            if self.timer >= self.duration:
                self.visible = False
                return True
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

        title = self.font_title.render("Harvest Complete!", True, self.title_color)
        title_rect = title.get_rect(center=(self.x + self.width // 2, self.y + 42))
        self.screen.blit(title, title_rect)

        message_lines = self._wrap_text(self.message, self.font_message, self.width - 60)
        y_offset = self.y + 86
        for line in message_lines:
            line_surf = self.font_message.render(line, True, self.text_color)
            line_rect = line_surf.get_rect(center=(self.x + self.width // 2, y_offset))
            self.screen.blit(line_surf, line_rect)
            y_offset += 28

        progress_width = self.width - 80
        progress_height = 14
        progress_x = self.x + 40
        progress_y = self.y + self.height - 52
        pygame.draw.rect(self.screen, self.progress_bg, (progress_x, progress_y, progress_width, progress_height), border_radius=8)
        fill_width = int(progress_width * min(self.timer / max(self.duration, 1), 1.0))
        pygame.draw.rect(self.screen, self.progress_fill, (progress_x, progress_y, fill_width, progress_height), border_radius=8)

        status_text = self.font_small.render("Crops regrowing soon...", True, (200, 240, 190))
        status_rect = status_text.get_rect(center=(self.x + self.width // 2, self.y + self.height - 22))
        self.screen.blit(status_text, status_rect)

    def _wrap_text(self, text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def is_visible(self):
        return self.visible

    def handle_event(self, event):
        return False