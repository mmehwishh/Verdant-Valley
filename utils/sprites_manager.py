"""
Sprite Manager - Handles both single sprites and sprite sheets
"""

import pygame
import os


class SpriteManager:
    def __init__(self):
        self.sprites = {}
        self.load_all_sprites()

    def load_all_sprites(self):
        """Load all farm sprites"""

        # ===== SINGLE SPRITES =====
        self.load_single_sprite("house", "assets/farm/house.png", (128, 128))
        self.load_single_sprite("oak_tree", "assets/farm/Oak_Tree.png", (64, 64))
        self.load_single_sprite(
            "oak_tree_small", "assets/farm/Oak_Tree_Small.png", (48, 48)
        )

        # ===== SPRITE SHEETS =====
        # Fence sprite sheet (assuming 3 fence pieces in a row)
        self.load_sprite_sheet("fence", "assets/farm/fence.png", 48, 48, 3, 1)

        # Bridge sprite sheet (assuming 3 bridge pieces)
        self.load_sprite_sheet("bridge", "assets/farm/bridge.png", 64, 32, 3, 1)

        # Outdoor decorations sprite sheet (4x4 grid of 32x32 sprites)
        self.load_sprite_sheet("decor", "assets/farm/Outdoor_Decor.png", 32, 32, 4, 4)

        print(f"✅ Loaded {len(self.sprites)} sprites")

    def load_single_sprite(self, name, path, size=None):
        """Load a single sprite image"""
        try:
            if os.path.exists(path):
                sprite = pygame.image.load(path).convert_alpha()
                if size:
                    sprite = pygame.transform.scale(sprite, size)
                self.sprites[name] = sprite
                print(f"  ✓ Loaded: {name}")
            else:
                print(f"  ✗ Not found: {path}")
        except Exception as e:
            print(f"  ✗ Error loading {name}: {e}")

    def load_sprite_sheet(self, name, path, sprite_w, sprite_h, cols, rows):
        """Load a sprite sheet and extract all sprites"""
        try:
            if os.path.exists(path):
                sheet = pygame.image.load(path).convert_alpha()
                sheet_w, sheet_h = sheet.get_size()

                sprites = []
                for row in range(rows):
                    for col in range(cols):
                        x = col * sprite_w
                        y = row * sprite_h

                        # Make sure we don't go out of bounds
                        if x + sprite_w <= sheet_w and y + sprite_h <= sheet_h:
                            sprite = pygame.Surface(
                                (sprite_w, sprite_h), pygame.SRCALPHA
                            )
                            sprite.blit(sheet, (0, 0), (x, y, sprite_w, sprite_h))
                            sprites.append(sprite)

                self.sprites[name] = sprites
                print(f"  ✓ Loaded sprite sheet: {name} ({len(sprites)} sprites)")
            else:
                print(f"  ✗ Not found: {path}")
        except Exception as e:
            print(f"  ✗ Error loading {name}: {e}")

    def get_sprite(self, name, index=0):
        """Get a sprite by name (index for sprite sheets)"""
        sprite = self.sprites.get(name)
        if isinstance(sprite, list):
            return sprite[index] if index < len(sprite) else sprite[0]
        return sprite

    def get_all_sprites(self, name):
        """Get all sprites from a sprite sheet"""
        return self.sprites.get(name, [])
