# KOHLER Bathroom Designer - Setup & Running Instructions

## Project Structure

```
KOHLER/
├── backend/
│   ├── api.py                     # Flask REST API server
│   ├── extraction_agent.py        # Theme inference engine
│   ├── recommendation_agent.py    # Bundle recommendation logic
│   ├── placement_agent.py         # 2D grid placement & constraints
│   ├── kohler_system.py           # System orchestrator
│   └── data/products.json         # Real KOHLER product catalog
├── src/
│   ├── index.jsx                  # (re-exported at repo root, see index.jsx)
│   ├── App.jsx                    # Main app component
│   ├── App.css                    # Main app styling
│   ├── utils/
│   │   └── bundleRationale.js     # Builds the plain-language bundle rationale
│   └── components/
│       ├── LandingPage.jsx/.css   # Entry screen
│       ├── ChatAgent.jsx/.css     # Conversational setup flow
│       ├── SetupPanel.jsx/.css    # Room dimension controls
│       ├── BundlePanel.jsx/.css   # Bundle review / lock / refresh
│       └── GridVisualization.jsx/.css  # 2D plan + isometric 3D room view
├── index.html                     # HTML entry point
├── index.jsx                      # React entry point
├── package.json                   # Node.js dependencies
├── vite.config.js                 # Vite build configuration
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore file
├── KOHLER_SYSTEM_ARCHITECTURE.md  # Original system design documentation
├── PLACEMENT_AGENT_RULES.md       # Placement engine's full rule spec
└── README_SETUP.md                # This file
```

## Prerequisites

- Python 3.8+ with pip
- Node.js 16+ with npm
- Git

## Backend Setup (Flask API)

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Flask API Server

```bash
python backend/api.py
```

The Flask server will start on `http://localhost:5000`

**Available Endpoints:**
- `GET /api/health` - Health check
- `GET /api/themes` - Get available design themes + their keyword sets
- `GET /api/categories` - Get product categories
- `POST /api/infer-themes` - Infer a best-guess design theme from freeform vision text
  - Request body: `{"text": "cozy and warm, nothing too fancy"}`
  - Always returns at least one theme (`low_confidence: true` when the match was a fallback rather than a strong keyword hit) -- never a dead end.
- `POST /api/recommend` - Get bundle recommendations
  - Request body: `{themes: [], budget: 500000, width: 60, depth: 80, categories: [], locked_products: []}`
  - `budget`/prices are in INR (₹); `width`/`depth` are in inches.
- `POST /api/refresh` - Refresh recommendations for unlocked categories only
- `GET /api/products/search` - Search products by theme/category

**Note:** Flask does not hot-reload backend `.py` changes -- restart `python backend/api.py` after editing any backend file.

## Frontend Setup (React + Vite)

### 1. Install Node Dependencies

```bash
npm install
```

### 2. Run Development Server

```bash
npm run dev
```

The React app will start on `http://localhost:3000`

**Important:** The Flask API server must be running on `http://localhost:5000` for the frontend to fetch recommendations.

## Running the Full Application

### Terminal 1: Start Flask Backend

```bash
python backend/api.py
```

Wait for: `Running on http://127.0.0.1:5000`

### Terminal 2: Start React Frontend

```bash
npm run dev
```

Wait for: `Local: http://localhost:3000/`

### Terminal 3 (Optional): Monitor Flask Logs

Keep the first terminal visible to see API request logs and any errors.

## Using the Application

1. **Open Browser:** Navigate to `http://localhost:3000`
2. **Enter the app** from the landing page
3. **Pick product categories** you want in your bundle
4. **Describe your vision** in your own words -- the system infers a design theme from it (always giving a confident best guess) and you can override the pick
5. **Set budget and room dimensions** (width/depth in inches, budget in ₹)
6. **Review the bundle**: see recommended real KOHLER products, their total price vs. budget, and a plain-language rationale for why they were chosen together
7. **Refine:** lock favorite products and click "Refresh" to get new recommendations for the rest, or "Build my bundle" to generate the full room layout
8. **View the room:** toggle between the 2D plan view and the isometric 3D view; click any fixture to open its real KOHLER product page; any spatial constraint issue (room too tight, item couldn't be placed) is shown explicitly, never hidden

## Building for Production

```bash
npm run build
```

This creates a `dist/` folder with optimized production files.

## Testing the API Directly

You can test the API without the frontend using curl:

```bash
# Health check
curl http://localhost:5000/api/health

# Get themes
curl http://localhost:5000/api/themes

# Get categories
curl http://localhost:5000/api/categories

# Infer a theme from freeform text
curl -X POST http://localhost:5000/api/infer-themes \
  -H "Content-Type: application/json" \
  -d '{"text": "modern and minimalist, clean lines, black fixtures"}'

# Get recommendations (example)
curl -X POST http://localhost:5000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "themes": ["Modern", "Contemporary"],
    "budget": 500000,
    "width": 96,
    "depth": 120,
    "categories": ["Toilets", "Basins", "Bathtubs", "Faucets", "Vanities", "Showers"],
    "locked_products": []
  }'
```

## Testing the Placement Engine Directly

The placement engine has its own standalone test scripts (not wired into a CI pipeline, run manually from `backend/`):

```bash
cd backend
python3 test_placement.py     # 8 hand-built room/bundle scenarios -- checks coincidence rules, wall-hugging, no overlaps, entrance clearance
python3 test_integration.py   # 4 full end-to-end scenarios through the real recommendation + placement pipeline
```

(If these files aren't present in your checkout, they were used during development for verification and can be recreated from `PLACEMENT_AGENT_RULES.md`'s rule list.)

## Troubleshooting

### Port 5000/3000 Already in Use

```bash
# Find process on port 5000
lsof -i :5000
kill -9 <PID>

# For Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### CORS Errors

- Flask API is already configured with `Flask-CORS`
- Ensure both servers are running on correct ports
- Check browser console for specific error messages

### React Component Not Rendering

- Verify all CSS files are in `src/` with correct paths
- Check browser developer console for JavaScript errors
- Ensure Flask API is returning valid JSON

### Backend changes not taking effect

- Flask does not hot-reload `.py` files -- stop and restart `python backend/api.py`
- Frontend `.jsx`/`.css` changes hot-reload automatically via Vite

## System Architecture

See `KOHLER_SYSTEM_ARCHITECTURE.md` for the original system design write-up, and `PLACEMENT_AGENT_RULES.md` for the full hard/strong/optimization rule spec the placement engine implements (functional-station model, coincidence rules, entrance clearance, long-wall assembly logic).
