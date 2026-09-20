# KOHLER Bathroom Designer - System Architecture

**Status:** Design Phase - Awaiting Approval Before Implementation

---

## 1. System Overview

The KOHLER Bathroom Designer is an AI-powered product recommendation system that creates personalized, coordinated bathroom bundles. Users input their design theme preferences, budget, bathroom dimensions, and which product categories they want to include. The system then recommends a cohesive bathroom design where all products work together visually and functionally.

**Core Philosophy:**
- Focus on **bundle cohesion** — all products must harmonize visually and functionally
- Respect **hard constraints** — budget and category selection are non-negotiable filters
- Enable **iterative refinement** — users can lock preferred products and refresh alternatives
- Prioritize **theme consistency** — all recommended products share at least one design theme keyword

**System Components:**
1. **Data Pipeline** — Web scraping + JSON product database with theme mappings
2. **Multi-Agent Architecture** — Three agents (Extraction, Recommendation, Placement Constraining) working in sequence
3. **UI Layer** — Conversational chatbot + product list + 2D bathroom layout visualization
4. **Constraint Engine** — Validates spatial relationships and placement rules

---

## 2. Data Pipeline

### 2.1 Web Scraping (In Progress)

**Source:** kohler.com (US site)
**Tool:** Selenium-based scraper with JavaScript rendering
**Status:** Currently scraping ~2 hours duration for full product descriptions

**Data Collection Process:**
1. Navigate to Kohler bathroom products category
2. Extract product listing pages (category-by-category)
3. For each product:
   - Retrieve basic info (name, SKU, price, URL)
   - Load product detail page
   - Click "Read More" to fetch full description
   - Extract color/finish options
   - Capture product images (store URLs, not embed)
   - Extract dimensions (when available)

**Scraping Challenges Addressed:**
- JS-heavy website → Selenium with wait conditions
- Truncated descriptions on listing → Click "Read More" for full text
- Missing dimensions → Plan to estimate from category or ask user
- Image embedding → Store as URLs only (links to product pages)

### 2.2 Data Storage & Structure

**Format:** JSON files organized by category
**Location:** `/data/products/` directory
**Filename:** `{category}_products.json`

**Categories:**
- toilets.json
- toilet_bidet_seats.json
- smart_toilets.json
- basins.json
- faucets.json
- bathtubs.json
- showers.json
- digital_showering.json
- mirrors.json
- cabinets.json
- bathroom_vanities.json
- (metadata.json for reference themes)

### 2.3 Product Data Schema

```json
{
  "products": [
    {
      "sku": "K-26107-LA-0",
      "name": "Entity 60\" x 36\" Alcove Bath with Integral Apron",
      "category": "Bathtubs",
      "price": 818.25,
      "dimensions": {
        "width_inches": 60,
        "depth_inches": 36,
        "height_inches": 20
      },
      "color_finish": "White / Biscuit / Black",
      "description": "Defined by crisp lines and a clean, simple aesthetic...",
      "image_url": "https://kohler.scene7.com/is/image/PAWEB/...",
      "product_url": "https://www.kohler.com/en/products/bathtubs/...",
      "inferred_themes": [
        {
          "theme": "Modern",
          "confidence": 0.95,
          "keywords": ["crisp lines", "clean", "simple", "aesthetic"]
        },
        {
          "theme": "Minimalist",
          "confidence": 0.85,
          "keywords": ["simple", "clean", "sleek"]
        }
      ],
      "availability": true,
      "features": []
    }
  ]
}
```

### 2.4 Theme Inference Mapping

**Approach:** Keyword matching + logical inference on product descriptions

**Keyword Map (25 Kohler Official Themes):**

| Theme | Keywords | Inference Signals |
|-------|----------|-------------------|
| Modern | crisp, clean, contemporary, sleek, minimalist, angular, geometric, linear | Contemporary product lines |
| Classic | traditional, timeless, elegant, refined, heritage, formal | Heritage collections |
| Spa | wellness, relaxation, therapeutic, hydrotherapy, steam, massage, heated | Whirlpool, jets, bubble features |
| Luxury | premium, high-end, bespoke, artisanal, crafted, signature | Premium pricing tier |
| Minimalist | simple, essential, uncluttered, functional, pared-down | Entity, Brazn collections |
| Transitional | blend, fusion, versatile, adaptable, bridge | Mid-range style products |
| Industrial | raw, metal, concrete, warehouse, exposed, urban | Modern metals finishes |
| Coastal | nautical, beach, bright, fresh, maritime, breezy | Light finishes |
| Rustic | natural, wood, stone, earthy, reclaimed, weathered | Earth tones |
| Scandinavian | nordic, minimalist, functional beauty, light | Clean design lines |
| Art Deco | geometric, bold, glamorous, vintage elegance | Detailed patterns |
| Victorian | ornate, detailed, classical, gothic, period | Ornamental features |
| Mediterranean | warm, tuscan, italian, spanish, earthy | Warm tones |
| Japanese | zen, harmony, natural materials, minimalist | Natural materials |
| Contemporary | current, cutting-edge, innovation | Latest collections |
| Transitional Modern | modern + traditional balance | Mid-contemporary products |
| Eclectic | mix, curated, unique, personalized | Varied feature sets |
| Bohemian | artistic, free-spirited, layered, unconventional | Colorful options |
| Glam | glamorous, shiny, bold, statement, luxury finish | Chrome, polished finishes |
| Industrial Chic | industrial + modern aesthetic | Exposed finishes |
| Farmhouse | rustic, farmhouse, country, lived-in | Country aesthetic |
| Mid-Century | mid-century, retro, vintage, atomic age | Vintage styling |
| Transitional Spa | spa + traditional blend | Hybrid features |
| Urban | city, urban loft, metropolitan | Metropolitan design |
| Nature-Inspired | organic, biophilic, natural forms, sustainable | Organic shapes |

**Theme Matching Process:**
1. Extract first 1-2 sentences of product description
2. Scan for exact keyword matches
3. Apply logical inference (e.g., "whirlpool jets" → Spa theme)
4. Score confidence (0.0-1.0) based on keyword density
5. Return top 2-4 themes per product

---

## 3. Multi-Agent Architecture

### 3.1 Agent 1: Extraction Agent

**Purpose:** Enrich raw product data with theme mappings
**Input:** Raw product JSON from scraper
**Output:** Products with inferred_themes field populated
**Logic:**
```
FOR each product:
  description = product.description + product.name
  themes = []
  FOR each theme in KOHLER_THEMES:
    keyword_matches = count_keyword_matches(description, theme.keywords)
    inference_score = apply_logical_inference(description, theme)
    confidence = (keyword_matches * 0.7) + (inference_score * 0.3)
    IF confidence > 0.5:
      themes.append({theme, confidence})
  product.inferred_themes = sort_by_confidence(themes)
  product.primary_theme = themes[0]
```

### 3.2 Agent 2: Recommendation Agent

**Purpose:** Suggest product bundles based on user input
**Input:** 
- User theme selection (multi-select from 25 themes)
- Budget constraint (hard bound)
- Category selection (checkboxes for which product types)
- Bathroom dimensions
**Output:** Recommended bundle + alternatives for refresh

**Flow:**
```
1. User provides theme + budget + dimensions + categories
2. Filter products:
   - Only include selected categories
   - Only include products in stock (availability = true)
   - Only include products within budget
3. Score remaining products:
   - Theme Match: % of user themes in product themes
   - Bundle Cohesion: How well product fits with previously selected products
   - Category Balance: Ensure one product per selected category
4. Recommend one bundle (highest combined score)
5. If user locks products + clicks refresh:
   - Re-score for unlocked categories only
   - Keep locked products + maintain bundle cohesion
```

**Scoring Formula:**
```
SCORE = (Theme_Match × 0.35) + (Bundle_Cohesion × 0.50) + (Category_Balance × 0.15)

Where:
- Theme_Match: % of user's selected themes present in product's inferred themes
- Bundle_Cohesion: Visual/style consistency score (0-1.0)
  - Primary theme match across all selected products (+0.4)
  - Color/finish consistency (+0.3)
  - Price tier consistency (+0.2)
  - Visual style consistency (+0.1)
- Category_Balance: Penalty if category already filled (ensures 1 per category)
```

**Hard Constraints (Filters, Not Scored):**
- Budget: Total bundle cost ≤ user's budget cap
- Availability: Only in-stock products
- Category: Only from user-selected categories

### 3.3 Agent 3: Placement Constraining Agent

**Purpose:** Validate and place products on 2D bathroom grid
**Input:** Recommended bundle, bathroom dimensions
**Output:** 2D grid layout with constraint validation

**Constraint Rules:**

| Constraint Type | Rules | Example |
|-----------------|-------|---------|
| **Spatial Dependencies** | Faucet must be above sink; shower head on wall; toilet needs fixture below | Faucet: x=sink.x, y=sink.y-6" |
| **Exclusivity** | Toilet + Bidet don't coexist; can't have 2 primary sinks in 60" width | IF toilet=true THEN bidet=false |
| **Clearance Requirements** | Toilet: 15" clearance both sides; Sink: 24" clearance; Shower: wall-mounted | validate_clearance(product, grid) |
| **Surface Mounting** | Mirrors/cabinets on walls only; basins on counters/sinks | product.mount_type in grid.available_surfaces |
| **Accessibility** | Fixtures must have minimum approach space | clearance ≥ ADA_MIN (36") |

**Placement Algorithm:**
```
1. Create grid based on bathroom dimensions
   - Cell size: 1" or 6" (configurable)
   - Example: 60" x 80" = 60x80 cells
   
2. FOR each selected product in bundle:
   a. Determine product footprint (from dimensions)
   b. Identify valid placement zones (wall vs floor)
   c. Check constraint rules:
      - Spatial dependencies (dependencies already placed?)
      - Clearance requirements (enough space?)
      - Exclusivity (conflicts with locked products?)
   d. Place product at valid location OR flag conflict
   
3. Validate final layout:
   - All products placed
   - All constraints satisfied
   - Visual flow is logical (e.g., sink/faucet grouped)
   
4. Return:
   - Grid visualization data
   - List of constraint violations (if any)
```

---

## 4. UI Components

### 4.1 Left Panel: Conversational Agent

**Purpose:** Gather user input and guide recommendations

**Conversation Flow:**
```
1. Agent: "Welcome to KOHLER Bathroom Designer. 
   Let's create your perfect bathroom.
   
   First, what's your style?
   [Multi-select: 25 themes with descriptions]"
   
2. User selects themes (e.g., Modern + Spa)

3. Agent: "Great choices! 
   What's your budget for the full bathroom?
   [Input: $1,000 - $20,000]"
   
4. User enters budget (e.g., $8,000)

5. Agent: "Perfect! What's your bathroom size?
   [Input: Width (inches) × Depth (inches)]"
   
6. User enters dimensions (e.g., 60 x 84)

7. Agent: "Which products do you want to include?
   [Checkboxes for: Toilet, Basin, Faucet, Bathtub, Shower, 
                     Mirror, Cabinet, Vanity, etc.]"
   
8. User checks desired categories

9. Agent: "Looking for your perfect bundle... 
   [Processes → Generates bundle]
   
   Here's my recommendation:
   [Displays bundle product list]
   
   Want to lock any products you love, or refresh others?"
```

**Refinement Loop:**
- User can "lock" products they like
- Click "refresh" to re-recommend for unlocked categories
- Iterate until satisfied

### 4.2 Center/Top: Product List

**Layout:**
```
┌─────────────────────────────────────────────┐
│  Recommended Bundle                         │
├─────────────────────────────────────────────┤
│ 1. Toilet: Entity 1.6 GPF         $189.99   │
│    [Link to product] [Color: White]         │
│    [Lock] [Remove]                          │
│                                             │
│ 2. Basin: Memoirs 24" Pedestal    $279.50   │
│    [Link to product] [Color: Biscuit]       │
│    [Lock] [Remove]                          │
│                                             │
│ 3. Faucet: Archer Polished Chrome $149.00   │
│    [Link to product] [Finish: Chrome]       │
│    [Lock] [Remove]                          │
│                                             │
│ ... (more products)                         │
│                                             │
│ TOTAL BUNDLE: $7,842.35 / $8,000 Budget ✓   │
└─────────────────────────────────────────────┘
```

**Each Product Card Shows:**
- Product name + SKU
- Price
- Color/finish
- Link to full Kohler product page
- Lock/Remove buttons
- Primary theme badge (e.g., "Modern" in color)

### 4.3 Right Panel: 2D Bathroom Layout Grid

**Purpose:** Visual representation of product placement

**Grid Visualization:**
```
┌──────────────────────────────────────┐
│  Your Bathroom Layout (60" × 80")    │
├──────────────────────────────────────┤
│                                      │
│  [Mirror]        [Cabinet]           │
│                                      │
│  [Sink/Basin]                        │
│  [Faucet ↓]                          │
│                                      │
│  ┌──────────────────────────────┐    │
│  │    Bathtub                   │    │
│  │                              │    │
│  └──────────────────────────────┘    │
│                                      │
│  [Toilet]  [Bidet]                   │
│                                      │
│  ┌──────────────────────────────┐    │
│  │    Shower Enclosure          │    │
│  │                              │    │
│  └──────────────────────────────┘    │
│                                      │
└──────────────────────────────────────┘
```

**Grid Features:**
- Symbolic placement (not photorealistic)
- Shows spatial relationships between products
- Validates constraint rules during visualization
- Static view (no dragging initially)
- Responsive to different bathroom dimensions

---

## 5. Data Schemas

### 5.1 Product JSON Schema

Already defined in Section 2.3

### 5.2 Bundle Output Schema

```json
{
  "bundle_id": "BUNDLE_20250920_001",
  "created_at": "2025-09-20T14:30:00Z",
  "user_input": {
    "selected_themes": ["Modern", "Spa"],
    "budget": 8000,
    "dimensions": {
      "width": 60,
      "depth": 84
    },
    "selected_categories": ["toilet", "basin", "faucet", "bathtub", "shower", "mirror", "vanity"]
  },
  "recommended_bundle": {
    "products": [
      {
        "sku": "K-26107-LA-0",
        "name": "Entity 60\" x 36\" Alcove Bath",
        "category": "bathtubs",
        "price": 818.25,
        "matched_themes": ["Modern", "Minimalist"],
        "theme_confidence": 0.92,
        "placement": {
          "x": 0,
          "y": 24,
          "width": 60,
          "height": 36
        },
        "locked": false
      },
      ...
    ],
    "total_price": 7842.35,
    "within_budget": true,
    "primary_theme": "Modern",
    "theme_cohesion_score": 0.88,
    "constraint_violations": []
  }
}
```

---

## 6. Constraint Logic

### 6.1 Spatial Placement Rules

**Fixture Dependencies:**
```
IF faucet.category = "faucet":
  faucet.mount_position = ABOVE(selected_basin)
  faucet.x = basin.center_x
  faucet.y = basin.y - 6_inches

IF toilet.selected AND bidet.selected:
  CONFLICT: Can't coexist in standard 60" width
  
IF shower_enclosure.selected:
  shower_enclosure.mount = "WALL_MOUNTED"
  shower_enclosure.requires_plumbing_wall = true
```

### 6.2 Clearance Constraints

```
IF product = "toilet":
  min_clearance_sides = 15_inches
  min_clearance_front = 24_inches
  
IF product = "sink":
  min_approach_distance = 24_inches
  
IF product = "shower":
  min_interior_width = 36_inches
  min_interior_depth = 36_inches
  min_approach_distance = 24_inches
```

### 6.3 Bundle Cohesion Rules

**Theme Consistency:**
```
primary_themes = [product.primary_theme for each product]
IF all products share >= 1 common theme:
  cohesion_score += 0.4

IF all products use same color_finish palette:
  cohesion_score += 0.3
  
IF all products in same price_tier:
  cohesion_score += 0.2
```

---

## 7. Integration Flow (End-to-End)

```
USER INPUT
   ↓
┌─────────────────────────────────────────┐
│ 1. Chatbot collects:                   │
│    - Theme selection (multi-select)     │
│    - Budget (hard constraint)           │
│    - Dimensions (grid basis)            │
│    - Categories (hard constraint)       │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ 2. Recommendation Agent processes:      │
│    - Filter products (budget, stock)    │
│    - Score by theme match               │
│    - Score by bundle cohesion           │
│    - Return top bundle + alternatives   │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ 3. Display Product List:                │
│    - SKU, name, price, color, link      │
│    - Lock/remove buttons                │
│    - Total price vs budget              │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ 4. Placement Agent processes:           │
│    - Validate constraint rules          │
│    - Place on 2D grid                   │
│    - Flag violations (if any)           │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ 5. Display 2D Layout:                   │
│    - Grid-based bathroom visualization  │
│    - Symbolic product placement         │
│    - Spatial relationships visible      │
└─────────────────────────────────────────┘
   ↓
REFINEMENT LOOP
(User can lock products → click "refresh" → re-recommend)

   ↓
FINAL OUTPUT
   ↓
┌─────────────────────────────────────────┐
│ Bundle JSON + 2D Layout Grid            │
│ User can download/share                 │
└─────────────────────────────────────────┘
```

---

## 8. Tech Stack & Implementation

### 8.1 Backend

**Language:** Python 3.9+
**Web Scraping:**
- Selenium (JS-heavy site navigation)
- BeautifulSoup (HTML parsing)
- Requests (HTTP)

**Data Processing:**
- Pandas (product data manipulation)
- JSON (data storage)
- String similarity libraries (keyword matching)

**Agent Logic:**
- Custom Python agents (recommendation scoring)
- Constraint validation engine (placement rules)

### 8.2 Frontend

**Framework:** React (or similar SPA framework)
**Components:**
- Chatbot UI (conversational interface)
- Product list (scrollable, sortable)
- 2D grid visualization (SVG or Canvas)

**Libraries:**
- D3.js or similar (grid visualization)
- Axios (API calls)

### 8.3 Data Storage

**Format:** JSON files (initial MVP)
**Scaling:** Can migrate to PostgreSQL + S3 for production

### 8.4 Deployment

**Local Development:**
- Python backend running on localhost:5000
- React frontend on localhost:3000
- JSON files in `/data/` directory

---

## 9. Implementation Timeline

### Phase 1: Data Preparation (2 hours - In Progress)
- ✅ Web scraping from Kohler website
- ✅ Extract product descriptions (clicking "Read More")
- ⏳ Compile product JSON files by category

### Phase 2: Backend Services (Implementation)
- Extraction Agent (theme mapping)
- Recommendation Agent (scoring + bundle selection)
- Placement Constraining Agent (2D grid logic)

### Phase 3: Frontend UI (Implementation)
- Chatbot interface
- Product list display
- 2D bathroom layout grid

### Phase 4: Integration & Testing (Implementation)
- Connect all agents to UI
- End-to-end user flow testing
- Constraint validation testing

### Phase 5: Refinement & Presentation (Post-Implementation)
- Film product demo
- Create presentation deck

---

## 10. Key Design Decisions

**Why Agent-Based Architecture?**
- Separation of concerns (extraction, recommendation, placement)
- Extensibility (can swap agents independently)
- Reusability (agents can be used in other contexts)

**Why Bundle Cohesion > Individual Score?**
- Users are buying a coordinated bathroom, not individual products
- Visual harmony matters more than individual product prestige

**Why Hard Constraints (Not Scored)?**
- Budget and category are non-negotiable user inputs
- Scoring only recommends within the feasible set

**Why 2D (Not 3D)?**
- Faster development
- MVP sufficient for spatial relationships
- 3D can be added later with same data

**Why Symbolic (Not Photorealistic)?**
- Focuses on layout logic, not aesthetics
- Reduces complexity
- Real photos from product links available

---

## Questions for Review

**Before we proceed with implementation, please confirm:**

1. **Data Format:** Are JSON files the right choice, or should we prep for a database from the start?
2. **Agent Orchestration:** Should agents be sequential functions, or do we need a more robust message-passing system?
3. **UI Priority:** Should we prioritize chatbot UX or 2D visualization accuracy first?
4. **Scope Confirmation:** Are we confident that 25 themes can be matched reliably with truncated descriptions + logical inference?

---

**Document Status:** Ready for approval
**Created:** 2025-09-20
