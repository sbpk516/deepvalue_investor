let scannerData = null;

async function initScanner() {
  const el = document.getElementById('scanner');
  try {
    // Try Pages path first, then local dev path
    let resp = await fetch('output/results.json').catch(() => null);
    if (!resp || !resp.ok) resp = await fetch('../output/results.json');
    scannerData = await resp.json();
  } catch (e) {
    el.innerHTML = '<div class="card"><p>No results found. Run the pipeline first: <code>python pipeline/main.py --test</code></p></div>';
    return;
  }

  const { candidates, stats, run_date, generated_at } = scannerData;

  el.innerHTML = `
    <div class="page-header">
      <h1>Today's Picks</h1>
      <div class="meta">
        Run: ${run_date || '—'} &middot;
        Screened: ${stats?.stocks_screened || 0} &middot;
        Scored: ${stats?.scored || 0} &middot;
        Runtime: ${stats?.runtime_seconds || 0}s
      </div>
    </div>
    <div class="filter-bar">
      <select id="filter-tier" onchange="filterCandidates()">
        <option value="">All tiers</option>
        <option value="Exceptional">Exceptional</option>
        <option value="High Conviction">High Conviction</option>
        <option value="Speculative">Speculative</option>
        <option value="Watch Only">Watch Only</option>
      </select>
      <select id="filter-sort" onchange="filterCandidates()">
        <option value="score">Sort by score</option>
        <option value="price">Sort by price</option>
        <option value="fcf_yield">Sort by FCF yield</option>
      </select>
    </div>
    <div id="candidates-list" class="candidates-list"></div>
  `;

  filterCandidates();
}

function filterCandidates() {
  if (!scannerData) return;
  let candidates = [...scannerData.candidates];

  const tierFilter = document.getElementById('filter-tier')?.value;
  if (tierFilter) {
    candidates = candidates.filter(c => c.score_tier === tierFilter);
  }

  const sortBy = document.getElementById('filter-sort')?.value || 'score';
  candidates.sort((a, b) => {
    if (sortBy === 'price') return (b.price || 0) - (a.price || 0);
    if (sortBy === 'fcf_yield') return (b.fcf_yield || 0) - (a.fcf_yield || 0);
    return (b.score_total || 0) - (a.score_total || 0);
  });

  const listEl = document.getElementById('candidates-list');
  if (!listEl) return;

  if (candidates.length === 0) {
    listEl.innerHTML = '<div class="card"><p>No candidates match the filter.</p></div>';
    return;
  }

  listEl.innerHTML = candidates.map(c => renderScoreCard(c)).join('');
}
