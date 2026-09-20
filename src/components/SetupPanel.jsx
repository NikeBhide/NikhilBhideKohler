import React, { useState } from 'react';
import './SetupPanel.css';

function SetupPanel({ themes, categories, onSubmit, loading, error }) {
  const [budget, setBudget] = useState(500000);
  const [width, setWidth] = useState(60);
  const [depth, setDepth] = useState(80);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedThemes, setSelectedThemes] = useState([]);

  const toggleCategory = (category) => {
    setSelectedCategories(prev =>
      prev.includes(category) ? prev.filter(c => c !== category) : [...prev, category]
    );
  };

  const toggleTheme = (theme) => {
    setSelectedThemes(prev =>
      prev.includes(theme) ? prev.filter(t => t !== theme) : [...prev, theme]
    );
  };

  const canSubmit = selectedCategories.length > 0 && selectedThemes.length > 0 && budget > 0 && width > 0 && depth > 0;

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit({
      themes: selectedThemes,
      categories: selectedCategories,
      budget,
      width,
      depth
    });
  };

  return (
    <div className="setup-panel">
      <h2 className="setup-title">Design Your Bathroom</h2>

      <div className="setup-section">
        <label className="setup-label">Budget (₹)</label>
        <div className="budget-dimensions-row">
          <input
            type="number"
            className="budget-field"
            value={budget}
            onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
            min="20000"
            max="5000000"
            step="5000"
          />
          <div className="dimension-field">
            <label>Width (in)</label>
            <input
              type="number"
              value={width}
              onChange={(e) => setWidth(parseInt(e.target.value) || 0)}
              min="30"
              max="200"
            />
          </div>
          <div className="dimension-field">
            <label>Depth (in)</label>
            <input
              type="number"
              value={depth}
              onChange={(e) => setDepth(parseInt(e.target.value) || 0)}
              min="30"
              max="200"
            />
          </div>
        </div>
      </div>

      <div className="setup-section">
        <label className="setup-label">Products</label>
        <div className="chip-grid">
          {categories.map(category => (
            <button
              key={category}
              type="button"
              className={`chip ${selectedCategories.includes(category) ? 'selected' : ''}`}
              onClick={() => toggleCategory(category)}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      <div className="setup-section">
        <label className="setup-label">Styles</label>
        <div className="chip-grid">
          {themes.map(theme => (
            <button
              key={theme}
              type="button"
              className={`chip ${selectedThemes.includes(theme) ? 'selected' : ''}`}
              onClick={() => toggleTheme(theme)}
            >
              {theme}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="setup-error">{error}</p>}

      <button
        className="generate-button"
        onClick={handleSubmit}
        disabled={!canSubmit || loading}
      >
        {loading ? 'Generating…' : 'Generate My Bundle'}
      </button>
    </div>
  );
}

export default SetupPanel;
