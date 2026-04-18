"""
game_ui/regeneration_popup.py — Popup for choosing Auto or Custom crop regeneration
"""

import pygame
from utils.constants import *


class RegenerationPopup:
    """Popup with 2 buttons: Auto Generate and Custom Input"""

    def __init__(
        self,
        screen,
        title="All Crops Collected!",
        message="Choose how to regenerate your crops:",
    ):
        self.screen = screen
        self.visible = True
        self.title = title
        self.message = message
        
        self.width = 600
        self.height = 280
        self.x = (SCREEN_W - self.width) // 2
        self.y = (SCREEN_H - self.height) // 2
        
        self.font_title = pygame.font.Font(None, 44)
        self.font_message = pygame.font.Font(None, 24)
        self.font_button = pygame.font.Font(None, 28)
        
        self.panel_bg = (20, 30, 25)
        self.border_color = (150, 220, 130)
        self.title_color = (255, 220, 110)
        self.text_color = (230, 230, 230)
        self.button_normal = (100, 160, 100)
        self.button_hover = (140, 200, 130)
        self.button_text = (255, 255, 255)
        
        # Button positions
        self.button_width = 220
        self.button_height = 60
        self.button_y = self.y + 160
        self.button_auto_x = self.x + 50
        self.button_custom_x = self.x + self.width - 50 - self.button_width
        
        self.button_auto_rect = pygame.Rect(self.button_auto_x, self.button_y, self.button_width, self.button_height)
        self.button_custom_rect = pygame.Rect(self.button_custom_x, self.button_y, self.button_width, self.button_height)
        
        self.mouse_pos = (0, 0)
        self.selected = None  # "auto" or "custom"
    
    def update(self):
        if self.visible:
            self.mouse_pos = pygame.mouse.get_pos()
        return False
    
    def draw(self):
        if not self.visible:
            return
        
        # Dark overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Main panel
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(self.screen, self.panel_bg, panel_rect, border_radius=22)
        pygame.draw.rect(self.screen, self.border_color, panel_rect, 3, border_radius=22)
        
        # Title
        title = self.font_title.render(self.title, True, self.title_color)
        title_rect = title.get_rect(center=(self.x + self.width // 2, self.y + 35))
        self.screen.blit(title, title_rect)

        # Message
        message = self.font_message.render(self.message, True, self.text_color)
        message_rect = message.get_rect(center=(self.x + self.width // 2, self.y + 85))
        self.screen.blit(message, message_rect)
        
        # Auto Generate Button
        auto_hover = self.button_auto_rect.collidepoint(self.mouse_pos)
        auto_color = self.button_hover if auto_hover else self.button_normal
        pygame.draw.rect(self.screen, auto_color, self.button_auto_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.border_color, self.button_auto_rect, 2, border_radius=12)
        auto_text = self.font_button.render("Auto Generate", True, self.button_text)
        auto_text_rect = auto_text.get_rect(center=self.button_auto_rect.center)
        self.screen.blit(auto_text, auto_text_rect)
        
        # Custom Input Button
        custom_hover = self.button_custom_rect.collidepoint(self.mouse_pos)
        custom_color = self.button_hover if custom_hover else self.button_normal
        pygame.draw.rect(self.screen, custom_color, self.button_custom_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.border_color, self.button_custom_rect, 2, border_radius=12)
        custom_text = self.font_button.render("Custom Input", True, self.button_text)
        custom_text_rect = custom_text.get_rect(center=self.button_custom_rect.center)
        self.screen.blit(custom_text, custom_text_rect)
    
    def handle_click(self, pos):
        """Returns 'auto', 'custom', or None based on button clicked"""
        if self.button_auto_rect.collidepoint(pos):
            self.selected = "auto"
            return "auto"
        elif self.button_custom_rect.collidepoint(pos):
            self.selected = "custom"
            return "custom"
        return None
    
    def is_visible(self):
        return self.visible
