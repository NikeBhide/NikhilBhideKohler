import React, { useState, useEffect } from 'react';
import './App.css';
import LandingPage from './components/LandingPage';
import ChatAgent from './components/ChatAgent';
import BundlePanel from './components/BundlePanel';
import GridVisualization from './components/GridVisualization';
import { buildBundleRationale } from './utils/bundleRationale';

function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [themes, setThemes] = useState([]);
  const [themeKeywords, setThemeKeywords] = useState({});
  const [categories, setCategories] = useState([]);
  const [recommendation, setRecommendation] = useState(null);
  const [setupData, setSetupData] = useState(null);
  // Kept across "Start Over" (unlike setupData, which only reflects the
  // last successfully generated bundle) so re-opening the chat starts
  // pre-filled with whatever was last typed/selected, instead of blank.
  const [savedInputs, setSavedInputs] = useState(null);
  const [lockedProducts, setLockedProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Set once the user clicks "Proceed with Bundle" -- swaps the two-column
  // working layout for a full-page reveal of the 3D room so they can
  // actually see the whole space at once.
  const [finalized, setFinalized] = useState(false);

  // Load available themes and categories on mount
  useEffect(() => {
    fetchThemesAndCategories();
  }, []);

  const fetchThemesAndCategories = async () => {
    try {
      const [themesRes, categoriesRes] = await Promise.all([
        fetch('http://localhost:5000/api/themes'),
        fetch('http://localhost:5000/api/categories')
      ]);

      const themesData = await themesRes.json();
      const categoriesData = await categoriesRes.json();

      if (themesData.success) {
        setThemes(themesData.themes);
        setThemeKeywords(themesData.theme_keywords || {});
      }
      if (categoriesData.success) setCategories(categoriesData.categories);
    } catch (err) {
      setError('Failed to load themes and categories');
      console.error(err);
    }
  };

  const handleGenerate = async (data) => {
    setLoading(true);
    setError(null);
    setSetupData(data);
    setSavedInputs(data);
    setLockedProducts([]);
    setFinalized(false);

    try {
      const response = await fetch('http://localhost:5000/api/recommend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          themes: data.themes,
          budget: data.budget,
          width: data.width,
          depth: data.depth,
          categories: data.categories,
          locked_products: []
        })
      });

      const result = await response.json();

      if (result.success) {
        setRecommendation(result);
      } else {
        setError(result.error || 'Failed to get recommendation');
      }
    } catch (err) {
      setError('Error contacting server');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleLock = (sku) => {
    setLockedProducts(prev =>
      prev.includes(sku) ? prev.filter(s => s !== sku) : [...prev, sku]
    );
  };

  const handleStartOver = () => {
    setRecommendation(null);
    setLockedProducts([]);
    setError(null);
    setFinalized(false);
    // savedInputs and setupData are intentionally left as-is, so the chat
    // reopens pre-filled with what was already entered.
  };

  const handleRefresh = async () => {
    if (!setupData || !recommendation) return;
    setLoading(true);
    setError(null);

    // Only the categories of products that are NOT ticked/locked get refreshed;
    // ticked products keep their category untouched.
    const lockedCategories = new Set(
      recommendation.bundle
        .filter(p => lockedProducts.includes(p.sku))
        .map(p => p.category)
    );
    const refreshCategories = setupData.categories.filter(c => !lockedCategories.has(c));

    try {
      const response = await fetch('http://localhost:5000/api/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          themes: setupData.themes,
          budget: setupData.budget,
          width: setupData.width,
          depth: setupData.depth,
          categories: setupData.categories,
          locked_products: lockedProducts,
          refresh_categories: refreshCategories
        })
      });

      const result = await response.json();

      if (result.success) {
        setRecommendation(result);
      } else {
        setError(result.error || 'Failed to refresh recommendation');
      }
    } catch (err) {
      setError('Error contacting server');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (showLanding) {
    return <LandingPage onEnter={() => setShowLanding(false)} />;
  }

  // Once the bundle is confirmed, give the room the whole screen instead of
  // sharing it with the working panels -- this is the moment the user
  // actually wants to look at the space, not edit it.
  if (finalized && recommendation) {
    const rationale = buildBundleRationale({
      products: recommendation.bundle,
      themes: setupData?.themes,
      themeKeywords
    });

    return (
      <div className="App reveal-page">
        <div className="reveal-topbar">
          <div className="reveal-topbar-main">
            <p className="reveal-eyebrow">Your Bathroom, Visualized</p>
            <p className="reveal-rationale">{rationale}</p>
          </div>
          <div className="reveal-topbar-side">
            <span className="reveal-total">₹{recommendation.total_price.toLocaleString('en-IN')}</span>
            <button className="reveal-edit-button" onClick={() => setFinalized(false)}>
              Edit Bundle
            </button>
          </div>
        </div>
        <div className="reveal-stage">
          <GridVisualization
            placementMap={recommendation.placement_map}
            products={recommendation.bundle}
            entrance={recommendation.entrance}
            violations={recommendation.violations}
            constraintsSatisfied={recommendation.all_constraints_satisfied}
            bathroomWidth={setupData.width}
            bathroomDepth={setupData.depth}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="app-header">
        <div className="app-header-title">
          <h1>Kohler Designer</h1>
          <span className="app-edition">Studio &middot; Real Catalog Pricing</span>
        </div>
        <p>Real KOHLER products, budget-fair recommendations, and a true-to-scale layout &mdash; no staged renders, just what actually fits and what it actually costs.</p>
      </header>

      <div className="app-container">
        {/* Left Panel: Setup form, then the personalised bundle once generated */}
        <div className="left-panel">
          {!recommendation ? (
            <ChatAgent
              themes={themes}
              themeKeywords={themeKeywords}
              categories={categories}
              onSubmit={handleGenerate}
              loading={loading}
              error={error}
              initialData={savedInputs}
            />
          ) : (
            <BundlePanel
              products={recommendation.bundle}
              totalPrice={recommendation.total_price}
              withinBudget={recommendation.within_budget}
              requestedBudget={recommendation.requested_budget}
              unfilledCategories={recommendation.unfilled_categories}
              unfilledDetails={recommendation.unfilled_details}
              lockedProducts={lockedProducts}
              onToggleLock={handleToggleLock}
              onRefresh={handleRefresh}
              onStartOver={handleStartOver}
              onProceed={() => setFinalized(true)}
              loading={loading}
              error={error}
            />
          )}
        </div>

        {/* Right Panel: Grid Visualization */}
        <div className="right-panel">
          {recommendation ? (
            <GridVisualization
              placementMap={recommendation.placement_map}
              products={recommendation.bundle}
              entrance={recommendation.entrance}
              violations={recommendation.violations}
              constraintsSatisfied={recommendation.all_constraints_satisfied}
              bathroomWidth={setupData.width}
              bathroomDepth={setupData.depth}
            />
          ) : (
            <div className="placeholder">
              <p>Your bathroom layout will appear here once you generate a bundle</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
