# KOHLER Bathroom Designer

An AI-assisted bathroom design tool built on KOHLER's real product catalog. A user describes their vision, picks a budget and room size, and the system recommends a coordinated bundle of real KOHLER products (vanity, toilet, shower/tub, faucet, mirror, lighting, accessories) that fits the budget, matches a design theme, and is laid out to scale in an interactive 2D/3D room visualization -- with every constraint violation reported honestly instead of silently ignored.

**Live components:** Flask REST API (Python) + React/Vite single-page app.

## What it does

1. **Vision → Theme** -- the user describes their bathroom in their own words; the system reads it against KOHLER's 25 design themes using weighted keyword matching and always returns a confident best-guess theme (never a dead-end "couldn't match"), while still letting the user pick a different one.
2. **Budget + room + categories → Bundle** -- a recommendation engine builds a cohesive product bundle from the real ~1,500-SKU catalog, respecting budget as a hard constraint and preferring products that share the chosen theme(s).
3. **Bundle → Layout** -- a placement engine classifies every product into a functional station (wash / toilet / wet) and lays the stations out along the room's actual long wall, entrance-aware, with hard rules for what must be physically coincident (faucet+mirror+light on the vanity, bidet seat on the toilet) and honest violation reporting when a room genuinely can't fit everything.
4. **Layout → Visualization** -- an isometric "3D" view and a plan (top-down) view, both rendered live from the real placement data (not a staged render), with clickable fixtures linking to their real KOHLER product pages.
5. **Refine** -- lock products you like and refresh the rest; the bundle re-optimizes around what's locked.

## Repository layout

```
KOHLER/
├── backend/
│   ├── api.py                   # Flask REST API
│   ├── extraction_agent.py      # Theme inference (keyword/pattern matching over 25 KOHLER themes)
│   ├── recommendation_agent.py  # Budget-bounded, theme-cohesive bundle selection
│   ├── placement_agent.py       # Functional-station spatial placement + constraint checking
│   ├── kohler_system.py         # Orchestrator gluing the three agents together
│   └── data/products.json       # Real KOHLER product catalog (~1,500 SKUs)
├── src/
│   ├── App.jsx / App.css        # Top-level app shell + layout
│   ├── components/
│   │   ├── LandingPage.jsx      # Entry screen
│   │   ├── ChatAgent.jsx        # Conversational setup flow (categories, vision, theme, budget)
│   │   ├── SetupPanel.jsx       # Room dimensions / setup controls
│   │   ├── BundlePanel.jsx      # Bundle review, lock/refresh, proceed
│   │   └── GridVisualization.jsx# 2D plan + isometric 3D room rendering
│   └── utils/bundleRationale.js # Builds the plain-language "here's my thinking" summary
├── index.html / index.jsx       # Vite entry points
├── package.json / vite.config.js
├── requirements.txt             # Python dependencies
├── PLACEMENT_AGENT_RULES.md     # Full hard/strong/optimization rule spec for the placement engine
├── KOHLER_SYSTEM_ARCHITECTURE.md# Original system design document
└── README_SETUP.md              # Detailed setup/run/troubleshooting reference
```

## Quick start

**Prerequisites:** Python 3.8+, Node.js 16+, npm.

```bash
# 1. Backend (Terminal 1)
pip install -r requirements.txt
python backend/api.py
# -> Flask API on http://localhost:5000

# 2. Frontend (Terminal 2)
npm install
npm run dev
# -> App on http://localhost:3000
```

Open `http://localhost:3000`, click through the guided setup (products → vision → style → budget/space → confirm), and click **Build my bundle**. See `README_SETUP.md` for full endpoint docs, curl examples, and troubleshooting.

## Tech stack

- **Backend:** Python, Flask, Flask-CORS
- **Frontend:** React 18, Vite, plain CSS (no UI framework)
- **"AI" layer:** deterministic, explainable weighted keyword/pattern matching for theme inference (not an external LLM call) -- chosen so recommendations are reproducible, auditable, and don't depend on external API latency/cost
- **Data:** a real, scraped KOHLER US product catalog (JSON), ~1,500 SKUs across 12 categories
- **Testing:** custom Python test harnesses (`test_placement.py`, `test_integration.py`) plus a large combinatorial sweep script validating the placement engine across room sizes, bundles, and themes

## Documentation

- `README_SETUP.md` -- detailed setup, all API endpoints, curl examples, troubleshooting
- `PLACEMENT_AGENT_RULES.md` -- the full spatial rule spec (hard rules, strong preferences, optimizations) the placement engine implements
- `KOHLER_SYSTEM_ARCHITECTURE.md` -- the original system design document written before implementation
- Prompts & build-process documentation, mind map, and presentation deck are included separately in this submission alongside a short video walkthrough.
