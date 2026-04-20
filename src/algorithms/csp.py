"""
CSP Farm Layout Planner - Updated to use per-tile domains, flooded/muddy state,
and utility-based heuristics so the solver respects hard constraints (flooded
tiles => CROP_NONE) and prefers higher-utility tiles.
"""

import random
from utils.constants import *
from utils.helpers import manhattan


# Simple expected-value weights for heuristic ordering (tunable).
CROP_HEURISTIC_VALUE = {
    CROP_WHEAT: 1.0,
    CROP_SUNFLOWER: 0.9,
    CROP_CORN: 1.3,
    CROP_TOMATO: 1.1,
    CROP_CARROT: 0.8,
    CROP_POTATO: 0.85,
    CROP_NONE: 0.0,
}


class CSPSolver:

    def set_requested_counts(self, requested_counts):
        """Set the requested crop counts for the solver."""
        self.requested_counts = requested_counts if requested_counts is not None else self._default_counts()
    def get_requested_counts(self):
        """Return the current requested crop counts dict."""
        return getattr(self, 'requested_counts', self._default_counts())
    def __init__(self, grid):
        self.grid = grid
        self.refresh_grid_context()
        self.assign = {}
        self.log = []
        self.requested_counts = self._default_counts()
        self.mode = "manual"

        print(f"Water sources found: {len(self.water)}")
        print(f"Field tiles found: {len(self.vars)}")

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

    def refresh_grid_context(self):
        """Pull fresh tile lists from the grid. Keep field tile coords even if temporarily pruned."""
        self.vars = self.grid.field_tiles()
        self.water = self.grid.water_sources()

        if self.vars:
            cols = [c for c, r in self.vars]
            rows = [r for c, r in self.vars]
            self.min_c, self.max_c = min(cols), max(cols)
            self.min_r, self.max_r = min(rows), max(rows)
        else:
            self.min_c = self.max_c = self.min_r = self.max_r = 0

    # ------------------------------
    # Helpers to access tile / domain
    # ------------------------------
    def _tile(self, pos):
        col, row = pos
        return self.grid.get(col, row)

    def _tile_allows(self, pos, crop):
        """Return True when the tile's current domain allows planting 'crop'."""
        tile = self._tile(pos)
        if tile is None:
            return False
        # If tile.domain explicitly contains the crop, it's allowed.
        # Domains are maintained by grid (season, flood, night, etc.)
        return crop in getattr(tile, "domain", [CROP_NONE])

    def _is_available(self, pos):
        """Available means not yet assigned in self.assign AND the tile still allows planting (not hard-flooded/frozen)."""
        assigned = self.assign.get(pos, CROP_NONE)
        if assigned != CROP_NONE:
            return False
        tile = self._tile(pos)
        if not tile:
            return False
        # Frozen tiles cannot be planted
        if getattr(tile, "frozen", False):
            return False
        # If tile domain is exactly [CROP_NONE], it's hard-constrained (flooded/blocked)
        domain = getattr(tile, "domain", [CROP_NONE])
        if len(domain) == 1 and domain[0] == CROP_NONE:
            return False
        return True

    def _is_edge(self, col, row):
        return (
            col == self.min_c
            or col == self.max_c
            or row == self.min_r
            or row == self.max_r
        )

    def _near_water(self, col, row, radius=4):
        # Expanded radius to 4 for better coverage (unchanged)
        for wc, wr in self.water:
            if manhattan((col, row), (wc, wr)) <= radius:
                return True
        return False

    def _has_adjacent_sunflower(self, col, row):
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if self.assign.get((col + dc, row + dr)) == CROP_SUNFLOWER:
                return True
        return False

    # ------------------------------
    # Candidate ordering utilities
    # ------------------------------
    def _score_tile_for_crop(self, pos, crop):
        """
        Compute a score combining:
         - tile.utility (0..1) (higher is better),
         - crop heuristic value (higher is better),
         - small bonus if near water for water-loving crops.
        """
        tile = self._tile(pos)
        if not tile:
            return -9999
        base = CROP_HEURISTIC_VALUE.get(crop, 0.0)
        utility = getattr(tile, "utility", 0.5)
        score = base * utility
        # slight near-water boost for some crops (corn, tomato)
        if crop in (CROP_CORN, CROP_TOMATO) and self._near_water(pos[0], pos[1], radius=3):
            score *= 1.08
        # penalize muddy tiles slightly for all crops (muddy already reduces tile.utility but add small penalty)
        if getattr(tile, "muddy", False):
            score *= 0.85
        return score

    def _ordered_candidates(self, positions, crop, limit=None):
        """
        Return candidate positions ordered by heuristic score and filtered by tile domains.
        If `limit` provided, return at most limit best positions.
        """
        filtered = [p for p in positions if self._is_available(p) and self._tile_allows(p, crop)]
        # sort by score descending
        filtered.sort(key=lambda p: self._score_tile_for_crop(p, crop), reverse=True)
        if limit:
            return filtered[:limit]
        return filtered

    # ------------------------------
    # Assignment routines
    # ------------------------------
    def _assign_crop(self, positions, crop, limit):
        """Assign crop to up to `limit` best positions from positions (which is a list of coords)."""
        placed = 0
        if limit <= 0:
            return 0

        candidates = self._ordered_candidates(positions, crop, limit * 3)
        for col, row in candidates:
            if placed >= limit:
                break
            if not self._is_available((col, row)):
                continue
            if crop == CROP_SUNFLOWER and self._has_adjacent_sunflower(col, row):
                continue
            # Final safety check: tile still allows this crop
            if not self._tile_allows((col, row), crop):
                continue
            self.assign[(col, row)] = crop
            self.log.append((col, row, crop, "assign"))
            placed += 1
            print(f"Placed {CROP_NAMES[crop]} at ({col},{row})")
        return placed

    def _assign_crop_relaxed(self, positions, crop, limit):
        """Relaxed assignment ignores sunflower adjacency constraint but still respects domains/utility."""
        placed = 0
        if limit <= 0:
            return 0

        candidates = self._ordered_candidates(positions, crop, limit * 3)
        for col, row in candidates:
            if placed >= limit:
                break
            if not self._is_available((col, row)):
                continue
            if not self._tile_allows((col, row), crop):
                continue
            self.assign[(col, row)] = crop
            self.log.append((col, row, crop, "assign"))
            placed += 1
            print(f"Placed {CROP_NAMES[crop]} at ({col},{row})")
        return placed

    # ------------------------------
    # Auto solver (heuristic-driven)
    # ------------------------------
    def _solve_auto(self):
        print(f"Solving CSP (auto) for {len(self.vars)} field tiles...")

        # Initialize assignment map but respect current tile domains: if tile domain == [CROP_NONE], we keep it NONE
        for var in self.vars:
            # if tile permanently blocked, keep NONE; otherwise start unassigned with CROP_NONE
            tile = self._tile(var)
            if tile and len(getattr(tile, "domain", [CROP_NONE])) == 1 and tile.domain[0] == CROP_NONE:
                self.assign[var] = CROP_NONE
            else:
                self.assign[var] = CROP_NONE

        target_planted = max(1, int(len(self.vars) * 0.4))
        planted = 0

        print(f"Target planted crops: {target_planted}")

        edge_tiles = [v for v in self.vars if self._is_edge(v[0], v[1])]
        inner_tiles = [v for v in self.vars if not self._is_edge(v[0], v[1])]

        print(f"Edge tiles: {len(edge_tiles)}, Inner tiles: {len(inner_tiles)}")

        # Prefer sunflowers on edge tiles near water or high-utility tiles
        sf_candidates = [v for v in edge_tiles if self._is_available(v) and self._tile_allows(v, CROP_SUNFLOWER)]
        # order by score
        sf_candidates.sort(key=lambda p: self._score_tile_for_crop(p, CROP_SUNFLOWER), reverse=True)

        for col, row in sf_candidates:
            if planted >= target_planted:
                break
            if self._has_adjacent_sunflower(col, row):
                continue
            if random.random() > 0.35:  # keep some randomness
                self.assign[(col, row)] = CROP_SUNFLOWER
                self.log.append((col, row, CROP_SUNFLOWER, "assign"))
                planted += 1
                print(f"Planted Sunflower at ({col},{row}) - {planted}/{target_planted}")

        all_tiles = [v for v in edge_tiles + inner_tiles if self._is_available(v)]
        # Shuffle preserves randomness but we'll score when selecting
        random.shuffle(all_tiles)

        # Fill remaining by scoring tiles for best crop choice
        while planted < target_planted and any(self._is_available(v) for v in all_tiles):
            # produce candidate list of available tiles
            available = [v for v in all_tiles if self._is_available(v)]
            # for each available tile, compute best crop by score
            scored = []
            for v in available:
                # pick highest scoring crop that's allowed in the tile's domain
                tile = self._tile(v)
                domain = getattr(tile, "domain", [])
                best_crop = None
                best_score = -1.0
                for crop in domain:
                    if crop == CROP_NONE:
                        continue
                    score = self._score_tile_for_crop(v, crop)
                    if score > best_score:
                        best_score = score
                        best_crop = crop
                if best_crop is not None:
                    scored.append((v, best_crop, best_score))
            # sort by score descending
            scored.sort(key=lambda t: t[2], reverse=True)
            if not scored:
                break
            # assign top candidate
            pos, best_crop, _ = scored[0]
            if best_crop == CROP_SUNFLOWER and self._has_adjacent_sunflower(pos[0], pos[1]):
                # if sunflower adjacency blocks, fallback to next best
                if len(scored) > 1:
                    pos, best_crop, _ = scored[1]
                else:
                    break
            self.assign[pos] = best_crop
            self.log.append((pos[0], pos[1], best_crop, "assign"))
            planted += 1
            print(f"Planted {CROP_NAMES[best_crop]} at {pos} - {planted}/{target_planted}")

        # final fill pass if needed
        if planted < target_planted:
            print(f"Need {target_planted - planted} more crops, final pass...")
            remaining = [v for v in all_tiles if self._is_available(v)]
            # order remaining by tile.utility so higher quality tiles fill first
            remaining.sort(key=lambda p: getattr(self._tile(p), "utility", 0.5), reverse=True)
            for col, row in remaining:
                if planted >= target_planted:
                    break
                # choose any allowed crop by score
                tile = self._tile((col, row))
                domain = getattr(tile, "domain", [])
                choices = [c for c in domain if c != CROP_NONE]
                if not choices:
                    continue
                # pick best by heuristic
                choices.sort(key=lambda c: self._score_tile_for_crop((col, row), c), reverse=True)
                chosen = choices[0]
                if chosen == CROP_SUNFLOWER and self._has_adjacent_sunflower(col, row):
                    continue
                self.assign[(col, row)] = chosen
                self.log.append((col, row, chosen, "assign"))
                planted += 1
                print(f"Placed {CROP_NAMES[chosen]} at ({col},{row})")

        for (col, row), crop in list(self.assign.items()):
            if crop != CROP_NONE:
                self.log.append((col, row, crop, "final"))

        print(f"CSP Complete: Planted {planted} crops (target: {target_planted})")
        return True

    # ------------------------------
    # Public solve path (manual / requested)
    # ------------------------------
    def solve(self, requested_counts=None):
        """Generate a grid using either auto mode or user-selected crop counts."""
        self.refresh_grid_context()
        if requested_counts is not None:
            self.set_requested_counts(requested_counts)

        # Initialize assignments: respect tiles that are hard-blocked (domain == [CROP_NONE])
        self.assign = {}
        for var in self.vars:
            tile = self._tile(var)
            if tile and len(getattr(tile, "domain", [CROP_NONE])) == 1 and tile.domain[0] == CROP_NONE:
                self.assign[var] = CROP_NONE
            else:
                self.assign[var] = CROP_NONE

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

        # Partition based on near water and filter out hard-blocked tiles immediately
        near_water_edge = [v for v in edge_tiles if self._near_water(v[0], v[1]) and self._is_available(v)]
        dry_edge = [v for v in edge_tiles if v not in near_water_edge and self._is_available(v)]
        near_water_inner = [v for v in inner_tiles if self._near_water(v[0], v[1]) and self._is_available(v)]
        dry_inner = [v for v in inner_tiles if v not in near_water_inner and self._is_available(v)]

        # SUNFLOWER placement (preferred near water and edge) - domain aware
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

        # CORN placement - prefer near water but only where tile domain allows corn
        corn_target = requested[CROP_CORN]
        corn_candidates = [v for v in (near_water_inner + near_water_edge + dry_inner + dry_edge) if self._is_available(v) and self._tile_allows(v, CROP_CORN)]
        corn_placed = self._assign_crop(
            corn_candidates[: corn_target * 3], CROP_CORN, corn_target
        )

        # WHEAT placement
        wheat_target = requested[CROP_WHEAT]
        wheat_candidates = [v for v in edge_tiles + inner_tiles if self._is_available(v) and self._tile_allows(v, CROP_WHEAT)]
        random.shuffle(wheat_candidates)
        wheat_placed = self._assign_crop(
            wheat_candidates[: wheat_target * 3], CROP_WHEAT, wheat_target
        )

        # TOMATO placement (prefer near water)
        tomato_target = requested[CROP_TOMATO]
        tomato_candidates = [v for v in (near_water_edge + near_water_inner + dry_edge + dry_inner) if self._is_available(v) and self._tile_allows(v, CROP_TOMATO)]
        tomato_placed = self._assign_crop(
            tomato_candidates[: tomato_target * 3], CROP_TOMATO, tomato_target
        )

        # CARROT placement (versatile)
        carrot_target = requested[CROP_CARROT]
        carrot_candidates = [v for v in edge_tiles + inner_tiles if self._is_available(v) and self._tile_allows(v, CROP_CARROT)]
        random.shuffle(carrot_candidates)
        carrot_placed = self._assign_crop(
            carrot_candidates[: carrot_target * 3], CROP_CARROT, carrot_target
        )

        # POTATO placement (prefer dry areas)
        potato_target = requested[CROP_POTATO]
        potato_candidates = [v for v in (dry_inner + dry_edge + near_water_inner + near_water_edge) if self._is_available(v) and self._tile_allows(v, CROP_POTATO)]
        potato_placed = self._assign_crop(
            potato_candidates[: potato_target * 3], CROP_POTATO, potato_target
        )

        # Fallbacks to fill requested counts from remaining allowed tiles
        def _fill_remaining(crop, placed, target):
            if placed >= target:
                return placed
            remaining = [v for v in self.vars if self._is_available(v) and self._tile_allows(v, crop)]
            random.shuffle(remaining)
            return placed + self._assign_crop(remaining[: (target - placed) * 3], crop, target - placed)

        corn_placed = _fill_remaining(CROP_CORN, corn_placed, corn_target)
        wheat_placed = _fill_remaining(CROP_WHEAT, wheat_placed, wheat_target)
        tomato_placed = _fill_remaining(CROP_TOMATO, tomato_placed, tomato_target)
        carrot_placed = _fill_remaining(CROP_CARROT, carrot_placed, carrot_target)
        potato_placed = _fill_remaining(CROP_POTATO, potato_placed, potato_target)

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

        for (col, row), crop in list(self.assign.items()):
            if crop != CROP_NONE:
                self.log.append((col, row, crop, "final"))

        planted = sum(placed_counts.values())
        print(f"CSP Complete: Planted {planted}/{total_requested} requested crops")
        return planted == total_requested

    # ------------------------------
    # Apply assignment to the grid
    # ------------------------------
    def apply_to_grid(self):
        """Write the solved assignment back to the grid tiles. Respect per-tile domains."""
        # Clear all crops first
        for col in range(self.grid.cols):
            for row in range(self.grid.rows):
                self.grid.tiles[col][row].crop = CROP_NONE
                self.grid.tiles[col][row].crop_stage = 0

        for (col, row), crop in self.assign.items():
            if 0 <= col < self.grid.cols and 0 <= row < self.grid.rows:
                tile = self.grid.tiles[col][row]
                # Only apply crops allowed by the current tile domain
                if crop != CROP_NONE and (crop in getattr(tile, "domain", [CROP_NONE])):
                    tile.crop = crop
                    tile.crop_stage = random.randint(1, 2)
                else:
                    # Ensure blocked tiles remain NONE
                    tile.crop = CROP_NONE
                    tile.crop_stage = 0

    def set_mode(self, mode):
        if mode not in ("auto", "manual"):
            raise ValueError(f"Unsupported CSP mode: {mode}")
        self.mode = mode

    def get_mode(self):
        return self.mode

    def available_field_count(self):
        """Return the number of available field tiles."""
        return len(self.vars) if hasattr(self, 'vars') else 0