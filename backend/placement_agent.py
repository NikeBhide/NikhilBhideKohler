"""
Placement Constraining Agent - 2D Grid Layout & Constraint Validation
Places products on bathroom grid respecting spatial constraints.

See docs/PLACEMENT_AGENT_RULES.md for the full rules spec this file
implements (HARD / STRONG / OPTIMIZATION hierarchy, functional-station
model, and the catalog-driven simplifications -- e.g. this catalog's
"Faucets" are basin faucets only, and there is no separate shower-control
or bathtub-filler product).

Core idea: classify every bundle SKU into a functional role, group roles
into stations (wash / toilet / wet), place the STATIONS along the
dry -> semi-dry -> wet progression against a single wall, and only then
resolve each station's internal layout (mirror over basin, faucet on
basin, bidet on toilet, accessories on their owning fixture). Only floor
furniture (Vanities, Basins-without-a-Vanity, Toilets, Showers, Bathtubs)
ever competes for grid cells; everything else is wall/fixture-mounted and
is positioned by coordinate math against its anchor.
"""

from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass


@dataclass
class GridCell:
    """Represents a cell on the bathroom grid."""
    x: int
    y: int
    product_sku: str = None
    occupied: bool = False


# Categories that are real floor furniture and therefore compete for grid
# space / collision checks. Everything else in PRODUCT_SPECS is wall- or
# fixture-mounted and gets attached by coordinate math instead (see
# ATTACHMENT rules below).
FLOOR_ANCHOR_CATEGORIES = {"Vanities", "Basins", "Toilets", "Showers", "Bathtubs"}

# Small fixed gap (inches) kept between adjacent station blocks along the
# plumbing wall -- purely cosmetic (O1), never a hard requirement.
STATION_GAP = 4

# Rectangular door-swing buffer kept clear in front of the entrance
# (H8 / Rule 19). Anchors may not enter this zone.
ENTRANCE_CLEARANCE_DEPTH = 20
ENTRANCE_CLEARANCE_MARGIN = 4


class PlacementAgent:
    """
    Validates and places bathroom products on a 2D grid.
    Enforces the functional-station spatial model described in
    docs/PLACEMENT_AGENT_RULES.md.
    """

    def __init__(self):
        """Initialize product footprint defaults."""

        # Default (width, depth) in inches per category, used whenever a
        # product doesn't carry its own `dimensions`. Kept for every
        # category (not just floor anchors) since attached items still
        # need a sensible box size for the 3D visualization.
        self.PRODUCT_SPECS = {
            "Toilets": {"default_width": 16, "default_depth": 28},
            "Toilet Bidet Seats": {"default_width": 16, "default_depth": 28},
            "Basins": {"default_width": 24, "default_depth": 18},
            "Faucets": {"default_width": 8, "default_depth": 4},
            "Bathtubs": {"default_width": 60, "default_depth": 32},
            "Showers": {"default_width": 36, "default_depth": 36},
            "Mirrors": {"default_width": 30, "default_depth": 2},
            "Cabinets": {"default_width": 24, "default_depth": 8},
            "Vanities": {"default_width": 48, "default_depth": 22},
            "Digital Showering": {"default_width": 8, "default_depth": 4},
            "Lighting": {"default_width": 12, "default_depth": 4},
            "Bathroom Accessories": {"default_width": 10, "default_depth": 4},
        }

    # ------------------------------------------------------------------
    # Grid mechanics (unchanged contract: create_grid / get_product_footprint
    # / can_place_at / place_product / visualize_grid)
    # ------------------------------------------------------------------

    def create_grid(self, width_inches: int, height_inches: int) -> List[List[GridCell]]:
        """Create a 2D grid representing the bathroom floor plan (1 cell = 1 inch)."""
        grid = []
        for y in range(height_inches):
            row = []
            for x in range(width_inches):
                row.append(GridCell(x=x, y=y))
            grid.append(row)
        return grid

    def get_product_footprint(self, product: Dict) -> Tuple[int, int]:
        """Get product (width, depth) from product data or category defaults."""
        category = product.get("category")

        dimensions = product.get("dimensions", {})
        if dimensions:
            return (
                dimensions.get("width_inches", 0),
                dimensions.get("depth_inches", 0)
            )

        if category in self.PRODUCT_SPECS:
            spec = self.PRODUCT_SPECS[category]
            return (spec.get("default_width", 24), spec.get("default_depth", 18))

        return (24, 18)

    def can_place_at(
        self,
        grid: List[List[GridCell]],
        product: Dict,
        x: int,
        y: int,
        placed_products: Dict[str, Dict]
    ) -> Tuple[bool, str]:
        """Check if product can be placed at (x, y): in bounds and collision-free."""
        width, depth = self.get_product_footprint(product)

        if x < 0 or y < 0 or x + width > len(grid[0]) or y + depth > len(grid):
            return False, "Exceeds grid boundaries"

        for dy in range(depth):
            for dx in range(width):
                if grid[y + dy][x + dx].occupied:
                    return False, "Collides with existing product"

        return True, "OK"

    def place_product(
        self,
        grid: List[List[GridCell]],
        product: Dict,
        x: int,
        y: int
    ) -> Tuple[bool, str]:
        """Mark grid cells as occupied by this product."""
        width, depth = self.get_product_footprint(product)
        sku = product.get("sku")

        for dy in range(depth):
            for dx in range(width):
                grid[y + dy][x + dx].occupied = True
                grid[y + dy][x + dx].product_sku = sku

        return True, "Placed successfully"

    def visualize_grid(self, grid: List[List[GridCell]]) -> str:
        """ASCII representation of the grid (debugging / backend test script only)."""
        sku_to_char = {}
        char_index = 0
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

        lines = []
        for row in grid:
            line = ""
            for cell in row:
                if cell.occupied:
                    if cell.product_sku not in sku_to_char:
                        if char_index < len(chars):
                            sku_to_char[cell.product_sku] = chars[char_index]
                            char_index += 1
                        else:
                            sku_to_char[cell.product_sku] = "?"
                    line += sku_to_char[cell.product_sku]
                else:
                    line += "."
            lines.append(line)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Functional classification (docs/PLACEMENT_AGENT_RULES.md: "catalog
    # reality check")
    # ------------------------------------------------------------------

    def _classify_accessory(self, name: str) -> str:
        """
        Bathroom Accessories has no functional sub-tag in the catalog --
        infer it from the product name (Rule 14 / S5).
        """
        n = (name or "").lower()
        if "toilet paper" in n or "toilet brush" in n or "bidet" in n:
            return "toilet"
        if "grab bar" in n:
            return "shower"
        if any(k in n for k in ("shower", "shelf", "caddy", "soap dish", "rod")):
            return "shower"
        if "towel" in n:
            return "towel"
        return "general"

    def _rectangles_overlap(self, a, b) -> bool:
        ax, ay, aw, ad = a
        bx, by, bw, bd = b
        return not (ax + aw <= bx or bx + bw <= ax or ay + ad <= by or by + bd <= ay)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def auto_place_bundle(
        self,
        grid: List[List[GridCell]],
        bundle: List[Dict]
    ) -> Dict:
        """
        Place the bundle as functional stations (wash / toilet / wet)
        along a single wall, dry -> semi-dry -> wet, then resolve each
        station's internal layout (mirror over basin, faucet on basin,
        bidet on toilet, accessories on their owning fixture).

        Returns the same shape as before: placement_map ({sku: (x, y)}),
        placed_products, violations, grid, success, entrance.
        """
        grid_width = len(grid[0])
        grid_height = len(grid)

        placement_map: Dict[str, Tuple[int, int]] = {}
        placed_products: Dict[str, Dict] = {}
        violations: List[str] = []
        # Rectangles actually occupying floor space, for the final H6/H9
        # overlap safety-net check. {sku: (x, y, w, d)}
        floor_rects: Dict[str, Tuple[int, int, int, int]] = {}

        # -- 1. Classify bundle products by role -------------------------------
        by_category: Dict[str, List[Dict]] = {}
        for product in bundle:
            by_category.setdefault(product.get("category"), []).append(product)

        vanities = by_category.get("Vanities", [])
        basins = by_category.get("Basins", [])
        faucets = by_category.get("Faucets", [])
        mirrors = by_category.get("Mirrors", [])
        cabinets = by_category.get("Cabinets", [])
        lighting = by_category.get("Lighting", [])
        toilets = by_category.get("Toilets", [])
        bidets = by_category.get("Toilet Bidet Seats", [])
        showers = by_category.get("Showers", [])
        bathtubs = by_category.get("Bathtubs", [])
        digital_showering = by_category.get("Digital Showering", [])
        accessories = by_category.get("Bathroom Accessories", [])

        # Wash station anchor: Vanity if present (basin sits on/in it),
        # else the Basin itself (e.g. a pedestal sink with no vanity).
        wash_anchor_product = vanities[0] if vanities else (basins[0] if basins else None)
        wash_active = wash_anchor_product is not None
        toilet_active = len(toilets) > 0
        wet_active = len(showers) > 0 or len(bathtubs) > 0

        # -- 2. Entrance (unchanged contract/shape) ------------------------------
        entrance_x_center = grid_width // 2
        entrance_width = min(30, grid_width)
        entrance = {
            "x": max(0, entrance_x_center - entrance_width // 2),
            "width": entrance_width,
            "wall": "near",  # bottom edge of the grid, y = grid_height
        }

        # H8 / Rule 19: the door-swing rectangle must stay clear of every
        # floor anchor. Mark it as pre-occupied on the grid *before* any
        # anchor search runs, so the search structurally avoids it instead
        # of just complaining about it after the fact.
        door_x0 = max(0, entrance["x"] - ENTRANCE_CLEARANCE_MARGIN)
        door_x1 = min(grid_width, entrance["x"] + entrance["width"] + ENTRANCE_CLEARANCE_MARGIN)
        door_y0 = max(0, grid_height - ENTRANCE_CLEARANCE_DEPTH)
        for y in range(door_y0, grid_height):
            for x in range(door_x0, door_x1):
                grid[y][x].occupied = True

        # -- 3. Choose which wall the fixture assembly runs along: the
        #    LONGER of the room's two horizontal walls, not always the
        #    back wall. A vanity + toilet + shower run needs real wall
        #    length; always forcing that run onto the back wall starves it
        #    of space the room doesn't actually lack -- it's just on a
        #    different wall (e.g. a 60"-wide x 96"-deep room has 96" of
        #    usable run along either SIDE wall, not just 60" along the
        #    back). Everything below works in an abstract (along, away)
        #    space -- `along` = position along the chosen wall, `away` =
        #    distance out from it -- on its own local grid, and converts
        #    back to real (x, y) only once a position is accepted.
        along_back_wall = grid_width >= grid_height
        wall_length = grid_width if along_back_wall else grid_height
        perp_depth = grid_height if along_back_wall else grid_width

        def to_real_rect(along, away, size_along, size_away):
            """Map an (along, away)-space rectangle to real (x, y, w, h)."""
            if along_back_wall:
                return (along, away, size_along, size_away)
            # Reflected so along=0 (built first below -- the wash station)
            # lands at the entrance's own edge (real y = grid_height) and
            # increasing `along` moves away from the entrance toward the
            # back wall (real y = 0) -- "Entrance -> Basin -> Toilet ->
            # Shower" read as distance from the door, now that the door
            # and the assembly are on different walls.
            real_y = wall_length - along - size_along
            real_x = away
            return (real_x, real_y, size_away, size_along)

        def away_of(real_x, real_y):
            """The real coordinate that measures distance from the chosen wall."""
            return real_y if along_back_wall else real_x

        def real_point_to_local(rx, ry):
            if along_back_wall:
                return (rx, ry)
            return (wall_length - 1 - ry, rx)

        def real_along_end(real_pos, size_along):
            """Given a placed anchor's real (x, y) and its along-axis size,
            return the local `along` coordinate right past its far edge --
            used to slide the NEXT station's zone to where this one
            actually landed, rather than where it was predicted to land.
            Predicted zones can be wrong once the entrance-clearance
            carve-out (or any other collision) pushes an anchor off its
            preferred spot; without this, a later station's exact-fit zone
            can end up overlapping the earlier one's real footprint."""
            rx, ry = real_pos
            if along_back_wall:
                return rx + size_along
            return (wall_length - size_along - ry) + size_along

        def mark_real_rect(rx, ry, rw, rh, sku):
            for dy in range(rh):
                for dx in range(rw):
                    yy, xx = ry + dy, rx + dx
                    if 0 <= yy < grid_height and 0 <= xx < grid_width:
                        grid[yy][xx].occupied = True
                        grid[yy][xx].product_sku = sku

        local_grid = self.create_grid(wall_length, perp_depth)

        # H8 / Rule 19: translate the door-swing clearance (already marked
        # on the real grid above) onto the local (along, away) grid too, so
        # the assembly search structurally avoids it regardless of which
        # real wall it ends up running along.
        for ry in range(door_y0, grid_height):
            for rx in range(door_x0, door_x1):
                if 0 <= rx < grid_width and 0 <= ry < grid_height:
                    along, away = real_point_to_local(rx, ry)
                    if 0 <= along < wall_length and 0 <= away < perp_depth:
                        local_grid[away][along].occupied = True

        wash_w, _ = self.get_product_footprint(wash_anchor_product) if wash_active else (0, 0)
        toilet_w, _ = self.get_product_footprint(toilets[0]) if toilet_active else (0, 0)

        wet_items = []  # [(product, width, depth)]
        for p in showers + bathtubs:
            w, d = self.get_product_footprint(p)
            wet_items.append((p, w, d))
        wet_total_w = sum(w for _, w, _ in wet_items)
        if len(wet_items) > 1:
            wet_total_w += STATION_GAP * (len(wet_items) - 1)

        # Assembly order (Rule 1 / S1): Wash | Toilet | Wet, built in that
        # order along the `along` axis -- "Entrance -> Basin -> Toilet ->
        # Shower", basin first (closest to the door once mapped back to
        # real coordinates -- see to_real_rect above), toilet in the
        # middle, wet fixtures furthest from the door. Each zone's length
        # is reserved based on what's actually in it -- NOT a blind 50/50
        # split of the wall, which ignores where the wash anchor's own
        # footprint actually falls and can starve the other zones of real
        # space. Centered along the wall when it fits; left-packed (S6)
        # when it doesn't, reported via `violations`, never silently
        # dropped.
        segment_widths = []
        if wash_active:
            segment_widths.append(wash_w)
        if toilet_active:
            segment_widths.append(toilet_w)
        if wet_active:
            segment_widths.append(wet_total_w)
        assembly_gaps = STATION_GAP * max(0, len(segment_widths) - 1)
        total_assembly_w = sum(segment_widths) + assembly_gaps

        # Along the back wall, center on the entrance's own sightline (O2).
        # Along a side wall, the entrance-adjacency is already encoded by
        # the build order + reflection above, so there's no equivalent
        # bias -- just center the assembly on the wall itself.
        along_center = entrance_x_center if along_back_wall else wall_length // 2

        if total_assembly_w <= wall_length:
            assembly_start = max(0, min(wall_length - total_assembly_w, along_center - total_assembly_w // 2))
        else:
            assembly_start = 0
            violations.append(
                "Room is narrow for this bundle -- fixtures are packed along "
                "the wall instead of centered."
            )

        cursor = assembly_start
        wash_zone = None
        toilet_zone = None
        if wash_active:
            wash_zone = (cursor, cursor + wash_w)
            cursor += wash_w + STATION_GAP
        if toilet_active:
            toilet_zone = (cursor, cursor + toilet_w)
            cursor += toilet_w + STATION_GAP
        # The wet zone's far edge is always the end of the wall (it's the
        # last segment, and wet items themselves prefer hugging that end --
        # see below), not a computed midpoint.
        wet_zone_start = cursor if wet_active else wall_length

        wash_along = wash_zone[0] if wash_zone else 0
        toilet_along = toilet_zone[0] if toilet_zone else 0

        # -- 4. Place floor anchors, hugging the chosen wall (away=0 tried
        #    first across the FULL candidate `along` range -- wall-hugging
        #    always wins over along-axis centering). ------------

        def place_anchor(product, preferred_along, along_bounds=None):
            """
            Search for a free spot in (along, away) space on the local
            grid: away ascending (wall-hugging always wins over along-axis
            centering) and along ordered by closeness to preferred_along.

            along_bounds, when given, confines the search to that zone
            (e.g. the toilet's own reserved slice) -- this is what keeps a
            fixture that gets pushed off away=0 from drifting into another
            zone's space. Only if the fixture's own zone has no room
            anywhere does the search widen to the full wall, and that
            widening is reported explicitly.
            Returns (real_x, real_y, zone_fallback: bool) -- the position
            is already converted back to real coordinates.
            """
            size_along, size_away = self.get_product_footprint(product)
            sku = product.get("sku")

            def scan(a_min, a_max):
                for away in range(0, perp_depth - size_away + 1):
                    for offset in [0] + [v for d in range(1, wall_length) for v in (d, -d)]:
                        along = preferred_along + offset
                        if along < a_min or along + size_along > a_max:
                            continue
                        can_place, _ = self.can_place_at(local_grid, product, along, away, placed_products)
                        if can_place:
                            return (along, away)
                return None

            result = scan(*along_bounds) if along_bounds else scan(0, wall_length)
            zone_fallback = result is None and along_bounds is not None
            if result is None and along_bounds:
                result = scan(0, wall_length)

            if result:
                along, away = result
                self.place_product(local_grid, product, along, away)
                real_x, real_y, real_w, real_h = to_real_rect(along, away, size_along, size_away)
                mark_real_rect(real_x, real_y, real_w, real_h, sku)
                placement_map[sku] = (real_x, real_y)
                placed_products[sku] = product
                floor_rects[sku] = (real_x, real_y, real_w, real_h)
                return (real_x, real_y, zone_fallback)
            return None

        wash_pos_r = place_anchor(wash_anchor_product, wash_along, along_bounds=wash_zone) if wash_active else None
        wash_pos = wash_pos_r[:2] if wash_pos_r else None

        # If the wash anchor got pushed off its predicted spot (e.g. by the
        # entrance-clearance carve-out), slide the toilet's zone to start
        # where the wash anchor ACTUALLY ended, not where it was predicted
        # to end -- otherwise the toilet's exact-fit zone can end up
        # physically overlapping the wash anchor's real footprint, forcing
        # it away from the wall for no real space reason.
        if wash_active and toilet_active:
            if wash_pos:
                wash_end = real_along_end(wash_pos, wash_w)
                toilet_start = max(toilet_zone[0], wash_end + STATION_GAP)
                toilet_zone = (toilet_start, toilet_start + toilet_w)
                toilet_along = toilet_start
            # If the wash anchor couldn't be placed at all, leave the
            # predicted toilet_zone as-is -- there's nothing to slide past.

        # Toilet confined to its own reserved zone, sized to its actual
        # footprint rather than half the wall (S1: dry -> semi-dry -> wet
        # reads as distance from the entrance) -- with a full-wall fallback
        # only as an absolute last resort, always reported when it happens.
        toilet_pos_r = place_anchor(toilets[0], toilet_along, along_bounds=toilet_zone) if toilet_active else None
        toilet_pos = toilet_pos_r[:2] if toilet_pos_r else None

        # Same idea for the wet zone: start it where the toilet (or, absent
        # a toilet, the wash anchor) actually landed, not the static
        # prediction -- prevents the same cascading collision one station
        # further down the line.
        if wet_active:
            if toilet_active and toilet_pos:
                wet_zone_start = max(wet_zone_start, real_along_end(toilet_pos, toilet_w) + STATION_GAP)
            elif not toilet_active and wash_active and wash_pos:
                wet_zone_start = max(wet_zone_start, real_along_end(wash_pos, wash_w) + STATION_GAP)

        # Each wet item independently prefers hugging the far end of the
        # wall (wall_length - its own width) and is confined to the wet
        # zone (wet_zone_start through the far end). This is deliberately
        # NOT a running cursor that subtracts widths cumulatively -- with
        # two wide items (e.g. a 36" shower + a 60" tub) whose combined
        # width exceeds the wall, a cumulative cursor goes negative and the
        # search then centers on along=0 instead of the far end. Collision
        # avoidance inside place_anchor (an exhaustive search of its zone)
        # is what actually keeps two wet items from overlapping each other.
        wet_positions = {}
        zone_fallback_notes = []
        for p, w, d in wet_items:
            preferred_along = max(0, wall_length - w)
            # The wet zone's near edge is wherever the wash+toilet blocks
            # end (wet_zone_start) -- not re-shrunk by a min() against the
            # item's own width, which used to silently let a wide item
            # creep back into the wash/toilet zone it was supposed to stay
            # out of. If the item genuinely doesn't fit in what's left of
            # the wall, place_anchor's own full-wall fallback (below) is
            # what handles that, and reports it via zone_fallback.
            result = place_anchor(p, preferred_along, along_bounds=(wet_zone_start, wall_length))
            if result:
                x, y, zone_fallback = result
                wet_positions[p.get("sku")] = (x, y)
                if zone_fallback:
                    zone_fallback_notes.append(p.get("category"))

        if toilet_pos_r and toilet_pos_r[2]:
            zone_fallback_notes.append("Toilets")

        # Honest, outcome-based "tight room" signal: if any anchor had to
        # give up wall-hugging (away > 0) to avoid a collision, the room
        # genuinely didn't have room for the ideal layout -- report it (S6)
        # rather than guessing from a raw width sum, which over-fires for
        # perfectly normal room sizes since this model uses more than one
        # row of depth.
        anchor_positions = [p for p in (wash_pos, toilet_pos) if p] + list(wet_positions.values())
        if any(away_of(x, y) > 0 for x, y in anchor_positions):
            violations.append(
                "Room is tight for this bundle -- one or more fixtures were pushed "
                "off the wall to avoid overlapping another fixture."
            )
        if zone_fallback_notes:
            violations.append(
                f"Room is tight for this bundle -- {', '.join(zone_fallback_notes)} couldn't fit "
                "on its usual side of the room and had to be placed wherever space allowed."
            )

        for product in toilets[1:] + vanities[1:] + basins[1:] + showers + bathtubs:
            # Extra floor anchors beyond the first of their kind (multiple
            # toilets/vanities, or any wet item not already handled above)
            # fall back to a general first-fit scan against whatever's
            # already on the grid, still y-first (wall-hugging).
            sku = product.get("sku")
            if sku in placement_map:
                continue
            width, depth = self.get_product_footprint(product)
            placed = False
            for y in range(0, grid_height - depth + 1):
                for x in range(0, grid_width - width + 1):
                    can_place, _ = self.can_place_at(grid, product, x, y, placed_products)
                    if can_place:
                        self.place_product(grid, product, x, y)
                        placement_map[sku] = (x, y)
                        placed_products[sku] = product
                        floor_rects[sku] = (x, y, width, depth)
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                violations.append(f"Could not find valid placement for {product.get('category')} ({sku})")

        if wash_active and not wash_pos:
            violations.append(f"Could not place wash station anchor ({wash_anchor_product.get('sku')})")
        if toilet_active and not toilet_pos:
            violations.append(f"Could not place toilet ({toilets[0].get('sku')})")

        # -- 5. Attach everything else by coordinate math (no grid, no search) ----

        def attach(product, coord, offset=(0, 0)):
            if coord is None or product is None:
                return
            sku = product.get("sku")
            x = max(0, min(grid_width - 1, coord[0] + offset[0]))
            y = max(0, min(grid_height - 1, coord[1] + offset[1]))
            placement_map[sku] = (x, y)
            placed_products[sku] = product

        def offset_along(coord, delta):
            """Shift a real (x, y) position by `delta` along the assembly's
            chosen wall -- e.g. "place this cabinet just past the wash
            anchor". Converts the abstract along-axis offset into the
            correct real axis/direction: real x when the assembly runs
            along the back wall, real y (and reflected, since increasing
            `along` moves toward the back wall) otherwise. Using a raw
            (delta, 0) offset here was the pre-rewrite assumption baked
            into `attach()` callers and silently broke once the assembly
            could run along a side wall instead."""
            if coord is None:
                return None
            rx, ry = coord
            if along_back_wall:
                return (rx + delta, ry)
            return (rx, ry - delta)

        # Basin rides on the vanity (H1 pairing via Rule 4); if there's no
        # vanity, the basin itself was already the floor anchor above.
        if vanities and basins:
            for b in basins:
                attach(b, wash_pos)

        # Faucet(s) + Mirror(s) + Lighting -> wash anchor's exact spot (H1, H3, S4).
        for f in faucets:
            attach(f, wash_pos)
        for m in mirrors:
            attach(m, wash_pos)
        for l in lighting:
            attach(l, wash_pos or toilet_pos)  # S4: mirror/vanity light; falls back if no wash station exists

        # Cabinet: dry/semi-dry zone, beside the wash anchor (S3), never
        # inside the wet block.
        if cabinets and wash_pos:
            cab_w, _ = self.get_product_footprint(cabinets[0])
            for i, c in enumerate(cabinets):
                pos = offset_along(wash_pos, wash_w + STATION_GAP + i * (cab_w + 2))
                attach(c, pos)
        elif cabinets:
            for c in cabinets:
                attach(c, toilet_pos or wet_positions.get(next(iter(wet_positions), None)))

        # Bidet seat -> toilet's exact spot (H7); flagged if no toilet exists.
        for bd in bidets:
            if toilet_pos:
                attach(bd, toilet_pos)
            else:
                violations.append(
                    f"Toilet Bidet Seat ({bd.get('sku')}) has no compatible Toilet in this bundle"
                )

        # Digital Showering (shower control panel) -> shower's spot, else bathtub's.
        shower_anchor_pos = wet_positions.get(showers[0].get("sku")) if showers else None
        bathtub_anchor_pos = wet_positions.get(bathtubs[0].get("sku")) if bathtubs else None
        for ds in digital_showering:
            attach(ds, shower_anchor_pos or bathtub_anchor_pos)

        # Bathroom Accessories -> function-classified target (S5), fanned
        # out with a small offset so multiples don't stack exactly (O3).
        towel_target = wash_pos or shower_anchor_pos or bathtub_anchor_pos
        shower_acc_target = shower_anchor_pos or bathtub_anchor_pos
        for i, acc in enumerate(accessories):
            kind = self._classify_accessory(acc.get("name"))
            if kind == "toilet":
                target = toilet_pos
            elif kind == "shower":
                target = shower_acc_target
            elif kind == "towel":
                target = towel_target
            else:
                target = wash_pos or toilet_pos or shower_acc_target
            attach(acc, target, offset=(i * 3, 0))

        # -- 6. Hard-rule safety net: overlap + entrance clearance checks ----------

        rect_list = list(floor_rects.items())
        for i in range(len(rect_list)):
            for j in range(i + 1, len(rect_list)):
                sku_a, rect_a = rect_list[i]
                sku_b, rect_b = rect_list[j]
                if self._rectangles_overlap(rect_a, rect_b):
                    violations.append(
                        f"{placed_products[sku_a].get('category')} and "
                        f"{placed_products[sku_b].get('category')} overlap -- room is too tight for this bundle"
                    )

        if toilets and (showers or bathtubs) and toilet_pos:
            toilet_rect = floor_rects.get(toilets[0].get("sku"))
            for p in showers + bathtubs:
                wet_rect = floor_rects.get(p.get("sku"))
                if toilet_rect and wet_rect and self._rectangles_overlap(toilet_rect, wet_rect):
                    violations.append("Toilet footprint overlaps the shower/bathtub's wet footprint")

        door_x0 = max(0, entrance["x"] - ENTRANCE_CLEARANCE_MARGIN)
        door_x1 = entrance["x"] + entrance["width"] + ENTRANCE_CLEARANCE_MARGIN
        door_y0 = max(0, grid_height - ENTRANCE_CLEARANCE_DEPTH)
        for sku, (x, y, w, d) in floor_rects.items():
            if self._rectangles_overlap((x, y, w, d), (door_x0, door_y0, door_x1 - door_x0, grid_height - door_y0)):
                violations.append(
                    f"{placed_products[sku].get('category')} ({sku}) sits in the entrance's door-swing path"
                )

        return {
            "placement_map": placement_map,
            "placed_products": placed_products,
            "violations": violations,
            "grid": grid,
            "success": len(violations) == 0,
            "entrance": entrance,
            "floor_rects": floor_rects,
        }


def main():
    """Test the Placement Agent."""
    agent = PlacementAgent()

    grid = agent.create_grid(60, 80)

    bundle = [
        {"sku": "K-TUB", "category": "Bathtubs", "name": "Entity 60\" x 36\" Bath", "price": 818.25},
        {"sku": "K-TOI", "category": "Toilets", "name": "Wellworth 1.6 GPF Toilet", "price": 189.99},
        {"sku": "K-VAN", "category": "Vanities", "name": "Poplin 48\" Vanity", "price": 999.0},
        {"sku": "K-BAS", "category": "Basins", "name": "Memoirs Pedestal Sink", "price": 279.50,
         "dimensions": {"width_inches": 24, "depth_inches": 18}},
        {"sku": "K-FAU", "category": "Faucets", "name": "Archer bathroom sink faucet", "price": 349.00},
        {"sku": "K-MIR", "category": "Mirrors", "name": "Verdera Mirror", "price": 199.0},
        {"sku": "K-TOWEL", "category": "Bathroom Accessories", "name": "Buckley 24\" towel bar", "price": 45.0},
        {"sku": "K-TP", "category": "Bathroom Accessories", "name": "Elate Vertical toilet paper holder", "price": 60.0},
    ]

    print("=" * 80)
    print("PLACEMENT AGENT - FUNCTIONAL STATION LAYOUT TEST")
    print("=" * 80)
    print(f"\nBathroom: 60\" x 80\"")
    print(f"Bundle: {len(bundle)} products\n")

    result = agent.auto_place_bundle(grid, bundle)

    print(f"Placement Success: {result['success']}")
    print(f"Products Placed: {len(result['placement_map'])}")

    if result["violations"]:
        print("\nViolations:")
        for v in result["violations"]:
            print(f"  - {v}")

    print("\nPlacement Map:")
    for sku, (x, y) in result["placement_map"].items():
        product = result["placed_products"][sku]
        print(f"  {product['name']} [{product['category']}]: ({x}, {y})")


if __name__ == "__main__":
    main()
