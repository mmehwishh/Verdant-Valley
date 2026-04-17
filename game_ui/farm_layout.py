import pygame
from utils.constants import *


class FarmUI:
    """Handles all farm decorations (house, trees, fence, animals, bridges)"""

    def __init__(self, grid):
        self.grid = grid
        self.sprites = {}
        self.decorations = []
        self.animals = []
        self.load_sprites()
        self.setup_farm()

    def load_sprites(self):
        """Load all farm sprites"""

        # HOUSE
        try:
            img = pygame.image.load("assets/farm/house.png").convert_alpha()
            self.sprites["house"] = pygame.transform.scale(img, (300, 330))
            print("House loaded")
        except:
            pass

        # PATH TILE
        try:
            img = pygame.image.load("assets/tiles/Path_Tile.png").convert_alpha()
            self.sprites["path"] = pygame.transform.scale(img, (220, 220))
            print("Path tile loaded")
        except:
            pass

        # CLIFF TILE
        try:
            img = pygame.image.load("assets/tiles/Cliff_Tile.png").convert_alpha()
            self.sprites["cliff"] = pygame.transform.scale(img, (250, 200))
            print("Cliff tile loaded")
        except:
            pass

        # TREES
        try:
            img = pygame.image.load("assets/farm/Oak_Tree.png").convert_alpha()
            self.sprites["big_tree"] = pygame.transform.scale(img, (100, 120))
            print("Big tree loaded")
        except:
            pass

        # Small tree for grid (normal size)
        try:
            img = pygame.image.load("assets/farm/Oak_Tree_Small.png").convert_alpha()
            self.sprites["small_tree"] = pygame.transform.scale(img, (140, 140))
            print("Small tree loaded")
        except:
            pass

        # House trees (smaller version - separate sprite)
        try:
            img = pygame.image.load("assets/farm/Oak_Tree.png").convert_alpha()
            self.sprites["house_tree"] = pygame.transform.scale(img, (90, 110))
            print("House trees loaded")
        except:
            if "small_tree" in self.sprites:
                self.sprites["house_tree"] = pygame.transform.scale(
                    self.sprites["small_tree"], (90, 110)
                )
            else:
                self.sprites["house_tree"] = None

        # BRIDGE
        try:
            sheet = pygame.image.load("assets/farm/bridge.png").convert_alpha()
            self.sprites["bridge"] = []
            for i in range(7):
                piece = pygame.Surface((45, 30), pygame.SRCALPHA)
                piece.blit(sheet, (0, 0), (i * 70, 0, 64, 32))
                piece = pygame.transform.scale(piece, (100, 50))
                self.sprites["bridge"].append(piece)
            print(f"Bridge loaded: {len(self.sprites['bridge'])} pieces")
        except:
            print("Bridge not found")
            pass

        # FENCE
        try:
            sheet = pygame.image.load("assets/farm/fences.png").convert_alpha()
            self.sprites["fence"] = []
            for i in range(3):
                piece = pygame.Surface((48, 48), pygame.SRCALPHA)
                piece.blit(sheet, (0, 0), (i * 48, 0, 48, 48))
                piece = pygame.transform.scale(piece, (64, 64))
                self.sprites["fence"].append(piece)
            print(f"Fence loaded: {len(self.sprites['fence'])} pieces")
        except:
            pass

        # ANIMALS
        try:
            img = pygame.image.load("assets/farm/farm_animals/Cow.png").convert_alpha()
            self.sprites["cow"] = pygame.transform.scale(img, (120, 120))
            print("Cow loaded")
        except:
            pass

        try:
            img = pygame.image.load(
                "assets/farm/farm_animals/Sheep.png"
            ).convert_alpha()
            self.sprites["sheep"] = pygame.transform.scale(img, (110, 110))
            print("Sheep loaded")
        except:
            pass

        try:
            img = pygame.image.load(
                "assets/farm/farm_animals/Chicken.png"
            ).convert_alpha()
            self.sprites["chicken"] = pygame.transform.scale(img, (90, 90))
            print("Chicken loaded")
        except:
            pass

    def setup_farm(self):
        """Position all decorations"""
        GX, GY = GRID_OFFSET_X, GRID_OFFSET_Y
        GW, GH = GRID_COLS * TILE_SIZE, GRID_ROWS * TILE_SIZE
        SW, SH = SCREEN_W, SCREEN_H

        # ===== PATH AROUND HOUSE =====
        if self.sprites.get("path") and self.sprites.get("house"):
            path = self.sprites["path"]
            house_x = SW - 360
            house_y = 50
            path_x = house_x - 50
            path_y = house_y + 35
            self.decorations.insert(
                0, {"sprite": path, "x": path_x, "y": path_y, "name": "path"}
            )

        if self.sprites.get("cliff") and self.sprites.get("house"):
            cliff = self.sprites["cliff"]
            house_x = SW - 360
            house_y = 250
            cliff_x = house_x - 50
            cliff_y = house_y + 35
            self.decorations.insert(
                0, {"sprite": cliff, "x": cliff_x, "y": cliff_y, "name": "cliff"}
            )

        if self.sprites.get("path") and self.sprites.get("house"):
            path = self.sprites["path"]
            house_x = SW - 120
            house_y = 230
            path_x = house_x - 50
            path_y = house_y + 35
            self.decorations.insert(
                0, {"sprite": path, "x": path_x, "y": path_y, "name": "path"}
            )

        if self.sprites.get("cliff") and self.sprites.get("house"):
            cliff = self.sprites["cliff"]
            house_x = SW - 360
            house_y = 450
            cliff_x = house_x - 50
            cliff_y = house_y + 35
            self.decorations.insert(
                0, {"sprite": cliff, "x": cliff_x, "y": cliff_y, "name": "cliff"}
            )

        if self.sprites.get("path") and self.sprites.get("house"):
            path = self.sprites["path"]
            house_x = SW - 120
            house_y = 430
            path_x = house_x - 50
            path_y = house_y + 35
            self.decorations.insert(
                0, {"sprite": path, "x": path_x, "y": path_y, "name": "path"}
            )

        house_x = SW - 270
        house_y = 10
        house_width = 300
        house_height = 330

        # ===== TREES THAT WILL COVER THE TOP OF HOUSE (drawn AFTER house) =====
        if self.sprites.get("big_tree"):
            # Trees covering the top of house (roof area)
            trees_covering_house = [
                (house_x + 20, house_y - 15),  # Top-left covering roof
                (house_x + 80, house_y - 25),  # Top covering
                (house_x + 140, house_y - 30),  # Top-center covering
                (house_x + 200, house_y - 25),  # Top-right covering
                (house_x + 260, house_y - 15),  # Far right covering
                (house_x + 50, house_y - 40),  # Higher covering
                (house_x + 110, house_y - 45),  # Higher center
                (house_x + 170, house_y - 45),  # Higher center
                (house_x + 230, house_y - 35),  # Higher right
            ]

            for x, y in trees_covering_house:
                self.decorations.append(
                    {
                        "sprite": self.sprites["big_tree"],
                        "x": x,
                        "y": y,
                        "name": "tree_covering_house",
                    }
                )

        # ===== TREES AROUND HOUSE SIDES =====
        if self.sprites.get("house_tree"):
            side_tree_positions = [
                (house_x - 70, house_y + 40),  # Left of house
                (house_x + house_width + 10, house_y + 50),  # Right of house
                (house_x - 55, house_y + 140),  # Middle left
                (house_x + house_width + 15, house_y + 140),  # Middle right
                (house_x - 60, house_y + 230),  # Left-bottom
                (house_x + house_width + 10, house_y + 230),  # Right-bottom
            ]

            for x, y in side_tree_positions:
                self.decorations.append(
                    {
                        "sprite": self.sprites["house_tree"],
                        "x": x,
                        "y": y,
                        "name": "side_tree",
                    }
                )

        # ===== HOUSE (drawn BEFORE the covering trees) =====
        if self.sprites.get("house"):
            self.decorations.append(
                {
                    "sprite": self.sprites["house"],
                    "x": SW - 270,
                    "y": 10,
                    "name": "house",
                }
            )

        # ===== BRIDGES =====
        if self.sprites.get("bridge"):
            bridge_pieces = self.sprites["bridge"]
            bridge_rows = [1, 3, 5, 7, 9, 11, 13]
            bridge_offset = -55

            for bridge_row in bridge_rows:
                bridge_y = GY + (bridge_row * TILE_SIZE) - 25
                for i, piece in enumerate(bridge_pieces):
                    bridge_x = GX + (1 * TILE_SIZE) + bridge_offset + (i * 8)
                    self.decorations.append(
                        {
                            "sprite": piece,
                            "x": bridge_x,
                            "y": bridge_y,
                            "name": "bridge",
                        }
                    )

        # ===== FENCE ON WATER =====
        if self.sprites.get("fence"):
            fence_sprites = self.sprites["fence"]
            fence_offset = -45

            for row in range(GRID_ROWS):
                if row in [1, 3, 5, 7, 9, 11] or row + 1 in [1, 3, 5, 7, 9, 11]:
                    continue

                x0 = GX + (0 * TILE_SIZE) + fence_offset
                y0 = GY + (row * TILE_SIZE)
                fence0 = fence_sprites[row % len(fence_sprites)]
                self.decorations.append(
                    {"sprite": fence0, "x": x0, "y": y0, "name": "fence_water_left"}
                )

                x1 = GX + (1 * TILE_SIZE) + fence_offset
                y1 = GY + (row * TILE_SIZE)
                fence1 = fence_sprites[(row + 1) % len(fence_sprites)]
                self.decorations.append(
                    {"sprite": fence1, "x": x1, "y": y1, "name": "fence_water_right"}
                )

        # ===== TREES (top and bottom of screen) =====
        if self.sprites.get("small_tree"):
            for i in range(12):
                self.decorations.append(
                    {"sprite": self.sprites["small_tree"], "x": -15 + i * 70, "y": -15}
                )
                self.decorations.append(
                    {
                        "sprite": self.sprites["small_tree"],
                        "x": -15 + i * 70,
                        "y": SH - 90,
                    }
                )

        if self.sprites.get("big_tree"):
            for i in range(13):
                self.decorations.append(
                    {"sprite": self.sprites["big_tree"], "x": -25 + i * 70, "y": -10}
                )
                self.decorations.append(
                    {
                        "sprite": self.sprites["big_tree"],
                        "x": -25 + i * 70,
                        "y": SH - 90,
                    }
                )

        # ===== FENCE AROUND ANIMALS =====
        if self.sprites.get("fence"):
            fence = self.sprites["fence"][0]
            fx = SW - 400
            fy = SH - 440
            for i in range(8):
                self.decorations.append({"sprite": fence, "x": fx + i * 64, "y": fy})
                self.decorations.append(
                    {"sprite": fence, "x": fx + i * 64, "y": fy + 180}
                )
            for i in range(3):
                self.decorations.append({"sprite": fence, "x": fx, "y": fy + i * 64})
                self.decorations.append(
                    {"sprite": fence, "x": fx + 448, "y": fy + i * 64}
                )

        # ===== ANIMALS =====
        animal_start_x = SW - 350
        animal_start_y = SH - 375

        if self.sprites.get("cow"):
            self.animals.append(
                {
                    "sprite": self.sprites["cow"],
                    "x": animal_start_x + 20,
                    "y": animal_start_y + 10,
                }
            )

        if self.sprites.get("sheep"):
            self.animals.append(
                {
                    "sprite": self.sprites["sheep"],
                    "x": animal_start_x + 120,
                    "y": animal_start_y + 15,
                }
            )

        if self.sprites.get("chicken"):
            for i in range(2):
                self.animals.append(
                    {
                        "sprite": self.sprites["chicken"],
                        "x": animal_start_x + 210 + i * 55,
                        "y": animal_start_y + 20,
                    }
                )

    def draw(self, surface):
        """Draw all decorations"""
        for d in self.decorations:
            if d.get("sprite"):
                surface.blit(d["sprite"], (d["x"], d["y"]))
        for a in self.animals:
            if a.get("sprite"):
                surface.blit(a["sprite"], (a["x"], a["y"]))
