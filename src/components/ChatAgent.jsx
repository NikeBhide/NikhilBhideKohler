import React, { useState } from 'react';
import './ChatAgent.css';

const STEPS = ['welcome', 'categories', 'vision', 'themes', 'budget', 'confirm'];

const STEP_LABELS = {
  welcome: '',
  categories: '01 / PRODUCTS',
  vision: '02 / VISION',
  themes: '03 / STYLE',
  budget: '04 / BUDGET & SPACE',
  confirm: '05 / CONFIRM',
};

function ChatAgent({ themes, categories, themeKeywords, onSubmit, loading, error, initialData }) {
  const [step, setStep] = useState('welcome');
  const [selectedCategories, setSelectedCategories] = useState(initialData?.categories || []);
  const [visionText, setVisionText] = useState(initialData?.visionText || '');
  const [inferring, setInferring] = useState(false);
  const [inferError, setInferError] = useState(null);
  const [inferredThemes, setInferredThemes] = useState(initialData?.themes || []);
  const [lowConfidence, setLowConfidence] = useState(false);
  const [selectedThemes, setSelectedThemes] = useState(initialData?.themes || []);
  const [budget, setBudget] = useState(initialData?.budget || 500000);
  const [width, setWidth] = useState(initialData?.width || 60);
  const [depth, setDepth] = useState(initialData?.depth || 80);

  const toggleCategory = (category) => {
    setSelectedCategories((prev) =>
      prev.includes(category) ? prev.filter((c) => c !== category) : [...prev, category]
    );
  };

  const toggleTheme = (theme) => {
    setSelectedThemes((prev) =>
      prev.includes(theme) ? prev.filter((t) => t !== theme) : [...prev, theme]
    );
  };

  const handleInferThemes = async () => {
    if (!visionText.trim()) return;
    setInferring(true);
    setInferError(null);
    try {
      const response = await fetch('http://localhost:5000/api/infer-themes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: visionText })
      });
      const result = await response.json();
      if (result.success) {
        const names = result.inferred_themes.map((t) => t.theme);
        setInferredThemes(names);
        setSelectedThemes(names);
        // The backend now always returns a best-guess theme (see
        // low_confidence) rather than an empty list, so this should only
        // ever be empty on a genuinely broken response.
        setLowConfidence(!!result.low_confidence);
        setStep('themes');
      } else {
        setInferError(result.error || 'Could not read that description');
      }
    } catch (err) {
      setInferError('Error contacting server');
      console.error(err);
    } finally {
      setInferring(false);
    }
  };

  const handleGenerate = () => {
    onSubmit({
      themes: selectedThemes,
      categories: selectedCategories,
      budget,
      width,
      depth,
      visionText
    });
  };

  const idx = (s) => STEPS.indexOf(s);
  const stepIdx = idx(step);

  // A short "think X, Y, Z" descriptor for a theme, pulled from the same
  // keyword data that tags real products -- used to make the agent's
  // reasoning sound like actual styling rationale instead of an echo of
  // what the user just typed.
  const themeBlurb = (themeName) => {
    const kws = (themeKeywords && themeKeywords[themeName]) || [];
    return kws.length > 0 ? `${themeName} (think ${kws.slice(0, 3).join(', ')})` : themeName;
  };

  const transcript = [];

  transcript.push({ sender: 'bot', text: "Hi! I'm here to help you put together your KOHLER bathroom bundle. Let's start with what you're looking for." });

  if (stepIdx >= idx('categories')) {
    transcript.push({ sender: 'bot', text: 'What kind of products do you want in your bundle? From an elegant shower to some beautiful lighting — pick as many as you like.' });
  }
  if (stepIdx > idx('categories') && selectedCategories.length > 0) {
    transcript.push({ sender: 'user', text: selectedCategories.join(', ') });
  }

  if (stepIdx >= idx('vision')) {
    transcript.push({ sender: 'bot', text: "What's your vision for the bathroom? Describe it however you like — I'll match it to a style." });
  }
  if (stepIdx > idx('vision') && visionText.trim()) {
    transcript.push({ sender: 'user', text: visionText });
  }

  if (stepIdx >= idx('themes')) {
    if (inferredThemes.length === 0) {
      // Should be rare now that the backend always returns a best guess --
      // kept only as a last-resort message if that ever genuinely fails.
      transcript.push({ sender: 'bot', text: "I couldn't read a style out of that description at all -- here are all the styles KOHLER offers, pick whatever fits." });
    } else {
      const blurbs = inferredThemes.map(themeBlurb).join('; ');
      if (lowConfidence) {
        transcript.push({
          sender: 'bot',
          text: `Okay — from what you described, here's what I'm picking up on: ${blurbs}. Your wording didn't land squarely on one KOHLER style, but based on keyword matching, that's the theme I think fits best for what you're describing. Still your call though — pick a different one below if I read that wrong.`
        });
      } else {
        transcript.push({ sender: 'bot', text: `From what you described, I'm reading this as: ${blurbs}. That's the aesthetic language I'll shop the rest of the bundle around — feel free to adjust below before we continue.` });
      }
    }
  }
  if (stepIdx > idx('themes') && selectedThemes.length > 0) {
    transcript.push({ sender: 'user', text: selectedThemes.join(', ') });
  }

  if (stepIdx >= idx('budget')) {
    transcript.push({ sender: 'bot', text: "Last thing — what's your budget, and roughly how big is the space? I'll fit as much as I can and tell you exactly what didn't make the cut, and why." });
  }

  if (stepIdx >= idx('confirm')) {
    const themeText = selectedThemes.length > 0 ? selectedThemes.map(themeBlurb).join(' and ') : 'a style that fits your space';
    const categoryText = selectedCategories.length > 0 ? selectedCategories.join(', ') : 'your selected products';
    const budgetText = Number(budget || 0).toLocaleString('en-IN');
    const visionClause = visionText.trim()
      ? ` You described it as "${visionText.trim().length > 90 ? visionText.trim().slice(0, 90) + '…' : visionText.trim()}", and that's exactly the direction I'm leaning into.`
      : '';
    transcript.push({
      sender: 'bot',
      text: `Here's my thinking: your ${width}"×${depth}" bathroom is shaping up around ${themeText}.${visionClause} For the pieces themselves, I'm picking across ${categoryText} that share consistent finishes, a matching price tier, and that same overall look, rather than just grabbing whatever's cheapest in each category — that's what makes it feel like one cohesive room instead of a pile of unrelated fixtures. All of it fits within your ₹${budgetText} budget. Want to change anything, or should I go ahead and build it?`
    });
  }

  const goNext = () => {
    if (stepIdx < STEPS.length - 1) setStep(STEPS[stepIdx + 1]);
  };

  const goBack = () => {
    if (stepIdx > 0) setStep(STEPS[stepIdx - 1]);
  };

  return (
    <div className="chat-agent">
      <div className="chat-transcript">
        {transcript.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
      </div>

      {error && <p className="chat-error">{error}</p>}
      {inferError && <p className="chat-error">{inferError}</p>}

      <div className="chat-controls">
        {STEP_LABELS[step] && <p className="chat-step-label">{STEP_LABELS[step]}</p>}
        {step === 'welcome' && (
          <button className="chat-primary-button" onClick={goNext}>
            Let's create my bundle
          </button>
        )}

        {step === 'categories' && (
          <>
            <div className="chat-chip-grid">
              {categories.map((category) => (
                <button
                  key={category}
                  type="button"
                  className={`chat-chip ${selectedCategories.includes(category) ? 'selected' : ''}`}
                  onClick={() => toggleCategory(category)}
                >
                  {category}
                </button>
              ))}
            </div>
            <div className="chat-nav-row">
              <button className="chat-primary-button" onClick={goNext} disabled={selectedCategories.length === 0}>
                Continue
              </button>
            </div>
          </>
        )}

        {step === 'vision' && (
          <>
            <textarea
              className="chat-vision-input"
              value={visionText}
              onChange={(e) => setVisionText(e.target.value)}
              placeholder="e.g. I want something modern and minimalist, clean lines, maybe black fixtures..."
              rows={4}
            />
            <div className="chat-nav-row">
              <button className="chat-secondary-button" onClick={goBack} disabled={inferring}>Back</button>
              <button className="chat-primary-button" onClick={handleInferThemes} disabled={inferring || !visionText.trim()}>
                {inferring ? 'Reading that…' : 'Continue'}
              </button>
            </div>
          </>
        )}

        {step === 'themes' && (
          <>
            <div className="chat-chip-grid">
              {themes.map((theme) => (
                <button
                  key={theme}
                  type="button"
                  className={`chat-chip ${selectedThemes.includes(theme) ? 'selected' : ''}`}
                  onClick={() => toggleTheme(theme)}
                >
                  {theme}
                </button>
              ))}
            </div>
            <div className="chat-nav-row">
              <button className="chat-secondary-button" onClick={goBack}>Back</button>
              <button className="chat-primary-button" onClick={goNext} disabled={selectedThemes.length === 0}>
                Continue
              </button>
            </div>
          </>
        )}

        {step === 'budget' && (
          <>
            <div className="chat-budget-row">
              <div className="chat-field">
                <label>Budget (₹)</label>
                <input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
                  min="20000"
                  max="5000000"
                  step="5000"
                />
              </div>
              <div className="chat-field">
                <label>Width (in)</label>
                <input
                  type="number"
                  value={width}
                  onChange={(e) => setWidth(parseInt(e.target.value) || 0)}
                  min="30"
                  max="200"
                />
              </div>
              <div className="chat-field">
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
            <div className="chat-nav-row">
              <button className="chat-secondary-button" onClick={goBack} disabled={loading}>Back</button>
              <button className="chat-primary-button" onClick={goNext} disabled={loading || budget <= 0 || width <= 0 || depth <= 0}>
                Continue
              </button>
            </div>
          </>
        )}

        {step === 'confirm' && (
          <div className="chat-nav-row">
            <button className="chat-secondary-button" onClick={goBack} disabled={loading}>Change something</button>
            <button className="chat-primary-button" onClick={handleGenerate} disabled={loading}>
              {loading ? 'Building it…' : 'Build my bundle'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatAgent;
