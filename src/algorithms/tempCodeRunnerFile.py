"""
CSP Farm Layout Planner

Uses per-tile domains, flooded/muddy state, and utility-based heuristics
so the solver respects hard constraints (flooded tiles => CROP_NONE)
and prefers higher-utility tiles.
"""

import random
import time
from utils.constants import *
from utils.helpers import manhattan


# Expected-value weights for heuristic ordering
CROP_HEURISTIC_VALUE = {
    CROP_WHEAT: 1.0,
    CROP_SUNFLOWER: 0.9,
    CROP_CORN: 1.3,
    CROP_TOMATO: 1.2,
    CROP_CARROT: 0.9,
    CROP_NONE: 0.0,
}


class CSPSolver:

    def set_requested_counts(self, requested_counts):
        """Set the requested crop counts for the solver."""
        self.requested_counts = (
            requested_counts if requested_counts is not None else self._default_counts()
        )

    def get_requested_counts(self):
        """Return the current requested crop counts dict."""
        return getattr(self, "requested_counts", self._default_counts())

    def __init__(self, grid):
        self.grid = grid
        self.refresh_grid_context()
        self.assign = {}
        self.log = []
        self.requested_counts = self._default_counts()
        self.mode = "manual"
        self.last_failure_reason = ""

        # Backtrack tracking for visualization
        self.backtrack_log = []  # Stores (col, row) of each backtrack
        self.domains = {}  # Stores current domains for each variable
        self._init_domains()  # Initialize domains
        
        # Timeout tracking
        self.solve_start_time = None
        self.solve_timeout_seconds = 5.0  # 5 second timeout
        self.timed_out = False

    def _init_domains(self):
        """Initialize domains for all variables."""
        for col, row in self.vars:
            self.domains[(col, row)] = self._base_domain_for_pos((col, row))

    def _base_domain_for_pos(self, pos):
        """Return the season-filtered base domain for a tile."""
        tile = self._tile(pos)
        if tile is None or tile.type != TILE_FIELD:
            return [CROP_NONE]

        base_domain = list(getattr(tile, "domain", []))
        if not base_domain:
            base_domain = [
                CROP_WHEAT,
                CROP_SUNFLOWER,
                CROP_CORN,
                CROP_TOMATO,
                CROP_CARROT,
                CROP_NONE,
            ]

        allowed_crops = set(self._get_allowed_crops_for_season())
        filtered = [crop for crop in base_domain if crop == CROP_NONE or crop in allowed_crops]
        if CROP_NONE not in filtered:
            filtered.append(CROP_NONE)
        return filtered

    def _default_counts(self):
        """Generate default crop counts based on total field tiles."""
        total_fields = len(self.vars)
        target_planted = max(1, int(total_fields * 0.4))
        sunflower = target_planted // 4
        corn = target_planted // 3
        tomato = target_planted // 5
        carrot = target_planted // 5
        wheat = max(0, target_planted - sunflower - corn - tomato - carrot)
        return {
            CROP_WHEAT: wheat,
            CROP_SUNFLOWER: sunflower,
            CROP_CORN: corn,
            CROP_TOMATO: tomato,
            CROP_CARROT: carrot,
        }

    def _check_timeout(self):
        """Check if solve operation has exceeded timeout."""
        if self.solve_start_time is None:
            return False
        elapsed = time.time() - self.solve_start_time
        if elapsed > self.solve_timeout_seconds:
            self.timed_out = True
            self.last_failure_reason = f"Solver timeout after {elapsed:.1f}s"
            return True
        return False

    def refresh_grid_context(self):
        """Pull fresh tile lists from the grid. Keep field tile coords even if temporarily pruned."""
        self.vars = self.grid.field_tiles()
        self.water = self.grid.water_sources()
        self._var_rank = {pos: idx for idx, pos in enumerate(sorted(self.vars))}

        if self.vars:
            cols = [c for c, r in self.vars]
            rows = [r for c, r in self.vars]
            self.min_c, self.max_c = min(cols), max(cols)
            self.min_r, self.max_r = min(rows), max(rows)
        else:
            self.min_c = self.max_c = self.min_r = self.max_r = 0

    # Tile and domain helpers

    def _tile(self, pos):
        """Get tile at position."""
        col, row = pos
        return self.grid.get(col, row)

    def _get_season(self):
        """Get current season index (0=Spring, 1=Summer, 2=Autumn, 3=Winter)."""
        if hasattr(self.grid, "season") and self.grid.season:
            return getattr(self.grid.season, "index", 0)
        return 0  # Default to Spring

    def _get_allowed_crops_for_season(self):
        """Return list of crops allowed in current season."""
        season = self._get_season()

        # Spring, Summer, Autumn - all crops allowed
        if season != 3:  # Not winter
            return [CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_TOMATO, CROP_CARROT]
        else:  # Winter - only corn and carrot
            return [CROP_CORN, CROP_CARROT]

    def _tile_allows(self, pos, crop):
        """Return True when the tile can plant this crop."""
        tile = self._tile(pos)
        if tile is None:
            return False
        if crop == CROP_NONE:
            return True
        if crop not in getattr(tile, "domain", [crop]):
            return False

        # Get allowed crops for current season
        allowed_crops = self._get_allowed_crops_for_season()

        # If crop is not allowed in this season, return False
        if crop not in allowed_crops:
            return False

        # For winter, Corn and Carrot are always allowed on field tiles
        season = self._get_season()
        if season == 3 and crop in (CROP_CORN, CROP_CARROT) and tile.type == TILE_FIELD:
            return True

        # For non-winter, check if tile is field or dirt
        if tile.type in (TILE_FIELD, TILE_DIRT):
            return True

        return False

    def _is_available(self, pos):
        """Available means not yet assigned and tile is plantable."""
        assigned = self.assign.get(pos, None)
        if assigned not in (None, CROP_NONE):
            return False

        tile = self._tile(pos)
        if not tile:
            return False

        # For winter, field tiles are always available for Corn/Carrot
        season = self._get_season()
        if season == 3 and tile.type == TILE_FIELD:
            return True

        # For non-winter, field and dirt tiles are available
        if tile.type in (TILE_FIELD, TILE_DIRT):
            return True

        return False

    def _is_edge(self, col, row):
        """Check if a field tile sits on an exposed edge of the planted region."""
        tile = self.grid.get(col, row)
        if tile is None or tile.type != TILE_FIELD:
            return False

        for neighbor in self._neighbors((col, row)):
            neighbor_tile = self._tile(neighbor)
            if neighbor_tile is None or neighbor_tile.type != TILE_FIELD:
                return True

        return False

    def _near_water(self, col, row, radius=4):
        """Check if tile is within radius of a water source."""
        for wc, wr in self.water:
            if manhattan((col, row), (wc, wr)) <= radius:
                return True
        return False

    def _has_adjacent_sunflower(self, col, row):
        """Check if there is an adjacent sunflower tile."""
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if self.assign.get((col + dc, row + dr)) == CROP_SUNFLOWER:
                return True
        return False

    def _neighbors(self, pos):
        """Yield orthogonal in-bounds neighbor positions."""
        col, row = pos
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nc, nr = col + dc, row + dr
            if 0 <= nc < self.grid.cols and 0 <= nr < self.grid.rows:
                yield (nc, nr)

    def _crop_counts_from_assignments(self):
        """Return crop counts from current assignments, ignoring empty/unassigned."""
        counts = {
            CROP_WHEAT: 0,
            CROP_SUNFLOWER: 0,
            CROP_CORN: 0,
            CROP_TOMATO: 0,
            CROP_CARROT: 0,
        }
        for crop in self.assign.values():
            if crop in counts:
                counts[crop] += 1
        return counts

    def _can_assign_crop(self, pos, crop):
        """Check whether a crop can be assigned to a tile under hard constraints."""
        if crop == CROP_NONE:
            return True
        if not self._tile_allows(pos, crop):
            return False

        col, row = pos

        if crop == CROP_TOMATO and not self._near_water(col, row, radius=3):
            return False

        if crop == CROP_SUNFLOWER:
            if not self._is_edge(col, row):
                return False
            if self._has_adjacent_sunflower(col, row):
                return False

        if crop == CROP_WHEAT:
            assigned_wheat_neighbors = sum(
                1 for neighbor in self._neighbors(pos) if self.assign.get(neighbor) == CROP_WHEAT
            )
            open_wheat_neighbors = sum(
                1
                for neighbor in self._neighbors(pos)
                if self.assign.get(neighbor) is None and self._tile_allows(neighbor, CROP_WHEAT)
            )
            requested_wheat = self.get_requested_counts().get(CROP_WHEAT, 0)
            if requested_wheat > 1 and assigned_wheat_neighbors == 0 and open_wheat_neighbors == 0:
                return False

        return True

    def _recompute_domains(self, remaining_counts):
        """Recompute domains for all unassigned variables after a tentative assignment."""
        domains = {}
        for pos in self.vars:
            assigned = self.assign.get(pos, None)
            if assigned is not None:
                domains[pos] = [assigned]
                continue

            domain = []
            for crop in self._base_domain_for_pos(pos):
                if crop != CROP_NONE and remaining_counts.get(crop, 0) <= 0:
                    continue
                if self._can_assign_crop(pos, crop):
                    domain.append(crop)

            domains[pos] = domain
        return domains

    def _wheat_feasible(self, domains, remaining_counts):
        """Check whether wheat adjacency can still be satisfied from this state."""
        requested_wheat = self.get_requested_counts().get(CROP_WHEAT, 0)
        if requested_wheat <= 1:
            return True

        assigned_wheat = [pos for pos, crop in self.assign.items() if crop == CROP_WHEAT]
        for pos in assigned_wheat:
            if any(self.assign.get(neighbor) == CROP_WHEAT for neighbor in self._neighbors(pos)):
                continue
            if not any(
                self.assign.get(neighbor) is None and CROP_WHEAT in domains.get(neighbor, [])
                for neighbor in self._neighbors(pos)
            ):
                self.last_failure_reason = "wheat adjacency can no longer be satisfied"
                return False

        remaining_wheat = remaining_counts.get(CROP_WHEAT, 0)
        if remaining_wheat <= 0:
            return True

        possible_wheat_tiles = [
            pos
            for pos in self.vars
            if self.assign.get(pos) is None and CROP_WHEAT in domains.get(pos, [])
        ]
        if len(possible_wheat_tiles) < remaining_wheat:
            self.last_failure_reason = "not enough spots for Wheat"
            return False

        return True

    def _forward_check(self, domains, remaining_counts):
        """Forward checking: remove impossible future branches early."""
        remaining_vars = [pos for pos in self.vars if self.assign.get(pos) is None]
        total_needed = sum(remaining_counts.values())
        if len(remaining_vars) < total_needed:
            self.last_failure_reason = "insufficient field tiles left"
            return False

        for pos in remaining_vars:
            if not domains.get(pos):
                self.last_failure_reason = f"domain wiped out at {pos}"
                return False

        for crop, count in remaining_counts.items():
            if crop == CROP_NONE or count <= 0:
                continue
            possible_spots = sum(
                1 for pos in remaining_vars if crop in domains.get(pos, [])
            )
            if possible_spots < count:
                self.last_failure_reason = f"not enough spots for {CROP_NAMES.get(crop)}"
                return False

        return self._wheat_feasible(domains, remaining_counts)

    def _select_unassigned_variable(self, domains):
        """MRV heuristic: choose the most constrained unassigned variable."""
        candidates = [pos for pos in self.vars if self.assign.get(pos) is None]
        if not candidates:
            return None

        def key(pos):
            domain = domains.get(pos, [])
            non_none = [crop for crop in domain if crop != CROP_NONE]
            return (
                len(non_none),
                len(domain),
                0 if self._near_water(pos[0], pos[1], radius=3) else 1,
                0 if self._is_edge(pos[0], pos[1]) else 1,
                -getattr(self._tile(pos), "utility", 0.0),
            )

        return min(candidates, key=key)

    def _ordered_values_for_var(self, pos, domains, remaining_counts):
        """Order values so the search tries constrained crops before NONE."""
        values = list(domains.get(pos, []))

        def key(crop):
            if crop == CROP_NONE:
                return (1, 999, 999)
            scarcity = sum(
                1
                for other in self.vars
                if self.assign.get(other) is None and crop in domains.get(other, [])
            )
            return (
                0,
                scarcity,
                -remaining_counts.get(crop, 0),
            )

        values.sort(key=key)
        return values

    def _final_constraints_satisfied(self):
        """Validate final assignment against all hard constraints."""
        counts = self._crop_counts_from_assignments()
        requested = self.get_requested_counts()

        for crop in (
            CROP_WHEAT,
            CROP_SUNFLOWER,
            CROP_CORN,
            CROP_TOMATO,
            CROP_CARROT,
        ):
            if counts.get(crop, 0) != requested.get(crop, 0):
                return False

        for pos, crop in self.assign.items():
            if crop in (None, CROP_NONE):
                continue
            if not self._can_assign_crop(pos, crop):
                return False

        if requested.get(CROP_WHEAT, 0) > 1:
            for pos, crop in self.assign.items():
                if crop != CROP_WHEAT:
                    continue
                if not any(
                    self.assign.get(neighbor) == CROP_WHEAT
                    for neighbor in self._neighbors(pos)
                ):
                    return False

        return True

    def _backtracking_search(self, domains, remaining_counts):
        """Recursive CSP search that tries values, forward-checks, and backtracks."""
        if self._check_timeout():
            return False

        unassigned = [pos for pos in self.vars if self.assign.get(pos) is None]
        if sum(remaining_counts.values()) == 0:
            self.domains = domains
            solved = self._final_constraints_satisfied()
            if solved:
                self.last_failure_reason = ""
            return solved

        if not unassigned:
            self.last_failure_reason = "ran out of tiles before placing all crops"
            return False

        pos = self._select_unassigned_variable(domains)
        if pos is None:
            self.last_failure_reason = "no unassigned variable left"
            return False

        for crop in self._ordered_values_for_var(pos, domains, remaining_counts):
            if crop != CROP_NONE and remaining_counts.get(crop, 0) <= 0:
                continue

            self.assign[pos] = crop
            self.log.append((pos[0], pos[1], crop, "assign"))

            next_remaining = dict(remaining_counts)
            if crop != CROP_NONE:
                next_remaining[crop] -= 1

            next_domains = self._recompute_domains(next_remaining)
            self.domains = next_domains

            if self._forward_check(next_domains, next_remaining) and self._backtracking_search(
                next_domains, next_remaining
            ):
                return True

            self.assign[pos] = None
            self.backtrack_log.append((pos[0], pos[1], crop))
            self.log.append((pos[0], pos[1], crop, "backtrack"))
            self.domains = domains

        return False

    # Candidate ordering utilities

    def _score_tile_for_crop(self, pos, crop):
        """Calculate a score for planting a specific crop on a tile."""
        tile = self._tile(pos)
        if not tile:
            return -9999

        base = CROP_HEURISTIC_VALUE.get(crop, 0.0)
        utility = getattr(tile, "utility", 0.5)
        score = base * utility

        if crop in (CROP_CORN, CROP_TOMATO) and self._near_water(
            pos[0], pos[1], radius=3
        ):
            score *= 1.08

        if getattr(tile, "muddy", False):
            score *= 0.85

        return score

    def _ordered_candidates(self, positions, crop, limit=None):
        """Return positions sorted by desirability for a given crop."""
        filtered = [
            p for p in positions if self._is_available(p) and self._tile_allows(p, crop)
        ]
        filtered.sort(key=lambda p: self._score_tile_for_crop(p, crop), reverse=True)
        if limit:
            return filtered[:limit]
        return filtered

    # Assignment routines

    def _assign_crop(self, positions, crop, limit):
        """Assign a crop to available positions with sunflower adjacency check."""
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
            if not self._tile_allows((col, row), crop):
                continue
            self.assign[(col, row)] = crop
            self.log.append((col, row, crop, "assign"))
            placed += 1
        return placed

    def _assign_crop_relaxed(self, positions, crop, limit):
        """Assign a crop to available positions without adjacency check."""
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
        return placed

    # Auto solver (heuristic-driven)

    def _solve_auto(self):
        """Auto-solve mode - heuristic-driven crop placement."""
        if len(self.grid.crop_tiles()) > 0:
            return False

        season = self._get_season()
        is_winter = season == 3

        if is_winter:
            # Plant Corn and Carrot on ALL field tiles in winter
            field_tiles = list(self.vars)
            random.shuffle(field_tiles)

            planted = 0
            for idx, (col, row) in enumerate(field_tiles):
                crop = CROP_CORN if idx % 2 == 0 else CROP_CARROT
                self.assign[(col, row)] = crop
                self.log.append((col, row, crop, "assign"))
                planted += 1

            return True

        # Normal seasons (Spring, Summer, Autumn) - Plant all crop types
        target_planted = max(1, int(len(self.vars) * 0.5))
        planted = 0

        edge_tiles = [v for v in self.vars if self._is_edge(v[0], v[1])]
        inner_tiles = [v for v in self.vars if not self._is_edge(v[0], v[1])]

        # Plant Sunflowers on edge tiles
        sf_candidates = [v for v in edge_tiles if self._is_available(v)]
        sf_candidates.sort(
            key=lambda p: self._score_tile_for_crop(p, CROP_SUNFLOWER), reverse=True
        )

        for col, row in sf_candidates:
            if planted >= target_planted:
                break
            if self._has_adjacent_sunflower(col, row):
                continue
            if random.random() > 0.35:
                self.assign[(col, row)] = CROP_SUNFLOWER
                self.log.append((col, row, CROP_SUNFLOWER, "assign"))
                planted += 1

        # Fill remaining with random crops
        all_tiles = [v for v in edge_tiles + inner_tiles if self._is_available(v)]
        random.shuffle(all_tiles)

        crop_types = [CROP_WHEAT, CROP_CORN, CROP_TOMATO, CROP_CARROT]

        for col, row in all_tiles:
            if planted >= target_planted:
                break
            if self.assign.get((col, row), CROP_NONE) != CROP_NONE:
                continue
            crop = random.choice(crop_types)
            self.assign[(col, row)] = crop
            self.log.append((col, row, crop, "assign"))
            planted += 1

        return True


    def solve(self, requested_counts=None):
        """Generate a grid layout using auto mode or manual backtracking mode."""
        self.solve_start_time = time.time()
        self.timed_out = False
        self.last_failure_reason = ""
        self.backtrack_log = []
        self.log = []

        self.refresh_grid_context()
        self._init_domains()

        if requested_counts is not None:
            self.set_requested_counts(requested_counts)

        self.assign = {pos: None for pos in self.vars}

        if self.mode == "auto":
            solved = self._solve_auto()
            self.solve_start_time = None
            return solved

        requested = dict(self.get_requested_counts())
        allowed = set(self._get_allowed_crops_for_season())
        for crop in list(requested.keys()):
            if crop not in allowed:
                requested[crop] = 0

        if sum(requested.values()) == 0:
            requested = self._default_counts()
            for crop in list(requested.keys()):
                if crop not in allowed:
                    requested[crop] = 0

        self.requested_counts = requested
        initial_domains = self._recompute_domains(dict(requested))
        self.domains = initial_domains
        solved = self._forward_check(initial_domains, dict(requested)) and self._backtracking_search(
            initial_domains, dict(requested)
        )

        if solved:
            self.last_failure_reason = ""
            for pos in self.vars:
                if self.assign.get(pos) is None:
                    self.assign[pos] = CROP_NONE
            self.apply_to_grid()
        else:
            for pos in self.vars:
                if self.assign.get(pos) is None:
                    self.assign[pos] = CROP_NONE

        self.solve_start_time = None
        return solved
    
    # Apply assignment to the grid

    def apply_to_grid(self):
        """Write the solved assignment back to the grid tiles."""
        # Clear all crops first
        for col in range(self.grid.cols):
            for row in range(self.grid.rows):
                self.grid.tiles[col][row].crop = CROP_NONE
                self.grid.tiles[col][row].crop_stage = 0

        placed_count = 0
        for (col, row), crop in self.assign.items():
            if 0 <= col < self.grid.cols and 0 <= row < self.grid.rows:
                if crop not in (None, CROP_NONE):
                    self.grid.tiles[col][row].crop = crop
                    self.grid.tiles[col][row].crop_stage = 2
                    placed_count += 1

    def set_mode(self, mode):
        """Set solver mode to 'auto' or 'manual'."""
        if mode not in ("auto", "manual"):
            raise ValueError(f"Unsupported CSP mode: {mode}")
        self.mode = mode

    def get_mode(self):
        """Get current solver mode."""
        return self.mode

    def available_field_count(self):
        """Return the number of available field tiles."""
        return len(self.vars) if hasattr(self, "vars") else 0

    def get_backtrack_log(self):
        """Return backtrack log for visualization."""
        return self.backtrack_log

    def get_domains(self):
        """Return current domains for visualization."""
        return self.domains

    def get_backtrack_count(self):
        """Return the total number of backtracks from the last solve."""
        return len(self.backtrack_log)
