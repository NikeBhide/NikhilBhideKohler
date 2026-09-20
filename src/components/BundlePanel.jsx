import React from 'react';
import './BundlePanel.css';

function buildExplanation({ products, totalPrice, withinBudget, requestedBudget, unfilledCategories, unfilledDetails }) {
  const filledCount = products.length;
  const unfilledCount = unfilledCategories.length;
  const totalRequested = filledCount + unfilledCount;

  if (unfilledCount === 0) {
    return `Nice — I found something for every category you asked for. The full bundle comes to ₹${totalPrice.toLocaleString('en-IN')}, ${withinBudget ? 'comfortably within' : 'just over'} your ₹${requestedBudget.toLocaleString('en-IN')} budget.`;
  }

  const reasonLine = (category) => {
    const detail = unfilledDetails[category];
    if (!detail) return category;
    if (detail.reason === 'budget') {
      return `${category} (cheapest option is ₹${detail.cheapest_price.toLocaleString('en-IN')} — about ₹${detail.shortfall.toLocaleString('en-IN')} more than you had left)`;
    }
    if (detail.reason === 'unavailable') {
      return `${category} (nothing currently in stock)`;
    }
    return `${category} (nothing available in this category yet)`;
  };

  const list = unfilledCategories.map(reasonLine).join('; ');

  return `I was able to fill ${filledCount} of ${totalRequested} categories you asked for, totalling ₹${totalPrice.toLocaleString('en-IN')} of your ₹${requestedBudget.toLocaleString('en-IN')} budget. I couldn't fit: ${list}. Want to raise your budget, drop one of those categories, or tick what you like below and refresh the rest?`;
}

function BundlePanel({
  products,
  totalPrice,
  withinBudget,
  requestedBudget,
  unfilledCategories,
  unfilledDetails,
  lockedProducts,
  onToggleLock,
  onRefresh,
  onStartOver,
  onProceed,
  loading,
  error
}) {
  const explanation = buildExplanation({
    products,
    totalPrice,
    withinBudget,
    requestedBudget: requestedBudget || 0,
    unfilledCategories: unfilledCategories || [],
    unfilledDetails: unfilledDetails || {}
  });

  return (
    <div className="bundle-panel">
      <div className="bundle-header">
        <p className="bundle-eyebrow">02 / Rationale &amp; Bundle</p>
        <h2>Your Personalised Bundle</h2>

        <div className="agent-message">{explanation}</div>

        <div className="bundle-summary">
          <span className="total-price">
            Total: <strong>₹{totalPrice.toLocaleString('en-IN')}</strong>
          </span>
          <span className={`budget-status ${withinBudget ? 'within' : 'over'}`}>
            {withinBudget ? '✓ Within Budget' : '✗ Over Budget'}
          </span>
        </div>
        <p className="tick-hint">Tick the products you like, then refresh the rest</p>
      </div>

      <div className="bundle-products">
        {products.map((product, idx) => (
          <label key={product.sku} className={`bundle-item ${lockedProducts.includes(product.sku) ? 'liked' : ''}`}>
            <input
              type="checkbox"
              checked={lockedProducts.includes(product.sku)}
              onChange={() => onToggleLock(product.sku)}
            />
            {product.image_url && (
              <img
                src={product.image_url}
                alt={product.name}
                className="bundle-item-thumb"
                loading="lazy"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            )}
            <div className="bundle-item-body">
              <div className="bundle-item-top">
                <span className="bundle-item-name">{product.name}</span>
                <span className="bundle-item-price">₹{product.price.toLocaleString('en-IN')}</span>
              </div>
              <div className="bundle-item-meta">
                <span>{product.category}</span>
                <span>·</span>
                <span>{product.color_finish || 'N/A'}</span>
                <span>·</span>
                <span>{product.primary_theme}</span>
              </div>
              {product.url && (
                <a
                  href={product.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bundle-item-link"
                  onClick={(e) => e.stopPropagation()}
                >
                  View on KOHLER.com ↗
                </a>
              )}
            </div>
          </label>
        ))}
      </div>

      {error && <p className="bundle-error">{error}</p>}

      <div className="bundle-actions">
        <button className="start-over-button" onClick={onStartOver} disabled={loading}>
          Start Over
        </button>
        <button className="refresh-button" onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh Unticked'}
        </button>
        <button className="proceed-button" onClick={onProceed} disabled={loading}>
          Proceed with Bundle
        </button>
      </div>
    </div>
  );
}

export default BundlePanel;
