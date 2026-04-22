import random
import os
import pygame
from .base_agent import Agent
from src.algorithms.astar import astar
from utils.constants import *
from utils.helpers import manhattan, tile_center


class Animal(Agent):
    FLEE_DISTANCE = 5  # Distance to start fleeing from guard
    STAMINA_MAX = 100
    STAMINA_DRAIN = 0.5  # Less drain for animal

    def __init__(self, col, row, animal_type="fox"):
        # Auto-detect frame size

        self.animal_type = animal_type

        if animal_type == "rabbit":
            path = "assets/agents/animal/hare.png"
            name = "Rabbit"
            color = (180, 140, 220)  # light purple
            speed = 1.8
            animation_cols = 6  # Rabbit has 6 columns
            animation_rows = 4  # Rabbit has 4 rows
            w_guard_avoid = 1.0
        else:  # fox
            path = "assets/agents/animal/fox.png"
            name = "Fox"
            color = (255, 100, 50)  # orange/reddish color for fox
            speed = 1.6
            animation_cols = 6  # Fox has 6 columns
            animation_rows = 4  # Fox has 4 rows
            w_guard_avoid = 1.5

        frame_w, frame_h = 16, 16

        # Try to load sprite sheet
        sprite_path = None
        if os.path.exists(path):
            img = pygame.image.load(path)
            w, h = img.get_size()
            # Calculate frame size based on actual image dimensions and grid layout
            frame_w = w // animation_cols
            frame_h = h // animation_rows
            sprite_path = path
            print(
                f"✅ {name} sheet: {w}x{h}, frames: {frame_w}x{frame_h} ({animation_cols}x{animation_rows} grid)"
            )
        else:
            print(f"⚠️ {name} sheet not found at: {path}, will use fallback")
            sprite_path = None

        super().__init__(
            col,
            row,
            color,
            speed=speed,
            name=name,
            sprite_sheet_path=sprite_path,
            frame_size=(frame_w, frame_h),
            animation_rows=animation_rows,
            animation_cols=animation_cols,
            scale=2,
        )
        self.alive = True
        self.crops_eaten = 0
        self.recent_crop_damage_timer = 0
        self.replan_cd = 0
        self.w_crop_value = 1.0
        self.w_guard_avoid = w_guard_avoid
        self._ate_this_tile = False
        self.season_mgr = None
        self.state = "hungry"  # hungry, scared, wandering
        self.stamina = self.STAMINA_MAX
        self.original_color = color
        self.scared_animation_timer = 0  # For flashing effect

    def get_color(self):
        # When scared, flash between red and dark red
        if self.state == "scared":
            # Flashing effect every 5 frames
            if (
                hasattr(self, "scared_animation_timer")
                and (self.scared_animation_timer // 5) % 2 == 0
            ):
                return (255, 0, 0)  # Bright red
            else:
                return (200, 0, 0)  # Dark red
        elif self.state == "wandering":
            return (128, 128, 128)  # Gray when wandering
        return self.original_color

    def draw(self, surface, font=None):
        # Update scared animation timer
        if self.state == "scared":
            self.scared_animation_timer = getattr(self, "scared_animation_timer", 0) + 1

        # Add stronger shaking effect when scared
        offset_x, offset_y = 0, 0
        if self.state == "scared":
            offset_x = random.randint(-4, 4)  # Increased shake range
            offset_y = random.randint(-4, 4)  # Increased shake range

        # Temporarily adjust position for drawing
        original_x, original_y = self.x, self.y
        self.x += offset_x
        self.y += offset_y

        # === SCARED VISUAL EFFECTS (Drawn BEHIND the animal) ===
        if self.state == "scared":
            # 1. Red glow/circle behind animal
            glow_radius = TILE_SIZE // 2 + 8
            for i in range(3):  # Multiple layers for better glow
                alpha = 100 - i * 30
                radius = glow_radius - i * 2
                pygame.draw.circle(
                    surface, (255, 0, 0, alpha), (int(self.x), int(self.y)), radius
                )

            # 2. Exclamation marks above animal
            if font:
                exclaim = font.render("!!!", True, (255, 0, 0))
                exclaim_shadow = font.render("!!!", True, (100, 0, 0))
                # Shadow
                surface.blit(
                    exclaim_shadow,
                    (
                        int(self.x) - exclaim.get_width() // 2 + 2,
                        int(self.y) - TILE_SIZE // 2 - 45 + 2,
                    ),
                )
                # Main text
                surface.blit(
                    exclaim,
                    (
                        int(self.x) - exclaim.get_width() // 2,
                        int(self.y) - TILE_SIZE // 2 - 45,
                    ),
                )

        # Draw the actual animal sprite
        super().draw(surface, font)

        # === SCARED VISUAL EFFECTS (Drawn ON TOP of the animal) ===
        if self.state == "scared":
            # 3. Red border around the animal
            rect = pygame.Rect(
                int(self.x) - TILE_SIZE // 2 - 2,
                int(self.y) - TILE_SIZE // 2 - 2,
                TILE_SIZE + 4,
                TILE_SIZE + 4,
            )
            pygame.draw.rect(surface, (255, 0, 0), rect, 3)  # Thick red border

            # 4. Red X marks on corners (extra scary!)
            corner_offset = 8
            corners = [
                (int(self.x) - corner_offset, int(self.y) - corner_offset),
                (int(self.x) + corner_offset, int(self.y) - corner_offset),
                (int(self.x) - corner_offset, int(self.y) + corner_offset),
                (int(self.x) + corner_offset, int(self.y) + corner_offset),
            ]
            for cx, cy in corners:
                pygame.draw.line(
                    surface, (255, 0, 0), (cx - 5, cy - 5), (cx + 5, cy + 5), 2
                )
                pygame.draw.line(
                    surface, (255, 0, 0), (cx + 5, cy - 5), (cx - 5, cy + 5), 2
                )

        # Restore position
        self.x, self.y = original_x, original_y

        # === SCARED TEXT ===
        if self.state == "scared" and font:
            scared_text = font.render("SCARED!", True, (255, 255, 255))
            scared_bg = font.render("SCARED!", True, (255, 0, 0))

            # Background text (shadow effect)
            for offset in [(2, 2), (-2, 2), (2, -2), (-2, -2)]:
                surface.blit(
                    scared_bg,
                    (
                        int(self.x) - scared_text.get_width() // 2 + offset[0],
                        int(self.y) - TILE_SIZE // 2 - 35 + offset[1],
                    ),
                )
            # Main white text
            surface.blit(
                scared_text,
                (
                    int(self.x) - scared_text.get_width() // 2,
                    int(self.y) - TILE_SIZE // 2 - 35,
                ),
            )

        # === STAMINA BAR (only when scared) ===
        if self.state == "scared":
            bar_width = TILE_SIZE
            bar_height = 6
            stamina_percent = max(0, self.stamina / self.STAMINA_MAX)

            bar_x = int(self.x) - bar_width // 2
            bar_y = int(self.y) - TILE_SIZE // 2 - 25

            # Background (dark red)
            pygame.draw.rect(surface, (80, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            # Stamina (bright red/orange)
            color = (255, 100, 0) if stamina_percent > 0.3 else (255, 0, 0)
            pygame.draw.rect(
                surface, color, (bar_x, bar_y, bar_width * stamina_percent, bar_height)
            )

            # Stamina text
            if font:
                stamina_text = font.render(
                    f"{int(stamina_percent * 100)}%", True, (255, 255, 255)
                )
                surface.blit(
                    stamina_text,
                    (
                        bar_x + bar_width // 2 - stamina_text.get_width() // 2,
                        bar_y - 12,
                    ),
                )

        # === WANDERING INDICATOR ===
        if self.state == "wandering" and font:
            wander_text = font.render("?", True, (150, 150, 150))
            surface.blit(
                wander_text,
                (
                    int(self.x) - wander_text.get_width() // 2,
                    int(self.y) - TILE_SIZE // 2 - 25,
                ),
            )

    def caught(self):
        self.alive = False
        self.state = "caught"
        self.moving = False
        self.path = []
        print(f"{self.name} was caught!")

    def _is_valid_step(self, tile, rain_active=False):
        if tile is None:
            return False
        if tile.type in (TILE_WATER, TILE_STONE, TILE_SNOW_STONE):
            return False
        return True

    def _can_step(self, grid, col, row):
        """Override: animal cannot step on water, stone, snow_stone."""
        # FIXED: Add boundary check first
        if not grid or col < 0 or col >= grid.cols or row < 0 or row >= grid.rows:
            return False
        tile = grid.get(col, row)
        rain_active = (
            getattr(self, "season_mgr", None) is not None
            and self.season_mgr.rain_active
        )
        return self._is_valid_step(tile, rain_active)

    def _nearest_valid_tile(self, grid, col, row):
        # FIXED: Clamp initial position to grid bounds
        if grid:
            col = max(0, min(grid.cols - 1, col))
            row = max(0, min(grid.rows - 1, row))

        start = grid.get(col, row)
        rain_active = (
            getattr(self, "season_mgr", None) is not None
            and self.season_mgr.rain_active
        )
        if start and self._is_valid_step(start, rain_active):
            return col, row

        for radius in range(1, 6):
            for dc in range(-radius, radius + 1):
                for dr in range(-radius, radius + 1):
                    if abs(dc) + abs(dr) != radius:
                        continue
                    nc = col + dc
                    nr = row + dr
                    # FIXED: Check bounds
                    if grid and (
                        nc < 0 or nc >= grid.cols or nr < 0 or nr >= grid.rows
                    ):
                        continue
                    if self._is_valid_step(grid.get(nc, nr)):
                        return nc, nr

        return col, row

    def respawn(self, col, row, grid=None):
        if grid is not None:
            col, row = self._nearest_valid_tile(grid, col, row)

        self.alive = True
        self.col = col
        self.row = row
        self.crops_eaten = 0
        self.recent_crop_damage_timer = 0
        from utils.helpers import tile_center

        cx, cy = tile_center(col, row)
        self.x = float(cx)
        self.y = float(cy)
        self.state = "hungry"  # Changed from "idle" to "hungry"
        self.path = []
        self.path_idx = 0
        self.moving = False
        self._ate_this_tile = False
        self.replan_cd = 0
        self.stamina = self.STAMINA_MAX
        print(f"{self.name} respawned at ({col}, {row})")

    def _plan_wander(self, grid):
        """Wander using _is_valid_step"""
        if not grid:
            return False
        for _ in range(5):
            nc = self.col + random.randint(-3, 3)
            nr = self.row + random.randint(-3, 3)
            # FIXED: Clamp to grid bounds
            nc = max(0, min(grid.cols - 1, nc))
            nr = max(0, min(grid.rows - 1, nr))
            t = grid.get(nc, nr)
            rain_active = (
                getattr(self, "season_mgr", None) is not None
                and self.season_mgr.rain_active
            )
            if not self._is_valid_step(t, rain_active):
                continue

            result = astar(
                grid,
                (self.col, self.row),
                (nc, nr),
                cost_dict=ANIMAL_COSTS,
                agent_type="Animal",
                rain_active=rain_active,
            )
            if result.path:
                self.set_path(result.path)
                return True

        return False

    def ensure_valid_position(self, grid):
        if not grid:
            return
        # FIXED: First clamp to grid bounds
        self.col = max(0, min(grid.cols - 1, self.col))
        self.row = max(0, min(grid.rows - 1, self.row))

        current_tile = grid.get(self.col, self.row)
        if current_tile and self._is_valid_step(current_tile):
            return

        nc, nr = self._nearest_valid_tile(grid, self.col, self.row)
        self.col, self.row = nc, nr
        cx, cy = tile_center(self.col, self.row)
        self.x = float(cx)
        self.y = float(cy)
        self.path = []
        self.path_idx = 0
        self.moving = False

    def _pick_target(self, grid, agents):
        if not grid:
            return None
        guard = next((a for a in agents if a.__class__.__name__ == "Guard"), None)

        best_score = -1
        best_tile = None

        for c, r in grid.crop_tiles():
            tile = grid.get(c, r)
            if tile is None or tile.crop == CROP_NONE:
                continue
            value = CROP_VALUE[tile.crop] * self.w_crop_value
            dist = manhattan((self.col, self.row), (c, r)) + 1

            guard_penalty = 0
            if guard:
                gd = manhattan((c, r), (guard.col, guard.row)) + 1
                guard_penalty = self.w_guard_avoid * (10 / gd)

            score = (value / dist) - guard_penalty
            if score > best_score:
                best_score = score
                best_tile = (c, r)

        return best_tile

    def _eat(self, grid):
        """Eat only when fully arrived at tile (not mid-movement)."""
        if self.moving or not grid:
            return
        tile = grid.get(self.col, self.row)
        if tile and tile.crop != CROP_NONE:
            crop_name = CROP_NAMES[tile.crop]

            if not self._ate_this_tile:
                if self.animal_type == "rabbit":
                    # Rabbit eats: reduces crop stage by 1, doesn't destroy
                    if tile.crop_stage > 0:
                        tile.crop_stage -= 1
                        self.crops_eaten += 1
                        self.recent_crop_damage_timer = 8 * FPS
                        self.score += CROP_VALUE[tile.crop]
                        print(
                            f"🐰 Rabbit nibbled {crop_name} (stage now {tile.crop_stage})! Score: {self.score}"
                        )
                        self._ate_this_tile = True
                        if tile.crop_stage <= 0:
                            tile.crop = CROP_NONE
                            tile.crop_stage = 0
                            print(f"🐰 Rabbit fully consumed {crop_name}!")
                else:  # Fox
                    # Fox destroys: removes crop entirely (like bear)
                    self.crops_eaten += 1
                    self.recent_crop_damage_timer = 8 * FPS
                    self.score += CROP_VALUE[tile.crop] * max(1, tile.crop_stage)
                    print(f"🦊 Fox destroyed {crop_name}! Score: {self.score}")
                    tile.crop = CROP_NONE
                    tile.crop_stage = 0
                    self._ate_this_tile = True
        else:
            self._ate_this_tile = False

    def _wander(self, grid):
        """Move to a random nearby tile that the animal can traverse, using full grid bounds."""
        if not grid:
            return False
        for _ in range(15):
            nc = self.col + random.randint(-4, 4)
            nr = self.row + random.randint(-4, 4)
            # FIXED: Clamp to grid bounds
            nc = max(0, min(grid.cols - 1, nc))
            nr = max(0, min(grid.rows - 1, nr))
            t = grid.get(nc, nr)
            rain_active = (
                getattr(self, "season_mgr", None) is not None
                and self.season_mgr.rain_active
            )
            if not self._is_valid_step(t, rain_active):
                continue
            if (nc, nr) != (self.col, self.row):
                result = astar(
                    grid,
                    (self.col, self.row),
                    (nc, nr),
                    cost_dict=ANIMAL_COSTS,
                    agent_type="Animal",
                    rain_active=rain_active,
                )
                if result.path:
                    self.set_path(result.path, result.explored)
                    return True
        return False

    def _flee_from_guard(self, grid, guard):
        """Move away from the guard, using full grid bounds."""
        if not guard or not grid:
            return
        # Find direction away from guard
        dx = self.col - guard.col
        dy = self.row - guard.row
        # Normalize and extend
        dist = max(1, abs(dx) + abs(dy))
        target_col = self.col + int(dx / dist * 5)
        target_row = self.row + int(dy / dist * 5)
        # FIXED: Clamp to full grid bounds
        target_col = max(0, min(grid.cols - 1, target_col))
        target_row = max(0, min(grid.rows - 1, target_row))
        # Try to path to that tile
        rain_active = (
            getattr(self, "season_mgr", None) is not None
            and self.season_mgr.rain_active
        )
        result = astar(
            grid,
            (self.col, self.row),
            (target_col, target_row),
            cost_dict=ANIMAL_COSTS,
            agent_type="Animal",
            rain_active=rain_active,
        )
        if result.path:
            self.set_path(result.path, result.explored)
        else:
            # Fallback to wander
            self._wander(grid)

    def update(self, grid, agents, season_mgr=None):
        if season_mgr:
            self.season_mgr = season_mgr
        if not self.alive or not grid:
            return
        self.ensure_valid_position(grid)
        super().update(grid, agents, season_mgr)
        self.replan_cd = max(0, self.replan_cd - 1)
        self.recent_crop_damage_timer = max(0, self.recent_crop_damage_timer - 1)

        # Update color based on state
        self.color = self.get_color()
        self._eat(grid)

        # Check for guard proximity
        guard = next((a for a in agents if a.__class__.__name__ == "Guard"), None)
        if guard:
            dist_to_guard = manhattan((self.col, self.row), (guard.col, guard.row))
            if dist_to_guard <= self.FLEE_DISTANCE:
                if self.state != "scared":
                    print(f"🟡 {self.name} is SCARED! Running from guard!")
                self.state = "scared"
                self.stamina = max(0, self.stamina - self.STAMINA_DRAIN)
                if self.stamina == 0:
                    self.speed = 1.0  # Slow down when tired
                    print(f"💨 {self.name} is exhausted! Slowing down...")
                else:
                    self.speed = 2.2  # Speed up when scared
            else:
                if self.state == "scared":
                    print(f"✅ {self.name} is no longer scared!")
                self.state = "hungry"
                self.stamina = min(self.STAMINA_MAX, self.stamina + 1)  # Recover
                self.speed = 1.7 if self.animal_type == "rabbit" else 1.6

        # Only replan when not moving OR cooldown expired
        if self.moving:
            return

        # Reset eat flag when starting a new move
        self._ate_this_tile = False

        if self.replan_cd > 0:
            return

        if self.state == "scared":
            # Flee from guard
            self._flee_from_guard(grid, guard)
            self.replan_cd = 5  # More frequent when scared
        elif self.state == "hungry":
            target = self._pick_target(grid, agents)
            if target:
                rain_active = (
                    getattr(self, "season_mgr", None) is not None
                    and self.season_mgr.rain_active
                )
                result = astar(
                    grid,
                    (self.col, self.row),
                    target,
                    cost_dict=ANIMAL_COSTS,
                    agent_type="Animal",
                    rain_active=rain_active,
                )
                if result.path:
                    self.set_path(result.path, result.explored)
                    self.replan_cd = 60
                else:
                    self.state = "wandering"
                if not result.path:
                    self.state = "wandering"
                    self._plan_wander(grid)
                    self.replan_cd = 45
            else:
                self.state = "wandering"
                self._plan_wander(grid)
                self.replan_cd = 90
        else:  # wandering
            self._plan_wander(grid)
            self.replan_cd = 45
