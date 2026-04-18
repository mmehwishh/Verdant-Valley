"""
main.py — Verdant Valley (Full Game with Menu, Settings & Music Control)
"""

import sys
import pygame
import os
import random
import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.constants import *
from src.world.environment.grid import Grid
from src.world.environment.season import SeasonManager
from src.agents.farmer import Farmer
from src.agents.guard import Guard
from src.agents.animal import Animal
from src.algorithms.csp import CSPSolver
from game_ui.farm_layout import FarmUI
from game_ui.csp_popup import CSPPopup
from game_ui.notification_popup import NotificationPopup
from game_ui.regeneration_popup import RegenerationPopup
from game_ui.custom_input_popup import CustomInputPopup


class VideoLoader:
    """Handles video playback (streaming - no preloading)"""

    def __init__(self, video_path):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            print(f"Could not open video: {video_path}")
            self.cap = None
        else:
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"✓ Video loaded: {self.total_frames} frames")

    def get_frame(self):
        if not self.cap:
            return None
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.rot90(frame)
            frame = pygame.surfarray.make_surface(frame)
            frame = pygame.transform.scale(frame, (SCREEN_W, SCREEN_H))
            return frame
        return None

    def __del__(self):
        if self.cap:
            self.cap.release()


class WoodButton:
    def __init__(self, x, y, width, height, text, text_color=(255, 215, 0)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.text_color = text_color
        self.hovered = False
        self.font = pygame.font.Font(None, 32)

    def draw(self, screen):
        wood_base = (160, 110, 60)
        wood_dark = (130, 85, 45)
        wood_light = (180, 130, 80)
        color = wood_light if self.hovered else wood_base
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        for i in range(3):
            line_y = self.rect.y + 15 + i * 15
            pygame.draw.line(screen, wood_dark,
                             (self.rect.x + 10, line_y),
                             (self.rect.x + self.rect.width - 10, line_y), 1)
        pygame.draw.rect(screen, (100, 70, 40), self.rect, 2, border_radius=12)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class Slider:
    def __init__(self, x, y, width, min_val=0, max_val=100, initial=70):
        self.rect = pygame.Rect(x, y, width, 10)
        self.knob_radius = 8
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial
        self.dragging = False

    def draw(self, screen, font):
        pygame.draw.rect(screen, (50, 50, 70), self.rect, border_radius=5)
        fill_width = int(
            (self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width
        )
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(screen, (100, 200, 100), fill_rect, border_radius=5)
        knob_x = self.rect.x + fill_width
        pygame.draw.circle(screen, (255, 215, 0), (knob_x, self.rect.centery), self.knob_radius)
        pygame.draw.circle(screen, (255, 255, 255), (knob_x, self.rect.centery), self.knob_radius - 2)
        value_text = font.render(f"{int(self.value)}%", True, (200, 200, 200))
        screen.blit(value_text, (self.rect.right + 10, self.rect.centery - 8))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            knob_x = self.rect.x + int(
                (self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width
            )
            knob_rect = pygame.Rect(
                knob_x - self.knob_radius,
                self.rect.centery - self.knob_radius,
                self.knob_radius * 2,
                self.knob_radius * 2,
            )
            if knob_rect.collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            rel_x = max(0, min(event.pos[0] - self.rect.x, self.rect.width))
            self.value = self.min_val + (rel_x / self.rect.width) * (self.max_val - self.min_val)
            return True
        return False


class MusicManager:
    def __init__(self):
        self.volume = 0.7
        self.music_playing = False
        self.current_music = None

    def load_music(self, music_path):
        try:
            pygame.mixer.music.load(music_path)
            self.current_music = music_path
            self.set_volume(self.volume)
            return True
        except:
            return False

    def play(self, loops=-1):
        if self.current_music:
            pygame.mixer.music.play(loops)
            self.music_playing = True

    def stop(self):
        pygame.mixer.music.stop()
        self.music_playing = False

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)

    def toggle(self):
        if self.music_playing:
            self.stop()
        else:
            self.play()


class BackgroundImage:
    def __init__(self, image_path):
        self.image = None
        try:
            self.image = pygame.image.load(image_path).convert()
            self.image = pygame.transform.scale(self.image, (SCREEN_W, SCREEN_H))
            print(f"✓ Background image loaded: {image_path}")
        except:
            print(f"Background image not found: {image_path}")

    def draw(self, screen):
        if self.image:
            screen.blit(self.image, (0, 0))
        else:
            screen.fill((25, 35, 30))


class SettingsScreen:
    def __init__(self, screen, music_manager):
        self.screen = screen
        self.music_manager = music_manager
        self.font_title = pygame.font.Font(None, 52)
        self.font_text = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 20)
        self.background = BackgroundImage("assets/loading/image.png")
        self.back_button = WoodButton(SCREEN_W // 2 - 100, SCREEN_H - 80, 200, 50, "BACK")
        self.volume_slider = Slider(
            SCREEN_W // 2 - 150, SCREEN_H // 2 - 20, 300, 0, 100,
            int(music_manager.volume * 100),
        )
        self.music_toggle = WoodButton(
            SCREEN_W // 2 - 100, SCREEN_H // 2 - 100, 200, 50,
            "MUSIC: ON" if music_manager.music_playing else "MUSIC: OFF",
        )

    def draw(self):
        self.background.draw(self.screen)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        panel_w, panel_h = 500, 350
        panel_x = SCREEN_W // 2 - panel_w // 2
        panel_y = SCREEN_H // 2 - panel_h // 2
        pygame.draw.rect(self.screen, (30, 35, 45),
                         (panel_x, panel_y, panel_w, panel_h), border_radius=15)
        pygame.draw.rect(self.screen, (100, 150, 100),
                         (panel_x, panel_y, panel_w, panel_h), 2, border_radius=15)
        title = self.font_title.render("SETTINGS", True, (255, 215, 0))
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, panel_y + 50)))
        music_label = self.font_text.render("MUSIC VOLUME", True, (200, 200, 200))
        self.screen.blit(music_label, (panel_x + 50, panel_y + 130))
        self.volume_slider.draw(self.screen, self.font_small)
        self.music_toggle.text = "MUSIC: ON" if self.music_manager.music_playing else "MUSIC: OFF"
        self.music_toggle.draw(self.screen)
        self.back_button.draw(self.screen)

    def handle_event(self, event):
        if self.volume_slider.handle_event(event):
            self.music_manager.set_volume(self.volume_slider.value / 100)
            return None
        if self.music_toggle.handle_event(event):
            self.music_manager.toggle()
            return None
        if self.back_button.handle_event(event):
            return "back"
        return None


class MainMenu:
    def __init__(self, screen, music_manager):
        self.screen = screen
        self.music_manager = music_manager
        self.font_title = pygame.font.Font(None, 96)
        self.font_sub = pygame.font.Font(None, 32)
        try:
            self.video = VideoLoader("assets/loading/background.mp4")
        except:
            self.video = None
        btn_width, btn_height = 280, 65
        center_x = SCREEN_W // 2 - btn_width // 2
        start_y = SCREEN_H // 2
        self.buttons = [
            WoodButton(center_x, start_y,        btn_width, btn_height, "START GAME"),
            WoodButton(center_x, start_y + 85,   btn_width, btn_height, "HOW TO PLAY"),
            WoodButton(center_x, start_y + 170,  btn_width, btn_height, "SETTINGS"),
            WoodButton(center_x, start_y + 255,  btn_width, btn_height, "QUIT"),
        ]

    def draw(self):
        if self.video:
            frame = self.video.get_frame()
            if frame:
                self.screen.blit(frame, (0, 0))
        else:
            self.screen.fill((18, 26, 18))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))
        shadow = self.font_title.render("VERDANT VALLEY", True, (0, 0, 0))
        self.screen.blit(shadow, shadow.get_rect(center=(SCREEN_W // 2 + 4, SCREEN_H // 2 - 176)))
        title = self.font_title.render("VERDANT VALLEY", True, (255, 215, 0))
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 180)))
        sub = self.font_sub.render("Multi-Agent AI Farming Simulation", True, (200, 200, 200))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 110)))
        for btn in self.buttons:
            btn.draw(self.screen)

    def handle_event(self, event):
        for i, btn in enumerate(self.buttons):
            if btn.handle_event(event):
                return i
        return -1


class HowToPlayScreen:
    def __init__(self, screen):
        self.screen = screen
        self.font_title = pygame.font.Font(None, 52)
        self.font_text = pygame.font.Font(None, 22)
        self.background = BackgroundImage("assets/loading/image.png")
        self.back_button = WoodButton(SCREEN_W // 2 - 100, SCREEN_H - 80, 200, 50, "BACK")

    def draw(self):
        self.background.draw(self.screen)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        title = self.font_title.render("HOW TO PLAY", True, (255, 215, 0))
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 60)))
        instructions = [
            "VERDANT VALLEY - AI FARMING SIMULATION",
            "",
            "CONTROLS:",
            "   P - Pause/Resume Game",
            "   ESC - Quit to Main Menu",
            "   R - Restart Game",
            "   G or Click PLANT button - Plant crops",
            "",
            "AI AGENTS:",
            "   FARMER - Harvests crops using A* pathfinding",
            "   GUARD - Patrols and chases animals",
            "   ANIMAL - Eats crops, evolves using Genetic Algorithm",
            "",
            "ALGORITHMS:",
            "   A* Search - Optimal pathfinding with terrain costs",
            "   CSP - Farm layout with backtracking",
            "   Genetic Algorithm - Animal evolution over seasons",
            "",
            "GAME ENDS after 4 seasons (1 full year)",
            "Final scores are displayed at the end",
        ]
        y = 120
        for line in instructions:
            if line.startswith(("CONTROLS:", "AI AGENTS:", "ALGORITHMS:", "GAME ENDS")):
                color = (255, 215, 0)
            elif line == "":
                color = (0, 0, 0)
            else:
                color = (220, 220, 220)
            self.screen.blit(self.font_text.render(line, True, color), (80, y))
            y += 28
        self.back_button.draw(self.screen)

    def handle_event(self, event):
        if self.back_button.handle_event(event):
            return "back"
        return None


class EndScreen:
    def __init__(self, screen, farmer_score, guard_score, animal_score):
        self.screen = screen
        self.farmer_score = farmer_score
        self.guard_score = guard_score
        self.animal_score = animal_score
        self.font_title = pygame.font.Font(None, 52)
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.restart_button = WoodButton(SCREEN_W // 2 - 130, SCREEN_H - 100, 120, 50, "RESTART")
        self.menu_button = WoodButton(SCREEN_W // 2 + 10, SCREEN_H - 100, 120, 50, "MENU")

    def draw(self):
        self.screen.fill((18, 26, 18))
        title = self.font_title.render("GAME COMPLETE!", True, (255, 215, 0))
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 80)))
        subtitle = self.font_large.render("Final Scores", True, (200, 200, 200))
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_W // 2, 140)))

        card_w, card_h, spacing = 250, 120, 30
        total_w = card_w * 3 + spacing * 2
        sx = (SCREEN_W - total_w) // 2
        y = 200
        cards = [
            (sx,                      (100,180,255), "FARMER", self.farmer_score, "🌾"),
            (sx + card_w + spacing,   (255,100,100), "GUARD",  self.guard_score,  "🛡️"),
            (sx + (card_w+spacing)*2, (255,180,100), "ANIMAL", self.animal_score, "🐮"),
        ]
        for cx, border, label, score, icon in cards:
            rect = pygame.Rect(cx, y, card_w, card_h)
            pygame.draw.rect(self.screen, (40, 70, 40), rect, border_radius=12)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=12)
            self.screen.blit(self.font_large.render(label, True, border), (cx + 20, y + 15))
            self.screen.blit(self.font_large.render(str(score), True, (255,215,0)), (cx + 20, y + 60))
            self.screen.blit(self.font_medium.render(icon, True, (255,215,0)), (cx + card_w - 50, y + 60))

        self.restart_button.draw(self.screen)
        self.menu_button.draw(self.screen)

    def handle_event(self, event):
        if self.restart_button.handle_event(event):
            return "restart"
        if self.menu_button.handle_event(event):
            return "menu"
        return None


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption("Verdant Valley")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        self.state = "MENU"
        self.running = True
        self.game_tick = 0
        self.completed_seasons = 0
        self.plant_button_rect = None

        self.music_manager = MusicManager()
        if self.music_manager.load_music("assets/loading/audio.mp3"):
            self.music_manager.play()
            print("✓ Background music loaded and playing")

        self.font_small  = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_large  = pygame.font.Font(None, 26)

        # Game objects (populated by init_game)
        self.grid       = None
        self.season     = None
        self.csp_solver = None
        self.csp_popup  = None
        self.farm_ui    = None
        self.farmer     = None
        self.guard      = None
        self.animal     = None
        self.agents     = []
        self.last_season_index = 0
        self.end_screen = None

        # ── Crop tracking (fixed) ──────────────────────────────────────────
        self.notification_popup   = None
        self.regeneration_popup   = None
        self.custom_input_popup   = None
        self.previous_crop_count  = 0
        self.initial_crops        = 0
        self.crops_left           = 0
        # Flips True once crops exist this cycle; resets after popup fires.
        # Prevents spurious popup on game start before CSP places any crops.
        self._field_was_populated = False
        self.regeneration_mode = None  # "auto" or "custom"

        # Screens
        self.menu        = MainMenu(self.screen, self.music_manager)
        self.how_to_play = HowToPlayScreen(self.screen)
        self.settings    = SettingsScreen(self.screen, self.music_manager)

    # ── Game initialisation ───────────────────────────────────────────────────

    def init_game(self):
        self.grid   = Grid()
        self.season = SeasonManager()
        self.completed_seasons = 0
        self.last_season_index = self.season.index

        self.csp_solver = CSPSolver(self.grid)
        self.csp_solver.solve()
        self.csp_solver.apply_to_grid()

        self.csp_popup = CSPPopup(self.screen, self.grid, self.csp_solver)
        self.farm_ui   = FarmUI(self.grid)

        self.farmer = Farmer(6, 6)
        self.guard  = Guard(10, 10)
        self.animal = Animal(8, 6)
        self.guard.set_waypoints([(4, 2), (13, 2), (13, 11), (4, 11)])
        self.agents = [self.farmer, self.guard, self.animal]

        self.game_tick            = 0
        self.animal_respawn_timer = 0
        self.respawn_delay        = 180

        # Reset crop tracking
        self.notification_popup   = None
        self.regeneration_popup   = None
        self.custom_input_popup   = None
        self.previous_crop_count  = 0
        self.initial_crops        = len(self.grid.crop_tiles())
        self.crops_left           = self.initial_crops
        self._field_was_populated = self.initial_crops > 0
        self.regeneration_mode = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sync_crop_tracking(self):
        current_crop_count = len(self.grid.crop_tiles())
        self.previous_crop_count = current_crop_count
        self.initial_crops = current_crop_count
        self.crops_left = current_crop_count
        self._field_was_populated = current_crop_count > 0

    def _show_generation_popup(self):
        title = "Harvest Complete"
        message = "Choose auto generate or custom input for the next crops."
        self.regeneration_popup = RegenerationPopup(
            self.screen,
            title=title,
            message=message,
        )

    def _complete_generation(self, message):
        self._sync_crop_tracking()
        self.notification_popup = NotificationPopup(
            self.screen,
            message,
            duration=180,
        )

    def _apply_auto_generation(self):
        self.csp_solver.set_mode("auto")
        self.csp_solver.solve()
        self.csp_solver.apply_to_grid()
        self.farm_ui = FarmUI(self.grid)
        self._complete_generation("All crops have been generated! Now start harvesting!")

    def choose_animal_respawn(self):
        guard_pos = (self.guard.col, self.guard.row) if self.guard else None
        min_col, max_col, min_row, max_row = 4, 13, 2, 11
        safe_tiles = []
        for c in range(max(0, min_col), min(self.grid.cols, max_col + 1)):
            for r in range(max(0, min_row), min(self.grid.rows, max_row + 1)):
                if guard_pos and (c, r) == guard_pos:
                    continue
                tile = self.grid.get(c, r)
                if not tile or not tile.walkable:
                    continue
                if abs(c - guard_pos[0]) + abs(r - guard_pos[1]) <= 4:
                    continue
                safe_tiles.append((c, r))
        if not safe_tiles:
            for c in range(self.grid.cols):
                for r in range(self.grid.rows):
                    tile = self.grid.get(c, r)
                    if tile and tile.walkable and (not guard_pos or (c, r) != guard_pos):
                        safe_tiles.append((c, r))
        if not safe_tiles:
            return (16, 1)
        random.shuffle(safe_tiles)
        return safe_tiles[0]

    def check_end_condition(self):
        if self.season.index == 0 and self.last_season_index == 3:
            self.completed_seasons += 1
        self.last_season_index = self.season.index
        if self.completed_seasons >= 1 and self.season.index == 0:
            return True
        return False

    def draw_minimap(self):
        mini_w, mini_h = 240, 180
        mini_x = SCREEN_W - mini_w - 15
        mini_y = SCREEN_H - mini_h - 15

        panel = pygame.Surface((mini_w, mini_h), pygame.SRCALPHA)
        panel.fill((20, 25, 30, 220))
        self.screen.blit(panel, (mini_x, mini_y))
        pygame.draw.rect(self.screen, (80, 120, 80), (mini_x, mini_y, mini_w, mini_h), 2)
        self.screen.blit(
            self.font_small.render("MINI MAP", True, (255, 215, 0)),
            (mini_x + 10, mini_y + 5),
        )

        map_x, map_y = mini_x + 10, mini_y + 25
        map_w, map_h = mini_w - 20, mini_h - 40
        cell_w = map_w / GRID_COLS
        cell_h = map_h / GRID_ROWS

        TILE_COLORS = {
            TILE_WATER: (40, 90, 160),
            TILE_FIELD: (101, 67, 33),
            TILE_GRASS: (56, 95, 40),
            TILE_DIRT:  (94, 68, 42),
            TILE_STONE: (100, 100, 110),
        }
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                cx = int(map_x + col * cell_w)
                cy = int(map_y + row * cell_h)
                cw, ch = max(2, int(cell_w)), max(2, int(cell_h))
                tile = self.grid.get(col, row)
                color = TILE_COLORS.get(tile.type, (85, 62, 40)) if tile else (80, 80, 80)
                pygame.draw.rect(self.screen, color, (cx, cy, cw, ch))
                pygame.draw.rect(self.screen, (50, 50, 60), (cx, cy, cw, ch), 1)

        for agent in self.agents:
            if hasattr(agent, "alive") and not agent.alive:
                continue
            dot_x = int(map_x + agent.col * cell_w)
            dot_y = int(map_y + agent.row * cell_h)
            if "Farmer" in agent.name:
                color = (100, 180, 255)
            elif "Guard" in agent.name:
                color = (255, 100, 100)
            else:
                color = (255, 180, 100)
            pygame.draw.circle(self.screen, color, (dot_x, dot_y), 4)

    def draw_season_info(self):
        panel_w, panel_h = 180, 65
        panel_x, panel_y = 15, 15
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((20, 25, 30, 220))
        self.screen.blit(panel, (panel_x, panel_y))
        pygame.draw.rect(self.screen, (80, 120, 80), (panel_x, panel_y, panel_w, panel_h), 2)
        season_name = (
            self.season.name
            .replace("🌱", "").replace("☀️", "").replace("🍂", "").replace("❄️", "")
            .strip()
        )
        self.screen.blit(
            self.font_medium.render(f"Season: {season_name}", True, (255, 215, 0)),
            (panel_x + 12, panel_y + 10),
        )
        day = (self.game_tick // 600) + 1
        self.screen.blit(
            self.font_small.render(f"Day: {day}", True, (220, 220, 220)),
            (panel_x + 12, panel_y + 38),
        )

    def draw_pause_screen(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        font_big = pygame.font.Font(None, 64)
        font_sm  = pygame.font.Font(None, 24)
        pause = font_big.render("PAUSED", True, (255, 215, 0))
        self.screen.blit(pause, pause.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 30)))
        hint = font_sm.render("Press P to Resume | ESC to Quit to Menu", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 30)))

    def draw_plant_button(self):
        btn_w, btn_h = 140, 45
        btn_x = SCREEN_W - SIDEBAR_W + 20
        btn_y = 320
        self.plant_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        mouse_pos = pygame.mouse.get_pos()
        is_hover  = self.plant_button_rect.collidepoint(mouse_pos)
        btn_color = (140, 105, 65) if is_hover else (100, 70, 40)
        pygame.draw.rect(self.screen, btn_color, self.plant_button_rect, border_radius=12)
        pygame.draw.rect(self.screen, (80, 150, 80), self.plant_button_rect, 2, border_radius=12)
        for i in range(2):
            line_y = btn_y + 15 + i * 18
            pygame.draw.line(self.screen, (80, 55, 30),
                             (btn_x + 10, line_y), (btn_x + btn_w - 10, line_y), 1)
        btn_font = pygame.font.Font(None, 20)
        btn_text = btn_font.render("🌱 PLANT CROPS", True, (255, 215, 0))
        self.screen.blit(btn_text, btn_text.get_rect(center=self.plant_button_rect.center))

    def _draw_game_world(self):
        """Shared draw call for PLAYING and PAUSED states."""
        self.screen.fill((34, 139, 34))
        self.grid.draw(self.screen, self.game_tick, None, self.season.index)
        if self.farm_ui:
            self.farm_ui.draw(self.screen)
        self.draw_season_info()
        self.draw_minimap()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while self.running:
            self.clock.tick(FPS)

            # ── Events ───────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if self.state == "MENU":
                    result = self.menu.handle_event(event)
                    if result == 0:
                        self.init_game()
                        self.state = "CSP"
                    elif result == 1:
                        self.state = "HOWTOPLAY"
                    elif result == 2:
                        self.state = "SETTINGS"
                    elif result == 3:
                        self.running = False

                elif self.state == "HOWTOPLAY":
                    if self.how_to_play.handle_event(event) == "back":
                        self.state = "MENU"

                elif self.state == "SETTINGS":
                    if self.settings.handle_event(event) == "back":
                        self.state = "MENU"

                elif self.state == "CSP":
                    if self.csp_popup.handle_event(event):
                        if self.csp_popup.is_confirmed():
                            self.state     = "PLAYING"
                            self.game_tick = 0
                            self._sync_crop_tracking()

                elif self.state == "PLAYING":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_p:
                            self.state = "PAUSED"
                        elif event.key == pygame.K_ESCAPE:
                            self.init_game()
                            self.state = "MENU"
                        elif event.key == pygame.K_r:
                            self.init_game()
                            self.state = "CSP"
                        elif event.key == pygame.K_g:
                            # Block manual planting while any popup is showing
                            if self.farmer and self.notification_popup is None and self.regeneration_popup is None and self.custom_input_popup is None:
                                self.farmer.trigger_planting()
                                print("🌱 Plant crops triggered by G key!")

                    if event.type == pygame.MOUSEBUTTONDOWN and self.plant_button_rect:
                        if (self.plant_button_rect.collidepoint(event.pos)
                                and self.notification_popup is None and self.regeneration_popup is None and self.custom_input_popup is None):
                            if self.farmer:
                                self.farmer.trigger_planting()
                                print("🌱 Plant crops triggered by button!")

                    if self.regeneration_popup and event.type == pygame.MOUSEBUTTONDOWN:
                        choice = self.regeneration_popup.handle_click(event.pos)
                        if choice == "auto":
                            self.regeneration_popup = None
                            self.regeneration_mode = "auto"
                            self._apply_auto_generation()
                        elif choice == "custom":
                            self.regeneration_mode = "custom"
                            self.custom_input_popup = CustomInputPopup(
                                self.screen,
                                max_crops=max(1, len(self.grid.field_tiles())),
                                initial_counts={
                                    CROP_WHEAT: 0,
                                    CROP_SUNFLOWER: 0,
                                    CROP_CORN: 0,
                                },
                            )
                            self.regeneration_popup = None

                    if self.custom_input_popup:
                        if event.type == pygame.KEYDOWN:
                            self.custom_input_popup.handle_keypress(event.key)
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            self.custom_input_popup.handle_click(event.pos)

                    if self.notification_popup:
                        self.notification_popup.handle_event(event)

                elif self.state == "PAUSED":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_p:
                            self.state = "PLAYING"
                        elif event.key == pygame.K_ESCAPE:
                            self.init_game()
                            self.state = "MENU"

                elif self.state == "END":
                    result = self.end_screen.handle_event(event)
                    if result == "restart":
                        self.init_game()
                        self.state = "CSP"
                    elif result == "menu":
                        self.state = "MENU"

            # ── Drawing / Logic ───────────────────────────────────────────────

            if self.state == "MENU":
                self.menu.draw()

            elif self.state == "HOWTOPLAY":
                self.how_to_play.draw()

            elif self.state == "SETTINGS":
                self.settings.draw()

            elif self.state == "CSP":
                self.screen.fill((34, 139, 34))
                self.grid.draw(self.screen, self.game_tick, None, 0)
                if self.farm_ui:
                    self.farm_ui.draw(self.screen)
                self.csp_popup.draw()

            elif self.state == "PLAYING":

                # ── Season / end-condition ────────────────────────────────
                self.season.update(self.grid)
                if self.check_end_condition():
                    self.end_screen = EndScreen(
                        self.screen,
                        self.farmer.score, self.guard.score, self.animal.score,
                    )
                    self.state = "END"

                # ── Agent updates ─────────────────────────────────────────
                # Freeze agents while any popup is on screen so the farmer
                # doesn't wander around on an empty grid.
                if self.notification_popup is None and self.regeneration_popup is None and self.custom_input_popup is None:
                    for agent in self.agents:
                        agent.update(self.grid, self.agents)

                    # Animal respawn
                    if not self.animal.alive:
                        self.animal_respawn_timer += 1
                        if self.animal_respawn_timer >= self.respawn_delay:
                            rc, rr = self.choose_animal_respawn()
                            self.animal.respawn(rc, rr)
                            self.animal_respawn_timer = 0

                # ── Crop count ────────────────────────────────────────────
                current_crop_count = len(self.grid.crop_tiles())
                ripe_crop_count = len(self.grid.ripe_crop_tiles())
                print(f"DEBUG: total_crops={current_crop_count}, ripe_crops={ripe_crop_count}, crops_left={self.crops_left}, initial={self.initial_crops}")

                # Mark the field as having been populated at least once
                if current_crop_count > 0:
                    self._field_was_populated = True

                # ── Detect when the field becomes empty ─────────────────────
                if (
                    self._field_was_populated
                    and current_crop_count == 0
                    and self.notification_popup is None
                    and self.regeneration_popup is None
                    and self.custom_input_popup is None
                ):
                    print("[HARVEST_TRIGGER] Grid empty — showing regeneration options")
                    self._show_generation_popup()
                    # Reset flag so the popup only fires once per cycle
                    self._field_was_populated = False

                # Update previous count AFTER the detection check
                self.previous_crop_count = current_crop_count

                # ── Regeneration popup lifecycle ──────────────────────────────
                if self.regeneration_popup:
                    self.regeneration_popup.update()

                # ── Custom input popup lifecycle ──────────────────────────────
                if self.custom_input_popup:
                    self.custom_input_popup.update()
                    if self.custom_input_popup.submitted:
                        selected_counts = self.custom_input_popup.get_value()
                        if selected_counts is not None:
                            print(f"🌾 Generating custom crops: {selected_counts}")
                            self.csp_solver.set_mode("manual")
                            self.csp_solver.set_requested_counts(selected_counts)
                            self.csp_solver.solve(selected_counts)
                            self.csp_solver.apply_to_grid()
                            self.farm_ui = FarmUI(self.grid)
                            self.custom_input_popup = None
                            total_selected = sum(selected_counts.values())
                            self._complete_generation(
                                f"{total_selected} custom crops generated successfully! Now start harvesting!"
                            )

                # ── Notification popup lifecycle ──────────────────────────────
                if self.notification_popup:
                    if self.notification_popup.update():
                        self._sync_crop_tracking()
                        self.regeneration_mode = None
                        self.notification_popup = None
                        print("✨ Ready to harvest again!")

                self.game_tick += 1

                # ── Draw ──────────────────────────────────────────────────
                self._draw_game_world()
                self.draw_plant_button()

                for agent in self.agents:
                    if hasattr(agent, "alive") and not agent.alive:
                        continue
                    agent.draw(self.screen)

                if self.farmer:
                    self.farmer.draw_failed_plant_indicator(self.screen)

                # Popup always drawn on top of everything
                if self.regeneration_popup:
                    self.regeneration_popup.draw()
                if self.custom_input_popup:
                    self.custom_input_popup.draw()
                if self.notification_popup:
                    self.notification_popup.draw()

            elif self.state == "PAUSED":
                self._draw_game_world()

                # Greyed-out plant button (disabled during pause)
                bw, bh = 140, 45
                bx = SCREEN_W - SIDEBAR_W + 20
                by = 320
                pr = pygame.Rect(bx, by, bw, bh)
                pygame.draw.rect(self.screen, (80, 80, 80), pr, border_radius=12)
                pygame.draw.rect(self.screen, (100, 100, 100), pr, 2, border_radius=12)
                bf = pygame.font.Font(None, 20)
                bt = bf.render("🌱 PLANT CROPS", True, (150, 150, 150))
                self.screen.blit(bt, bt.get_rect(center=pr.center))

                for agent in self.agents:
                    if hasattr(agent, "alive") and not agent.alive:
                        continue
                    agent.draw(self.screen)

                if self.farmer:
                    self.farmer.draw_failed_plant_indicator(self.screen)

                self.draw_pause_screen()

            elif self.state == "END":
                self.end_screen.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
