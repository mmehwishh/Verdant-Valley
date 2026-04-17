import math
from utils.constants import *


class SeasonManager:
    def __init__(self):
        self.index = 0  # 0-3
        self.tick = 0
        self.rain_active = False
        self.rain_timer = 0
        self.bloom = 0.0

    @property
    def name(self):
        return SEASONS[self.index % len(SEASONS)]

    @property
    def progress(self):
        return min(1.0, self.tick / SEASON_DURATION)

    def update(self, grid):
        self.tick += 1

        # Grow crops each 120 ticks
        if self.tick % 120 == 0:
            for c in range(grid.cols):
                for r in range(grid.rows):
                    t = grid.tiles[c][r]
                    if t.crop != CROP_NONE and t.crop_stage < 3:
                        t.crop_stage += 1

        # Random rain every ~15 seconds in summer
        if self.name == "☀️ Summer" and self.tick % (15 * FPS) == 0:
            self.rain_active = True
            self.rain_timer = 5 * FPS
            grid.apply_rain()

        if self.rain_active:
            self.rain_timer -= 1
            if self.rain_timer <= 0:
                self.rain_active = False

        # Seasonal bloom pulse for UI shine
        self.bloom = abs(math.sin(self.tick * 0.02))

        # Season end
        if self.tick >= SEASON_DURATION:
            self._advance(grid)

    def _advance(self, grid):
        self.tick = 0
        self.index += 1
        # Reset rain/wet status at season boundaries
        self.rain_active = False
        self.rain_timer = 0
        if self.name == "🌱 Spring":
            for c in range(grid.cols):
                for r in range(grid.rows):
                    grid.tiles[c][r].wet = False

    def time_label(self):
        secs_left = max(0, (SEASON_DURATION - self.tick) // FPS)
        m, s = divmod(secs_left, 60)
        return f"{m:02d}:{s:02d}"
