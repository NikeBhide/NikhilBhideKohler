import React from 'react';
import './LandingPage.css';

function LandingPage({ onEnter }) {
  return (
    <div className="landing-page">
      <div className="landing-grid-lines" aria-hidden="true" />
      <div className="landing-content">
        <p className="landing-eyebrow">KOHLER Studio</p>
        <h1 className="landing-title">
          Enter to Create<br />Your Perfect Bathroom
        </h1>
        <p className="landing-subtitle">
          Real KOHLER products, a budget-fair bundle, and a true-to-scale 3D layout —
          built around your space, your style, and your price.
        </p>
        <button className="landing-cta" onClick={onEnter}>
          Begin Designing
          <span className="landing-cta-arrow">&rarr;</span>
        </button>
      </div>
      <div className="landing-footer">Studio &middot; Real Catalog Pricing</div>
    </div>
  );
}

export default LandingPage;
