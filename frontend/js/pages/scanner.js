let scannerData = null;

async function initScanner() {
  const el = document.getElementById('scanner');
  try {
    let resp = await fetch('output/results.json').catch(() => null);
    if (!resp || !resp.ok) resp = await fetch('../output/results.json');
    scannerData = await resp.json();
  } catch (e) {
    el.innerHTML = '<div class="card"><p>No results found. Run the pipeline first: <code>PYTHONPATH=. python3 pipeline/main.py --test</code></p></div>';
    return;
  }

  const { candidates, stats, pipeline, parameters, run_date } = scannerData;

  el.innerHTML = `
    <div class="page-header">
      <h1>RK Deep Value Scanner</h1>
      <div class="meta">
        Run: ${run_date || '—'} &middot;
        Screened: ${stats?.stocks_screened?.toLocaleString() || 0} &middot;
        Final: ${stats?.scored || 0} candidates &middot;
        Runtime: ${stats?.runtime_seconds || 0}s
      </div>
    </div>

    ${pipeline ? renderFunnel(pipeline, stats) : ''}
    ${parameters ? renderParameters(parameters) : ''}

    <div style="margin-top:24px;">
      <h2 style="font-size:16px; margin-bottom:12px;">
        Scored Candidates (${candidates.length})
      </h2>
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
          <option value="price_to_tbv">Sort by P/TBV</option>
        </select>
      </div>
      <div id="candidates-list" class="candidates-list"></div>
    </div>
  `;

  filterCandidates();
}

function renderFunnel(pipeline, stats) {
  const layers = [
    { key: 'layer1_universe', icon: '1', color: 'var(--accent)' },
    { key: 'layer2_price', icon: '2', color: 'var(--yellow)' },
    { key: 'layer3_fundamentals', icon: '3', color: 'var(--orange)' },
    { key: 'layer4_conviction', icon: '4', color: 'var(--green)' },
    { key: 'layer5_bonds', icon: '5', color: 'var(--red)' },
    { key: 'layer6_technical', icon: '6', color: 'var(--exceptional)' },
  ];

  const maxCount = pipeline.layer1_universe?.count || 1;

  let html = `
    <div class="card" id="funnel-card">
      <h2 style="font-size:16px; margin-bottom:16px;">Pipeline Funnel — Layer by Layer</h2>
      <div class="funnel">
  `;

  for (const layer of layers) {
    const data = pipeline[layer.key];
    if (!data) continue;
    const pct = Math.max(3, (data.count / maxCount) * 100);
    const hasStocks = data.stocks && data.stocks.length > 0;
    const filteredCount = data.filtered != null ? data.filtered : 0;

    html += `
      <div class="funnel-layer" data-layer="${layer.key}">
        <div class="funnel-bar-row">
          <div class="funnel-label">
            <span class="funnel-step" style="background:${layer.color};">${layer.icon}</span>
            <span class="funnel-name">${data.description}</span>
          </div>
          <div class="funnel-count">
            <strong>${data.count.toLocaleString()}</strong>
            ${filteredCount > 0 ? `<span class="funnel-filtered">(-${filteredCount.toLocaleString()})</span>` : ''}
          </div>
        </div>
        <div class="funnel-bar-track">
          <div class="funnel-bar-fill" style="width:${pct}%; background:${layer.color};"></div>
        </div>
        ${hasStocks ? `
          <button class="btn funnel-expand-btn" onclick="toggleLayerStocks('${layer.key}')">
            Show ${data.count} stocks
          </button>
          <div id="layer-stocks-${layer.key}" class="layer-stocks" style="display:none;"></div>
        ` : ''}
      </div>
    `;
  }

  html += `
      </div>
    </div>
  `;
  return html;
}

function toggleLayerStocks(layerKey) {
  const el = document.getElementById(`layer-stocks-${layerKey}`);
  const btn = el.previousElementSibling;
  if (el.style.display === 'none') {
    const data = scannerData.pipeline[layerKey];
    const stocks = data.stocks || [];
    el.innerHTML = renderLayerTable(stocks, layerKey);
    el.style.display = 'block';
    btn.textContent = `Hide ${data.count} stocks`;
  } else {
    el.style.display = 'none';
    const data = scannerData.pipeline[layerKey];
    btn.textContent = `Show ${data.count} stocks`;
  }
}

function renderLayerTable(stocks, layerKey) {
  if (!stocks.length) return '<p style="color:var(--text-muted);padding:8px;">No stocks at this layer.</p>';

  // Pick columns based on layer
  let columns = [
    { key: 'ticker', label: 'Ticker' },
    { key: 'company_name', label: 'Company', fmt: v => (v||'').substring(0,30) },
    { key: 'price', label: 'Price', fmt: v => v != null ? '$'+v.toFixed(2) : '—' },
  ];

  if (layerKey === 'layer2_price') {
    columns.push(
      { key: 'pct_below_3yr_high', label: 'Drawdown', fmt: v => v != null ? (v*100).toFixed(1)+'%' : '—' },
      { key: 'high_3yr', label: '3yr High', fmt: v => v != null ? '$'+v.toFixed(2) : '—' },
    );
  }
  if (layerKey === 'layer3_fundamentals' || layerKey === 'layer4_conviction' || layerKey === 'layer5_bonds' || layerKey === 'layer6_technical') {
    columns.push(
      { key: 'price_to_tbv', label: 'P/TBV', fmt: v => v != null ? v.toFixed(2) : '—' },
      { key: 'fcf_yield', label: 'FCF Yield', fmt: v => v != null ? (v*100).toFixed(1)+'%' : '—' },
      { key: 'revenue_ttm', label: 'Revenue', fmt: v => v != null ? Format.money(v) : '—' },
      { key: 'net_overhang_fcf_ratio', label: 'OH/FCF', fmt: v => v != null ? v.toFixed(1)+'x' : '—' },
    );
  }
  if (layerKey === 'layer4_conviction') {
    columns.push(
      { key: 'insider_buy_amount', label: 'Insider Buy', fmt: v => v ? Format.money(v) : '—' },
      { key: 'insider_buy_role', label: 'Role', fmt: v => v || '—' },
      { key: 'value_fund_name', label: 'Value Fund', fmt: v => v || '—' },
    );
  }
  if (layerKey === 'layer5_bonds') {
    columns.push(
      { key: 'bond_tier', label: 'Bond Tier', fmt: v => v || '—' },
      { key: 'bond_price', label: 'Bond Price', fmt: v => v != null ? v.toFixed(0) : '—' },
    );
  }
  if (layerKey === 'layer6_technical') {
    columns.push(
      { key: 'rsi_weekly', label: 'RSI', fmt: v => v != null ? v.toFixed(1) : '—' },
      { key: 'rsi_trend', label: 'Trend', fmt: v => v || '—' },
      { key: 'decline_type', label: 'Decline', fmt: v => v || '—' },
    );
  }

  let html = '<div class="layer-table-wrap"><table class="layer-table"><thead><tr>';
  for (const col of columns) {
    html += `<th>${col.label}</th>`;
  }
  html += '</tr></thead><tbody>';
  for (const stock of stocks) {
    html += '<tr>';
    for (const col of columns) {
      const val = stock[col.key];
      const display = col.fmt ? col.fmt(val) : (val != null ? val : '—');
      html += `<td>${display}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table></div>';
  return html;
}

function renderParameters(params) {
  return `
    <div class="card" id="params-card">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2 style="font-size:16px;">Pipeline Parameters</h2>
        <button class="btn" onclick="toggleParams()">Show / Hide</button>
      </div>
      <div id="params-body" style="display:none; margin-top:12px;">
        <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
          These are the thresholds used in the last pipeline run. To adjust, set environment variables before running.
        </p>
        <div class="params-grid">
          ${renderParamGroup('Layer 2 — Price Pain', [
            { key: 'LAYER2_MIN_DRAWDOWN_PCT', label: 'Min drawdown %', val: params.LAYER2_MIN_DRAWDOWN_PCT, unit: '%', desc: 'Stock must be down this much from 3yr high' },
          ])}
          ${renderParamGroup('Layer 3 — Fundamentals', [
            { key: 'LAYER3_MAX_PTBV', label: 'Max P/TBV', val: params.LAYER3_MAX_PTBV, unit: 'x', desc: 'Price / tangible book value ceiling' },
            { key: 'LAYER3_MIN_REVENUE', label: 'Min revenue', val: params.LAYER3_MIN_REVENUE, unit: '$', desc: 'Minimum trailing revenue', fmt: v => Format.money(v) },
            { key: 'LAYER3_MAX_OVERHANG_RATIO', label: 'Max overhang/FCF', val: params.LAYER3_MAX_OVERHANG_RATIO, unit: 'x', desc: 'Net debt / FCF ceiling' },
          ])}
          ${renderParamGroup('Layer 4 — Conviction', [
            { key: 'LAYER4_MIN_INSIDER_BUY', label: 'Min insider buy', val: params.LAYER4_MIN_INSIDER_BUY, unit: '$', desc: 'Minimum open-market purchase value', fmt: v => Format.money(v) },
          ])}
          ${renderParamGroup('Layer 5 — Bond Tiers', [
            { key: 'LAYER5_BOND_SAFE', label: 'Safe threshold', val: params.LAYER5_BOND_SAFE, unit: '', desc: 'Bond price >= this = safe' },
            { key: 'LAYER5_BOND_CAUTION', label: 'Caution threshold', val: params.LAYER5_BOND_CAUTION, unit: '', desc: 'Bond price >= this = caution' },
            { key: 'LAYER5_BOND_ELEVATED', label: 'Elevated threshold', val: params.LAYER5_BOND_ELEVATED, unit: '', desc: 'Bond price >= this = elevated' },
            { key: 'LAYER5_BOND_HIGH_RISK', label: 'High risk threshold', val: params.LAYER5_BOND_HIGH_RISK, unit: '', desc: 'Bond price >= this = high risk' },
          ])}
          ${renderParamGroup('Scoring Tiers', [
            { key: 'TIER_EXCEPTIONAL', label: 'Exceptional', val: params.TIER_EXCEPTIONAL, unit: 'pts', desc: 'Score >= this = Exceptional' },
            { key: 'TIER_HIGH_CONVICTION', label: 'High Conviction', val: params.TIER_HIGH_CONVICTION, unit: 'pts', desc: 'Score >= this = High Conviction' },
            { key: 'TIER_SPECULATIVE', label: 'Speculative', val: params.TIER_SPECULATIVE, unit: 'pts', desc: 'Score >= this = Speculative' },
          ])}
          ${params.SCORE_WEIGHTS ? renderParamGroup('Score Weights (must sum to 100)', [
            { key: 'insider', label: 'Insider', val: params.SCORE_WEIGHTS.insider, unit: 'pts' },
            { key: 'bonds', label: 'Bonds', val: params.SCORE_WEIGHTS.bonds, unit: 'pts' },
            { key: 'fcf', label: 'FCF', val: params.SCORE_WEIGHTS.fcf, unit: 'pts' },
            { key: 'institutional', label: 'Institutional', val: params.SCORE_WEIGHTS.institutional, unit: 'pts' },
            { key: 'technical', label: 'Technical', val: params.SCORE_WEIGHTS.technical, unit: 'pts' },
          ]) : ''}
        </div>
        <div style="margin-top:16px; padding:12px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius);">
          <h4 style="font-size:13px; margin-bottom:8px;">How to adjust parameters</h4>
          <code style="font-size:12px; color:var(--accent); display:block; white-space:pre-wrap;">LAYER2_MIN_DRAWDOWN_PCT=30 LAYER3_MAX_PTBV=2.0 PYTHONPATH=. python3 pipeline/main.py --test</code>
          <p style="font-size:12px; color:var(--text-muted); margin-top:8px;">Or set them in your <code>.env</code> file.</p>
        </div>
      </div>
    </div>
  `;
}

function renderParamGroup(title, params) {
  let html = `<div class="param-group"><h4 class="param-group-title">${title}</h4>`;
  for (const p of params) {
    const display = p.fmt ? p.fmt(p.val) : p.val;
    html += `
      <div class="param-row">
        <span class="param-label">${p.label}</span>
        <span class="param-value">${display}<span class="param-unit">${p.unit || ''}</span></span>
        ${p.desc ? `<span class="param-desc">${p.desc}</span>` : ''}
      </div>
    `;
  }
  html += '</div>';
  return html;
}

function toggleParams() {
  const body = document.getElementById('params-body');
  body.style.display = body.style.display === 'none' ? 'block' : 'none';
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
    if (sortBy === 'price_to_tbv') return (a.price_to_tbv || 99) - (b.price_to_tbv || 99);
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
