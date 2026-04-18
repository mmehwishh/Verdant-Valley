"""
CSP Farm Layout Planner - Fixed for better crop placement
"""

import random
from utils.constants import *
from utils.helpers import manhattan


class CSPSolver:
    def __init__(self, grid):
        self.grid = grid
        self.vars = grid.field_tiles()
        self.water = grid.water_sources()
        self.assign = {}
        self.log = []
        self.requested_counts = self._default_counts()
        self.mode = "manual"

        print(f"Water sources found: {len(self.water)}")
        print(f"Field tiles found: {len(self.vars)}")

        # Find field boundaries
        if self.vars:
            cols = [c for c, r in self.vars]
            rows = [r for c, r in self.vars]
            self.min_c, self.max_c = min(cols), max(cols)
            self.min_r, self.max_r = min(rows), max(rows)
        else:
            self.min_c = self.max_c = self.min_r = self.max_r = 0

    def _default_counts(self):
        total_fields = len(self.vars)
        target_planted = max(1, int(total_fields * 0.4))
        sunflower = target_planted // 4
        corn = target_planted // 3
        wheat = max(0, target_planted - sunflower - corn)
        return {
            CROP_WHEAT: wheat,
            CROP_SUNFLOWER: sunflower,
            CROP_CORN: corn,
            CROP_TOMATO: 0,
            CROP_CARROT: 0,
            CROP_POTATO: 0,
        }

    def available_field_count(self):
        return len(self.vars)

    def get_requested_counts(self):
        return dict(self.requested_counts)

    def set_mode(self, mode):
        if mode not in ("auto", "manual"):
            raise ValueError(f"Unsupported CSP mode: {mode}")
        self.mode = mode

    def get_mode(self):
        return self.mode

    def set_requested_counts(self, counts):
        normalized = {
            CROP_WHEAT: max(0, int(counts.get(CROP_WHEAT, 0))),
            CROP_SUNFLOWER: max(0, int(counts.get(CROP_SUNFLOWER, 0))),
            CROP_CORN: max(0, int(counts.get(CROP_CORN, 0))),
            CROP_TOMATO: max(0, int(counts.get(CROP_TOMATO, 0))),
            CROP_CARROT: max(0, int(counts.get(CROP_CARROT, 0))),
            CROP_POTATO: max(0, int(counts.get(CROP_POTATO, 0))),
        }
        total = sum(normalized.values())
        field_count = self.available_field_count()
        if total > field_count:
            raise ValueError(
                f"Requested {total} crops but only {field_count} field tiles are available."
            )
        self.requested_counts = normalized

    def refresh_grid_context(self):
        self.vars = self.grid.field_tiles()
        self.water = self.grid.water_sources()

        if self.vars:
            cols = [c for c, r in self.vars]
            rows = [r for c, r in self.vars]
            self.min_c, self.max_c = min(cols), max(cols)
            self.min_r, self.max_r = min(rows), max(rows)
        else:
            self.min_c = self.max_c = self.min_r = self.max_r = 0

    def _is_edge(self, col, row):
        return (
            col == self.min_c
            or col == self.max_c
            or row == self.min_r
            or row == self.max_r
        )

    def _near_water(self, col, row, radius=4):
        # Expanded radius to 4 for better coverage
        for wc, wr in self.water:
            if manhattan((col, row), (wc, wr)) <= radius:
                return True
        return False

    def _is_available(self, pos):
        return self.assign.get(pos, CROP_NONE) == CROP_NONE

    def _has_adjacent_sunflower(self, col, row):
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if self.assign.get((col + dc, row + dr)) == CROP_SUNFLOWER:
                return True
        return False

    def _assign_crop(self, positions, crop, limit):
        placed = 0
        for col, row in positions:
            if placed >= limit:
                break
            if not self._is_available((col, row)):
                continue
            if crop == CROP_SUNFLOWER and self._has_adjacent_sunflower(col, row):
                continue
            self.assign[(col, row)] = crop
            self.log.append((col, row, crop, "assign"))
            placed += 1
            print(f"Placed {CROP_NAMES[crop]} at ({col},{row})")
        return placed

    def _assign_crop_relaxed(self, positions, crop, limit):
        placed = 0
        for col, row in positions:
            if placed >= limit:
                break
            if not self._is_available((col, row)):
                continue
            self.assign[(col, row)] = crop
            self.log.append((col, row, crop, "assign"))
            placed += 1
            print(f"Placed {CROP_NAMES[crop]} at ({col},{row})")
        return placed

    def _solve_auto(self):
        print(f"Solving CSP for {len(self.vars)} field tiles...")

        for var in self.vars:
            self.assign[var] = CROP_NONE

        target_planted = max(1, int(len(self.vars) * 0.4))
        planted = 0

        print(f"Target planted crops: {target_planted}")

        edge_tiles = [v for v in self.vars if self._is_edge(v[0], v[1])]
        inner_tiles = [v for v in self.vars if not self._is_edge(v[0], v[1])]

        print(f"Edge tiles: {len(edge_tiles)}, Inner tiles: {len(inner_tiles)}")

        for col, row in edge_tiles:
            if planted >= target_planted:
                break
            near_water = self._near_water(col, row)
            if near_water or random.random() > 0.3:
                adjacent_free = True
                for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if self.assign.get((col + dc, row + dr)) == CROP_SUNFLOWER:
                        adjacent_free = False
                        break
                if adjacent_free and random.random() > 0.5:
                    self.assign[(col, row)] = CROP_SUNFLOWER
                    self.log.append((col, row, CROP_SUNFLOWER, "assign"))
                    planted += 1
                    print(
                        f"Planted Sunflower at ({col},{row}) - {planted}/{target_planted}"
                    )

        all_tiles = edge_tiles + inner_tiles
        random.shuffle(all_tiles)

        for col, row in all_tiles:
            if planted >= target_planted:
                break
            if self.assign[(col, row)] == CROP_NONE and random.random() > 0.3:
                if self._is_edge(col, row):
                    crop = random.choice([CROP_CORN, CROP_SUNFLOWER])
                else:
                    crop = random.choice([CROP_WHEAT, CROP_CORN, CROP_WHEAT])

                self.assign[(col, row)] = crop
                self.log.append((col, row, crop, "assign"))
                planted += 1
                print(
                    f"Planted {CROP_NAMES[crop]} at ({col},{row}) - {planted}/{target_planted}"
                )

        if planted < target_planted:
            print(f"Need {target_planted - planted} more crops, final pass...")
            for col, row in all_tiles:
                if planted >= target_planted:
                    break
                if self.assign[(col, row)] == CROP_NONE:
                    crop = random.choice([CROP_WHEAT, CROP_CORN])
                    self.assign[(col, row)] = crop
                    self.log.append((col, row, crop, "assign"))
                    planted += 1

        for (col, row), crop in self.assign.items():
            if crop != CROP_NONE:
                self.log.append((col, row, crop, "final"))

        print(f"CSP Complete: Planted {planted} crops (target: {target_planted})")
        return True

    def solve(self, requested_counts=None):
        """Generate a grid using either auto mode or user-selected crop counts."""
        self.refresh_grid_context()
        if requested_counts is not None:
            self.set_requested_counts(requested_counts)

        self.assign = {var: CROP_NONE for var in self.vars}
        self.log = []

        if self.mode == "auto":
            return self._solve_auto()

        requested = self.get_requested_counts()
        total_requested = sum(requested.values())

        print(f"Solving CSP for {len(self.vars)} field tiles...")
        print(
            "Requested crops: "
            f"Wheat={requested[CROP_WHEAT]}, "
            f"Sunflower={requested[CROP_SUNFLOWER]}, "
            f"Corn={requested[CROP_CORN]}, "
            f"Tomato={requested[CROP_TOMATO]}, "
            f"Carrot={requested[CROP_CARROT]}, "
            f"Potato={requested[CROP_POTATO]}"
        )

        edge_tiles = [v for v in self.vars if self._is_edge(v[0], v[1])]
        inner_tiles = [v for v in self.vars if not self._is_edge(v[0], v[1])]

        random.shuffle(edge_tiles)
        random.shuffle(inner_tiles)

        near_water_edge = [v for v in edge_tiles if self._near_water(v[0], v[1])]
        dry_edge = [v for v in edge_tiles if v not in near_water_edge]
        near_water_inner = [v for v in inner_tiles if self._near_water(v[0], v[1])]
        dry_inner = [v for v in inner_tiles if v not in near_water_inner]

        sunflower_target = requested[CROP_SUNFLOWER]
        sunflower_placed = 0

        sunflower_placed += self._assign_crop(
            near_water_edge, CROP_SUNFLOWER, sunflower_target - sunflower_placed
        )
        if sunflower_placed < sunflower_target:
            sunflower_placed += self._assign_crop(
                dry_edge, CROP_SUNFLOWER, sunflower_target - sunflower_placed
            )
        if sunflower_placed < sunflower_target:
            sunflower_placed += self._assign_crop(
                near_water_inner, CROP_SUNFLOWER, sunflower_target - sunflower_placed
            )
        if sunflower_placed < sunflower_target:
            sunflower_placed += self._assign_crop(
                dry_inner, CROP_SUNFLOWER, sunflower_target - sunflower_placed
            )
        if sunflower_placed < sunflower_target:
            remaining = [v for v in self.vars if self._is_available(v)]
            random.shuffle(remaining)
            sunflower_placed += self._assign_crop_relaxed(
                remaining,
                CROP_SUNFLOWER,
                sunflower_target - sunflower_placed,
            )

        corn_target = requested[CROP_CORN]
        corn_candidates = near_water_inner + near_water_edge + dry_inner + dry_edge
        corn_placed = self._assign_crop(
            corn_candidates[: corn_target * 3], CROP_CORN, corn_target
        )

        wheat_target = requested[CROP_WHEAT]
        wheat_candidates = [v for v in edge_tiles + inner_tiles if self._is_available(v)]
        random.shuffle(wheat_candidates)
        wheat_placed = self._assign_crop(
            wheat_candidates[: wheat_target * 3], CROP_WHEAT, wheat_target
        )

        # Place tomatoes (prefer near water, edges)
        tomato_target = requested[CROP_TOMATO]
        tomato_candidates = near_water_edge + near_water_inner + dry_edge + dry_inner
        tomato_placed = self._assign_crop(
            tomato_candidates[: tomato_target * 3], CROP_TOMATO, tomato_target
        )

        # Place carrots (versatile, anywhere)
        carrot_target = requested[CROP_CARROT]
        carrot_candidates = [v for v in edge_tiles + inner_tiles if self._is_available(v)]
        random.shuffle(carrot_candidates)
        carrot_placed = self._assign_crop(
            carrot_candidates[: carrot_target * 3], CROP_CARROT, carrot_target
        )

        # Place potatoes (prefer dry areas, inner tiles)
        potato_target = requested[CROP_POTATO]
        potato_candidates = dry_inner + dry_edge + near_water_inner + near_water_edge
        potato_placed = self._assign_crop(
            potato_candidates[: potato_target * 3], CROP_POTATO, potato_target
        )

        if corn_placed < corn_target:
            remaining = [v for v in self.vars if self._is_available(v)]
            random.shuffle(remaining)
            corn_placed += self._assign_crop(
                remaining[: (corn_target - corn_placed) * 3],
                CROP_CORN,
                corn_target - corn_placed,
            )

        if wheat_placed < wheat_target:
            remaining = [v for v in self.vars if self._is_available(v)]
            random.shuffle(remaining)
            wheat_placed += self._assign_crop(
                remaining[: (wheat_target - wheat_placed) * 3],
                CROP_WHEAT,
                wheat_target - wheat_placed,
            )

        if tomato_placed < tomato_target:
            remaining = [v for v in self.vars if self._is_available(v)]
            random.shuffle(remaining)
            tomato_placed += self._assign_crop(
                remaining[: (tomato_target - tomato_placed) * 3],
                CROP_TOMATO,
                tomato_target - tomato_placed,
            )

        if carrot_placed < carrot_target:
            remaining = [v for v in self.vars if self._is_available(v)]
            random.shuffle(remaining)
            carrot_placed += self._assign_crop(
                remaining[: (carrot_target - carrot_placed) * 3],
                CROP_CARROT,
                carrot_target - carrot_placed,
            )

        if potato_placed < potato_target:
            remaining = [v for v in self.vars if self._is_available(v)]
            random.shuffle(remaining)
            potato_placed += self._assign_crop(
                remaining[: (potato_target - potato_placed) * 3],
                CROP_POTATO,
                potato_target - potato_placed,
            )

        placed_counts = {
            CROP_WHEAT: 0,
            CROP_SUNFLOWER: 0,
            CROP_CORN: 0,
            CROP_TOMATO: 0,
            CROP_CARROT: 0,
            CROP_POTATO: 0,
        }
        for crop in self.assign.values():
            if crop in placed_counts:
                placed_counts[crop] += 1

        for (col, row), crop in self.assign.items():
            if crop != CROP_NONE:
                self.log.append((col, row, crop, "final"))

        planted = sum(placed_counts.values())
        print(f"CSP Complete: Planted {planted}/{total_requested} requested crops")
        return planted == total_requested

    def apply_to_grid(self):
        """Write the solved assignment back to the grid tiles."""
        for col in range(self.grid.cols):
            for row in range(self.grid.rows):
                self.grid.tiles[col][row].crop = CROP_NONE
                self.grid.tiles[col][row].crop_stage = 0

        for (col, row), crop in self.assign.items():
            if 0 <= col < self.grid.cols and 0 <= row < self.grid.rows:
                self.grid.tiles[col][row].crop = crop
                if crop != CROP_NONE:
                    self.grid.tiles[col][row].crop_stage = random.randint(1, 2)
