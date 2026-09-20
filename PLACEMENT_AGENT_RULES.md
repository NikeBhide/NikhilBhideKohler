# Placement Agent — Rules Specification

Machine-readable placement rules for the KOHLER Bathroom Designer's spatial
layout engine (`backend/placement_agent.py`). Source: Nikhil, 2026-09-20
(bathroom zoning / functional-cluster rules). Each rule below is expressed
as `RULE_ID / SOURCE / PRIORITY / IF / THEN / FORBIDDEN / PREFERENCE` so it
maps directly onto the three-level hierarchy the implementation enforces:
**HARD** (never violated, enforced by construction), **STRONG** (violated
only when room geometry forces it, and always surfaced as a `violations`
note when that happens), **OPTIMIZATION** (tie-breaker between otherwise
valid layouts).

## Catalog reality check (read this before the rules)

The rules below assume product subtypes ("basin faucet", "shower control",
"bathtub filler") that the real KOHLER catalog (`backend/data/products.json`,
1,566 SKUs) does not carry as separate fields — there is no subcategory or
product-type column, only `category` and a free-text `name`. Checked
directly against the data before implementing:

- **`Faucets` (130 SKUs) = basin/sink faucets only.** Every sampled name is
  literally "... bathroom sink faucet ...". There is no shower-control or
  bathtub-filler product anywhere in `Faucets`.
- **`Showers` (83 SKUs) already *is* the control/head** — showerheads,
  rainheads, handshowers. Rule 6 ("shower requires a shower
  faucet/control") is satisfied by the Shower product itself; there is no
  separate control SKU to attach.
- **There is no bathtub filler/faucet product in the catalog at all.**
  Rule 7 as written ("every bathtub must have an associated bathtub
  faucet") is not satisfiable with real inventory today. Bathtubs are
  placed as standalone fixtures. If a "Bathtub Fillers" category is ever
  added to the catalog, the classifier below picks it up automatically —
  no rule change needed.
- **`Bathroom Accessories` (245 SKUs) has no functional sub-tag.**
  Function (towel / toilet / shower) is inferred from the product `name`
  by keyword match (`_classify_accessory` in the implementation): "towel"
  → towel-related, "toilet paper"/"toilet brush" → toilet-related,
  "grab bar"/"shower"/"shelf"/"caddy"/"soap dish"/"rod" → shower-related,
  else → general (attached to the wash station).
- **`Lighting` (109 SKUs) has no mirror/shower/tub sub-tag either**, and
  the recommender currently selects at most one Lighting SKU per bundle.
  Per Rule 15 (the strongest of the three lighting rules), any Lighting
  item in the bundle is treated as the vanity/mirror light.

None of this weakens the rules — it just means "requires an associated X"
is enforced against what the catalog can actually supply, and the gaps
above are deliberate, documented simplifications rather than bugs.

## The core model: functional stations, not independent SKUs

The agent does not ask "where should I put this product?" It classifies
every bundle SKU into a role, groups roles into **stations**, places
stations (not SKUs) along the dry → semi-dry → wet progression, and only
then resolves each station's internal layout (mirror over basin, faucet
on basin, bidet on toilet, accessories on their owning fixture).

| Station | Anchor (competes for floor space) | Attached (rides on the anchor's position) |
|---|---|---|
| Wash station | Vanity (or Basin if no Vanity in bundle) | Basin (if Vanity present), Faucet(s), Mirror(s), Lighting, Cabinet, towel/general accessories |
| Toilet station | Toilet | Toilet Bidet Seat, toilet accessories |
| Wet station(s) | Shower and/or Bathtub | Digital Showering, shower/grab-bar accessories |

Only the five anchor categories (Vanities, Basins-without-a-Vanity,
Toilets, Showers, Bathtubs) ever compete for grid cells / collision
checks. Everything else is wall- or fixture-mounted with no independent
floor footprint, so it is positioned by coordinate math against its
anchor, never by an independent search — this is what makes "basin in the
middle of the room" structurally impossible rather than just less likely.

## Geometry

- Entrance stays on the near wall (`y = depth`), as before.
- All anchors hug the far wall (`y = 0`) by construction — the placement
  search tries every valid `y` starting at `0` for the *entire* candidate
  x-range before ever accepting `y > 0`. (The old bug: the search tried
  `x` positions closest to center first and accepted the first free `y`
  at that `x` — which could be deep in the room if the center column was
  blocked. Y is now the outer, non-negotiable loop.)
- Along that wall, station order from the entrance's x-center outward is
  **Toilet ← Wash → Wet**: the wash station's block is centered on the
  entrance's x, the toilet station sits immediately to one side, the wet
  station(s) immediately to the other — reproducing the "Entrance → Basin
  → Toilet → Shower" row from Rule 1's own diagram, with basin as the
  pivot closest to the door's sightline.
- If the combined width of all three blocks doesn't fit the room, the
  assembly is left-packed instead of centered and a STRONG-level note is
  added to `violations` — reported, never silently dropped.

## Rules

### Level 1 — HARD (enforced by construction; a violation here is a bug, not a compromise)

| RULE_ID | SOURCE | IF | THEN | FORBIDDEN |
|---|---|---|---|---|
| H1 | Basin↔Faucet | Basin or Vanity in bundle | Faucet (if present in bundle) placed at the wash anchor's exact (x,y) | Faucet placed anywhere not coincident with its basin |
| H2 | Basin/Vanity zoning | Wash station active | Wash anchor's block centered on entrance x | Wash anchor placed inside the wet station's x-range |
| H3 | Mirror↔Basin | Mirror in bundle and wash station active | Mirror placed at wash anchor's exact (x,y) | Mirror associated with Shower/Bathtub while a wash station exists (Rule 18) |
| H4 | Shower↔Wet zone | Shower in bundle | Shower placed in the wet x-block, y hugging far wall | Shower placed inside the dry (wash) or semi-dry (toilet) x-block |
| H5 | Bathtub↔Wet zone | Bathtub in bundle | Bathtub placed in the wet x-block alongside Shower (if both present) | Bathtub placed between entrance and wash station |
| H6 | Toilet↔Shower | Toilet and Shower both in bundle | Toilet's rectangle and Shower's rectangle are disjoint (checked, not assumed) | Toilet footprint intersects shower footprint |
| H7 | Bidet↔Toilet | Toilet Bidet Seat in bundle | Bidet placed at Toilet's exact (x,y); only valid if a Toilet exists in the same bundle | Bidet Seat placed as an independent fixture with no Toilet in bundle (flagged, not silently placed) |
| H8 | Entrance clearance | Any anchor placement | Anchor's rectangle checked against the door's x-range at y near `depth` | Any anchor placed inside the door swing rectangle |
| H9 | No overlap | Any two anchors | Disjoint rectangles enforced by pre-computed, non-overlapping x-blocks + real collision check | Two anchors sharing grid cells |

### Level 2 — STRONG (violated only when geometry forces it; always logged)

| RULE_ID | SOURCE | PREFERENCE |
|---|---|---|
| S1 | Dry → semi-dry → wet | Toilet block sits between the wash block and the wet block along the wall |
| S2 | Common plumbing wall | Wash / Toilet / Wet anchors all hug the same wall (`y = 0`) so basin, toilet and shower/tub water connections run along one wall instead of opposite walls |
| S3 | Cabinets in dry/semi-dry | Cabinet attached adjacent to the wash anchor, never inside the wet block |
| S4 | Lighting↔Mirror | A single Lighting SKU in the bundle is attached to the mirror/wash anchor, not free-floating |
| S5 | Accessories follow function | Towel accessories → wash/shower/bathtub; toilet accessories → toilet; shower accessories (incl. grab bars) → shower/bathtub — never left unassociated |
| S6 | Room too narrow | If the room can't fit all three blocks at full width, left-pack instead of centering and log it |

### Level 3 — OPTIMIZATION (tie-breakers, applied within the rules above)

- O1: Minimize the wall-run length (stations packed with a fixed small gap, not spread out).
- O2: Wash station's block center kept as close to the entrance's x-center as the room allows.
- O3: Multiple accessories on the same anchor are fanned out with a small fixed offset rather than stacked exactly on top of one another (cosmetic only — doesn't affect any hard/strong rule).

## Conflict resolution

When a STRONG rule can't be satisfied because the room is too small for
the full three-block layout (S6), the HARD rules always win: anchors are
still guaranteed non-overlapping and off the door path (H6/H8/H9); the
compromise is the assembly's centering (O2) and, in extreme cases, station
blocks touching with zero gap instead of the small preferred gap (O1).
Every time a STRONG rule is compromised, a plain-language note is appended
to the `violations` list returned to the frontend, which surfaces it as a
"clearance note" rather than a hard error.
