// Builds a plain-language "why this bundle works" paragraph from the
// products, the themes the user picked, and the theme keyword data the
// backend exposes (/api/themes -> theme_keywords). This is deterministic
// keyword/attribute matching, not a live model call -- it looks at what
// the products actually have in common (shared theme, shared finish,
// shared theme grouping) and says so in plain terms, instead of just
// repeating "the themes match."
export function buildBundleRationale({ products, themes, themeKeywords }) {
  if (!products || products.length === 0) return '';

  const themeList = themes && themes.length > 0
    ? themes
    : [...new Set(products.map((p) => p.primary_theme).filter(Boolean))];

  const blurb = (name) => {
    const kws = (themeKeywords && themeKeywords[name]) || [];
    return kws.length > 0 ? `${name} (${kws.slice(0, 3).join(', ')})` : name;
  };

  const sentences = [];

  if (themeList.length > 0) {
    sentences.push(
      `This bundle is built around ${themeList.map(blurb).join(' and ')} — every piece here was chosen because it speaks that same design language, not just because it fit the budget.`
    );
  }

  // Shared finish across products -- a strong, easy-to-see cohesion signal.
  const finishCounts = {};
  products.forEach((p) => {
    if (p.color_finish) finishCounts[p.color_finish] = (finishCounts[p.color_finish] || 0) + 1;
  });
  const topFinish = Object.entries(finishCounts).sort((a, b) => b[1] - a[1])[0];
  if (topFinish && topFinish[1] >= 2) {
    const [finish, count] = topFinish;
    sentences.push(
      `${count} of the ${products.length} pieces share a ${finish} finish, so the fixtures read as one coordinated set instead of items bought separately.`
    );
  }

  // Call out a specific pair that sits under the same theme, to make the
  // "this product works with this product" reasoning concrete rather than
  // abstract.
  const byTheme = {};
  products.forEach((p) => {
    const t = p.primary_theme || 'Unassigned';
    if (!byTheme[t]) byTheme[t] = [];
    byTheme[t].push(p);
  });
  const biggestGroup = Object.entries(byTheme).sort((a, b) => b[1].length - a[1].length)[0];
  if (biggestGroup && biggestGroup[1].length >= 2) {
    const [theme, group] = biggestGroup;
    const [a, b] = group;
    sentences.push(
      `The ${a.name} and the ${b.name} both sit under the ${theme} line, so they're designed to be seen side by side.`
    );
  }

  return sentences.join(' ');
}
