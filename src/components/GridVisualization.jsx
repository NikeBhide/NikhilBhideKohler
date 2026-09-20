import React, { useState, useMemo } from 'react';
import './GridVisualization.css';

// Short, generic labels for the grid boxes -- a full product name doesn't
// fit in a small box and isn't what someone needs to recognize a fixture
// by at a glance.
const CATEGORY_LABELS = {
  'Toilets': 'Toilet',
  'Toilet Bidet Seats': 'Toilet',
  'Smart Toilets': 'Toilet',
  'Basins': 'Sink',
  'Vanities': 'Vanity',
  'Faucets': 'Faucet',
  'Bathtubs': 'Tub',
  'Showers': 'Shower',
  'Digital Showering': 'Shower Panel',
  'Mirrors': 'Mirror',
  'Cabinets': 'Cabinet',
  'Lighting': 'Light',
  'Bathroom Accessories': 'Accessory',
};

// Category default footprints (inches) -- mirrors backend PRODUCT_SPECS
// defaults, used only for drawing since the API doesn't send per-product
// dimensions.
const CATEGORY_FOOTPRINTS = {
  'Toilets': { width: 16, depth: 28 },
  'Toilet Bidet Seats': { width: 16, depth: 28 },
  'Smart Toilets': { width: 16, depth: 28 },
  'Basins': { width: 24, depth: 18 },
  'Faucets': { width: 8, depth: 4 },
  'Bathtubs': { width: 60, depth: 32 },
  'Showers': { width: 36, depth: 36 },
  'Digital Showering': { width: 8, depth: 4 },
  'Mirrors': { width: 30, depth: 2 },
  'Cabinets': { width: 24, depth: 8 },
  'Vanities': { width: 48, depth: 22 },
  'Lighting': { width: 12, depth: 4 },
  'Bathroom Accessories': { width: 12, depth: 4 },
};

// Rendering-only floor for very small footprints (faucets, mirrors,
// lighting, digital showering panels) so they stay legible and clickable
// at room scale -- this never touches the real placement data or the
// backend's actual footprint math, only how big the box is drawn.
const MIN_DISPLAY_DIM = 11;

function getDisplayFootprint(category) {
  const fp = CATEGORY_FOOTPRINTS[category] || { width: 24, depth: 18 };
  return {
    width: Math.max(fp.width, MIN_DISPLAY_DIM),
    depth: Math.max(fp.depth, MIN_DISPLAY_DIM),
  };
}

// Categories that are wall/fixture-mounted extras which the placement
// agent deliberately places *coincident* with their owning fixture (H1:
// faucet on basin, H3: mirror/light on the wash anchor -- see
// PLACEMENT_AGENT_RULES.md). That's correct data, but drawing several
// boxes at the exact same (x, y) buries all but the last one under
// whichever anchor is biggest. These get fanned out a few inches apart
// for rendering only -- the underlying placement_map coordinates (and
// the coincidence the rules require) are never touched.
const FAN_CATEGORIES = new Set(['Faucets', 'Mirrors', 'Lighting', 'Digital Showering']);
const FAN_SPACING = 9; // inches, visual only

function computeFanOffsets(placedEntries, productsBySku) {
  const groups = {};
  placedEntries.forEach(([sku, pos]) => {
    const category = (productsBySku[sku] || {}).category;
    if (!FAN_CATEGORIES.has(category)) return;
    const key = `${pos.x}_${pos.y}`;
    groups[key] = groups[key] || [];
    groups[key].push(sku);
  });
  const offsets = {};
  Object.values(groups).forEach((skus) => {
    skus.forEach((sku, i) => {
      offsets[sku] = i * FAN_SPACING;
    });
  });
  return offsets;
}

const CATEGORY_COLORS = {
  'Toilets': '#e8e2d4',
  'Toilet Bidet Seats': '#e8e2d4',
  'Smart Toilets': '#e8e2d4',
  'Basins': '#d8cba8',
  'Vanities': '#8a6f4a',
  'Faucets': '#c9a24a',
  'Bathtubs': '#eee8dc',
  'Showers': '#9fb3ab',
  'Digital Showering': '#6f8f87',
  'Mirrors': '#7a8a94',
  'Cabinets': '#5c4a36',
  'Lighting': '#e0bb5e',
  'Bathroom Accessories': '#b7ab94',
};

// Realistic-ish mount heights/heights (inches) for the 3D massing model.
// Floor fixtures sit at baseZ 0; wall/counter-mounted items float above
// the floor at roughly the height they're actually installed at.
const CATEGORY_ISO = {
  'Bathtubs': { height: 18, baseZ: 0 },
  'Showers': { height: 10, baseZ: 0, showerHead: true },
  'Digital Showering': { height: 8, baseZ: 34 },
  'Toilets': { height: 16, baseZ: 0 },
  'Toilet Bidet Seats': { height: 16, baseZ: 0 },
  'Smart Toilets': { height: 16, baseZ: 0 },
  'Basins': { height: 32, baseZ: 0 },
  'Vanities': { height: 32, baseZ: 0 },
  'Faucets': { height: 9, baseZ: 32 },
  'Mirrors': { height: 26, baseZ: 40 },
  'Cabinets': { height: 22, baseZ: 50 },
  'Lighting': { height: 6, baseZ: 68 },
  'Bathroom Accessories': { height: 6, baseZ: 30 },
};

const WALL_HEIGHT = 66;
const ISO_COS = Math.cos(Math.PI / 6);
const ISO_SIN = Math.sin(Math.PI / 6);

function shade(hex, amount) {
  // amount < 0 darkens, > 0 lightens. hex like '#rrggbb'.
  const n = parseInt(hex.slice(1), 16);
  let r = (n >> 16) & 0xff;
  let g = (n >> 8) & 0xff;
  let b = n & 0xff;
  const adjust = (c) => Math.max(0, Math.min(255, Math.round(c + amount)));
  r = adjust(r); g = adjust(g); b = adjust(b);
  return `rgb(${r}, ${g}, ${b})`;
}

function GridVisualization({ placementMap, products, entrance, violations, constraintsSatisfied, bathroomWidth, bathroomDepth }) {
  const [viewMode, setViewMode] = useState('3d');
  const width = Number(bathroomWidth) || 60;
  const depth = Number(bathroomDepth) || 80;
  const unit = 4;
  const gridWidth = width * unit;
  const gridHeight = depth * unit;

  const productsBySku = {};
  (products || []).forEach((p) => {
    productsBySku[p.sku] = p;
  });

  const placedEntries = placementMap ? Object.entries(placementMap) : [];
  const fanOffsets = useMemo(() => computeFanOffsets(placedEntries, productsBySku), [placementMap, products]);

  // ---------- Isometric ("3D") view ----------
  const isoScene = useMemo(() => {
    if (placedEntries.length === 0) return null;
    const scale = unit;

    const project = (x, y, z) => [
      (x - y) * ISO_COS * scale,
      (x + y) * ISO_SIN * scale - z * scale,
    ];

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    const track = ([sx, sy]) => {
      minX = Math.min(minX, sx); maxX = Math.max(maxX, sx);
      minY = Math.min(minY, sy); maxY = Math.max(maxY, sy);
    };

    const floorCorners = [[0, 0], [width, 0], [width, depth], [0, depth]].map(([x, y]) => project(x, y, 0));
    floorCorners.forEach(track);

    const backWall = [[0, 0, 0], [width, 0, 0], [width, 0, WALL_HEIGHT], [0, 0, WALL_HEIGHT]].map(([x, y, z]) => project(x, y, z));
    const leftWall = [[0, 0, 0], [0, depth, 0], [0, depth, WALL_HEIGHT], [0, 0, WALL_HEIGHT]].map(([x, y, z]) => project(x, y, z));
    backWall.forEach(track);
    leftWall.forEach(track);

    const items = placedEntries.map(([sku, pos]) => {
      const product = productsBySku[sku] || {};
      const category = product.category || 'Unknown';
      const footprint = getDisplayFootprint(category);
      const iso = CATEGORY_ISO[category] || { height: 16, baseZ: 0 };
      const px = pos.x + (fanOffsets[sku] || 0), py = pos.y;
      const w = footprint.width, d = footprint.depth;
      const baseZ = iso.baseZ, h = iso.height;

      const top = [
        project(px, py, baseZ + h),
        project(px + w, py, baseZ + h),
        project(px + w, py + d, baseZ + h),
        project(px, py + d, baseZ + h),
      ];
      const right = [
        project(px + w, py, baseZ),
        project(px + w, py + d, baseZ),
        project(px + w, py + d, baseZ + h),
        project(px + w, py, baseZ + h),
      ];
      const front = [
        project(px + w, py + d, baseZ),
        project(px, py + d, baseZ),
        project(px, py + d, baseZ + h),
        project(px + w, py + d, baseZ + h),
      ];
      [...top, ...right, ...front].forEach(track);

      const topCenter = project(px + w / 2, py + d / 2, baseZ + h);
      const color = CATEGORY_COLORS[category] || '#999';
      const label = CATEGORY_LABELS[category] || category;

      let showerHead = null;
      if (iso.showerHead) {
        const headBase = project(px + w / 2, py + d / 2, baseZ + h);
        const headTop = project(px + w / 2, py + d / 2, 72);
        [headBase, headTop].forEach(track);
        showerHead = { headBase, headTop, headTopRaw: [px + w / 2, py + d / 2, 72] };
      }

      return {
        sku, product, category, label, color, top, right, front, topCenter,
        // Depth-sort primarily by screen position (correct painter's-algorithm
        // ordering for items that don't share a footprint); break ties by
        // area ascending so a small fanned/attached item (faucet, mirror,
        // light) always paints AFTER -- on top of -- a bigger anchor it's
        // near or coincident with, instead of getting buried under it.
        sortKey: px + py,
        area: w * d,
        showerHead,
      };
    });

    items.sort((a, b) => (a.sortKey - b.sortKey) || (a.area - b.area));

    // Entrance marker on the open (near) edge.
    let entranceLine = null;
    if (entrance) {
      const ex = entrance.x, ew = entrance.width;
      entranceLine = {
        a: project(ex, depth, 0),
        b: project(ex + ew, depth, 0),
        label: project(ex + ew / 2, depth, 0),
      };
      [entranceLine.a, entranceLine.b, entranceLine.label].forEach(track);
    }

    const pad = 40;
    const viewBox = `${minX - pad} ${minY - pad - 20} ${maxX - minX + pad * 2} ${maxY - minY + pad * 2 + 20}`;

    return { floorCorners, backWall, leftWall, items, entranceLine, viewBox };
  }, [placementMap, products, entrance, width, depth, fanOffsets]);

  const renderIsoBox = (item) => {
    const pathOf = (pts) => `M ${pts.map((p) => p.join(',')).join(' L ')} Z`;
    const box = (
      <g key={item.sku}>
        <path d={pathOf(item.front)} fill={shade(item.color, -55)} stroke="#000" strokeOpacity="0.25" strokeWidth="1" />
        <path d={pathOf(item.right)} fill={shade(item.color, -25)} stroke="#000" strokeOpacity="0.25" strokeWidth="1" />
        <path d={pathOf(item.top)} fill={item.color} stroke="#000" strokeOpacity="0.2" strokeWidth="1" />
        {item.showerHead && (
          <>
            <line x1={item.showerHead.headBase[0]} y1={item.showerHead.headBase[1]} x2={item.showerHead.headTop[0]} y2={item.showerHead.headTop[1]} stroke="#3d7ec2" strokeWidth="2" />
            <circle cx={item.showerHead.headTop[0]} cy={item.showerHead.headTop[1]} r="5" fill="#3d7ec2" />
          </>
        )}
      </g>
    );

    if (item.product.url) {
      return (
        <a key={item.sku} href={item.product.url} target="_blank" rel="noopener noreferrer" className="grid-product-link">
          <title>{`${item.product.name || item.label} — click to view on KOHLER.com`}</title>
          {box}
        </a>
      );
    }
    return box;
  };

  const renderIsoLabel = (item) => {
    const [cx, cy] = item.topCenter;
    const liftedY = cy - 26;
    const text = item.label.toUpperCase();
    const pillWidth = Math.max(46, text.length * 6.4 + 18);
    return (
      <g key={`label-${item.sku}`} className="iso-label-group">
        <line x1={cx} y1={cy} x2={cx} y2={liftedY + 9} stroke="#5b9bd8" strokeWidth="1" strokeDasharray="2 2" />
        <rect x={cx - pillWidth / 2} y={liftedY - 9} width={pillWidth} height={18} rx="9" fill="#0a1a30" stroke="#3d7ec2" strokeWidth="1" />
        <text x={cx} y={liftedY + 4} textAnchor="middle" fontSize="9.5" fontWeight="700" letterSpacing="0.04em" fill="#ffffff">
          {text}
        </text>
      </g>
    );
  };

  const renderIsoView = () => {
    if (!isoScene) {
      return <p className="no-placement">No placements available</p>;
    }
    const pathOf = (pts) => `M ${pts.map((p) => p.join(',')).join(' L ')} Z`;

    return (
      <svg viewBox={isoScene.viewBox} width="100%" height="100%" className="symbolic-grid" preserveAspectRatio="xMidYMid meet">
        {/* Enclosing walls (the two sides away from the viewer/entrance) */}
        <path d={pathOf(isoScene.backWall)} fill="#0d1f38" stroke="#1f3a5c" strokeWidth="1" />
        <path d={pathOf(isoScene.leftWall)} fill="#123152" stroke="#1f3a5c" strokeWidth="1" />
        {/* Floor */}
        <path d={pathOf(isoScene.floorCorners)} fill="#faf7f0" stroke="#3d7ec2" strokeWidth="1.5" />
        {/* Floor tile lines every 12" */}
        {Array.from({ length: Math.ceil(width / 12) }).map((_, i) => {
          const x = (i + 1) * 12;
          if (x >= width) return null;
          const [x1, y1] = [(x - 0) * ISO_COS * unit, (x + 0) * ISO_SIN * unit];
          const [x2, y2] = [(x - depth) * ISO_COS * unit, (x + depth) * ISO_SIN * unit];
          return <line key={`gx-${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1f4e8c" strokeOpacity="0.18" strokeWidth="0.75" />;
        })}
        {Array.from({ length: Math.ceil(depth / 12) }).map((_, i) => {
          const y = (i + 1) * 12;
          if (y >= depth) return null;
          const [x1, y1] = [(0 - y) * ISO_COS * unit, (0 + y) * ISO_SIN * unit];
          const [x2, y2] = [(width - y) * ISO_COS * unit, (width + y) * ISO_SIN * unit];
          return <line key={`gy-${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1f4e8c" strokeOpacity="0.18" strokeWidth="0.75" />;
        })}

        {isoScene.entranceLine && (
          <g>
            <line
              x1={isoScene.entranceLine.a[0]} y1={isoScene.entranceLine.a[1]}
              x2={isoScene.entranceLine.b[0]} y2={isoScene.entranceLine.b[1]}
              stroke="#3d7ec2" strokeWidth="3" strokeDasharray="6 4"
            />
            <text
              x={isoScene.entranceLine.label[0]} y={isoScene.entranceLine.label[1] + 18}
              textAnchor="middle" fontSize="10" fontWeight="700" letterSpacing="0.08em" fill="#9fb4c9"
            >
              ENTRANCE
            </text>
          </g>
        )}

        {isoScene.items.map(renderIsoBox)}
        {isoScene.items.map(renderIsoLabel)}
      </svg>
    );
  };

  // ---------- Flat top-down ("Plan") view ----------
  const renderPlanView = () => {
    if (placedEntries.length === 0) {
      return <p className="no-placement">No placements available</p>;
    }

    const renderEntrance = () => {
      if (!entrance) return null;
      const doorX = entrance.x * unit;
      const doorWidth = entrance.width * unit;
      const doorY = gridHeight;
      return (
        <g>
          <rect x={doorX} y={doorY - 3} width={doorWidth} height={3} fill="#3d7ec2" />
          <path
            d={`M ${doorX} ${doorY} A ${doorWidth} ${doorWidth} 0 0 1 ${doorX + doorWidth} ${doorY - doorWidth}`}
            fill="none" stroke="#9fb4c9" strokeDasharray="4 3" strokeWidth="1.5"
          />
          <text x={doorX + doorWidth / 2} y={doorY + 16} textAnchor="middle" fontSize="12" fill="#9fb4c9" fontWeight="600">
            Entrance
          </text>
        </g>
      );
    };

    // Sort so fanned/attached small items (faucet, mirror, light) draw
    // after -- on top of -- the bigger anchor they're coincident with,
    // same reasoning as the iso view.
    const sortedEntries = [...placedEntries].sort(([skuA, posA], [skuB, posB]) => {
      const catA = (productsBySku[skuA] || {}).category;
      const catB = (productsBySku[skuB] || {}).category;
      const areaA = getDisplayFootprint(catA).width * getDisplayFootprint(catA).depth;
      const areaB = getDisplayFootprint(catB).width * getDisplayFootprint(catB).depth;
      return areaB - areaA;
    });

    return (
      <svg viewBox={`0 0 ${gridWidth} ${gridHeight + 30}`} width="100%" height="100%" className="symbolic-grid" preserveAspectRatio="xMidYMid meet">
        <rect x={0} y={0} width={gridWidth} height={gridHeight} fill="#0d1f38" stroke="#1f3a5c" strokeWidth="2" />
        {Array.from({ length: Math.ceil(width / 12) + 1 }).map((_, i) => (
          <line key={`vline-${i}`} x1={i * 12 * unit} y1={0} x2={i * 12 * unit} y2={gridHeight} stroke="#1f3a5c" strokeWidth="1" />
        ))}
        {Array.from({ length: Math.ceil(depth / 12) + 1 }).map((_, i) => (
          <line key={`hline-${i}`} x1={0} y1={i * 12 * unit} x2={gridWidth} y2={i * 12 * unit} stroke="#1f3a5c" strokeWidth="1" />
        ))}
        {sortedEntries.map(([sku, pos]) => {
          const product = productsBySku[sku] || {};
          const category = product.category || 'Unknown';
          const footprint = getDisplayFootprint(category);
          const px = pos.x + (fanOffsets[sku] || 0);
          const x = px * unit, y = pos.y * unit;
          const w = footprint.width * unit, h = footprint.depth * unit;
          const color = CATEGORY_COLORS[category] || '#999';
          const label = CATEGORY_LABELS[category] || category;
          const box = (
            <g key={sku}>
              <rect x={x} y={y} width={w} height={h} fill={color} stroke="#0a0a0b" strokeWidth="2" opacity="0.9" rx="3" />
              <text x={x + w / 2} y={y + h / 2} textAnchor="middle" dominantBaseline="middle" fontSize="12" fontWeight="700" fill="#1a1408">
                {label}
              </text>
            </g>
          );
          if (product.url) {
            return (
              <a key={sku} href={product.url} target="_blank" rel="noopener noreferrer" className="grid-product-link">
                <title>{`${product.name || label} — click to view on KOHLER.com`}</title>
                {box}
              </a>
            );
          }
          return box;
        })}
        {renderEntrance()}
      </svg>
    );
  };

  const violationCount = (violations || []).length;

  return (
    <div className="grid-visualization-container">
      <div className="visualization-header">
        <div>
          <p className="grid-eyebrow">Spatial Curation Engine</p>
          <h2>Generative Spatial Studio</h2>
        </div>
        <div className="dimensions">
          {bathroomWidth}&quot; &times; {bathroomDepth}&quot;
        </div>
      </div>

      <div className="view-toggle-row">
        <button className={`view-toggle-button ${viewMode === '3d' ? 'active' : ''}`} onClick={() => setViewMode('3d')}>3D</button>
        <button className={`view-toggle-button ${viewMode === 'plan' ? 'active' : ''}`} onClick={() => setViewMode('plan')}>Plan</button>
        <div className="clearance-badge">
          {violationCount === 0 ? (
            <span className="clearance-ok">&#10003; All clearances validated</span>
          ) : (
            <span className="clearance-warn">&#9888; {violationCount} clearance note{violationCount > 1 ? 's' : ''}</span>
          )}
        </div>
      </div>

      <div className="visualization-content">
        <div className="symbolic-grid-wrapper">
          {viewMode === '3d' ? renderIsoView() : renderPlanView()}
        </div>
      </div>

      <p className="grid-hint">Click any fixture to open its real KOHLER product page.</p>

      {/* Constraints Status */}
      <div className={`constraints-status ${constraintsSatisfied ? 'satisfied' : 'violated'}`}>
        <div className="status-header">
          {constraintsSatisfied ? (
            <>
              <span className="icon">✓</span>
              <h3>All Constraints Satisfied</h3>
            </>
          ) : (
            <>
              <span className="icon">⚠</span>
              <h3>Constraint Violations</h3>
            </>
          )}
        </div>

        {violations && violations.length > 0 && (
          <div className="violations-list">
            {violations.map((violation, idx) => (
              <div key={idx} className="violation">
                <span className="violation-icon">⚠</span>
                <p>{violation}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="legend">
        <h4>Product Types</h4>
        <div className="legend-items">
          {Object.entries(CATEGORY_COLORS)
            .filter(([category]) => Object.values(productsBySku).some((p) => p.category === category))
            .map(([category, color]) => (
              <div key={category} className="legend-item">
                <div className="legend-color" style={{ backgroundColor: color }}></div>
                <span>{CATEGORY_LABELS[category] || category}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

export default GridVisualization;
