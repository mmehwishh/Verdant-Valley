"""
Main Game Module - Verdant Valley

Orchestrates all game systems including:
- Grid and season management
- Agent updates (Farmer, Guard, Animals)
- CSP farm layout planning
- Genetic algorithm for animal evolution
- UI components (menus, buttons, popups)
- Visualization manager for algorithms
"""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pygame')
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pygame
import os
import random
import cv2
import numpy as np


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.constants import (
    SCREEN_W,
    SCREEN_H,
    SIDEBAR_W,
    FPS,
    TILE_WATER,
    TILE_STONE,
    TILE_FIELD,
    TILE_GRASS,
    TILE_DIRT,
    GRID_COLS,
    GRID_ROWS,
    C_GUARD,
    SEASON_TINTS,
    CROP_WHEAT,
    CROP_SUNFLOWER,
    CROP_CORN,
    CROP_TOMATO,
    CROP_CARROT,
)
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
from game_ui.rain_animation import RainAnimation
from game_ui.visualization_manager import VisualizationManager
from game_ui.ga_popup import GAPopup
from game_ui.year_end_screen import YearEndScreen
from src.world.environment.clock import GameClock


# ============================================================================
# VIDEO LOADER
# ============================================================================


class VideoLoader:
    """Handles video playback for main menu background."""

    def __init__(self, video_path):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.cap = None
        else:
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_frame(self):
        """Get the next frame from the video, loop when finished."""
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


# ============================================================================
# UI COMPONENTS
# ============================================================================


class WoodButton:
    """Wood-textured button with hover effect."""

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

        # Wood grain lines
        for i in range(3):
            line_y = self.rect.y + 15 + i * 15
            pygame.draw.line(
                screen,
                wood_dark,
                (self.rect.x + 10, line_y),
                (self.rect.x + self.rect.width - 10, line_y),
                1,
            )

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
    """Volume control slider for settings menu."""

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
            (self.value - self.min_val)
            / (self.max_val - self.min_val)
            * self.rect.width
        )
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(screen, (100, 200, 100), fill_rect, border_radius=5)

        knob_x = self.rect.x + fill_width
        pygame.draw.circle(
            screen, (255, 215, 0), (knob_x, self.rect.centery), self.knob_radius
        )
        pygame.draw.circle(
            screen, (255, 255, 255), (knob_x, self.rect.centery), self.knob_radius - 2
        )

        value_text = font.render(f"{int(self.value)}%", True, (200, 200, 200))
        screen.blit(value_text, (self.rect.right + 10, self.rect.centery - 8))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            knob_x = self.rect.x + int(
                (self.value - self.min_val)
                / (self.max_val - self.min_val)
                * self.rect.width
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
            self.value = self.min_val + (rel_x / self.rect.width) * (
                self.max_val - self.min_val
            )
            return True
        return False


class MusicManager:
    """Manages background music playback and volume."""

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
        except Exception:
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
    """Simple background image loader and drawer."""

    def __init__(self, image_path):
        self.image = None
        try:
            self.image = pygame.image.load(image_path).convert()
            self.image = pygame.transform.scale(self.image, (SCREEN_W, SCREEN_H))
        except Exception:
            pass

    def draw(self, screen):
        if self.image:
            screen.blit(self.image, (0, 0))
        else:
            screen.fill((25, 35, 30))

    def debug_image(self, image_path):
        try:
            img = pygame.image.load(image_path)
            return img
        except Exception:
            return None


# ============================================================================
# SCREENS
# ============================================================================


class SettingsScreen:
    """Settings screen for volume and music controls."""

    def __init__(self, screen, music_manager):
        self.screen = screen
        self.music_manager = music_manager
        self.font_title = pygame.font.Font(None, 52)
        self.font_text = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 20)
        self.background = BackgroundImage("assets/loading/image.png")
        self.back_button = WoodButton(
            SCREEN_W // 2 - 100, SCREEN_H - 80, 200, 50, "BACK"
        )
        self.volume_slider = Slider(
            SCREEN_W // 2 - 150,
            SCREEN_H // 2 - 20,
            300,
            0,
            100,
            int(music_manager.volume * 100),
        )
        self.music_toggle = WoodButton(
            SCREEN_W // 2 - 100,
            SCREEN_H // 2 - 100,
            200,
            50,
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

        pygame.draw.rect(
            self.screen,
            (30, 35, 45),
            (panel_x, panel_y, panel_w, panel_h),
            border_radius=15,
        )
        pygame.draw.rect(
            self.screen,
            (100, 150, 100),
            (panel_x, panel_y, panel_w, panel_h),
            2,
            border_radius=15,
        )

        title = self.font_title.render("SETTINGS", True, (255, 215, 0))
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, panel_y + 50)))

        music_label = self.font_text.render("MUSIC VOLUME", True, (200, 200, 200))
        self.screen.blit(music_label, (panel_x + 50, panel_y + 130))

        self.volume_slider.draw(self.screen, self.font_small)
        self.music_toggle.text = (
            "MUSIC: ON" if self.music_manager.music_playing else "MUSIC: OFF"
        )
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
    """Main menu screen with options to start game, view help, settings, or quit."""

    def __init__(self, screen, music_manager):
        self.screen = screen
        self.music_manager = music_manager
        self.font_title = pygame.font.Font(None, 96)
        self.font_sub = pygame.font.Font(None, 32)

        try:
            self.video = VideoLoader("assets/loading/background.mp4")
        except Exception:
            self.video = None

        btn_width, btn_height = 280, 65
        center_x = SCREEN_W // 2 - btn_width // 2
        start_y = SCREEN_H // 2

        self.buttons = [
            WoodButton(center_x, start_y, btn_width, btn_height, "START GAME"),
            WoodButton(center_x, start_y + 85, btn_width, btn_height, "HOW TO PLAY"),
            WoodButton(center_x, start_y + 170, btn_width, btn_height, "SETTINGS"),
            WoodButton(center_x, start_y + 255, btn_width, btn_height, "QUIT"),
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

        # Title shadow for depth
        shadow = self.font_title.render("VERDANT VALLEY", True, (0, 0, 0))
        self.screen.blit(
            shadow, shadow.get_rect(center=(SCREEN_W // 2 + 4, SCREEN_H // 2 - 176))
        )

        title = self.font_title.render("VERDANT VALLEY", True, (255, 215, 0))
        self.screen.blit(
            title, title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 180))
        )

        sub = self.font_sub.render(
            "Multi-Agent AI Farming Simulation", True, (200, 200, 200)
        )
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 110)))

        for btn in self.buttons:
            btn.draw(self.screen)

    def handle_event(self, event):
        for i, btn in enumerate(self.buttons):
            if btn.handle_event(event):
                return i
        return -1


class HowToPlayScreen:
    """Instructions screen explaining game controls and mechanics."""

    def __init__(self, screen):
        self.screen = screen
        self.font_title = pygame.font.Font(None, 52)
        self.font_text = pygame.font.Font(None, 22)
        self.background = BackgroundImage("assets/loading/image.png")
        self.back_button = WoodButton(
            SCREEN_W // 2 - 100, SCREEN_H - 80, 200, 50, "BACK"
        )

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
            "   E - View Genetic Algorithm (Animal Evolution)",
            "   TAB - Toggle Algorithm Visualizer Panel",
            "   N - Toggle Node Expansion",
            "   M - Toggle Path Overlays",
            "",
            "AI AGENTS:",
            "   FARMER - Harvests crops using A* pathfinding",
            "   GUARD - Patrols and chases animals",
            "   ANIMAL - Eats crops, evolves using Genetic Algorithm",
            "",
            "ALGORITHMS:",
            "   A* Search - Optimal pathfinding",
            "   CSP - Farm layout planning",
            "   Genetic Algorithm - Animal evolution over years",
            "",
            "MULTIPLE YEARS: Press CONTINUE after each year",
            "Animals evolve and get smarter each generation!",
        ]

        y = 120
        for line in instructions:
            if line.startswith(
                ("CONTROLS:", "AI AGENTS:", "ALGORITHMS:", "MULTIPLE YEARS:")
            ):
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


# ============================================================================
# MAIN GAME CLASS
# ============================================================================


class Game:
    """Main game controller that orchestrates all game systems."""

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
        self.rain_button_rect = None
        self.snow_button_rect = None
        self.change_season_button_rect = None
        self.clock_obj = GameClock()

        # Music manager
        self.music_manager = MusicManager()
        if self.music_manager.load_music("assets/loading/audio.mp3"):
            self.music_manager.play()

        # Fonts
        self.font_small = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 26)
        self.font_tiny = pygame.font.Font(None, 12)

        # Game objects (initialized later)
        self.grid = None
        self.season = None
        self.csp_solver = None
        self.csp_popup = None
        self.farm_ui = None
        self.farmer = None
        self.guard = None
        self.animal_fox = None
        self.animal_rabbit = None
        self.agents = []
        self.last_season_index = 0
        self.end_screen = None
        self.rain_animation = None

        # Crop tracking
        self.notification_popup = None
        self.regeneration_popup = None
        self.custom_input_popup = None
        self.previous_crop_count = 0
        self.initial_crops = 0
        self.crops_left = 0
        self._field_was_populated = False
        self._waiting_for_regeneration = False
        self.regeneration_mode = None

        # Visualization Manager
        self.viz_manager = None

        # Genetic Algorithm tracking
        self.ga_popup = None
        self.generation_count = 1
        self.current_year = 1
        self.last_fox_fitness = 0
        self.last_rabbit_fitness = 0
        self.last_fox_chromo = {}
        self.last_rabbit_chromo = {}

        # Screens
        self.menu = MainMenu(self.screen, self.music_manager)
        self.how_to_play = HowToPlayScreen(self.screen)
        self.settings = SettingsScreen(self.screen, self.music_manager)

    # ------------------------------------------------------------------------
    # Game Initialization
    # ------------------------------------------------------------------------

    def init_game(self):
        """Initialize or reset the entire game state."""

        # Reset all attributes
        self.grid = None
        self.season = None
        self.csp_solver = None
        self.csp_popup = None
        self.farm_ui = None
        self.farmer = None
        self.guard = None
        self.animal_fox = None
        self.animal_rabbit = None
        self.agents = []
        self.notification_popup = None
        self.regeneration_popup = None
        self.custom_input_popup = None
        self.previous_crop_count = 0
        self.initial_crops = 0
        self.crops_left = 0
        self._field_was_populated = False
        self._waiting_for_regeneration = False
        self.regeneration_mode = None
        self.completed_seasons = 0
        self.last_season_index = 0
        self.game_tick = 0
        self.animal_respawn_timer = 0
        self.respawn_delay = 180
        self.current_year = 1
        self.generation_count = 1
        self.last_fox_fitness = 0
        self.last_rabbit_fitness = 0
        self.last_fox_chromo = {}
        self.last_rabbit_chromo = {}

        # Initialize game objects
        self.grid = Grid()
        self.rain_animation = RainAnimation(self.grid)
        self.season = SeasonManager()
        self.grid.season = self.season

        if self.season and self.grid:
            self.season.apply_current_effects(self.grid)
            self.last_season_index = getattr(self.season, "index", 0)

        # CSP Solver
        self.csp_solver = CSPSolver(self.grid) if self.grid else None
        if self.csp_solver:
            if hasattr(self.csp_solver, "solve"):
                self.csp_solver.solve()
            if hasattr(self.csp_solver, "apply_to_grid"):
                self.csp_solver.apply_to_grid()

        self.csp_popup = (
            CSPPopup(self.screen, self.grid, self.csp_solver)
            if self.grid and self.csp_solver
            else None
        )
        self.farm_ui = FarmUI(self.grid) if self.grid else None

        # Create agents
        self.farmer = Farmer(6, 6)
        if self.farmer and self.grid:
            self.farmer._ensure_valid_position(self.grid)

        self.guard = Guard(10, 10, C_GUARD)
        if self.guard and self.grid:
            self.guard.ensure_valid_position(self.grid)

        # Create animals
        self.animal_fox = Animal(17, 1, animal_type="fox")
        if self.animal_fox and self.grid:
            spawn = self._random_spawn(self.grid)
            if isinstance(spawn, (tuple, list)) and len(spawn) == 2:
                self.animal_fox.respawn(spawn[0], spawn[1], self.grid)

        self.animal_rabbit = Animal(15, 3, animal_type="rabbit")
        if self.animal_rabbit and self.grid:
            spawn = self._random_spawn(self.grid)
            if isinstance(spawn, (tuple, list)) and len(spawn) == 2:
                self.animal_rabbit.respawn(spawn[0], spawn[1], self.grid)

        # Set guard waypoints
        if self.guard:
            self.guard.set_waypoints([(4, 2), (17, 2), (17, 13), (4, 13)])

        self.agents = [
            a
            for a in [self.farmer, self.guard, self.animal_fox, self.animal_rabbit]
            if a
        ]

        # Crop tracking
        if self.grid and hasattr(self.grid, "crop_tiles"):
            self.initial_crops = len(self.grid.crop_tiles())
        else:
            self.initial_crops = 0
        self.crops_left = self.initial_crops
        self._field_was_populated = self.initial_crops > 0

        # Visualization Manager
        self.viz_manager = VisualizationManager(self.screen, self.grid)

        # GA Popup
        self.ga_popup = GAPopup(
            self.screen, self.animal_fox, self.animal_rabbit, self.season
        )
        self.generation_count = 1

    # ------------------------------------------------------------------------
    # Genetic Algorithm Methods
    # ------------------------------------------------------------------------

    def _crossover(self, parent1_chromo, parent2_chromo):
        """Mix genes from two parents using single-point crossover."""
        child = {}
        for trait in parent1_chromo:
            if random.random() > 0.5:
                child[trait] = parent1_chromo[trait]
            else:
                child[trait] = parent2_chromo[trait]
        return child

    def _mutate(self, chromosome, mutation_rate=0.15):
        """Apply random mutations to chromosome."""
        mutated = chromosome.copy()
        for trait in mutated:
            if random.random() < mutation_rate:
                change = random.uniform(-0.15, 0.15)
                mutated[trait] += change
                if trait == "speed":
                    mutated[trait] = max(1.0, min(3.0, mutated[trait]))
                else:
                    mutated[trait] = max(0.5, min(2.0, mutated[trait]))
        return mutated

    def run_genetic_algorithm(self):
        """Run GA at end of winter season to evolve animals."""
        animals = []
        if self.animal_fox and self.animal_fox.alive:
            animals.append(("fox", self.animal_fox))
        if self.animal_rabbit and self.animal_rabbit.alive:
            animals.append(("rabbit", self.animal_rabbit))

        if len(animals) < 2:
            return

        # Store pre-evolution fitness
        for name, animal in animals:
            animal.update_fitness()
            if name == "fox":
                self.last_fox_fitness = animal.fitness
                self.last_fox_chromo = animal.chromosome.copy()
            else:
                self.last_rabbit_fitness = animal.fitness
                self.last_rabbit_chromo = animal.chromosome.copy()

        # Sort by fitness
        animals.sort(key=lambda x: x[1].fitness, reverse=True)
        parents = animals[:2]

        # Crossover and mutate
        child1_chromo = self._crossover(
            parents[0][1].chromosome, parents[1][1].chromosome
        )
        child2_chromo = self._crossover(
            parents[1][1].chromosome, parents[0][1].chromosome
        )
        child1_chromo = self._mutate(child1_chromo)
        child2_chromo = self._mutate(child2_chromo)

        # Apply to animals
        if self.animal_fox:
            self.animal_fox.apply_chromosome(child1_chromo)
            self.animal_fox.generation += 1
            self.animal_fox.reset_for_new_season()

        if self.animal_rabbit:
            self.animal_rabbit.apply_chromosome(child2_chromo)
            self.animal_rabbit.generation += 1
            self.animal_rabbit.reset_for_new_season()

        # Record evolution history
        if self.ga_popup:
            self.ga_popup.add_evolution_record(
                self.generation_count,
                self.animal_fox.fitness if self.animal_fox else 0,
                self.animal_rabbit.fitness if self.animal_rabbit else 0,
                child1_chromo,
                child2_chromo,
            )

        self.generation_count += 1

    def start_next_year(self):
        """Start a new year with evolved animals."""
        self.current_year += 1
        self.completed_seasons = 0
        self.game_tick = 0
        self.last_season_index = 0

        # Reset scores
        if self.farmer:
            self.farmer.score = 0
        if self.guard:
            self.guard.score = 0
        if self.animal_fox:
            self.animal_fox.score = 0
            self.animal_fox.crops_eaten_this_season = 0
            self.animal_fox.survival_time = 0
        if self.animal_rabbit:
            self.animal_rabbit.score = 0
            self.animal_rabbit.crops_eaten_this_season = 0
            self.animal_rabbit.survival_time = 0

        # Reset season to Spring
        if self.season:
            self.season.index = 0
            self.season.tick = 0
            self.season.apply_current_effects(self.grid)

        # Clear crops from grid
        for col in range(self.grid.cols):
            for row in range(self.grid.rows):
                self.grid.tiles[col][row].crop = 0
                self.grid.tiles[col][row].crop_stage = 0

        # Generate new farm layout
        if self.csp_solver:
            self.csp_solver.solve()
            self.csp_solver.apply_to_grid()

        self._field_was_populated = True
        self.state = "PLAYING"

    # ------------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------------

    def _sync_crop_tracking(self):
        """Synchronize crop tracking variables with current grid state."""
        if self.grid and hasattr(self.grid, "crop_tiles"):
            current_crop_count = len(self.grid.crop_tiles())
        else:
            current_crop_count = 0
        self.previous_crop_count = current_crop_count
        self.initial_crops = current_crop_count
        self.crops_left = current_crop_count
        self._field_was_populated = current_crop_count > 0
        if current_crop_count > 0:
            self._waiting_for_regeneration = False

    def _show_generation_popup(self):
        """Show popup for crop regeneration options."""
        self.regeneration_popup = RegenerationPopup(
            self.screen,
            title="Harvest Complete",
            message="Choose auto generate or custom input for the next crops.",
        )

    def _complete_generation(self, message):
        """Complete crop generation and show notification."""
        self._sync_crop_tracking()
        self.notification_popup = NotificationPopup(
            self.screen,
            message,
            duration=180,
        )

    def _apply_auto_generation(self):
        """Apply auto-generation of crops using CSP solver."""
        self._waiting_for_regeneration = False
        if (
            self.csp_solver
            and hasattr(self.csp_solver, "solve")
            and hasattr(self.csp_solver, "apply_to_grid")
        ):
            previous_mode = (
                self.csp_solver.get_mode()
                if hasattr(self.csp_solver, "get_mode")
                else "manual"
            )
            if hasattr(self.csp_solver, "set_mode"):
                self.csp_solver.set_mode("auto")
            self.csp_solver.solve()
            self.csp_solver.apply_to_grid()
            if hasattr(self.csp_solver, "set_mode"):
                self.csp_solver.set_mode(previous_mode)
        if self.grid:
            self.farm_ui = FarmUI(self.grid)
        self._complete_generation(
            "All crops have been generated! Now start harvesting!"
        )

    def _no_popup_active(self):
        """Check if any popup is currently active."""
        return (
            self.notification_popup is None
            and self.regeneration_popup is None
            and self.custom_input_popup is None
        )

    def choose_animal_respawn(self):
        """Find a safe spawn position for animals away from the guard."""
        guard_pos = (self.guard.col, self.guard.row) if self.guard else None
        min_col, max_col, min_row, max_row = 4, 17, 2, 13
        safe_tiles = []

        if not self.grid:
            return (17, 1)

        for c in range(
            max(0, min_col), min(getattr(self.grid, "cols", 0), max_col + 1)
        ):
            for r in range(
                max(0, min_row), min(getattr(self.grid, "rows", 0), max_row + 1)
            ):
                if guard_pos and (c, r) == guard_pos:
                    continue
                tile = self.grid.get(c, r) if hasattr(self.grid, "get") else None
                if not tile or not getattr(tile, "walkable", False):
                    continue
                if (
                    guard_pos
                    and isinstance(guard_pos, (tuple, list))
                    and len(guard_pos) == 2
                ):
                    if abs(c - guard_pos[0]) + abs(r - guard_pos[1]) <= 4:
                        continue
                safe_tiles.append((c, r))

        if not safe_tiles:
            for c in range(getattr(self.grid, "cols", 0)):
                for r in range(getattr(self.grid, "rows", 0)):
                    tile = self.grid.get(c, r) if hasattr(self.grid, "get") else None
                    if (
                        tile
                        and getattr(tile, "walkable", False)
                        and (not guard_pos or (c, r) != guard_pos)
                    ):
                        safe_tiles.append((c, r))

        if not safe_tiles:
            return (17, 1)

        random.shuffle(safe_tiles)
        return safe_tiles[0]

    @staticmethod
    def _random_spawn(grid):
        """Find a random walkable spawn position."""
        candidates = []
        if (
            not grid
            or not hasattr(grid, "cols")
            or not hasattr(grid, "rows")
            or not hasattr(grid, "get")
        ):
            return (6, 6)

        for c in range(2, grid.cols):
            for r in range(grid.rows):
                t = grid.get(c, r)
                if t and getattr(t, "type", None) not in (TILE_WATER, TILE_STONE):
                    candidates.append((c, r))

        if candidates:
            return random.choice(candidates)
        return (6, 6)

    def check_end_condition(self):
        """Check if a year has completed (winter -> spring transition)."""
        if (
            self.season
            and getattr(self.season, "index", None) == 0
            and self.last_season_index == 3
        ):
            self.completed_seasons += 1
        if self.season:
            self.last_season_index = getattr(self.season, "index", 0)
        if (
            self.completed_seasons >= 1
            and self.season
            and getattr(self.season, "index", None) == 0
        ):
            return True
        return False

    # ------------------------------------------------------------------------
    # Drawing Methods
    # ------------------------------------------------------------------------

    def draw_minimap(self):
        """Draw a small minimap showing tile colors and agent positions."""
        mini_w, mini_h = 240, 180
        mini_x = SCREEN_W - mini_w - 15
        mini_y = SCREEN_H - mini_h - 15

        panel = pygame.Surface((mini_w, mini_h), pygame.SRCALPHA)
        panel.fill((20, 25, 30, 220))
        self.screen.blit(panel, (mini_x, mini_y))
        pygame.draw.rect(
            self.screen, (80, 120, 80), (mini_x, mini_y, mini_w, mini_h), 2
        )
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
            TILE_DIRT: (94, 68, 42),
            TILE_STONE: (100, 100, 110),
        }

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                cx = int(map_x + col * cell_w)
                cy = int(map_y + row * cell_h)
                cw, ch = max(2, int(cell_w)), max(2, int(cell_h))
                tile = (
                    self.grid.get(col, row)
                    if self.grid and hasattr(self.grid, "get")
                    else None
                )
                color = (
                    TILE_COLORS.get(tile.type, (85, 62, 40)) if tile else (80, 80, 80)
                )
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
        """Draw the season information panel with current stats."""
        panel_w = 210
        panel_h = 160
        panel_x = 15
        panel_y = 15

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((20, 25, 30, 220))
        self.screen.blit(panel, (panel_x, panel_y))
        pygame.draw.rect(
            self.screen, (80, 120, 80), (panel_x, panel_y, panel_w, panel_h), 2
        )

        season_name = ""
        if self.season and hasattr(self.season, "name"):
            season_name = self.season.name.strip()
        self.screen.blit(
            self.font_medium.render(f"Season: {season_name}", True, (255, 215, 0)),
            (panel_x + 12, panel_y + 10),
        )

        self.screen.blit(
            self.font_small.render(f"Year: {self.current_year}", True, (255, 200, 100)),
            (panel_x + 12, panel_y + 32),
        )

        day = (
            getattr(self.season, "day_count", None)
            if self.season
            and hasattr(self.season, "day_count")
            and getattr(self.season, "day_count", None)
            else (self.game_tick // 600) + 1
        )
        self.screen.blit(
            self.font_small.render(f"Day: {day}", True, (220, 220, 220)),
            (panel_x + 12, panel_y + 52),
        )

        tod_color = (
            (160, 200, 255) if self.season and self.season.is_night else (255, 230, 140)
        )
        tod = self.season.time_of_day if self.season else "Day"
        self.screen.blit(
            self.font_small.render(f"Time: {tod}", True, tod_color),
            (panel_x + 12, panel_y + 72),
        )

        money = self.farmer.score if self.farmer else 0
        self.screen.blit(
            self.font_small.render(f"Money: {money}", True, (100, 220, 140)),
            (panel_x + 12, panel_y + 92),
        )

        if self.animal_fox:
            self.screen.blit(
                self.font_small.render(
                    f"Fox Gen: {self.animal_fox.generation}", True, (255, 150, 100)
                ),
                (panel_x + 12, panel_y + 112),
            )

        if self.animal_rabbit:
            self.screen.blit(
                self.font_small.render(
                    f"Rabbit Gen: {self.animal_rabbit.generation}",
                    True,
                    (190, 140, 255),
                ),
                (panel_x + 12, panel_y + 132),
            )

    def draw_change_season_button(self, enabled=True):
        """Draw the button to manually advance the season."""
        btn_width = 190
        btn_height = 40
        btn_x = SCREEN_W - btn_width - 20
        btn_y = 18
        self.change_season_button_rect = pygame.Rect(
            btn_x, btn_y, btn_width, btn_height
        )

        mouse_pos = pygame.mouse.get_pos()
        is_hover = enabled and self.change_season_button_rect.collidepoint(mouse_pos)

        if enabled:
            wood_base = (100, 70, 40)
            wood_light = (140, 105, 65)
            border = (80, 150, 80)
            text_color = (255, 215, 0)
            btn_color = wood_light if is_hover else wood_base
        else:
            btn_color = (80, 80, 80)
            border = (110, 110, 110)
            text_color = (170, 170, 170)

        pygame.draw.rect(
            self.screen, btn_color, self.change_season_button_rect, border_radius=12
        )
        pygame.draw.rect(
            self.screen, border, self.change_season_button_rect, 2, border_radius=12
        )

        for i in range(2):
            line_y = btn_y + 12 + i * 14
            pygame.draw.line(
                self.screen,
                (80, 55, 30),
                (btn_x + 10, line_y),
                (btn_x + btn_width - 10, line_y),
                1,
            )

        btn_font = pygame.font.Font(None, 22)
        btn_text = btn_font.render("CHANGE SEASON", True, text_color)
        self.screen.blit(
            btn_text, btn_text.get_rect(center=self.change_season_button_rect.center)
        )

    def draw_day_night_overlay(self):
        """Draw overlay for day/night cycle."""
        if not self.season or self.season.night_alpha <= 0:
            return
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((18, 24, 50, self.season.night_alpha))
        self.screen.blit(overlay, (0, 0))

    def draw_season_fullscreen_overlay(self):
        """Draw color tint overlay for current season."""
        if not self.season:
            return
        tint_color = SEASON_TINTS.get(self.season.index % len(SEASON_TINTS))
        if not tint_color:
            return
        r, g, b, base_alpha = tint_color
        pulse = int(self.season.bloom * 8)
        alpha = max(0, min(80, base_alpha + pulse))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((r, g, b, alpha))
        self.screen.blit(overlay, (0, 0))

    def draw_pause_screen(self):
        """Draw the pause overlay screen."""
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font_big = pygame.font.Font(None, 64)
        font_sm = pygame.font.Font(None, 24)

        pause = font_big.render("PAUSED", True, (255, 215, 0))
        self.screen.blit(
            pause, pause.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 30))
        )

        hint = font_sm.render(
            "Press P to Resume | ESC to Quit to Menu", True, (200, 200, 200)
        )
        self.screen.blit(
            hint, hint.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 30))
        )

    def draw_plant_button(self):
        """Draw the plant crop button."""
        btn_w, btn_h = 140, 45
        btn_x = SCREEN_W - btn_w - 20
        btn_y = 70
        self.plant_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.plant_button_rect.collidepoint(mouse_pos)
        btn_color = (140, 105, 65) if is_hover else (100, 70, 40)

        pygame.draw.rect(
            self.screen, btn_color, self.plant_button_rect, border_radius=12
        )
        pygame.draw.rect(
            self.screen, (80, 150, 80), self.plant_button_rect, 2, border_radius=12
        )

        for i in range(2):
            line_y = btn_y + 15 + i * 18
            pygame.draw.line(
                self.screen,
                (80, 55, 30),
                (btn_x + 10, line_y),
                (btn_x + btn_w - 10, line_y),
                1,
            )

        btn_font = pygame.font.Font(None, 20)
        btn_text = btn_font.render("Plant Crop", True, (255, 215, 0))
        self.screen.blit(
            btn_text, btn_text.get_rect(center=self.plant_button_rect.center)
        )

    def draw_rain_button(self):
        """Draw the rain trigger button."""
        btn_width = 140
        btn_height = 45
        btn_x = SCREEN_W - btn_width - 20
        btn_y = 122
        self.rain_button_rect = pygame.Rect(btn_x, btn_y, btn_width, btn_height)

        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rain_button_rect.collidepoint(mouse_pos)
        btn_color = (80, 105, 140) if is_hover else (60, 80, 110)

        pygame.draw.rect(
            self.screen, btn_color, self.rain_button_rect, border_radius=12
        )
        pygame.draw.rect(
            self.screen, (80, 120, 180), self.rain_button_rect, 2, border_radius=12
        )

        for i in range(2):
            line_y = btn_y + 15 + i * 18
            pygame.draw.line(
                self.screen,
                (50, 65, 90),
                (btn_x + 10, line_y),
                (btn_x + btn_width - 10, line_y),
                1,
            )

        btn_font = pygame.font.Font(None, 20)
        btn_text = btn_font.render("Raining", True, (180, 210, 255))
        self.screen.blit(
            btn_text, btn_text.get_rect(center=self.rain_button_rect.center)
        )

    def draw_snow_button(self):
        """Draw the snow/thaw trigger button."""
        btn_width = 140
        btn_height = 45
        btn_x = SCREEN_W - SIDEBAR_W + 20
        btn_y = 430
        self.snow_button_rect = pygame.Rect(btn_x, btn_y, btn_width, btn_height)

        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.snow_button_rect.collidepoint(mouse_pos)
        is_winter = self.season and self.season.index == 3
        btn_color = (
            (130, 160, 190)
            if is_winter
            else ((80, 120, 160) if is_hover else (60, 90, 130))
        )

        pygame.draw.rect(
            self.screen, btn_color, self.snow_button_rect, border_radius=12
        )
        pygame.draw.rect(
            self.screen, (100, 150, 200), self.snow_button_rect, 2, border_radius=12
        )

        btn_font = pygame.font.Font(None, 20)
        label = "THAW" if is_winter else "TRIGGER SNOW"
        btn_text = btn_font.render(label, True, (200, 225, 255))
        self.screen.blit(
            btn_text, btn_text.get_rect(center=self.snow_button_rect.center)
        )

    def _draw_game_world(self):
        """Draw the complete game world including grid, overlays, and UI."""
        self.screen.fill((34, 139, 34))

        if self.grid and hasattr(self.grid, "draw") and self.season:
            self.grid.draw(
                self.screen, self.game_tick, None, getattr(self.season, "index", 0)
            )

        if self.farm_ui:
            self.farm_ui.draw(self.screen)

        self.draw_season_fullscreen_overlay()
        self.draw_day_night_overlay()
        self.draw_season_info()
        self.draw_minimap()

        if self.rain_animation:
            self.rain_animation.draw(self.screen)

    # ------------------------------------------------------------------------
    # Main Game Loop
    # ------------------------------------------------------------------------

    def run(self):
        """Main game loop - handles events, updates, and rendering."""
        while self.running:
            self.clock.tick(FPS)
            self.clock_obj.update()

            # -----------------------------------------------------------------
            # EVENT HANDLING
            # -----------------------------------------------------------------

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                # Main Menu State
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

                # How To Play State
                elif self.state == "HOWTOPLAY":
                    if self.how_to_play.handle_event(event) == "back":
                        self.state = "MENU"

                # Settings State
                elif self.state == "SETTINGS":
                    if self.settings.handle_event(event) == "back":
                        self.state = "MENU"

                # CSP Planning State
                elif self.state == "CSP":
                    if (
                        self.csp_popup
                        and hasattr(self.csp_popup, "handle_event")
                        and self.csp_popup.handle_event(event)
                    ):
                        if (
                            hasattr(self.csp_popup, "is_confirmed")
                            and self.csp_popup.is_confirmed()
                        ):
                            self.state = "PLAYING"
                            self.game_tick = 0
                            self._sync_crop_tracking()

                # Playing State
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
                        elif event.key == pygame.K_e:
                            if self.ga_popup:
                                self.ga_popup.toggle()
                        elif event.key == pygame.K_TAB:
                            if self.viz_manager:
                                self.viz_manager.toggle_panel()
                        elif event.key == pygame.K_n:
                            if self.viz_manager:
                                self.viz_manager.toggle_nodes()
                        elif event.key == pygame.K_d:
                            if self.viz_manager:
                                self.viz_manager.toggle_danger_zones()
                        elif event.key == pygame.K_m:
                            if self.viz_manager:
                                self.viz_manager.toggle_paths()

                    if event.type == pygame.MOUSEBUTTONDOWN:
                        # Change season button
                        if (
                            self.change_season_button_rect
                            and self.change_season_button_rect.collidepoint(event.pos)
                            and self.season
                        ):
                            self.season.advance_manual(self.grid)

                        # Plant button
                        if (
                            self.plant_button_rect
                            and self.plant_button_rect.collidepoint(event.pos)
                            and self._no_popup_active()
                        ):
                            if self.farmer:
                                self.farmer.trigger_planting()

                        # Rain button
                        if (
                            self.rain_button_rect
                            and self.rain_button_rect.collidepoint(event.pos)
                        ):
                            if self.grid and self.season:
                                self.season.trigger_rain(self.grid)
                                if self.rain_animation:
                                    self.rain_animation.start()

                    # Regeneration popup handling
                    if self.regeneration_popup and event.type == pygame.MOUSEBUTTONDOWN:
                        choice = self.regeneration_popup.handle_click(event.pos)
                        if choice == "auto":
                            self.regeneration_popup = None
                            self.regeneration_mode = "auto"
                            self._apply_auto_generation()
                        elif choice == "custom":
                            self.regeneration_mode = "custom"
                            winter_only = bool(self.season and self.season.index == 3)
                            self.custom_input_popup = CustomInputPopup(
                                self.screen,
                                max_crops=(
                                    max(1, len(self.grid.field_tiles()))
                                    if self.grid and hasattr(self.grid, "field_tiles")
                                    else 1
                                ),
                                initial_counts={
                                    CROP_WHEAT: 0,
                                    CROP_SUNFLOWER: 0,
                                    CROP_CORN: 0,
                                    CROP_TOMATO: 0,
                                    CROP_CARROT: 0,
                                },
                                allowed_crops=(
                                    [CROP_CORN, CROP_CARROT] if winter_only else None
                                ),
                            )
                            self.regeneration_popup = None

                    # Custom input popup handling
                    if self.custom_input_popup:
                        if event.type == pygame.KEYDOWN:
                            self.custom_input_popup.handle_keypress(event.key)
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            self.custom_input_popup.handle_click(event.pos)
                            if self.custom_input_popup.submitted:
                                self._waiting_for_regeneration = False

                    if self.notification_popup:
                        self.notification_popup.handle_event(event)

                    if self.ga_popup:
                        self.ga_popup.handle_event(event)

                # Paused State
                elif self.state == "PAUSED":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_p:
                            self.state = "PLAYING"
                        elif event.key == pygame.K_ESCAPE:
                            self.init_game()
                            self.state = "MENU"
                        elif event.key == pygame.K_TAB:
                            if self.viz_manager:
                                self.viz_manager.toggle_panel()
                        elif event.key == pygame.K_n:
                            if self.viz_manager:
                                self.viz_manager.toggle_nodes()
                        elif event.key == pygame.K_d:
                            if self.viz_manager:
                                self.viz_manager.toggle_danger_zones()
                        elif event.key == pygame.K_m:
                            if self.viz_manager:
                                self.viz_manager.toggle_paths()
                        elif event.key == pygame.K_e:
                            if self.ga_popup:
                                self.ga_popup.toggle()

                # End Screen State
                elif self.state == "END":
                    result = (
                        self.end_screen.handle_event(event)
                        if self.end_screen and hasattr(self.end_screen, "handle_event")
                        else None
                    )
                    if result == "continue":
                        self.start_next_year()
                    elif result == "restart":
                        self.init_game()
                        self.state = "CSP"
                    elif result == "menu":
                        self.state = "MENU"

            # -----------------------------------------------------------------
            # GAME LOGIC & RENDERING
            # -----------------------------------------------------------------

            # Main Menu
            if self.state == "MENU":
                self.menu.draw()

            # How To Play Screen
            elif self.state == "HOWTOPLAY":
                self.how_to_play.draw()

            # Settings Screen
            elif self.state == "SETTINGS":
                self.settings.draw()

            # CSP Planning Screen
            elif self.state == "CSP":
                self.screen.fill((34, 139, 34))
                if self.grid and hasattr(self.grid, "draw"):
                    self.grid.draw(self.screen, self.game_tick, None, -1)
                if self.farm_ui and hasattr(self.farm_ui, "draw"):
                    self.farm_ui.draw(self.screen)
                if self.csp_popup and hasattr(self.csp_popup, "draw"):
                    self.csp_popup.draw()

            # Playing State
            elif self.state == "PLAYING":
                # Update season
                day_night_flipped = False
                if self.season and hasattr(self.season, "update") and self.grid:
                    day_night_flipped = self.season.update(self.grid, self.clock_obj)

                    # Trigger GA when winter ends
                    if hasattr(self.season, "_last_index"):
                        if self.season._last_index == 3 and self.season.index == 0:
                            self.run_genetic_algorithm()
                    self.season._last_index = self.season.index

                # Check if year ended
                if self.check_end_condition():
                    animal_score = 0
                    if self.animal_fox and hasattr(self.animal_fox, "score"):
                        animal_score += self.animal_fox.score
                    if self.animal_rabbit and hasattr(self.animal_rabbit, "score"):
                        animal_score += self.animal_rabbit.score

                    fox_fitness = self.animal_fox.fitness if self.animal_fox else 0
                    rabbit_fitness = (
                        self.animal_rabbit.fitness if self.animal_rabbit else 0
                    )
                    fox_chromo = self.animal_fox.chromosome if self.animal_fox else {}
                    rabbit_chromo = (
                        self.animal_rabbit.chromosome if self.animal_rabbit else {}
                    )

                    self.end_screen = YearEndScreen(
                        self.screen,
                        getattr(self.farmer, "score", 0),
                        getattr(self.guard, "score", 0),
                        animal_score,
                        self.current_year,
                        self.last_fox_fitness,
                        self.last_rabbit_fitness,
                        self.last_fox_chromo,
                        self.last_rabbit_chromo,
                        fox_fitness,
                        rabbit_fitness,
                        fox_chromo,
                        rabbit_chromo,
                    )
                    self.state = "END"

                # Update agents if no popups active
                if self._no_popup_active():
                    for agent in self.agents:
                        if agent and hasattr(agent, "update"):
                            agent.update(self.grid, self.agents, self.season)

                    if self.rain_animation:
                        rain_finished = self.rain_animation.update()

                    # Respawn animals if dead
                    if (
                        self.animal_fox
                        and hasattr(self.animal_fox, "alive")
                        and not self.animal_fox.alive
                        and hasattr(self.animal_fox, "respawn")
                        and self.grid
                    ):
                        spawn = self._random_spawn(self.grid)
                        if isinstance(spawn, (tuple, list)) and len(spawn) == 2:
                            self.animal_fox.respawn(spawn[0], spawn[1], self.grid)
                    if (
                        self.animal_rabbit
                        and hasattr(self.animal_rabbit, "alive")
                        and not self.animal_rabbit.alive
                        and hasattr(self.animal_rabbit, "respawn")
                        and self.grid
                    ):
                        spawn = self._random_spawn(self.grid)
                        if isinstance(spawn, (tuple, list)) and len(spawn) == 2:
                            self.animal_rabbit.respawn(spawn[0], spawn[1], self.grid)

                self.game_tick += 1

                # Update grid timers and pruning
                farmer_pos = (self.farmer.col, self.farmer.row) if self.farmer else None
                if self.grid and self.season and hasattr(self.grid, "update_tick"):
                    self.grid.update_tick(
                        self.game_tick,
                        getattr(self.season, "is_night", False),
                        getattr(self.season, "index", 0),
                        farmer_pos,
                    )

                # Crop regeneration logic
                current_crop_count = (
                    len(self.grid.crop_tiles())
                    if self.grid and hasattr(self.grid, "crop_tiles")
                    else 0
                )

                if current_crop_count > 0:
                    self._field_was_populated = True
                    self._waiting_for_regeneration = False

                if (
                    self._field_was_populated
                    and current_crop_count == 0
                    and not self._waiting_for_regeneration
                    and self._no_popup_active()
                ):
                    self._show_generation_popup()
                    self._waiting_for_regeneration = True
                    self._field_was_populated = False

                self.previous_crop_count = current_crop_count

                # Update popups
                if self.regeneration_popup:
                    self.regeneration_popup.update()

                if self.custom_input_popup:
                    self.custom_input_popup.update()
                    if self.custom_input_popup.submitted:
                        self._waiting_for_regeneration = False
                        selected_counts = self.custom_input_popup.get_value()
                        if selected_counts is not None:
                            if self.csp_solver:
                                if hasattr(self.csp_solver, "solve"):
                                    self.csp_solver.solve(selected_counts)
                                if hasattr(self.csp_solver, "apply_to_grid"):
                                    self.csp_solver.apply_to_grid()
                            if self.grid:
                                self.farm_ui = FarmUI(self.grid)
                            self.custom_input_popup = None
                            total_selected = sum(selected_counts.values())
                            self._complete_generation(
                                f"{total_selected} custom crops generated successfully!"
                            )

                if self.notification_popup:
                    if self.notification_popup.update():
                        self._sync_crop_tracking()
                        self.regeneration_mode = None
                        self.notification_popup = None

                # Draw everything
                self._draw_game_world()

                if self.viz_manager:
                    self.viz_manager.update_astar_data(
                        self.farmer, self.guard, self.animal_fox, self.animal_rabbit
                    )
                    self.viz_manager.update_csp_data(self.csp_solver)
                    self.viz_manager.draw_all(
                        farmer_score=getattr(self.farmer, "score", 0),
                        guard_score=getattr(self.guard, "score", 0),
                        fox_score=getattr(self.animal_fox, "score", 0),
                        rabbit_score=getattr(self.animal_rabbit, "score", 0),
                        fps=int(self.clock.get_fps()),
                        guard=self.guard,
                    )

                self.draw_change_season_button(enabled=True)
                self.draw_plant_button()
                self.draw_rain_button()

                # Draw agents and their indicators
                for agent in self.agents:
                    if hasattr(agent, "alive") and not agent.alive:
                        continue
                    agent.draw(self.screen)
                    if hasattr(agent, "draw_failed_plant_indicator"):
                        agent.draw_failed_plant_indicator(self.screen, self.grid)
                    if hasattr(agent, "draw_failed_move_indicator"):
                        agent.draw_failed_move_indicator(self.screen, self.grid)
                    if hasattr(agent, "show_blocked_cross"):
                        agent.show_blocked_cross(self.screen, self.grid)

                if self.ga_popup:
                    self.ga_popup.draw()

                if self.regeneration_popup:
                    self.regeneration_popup.draw()
                if self.custom_input_popup:
                    self.custom_input_popup.draw()
                if self.notification_popup:
                    self.notification_popup.draw()

            # Paused State
            elif self.state == "PAUSED":
                self._draw_game_world()
                self.draw_change_season_button(enabled=False)

                # Draw disabled plant button overlay
                bw, bh = 140, 45
                bx = SCREEN_W - SIDEBAR_W + 20
                by = 320
                pr = pygame.Rect(bx, by, bw, bh)
                pygame.draw.rect(self.screen, (80, 80, 80), pr, border_radius=12)
                pygame.draw.rect(self.screen, (100, 100, 100), pr, 2, border_radius=12)
                bf = pygame.font.Font(None, 20)
                bt = bf.render("PLANT CROPS", True, (150, 150, 150))
                self.screen.blit(bt, bt.get_rect(center=pr.center))

                for agent in self.agents:
                    if hasattr(agent, "alive") and not agent.alive:
                        continue
                    agent.draw(self.screen)
                    if hasattr(agent, "show_blocked_cross"):
                        agent.show_blocked_cross(self.screen, self.grid)

                if self.farmer:
                    self.farmer.draw_failed_plant_indicator(self.screen, self.grid)

                if self.ga_popup:
                    self.ga_popup.draw()

                self.draw_pause_screen()

            # End Screen State
            elif self.state == "END":
                if self.end_screen and hasattr(self.end_screen, "draw"):
                    self.end_screen.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    game = Game()
    game.run()
