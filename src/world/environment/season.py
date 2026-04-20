"""
world/season.py  —  Verdant Valley
Season and time manager for deterministic world progression.
Handles automatic/manual season cycling, synchronized day/night state,
seasonal weather effects (rain), and winter freeze hooks for the grid.
"""

import math
from utils.constants import *


class SeasonManager:
    def __init__(self):
        self.index = 0  # 0-3
        self.tick = 0
        self.rain_active = False
        self.rain_timer = 0
        self.bloom = 0.0
        self.day_night_cycle = 24 * FPS
        self.day_count = 1
        self.time_of_day = "Day"
        self.is_night = False
        self.night_alpha = 0
        self.last_rain_tick = 0
        self.last_flood_to_mud_tick = 0

    @property
    def name(self):
        return SEASONS[self.index % len(SEASONS)]

    @property
    def progress(self):
        return min(1.0, self.tick / SEASON_DURATION)

    def update(self, grid, clock=None):
        self.tick += 1
        flipped = self._update_day_night()

        # Grow crops each 120 ticks
        if self.tick % 120 == 0:
            for c in range(grid.cols):
                for r in range(grid.rows):
                    t = grid.tiles[c][r]
                    if getattr(t, "managed_growth", False):
                        continue
                    if t.crop != CROP_NONE and t.crop_stage < 3:
                        t.crop_stage += 1

        # --- Season change every SEASON_DURATION ---
        if self.tick >= SEASON_DURATION:
            self._advance(grid)

        # --- Auto rain every 60 seconds ---
        if clock and clock.seconds - self.last_rain_tick >= 60:
            self.trigger_rain(grid)
            self.last_rain_tick = clock.seconds

        # Rain timer logic
        if self.rain_active:
            self.rain_timer -= 1
            if self.rain_timer <= 0:
                self.rain_active = False

        # Seasonal bloom pulse for UI shine
        self.bloom = abs(math.sin(self.tick * 0.02))

        return flipped

    def trigger_rain(self, grid):
        self.rain_active = True
        self.rain_timer = 10 * FPS  # 10 seconds of rain
        grid.apply_rain()

    def advance_manual(self, grid):
        """Manually force the next season while preserving runtime flow."""
        self._advance(grid)

    def _advance(self, grid):
        self.tick = 0
        self.index = (self.index + 1) % len(SEASONS)
        # Reset rain/wet status at season boundaries
        self.rain_active = False
        self.rain_timer = 0
        self._update_day_night()
        self._apply_season_effects(grid)
        if self.name == "🌱 Spring":
            for c in range(grid.cols):
                for r in range(grid.rows):
                    grid.tiles[c][r].wet = False

    def apply_current_effects(self, grid):
        self._apply_season_effects(grid)

    def _apply_season_effects(self, grid):
        if self.name == "❄️ Winter":
            grid.apply_winter_freeze()
        else:
            grid.clear_winter_freeze()

    def _update_day_night(self):
        if self.day_night_cycle <= 0:
            self.day_night_cycle = 24 * FPS

        cycle_pos = self.tick % self.day_night_cycle
        cycle_ratio = cycle_pos / self.day_night_cycle
        night_level_raw = 0.5 - 0.5 * math.cos(2 * math.pi * cycle_ratio)
        night_level = max(0.0, (night_level_raw - 0.50) / 0.50)

        self.night_alpha = int(night_level * 130)
        
        new_is_night = cycle_pos >= (self.day_night_cycle // 2)
        flipped = (new_is_night != self.is_night)
        
        self.is_night = new_is_night
        self.time_of_day = "Night" if self.is_night else "Day"
        self.day_count = (self.tick // self.day_night_cycle) + 1
        
        return flipped

    def time_label(self):
        secs_left = max(0, (SEASON_DURATION - self.tick) // FPS)
        m, s = divmod(secs_left, 60)
        return f"{m:02d}:{s:02d}"
