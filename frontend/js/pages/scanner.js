let scannerData = null;
let activeParams = {};

async function initScanner() {
  const el = document.getElementById('scanner');
  try {
    let resp = await fetch('output/results.json').catch(() => null);
    if (!resp || !resp.ok) resp = await fetch('../output/results.json');
    scannerData = await resp.json();
  } catch (e) {
    el.innerHTML = '<div class="card"><p>No results found. Run the pipeline first.</p></div>';
    return;
  }

  // Initialize active params from pipeline defaults
  const p = scannerData.parameters || {};
  activeParams = {
    drawdown: p.LAYER2_MIN_DRAWDOWN_PCT || 40,
    maxPTBV: p.LAYER3_MAX_PTBV || 1.5,
    minRevenue: p.LAYER3_MIN_REVENUE || 50000000,
    maxOverhang: p.LAYER3_MAX_OVERHANG_RATIO || 15,
    minInsiderBuy: p.LAYER4_MIN_INSIDER_BUY || 200000,
  };

  renderFullPage();
}

function renderFullPage() {
  const el = document.getElementById('scanner');
  const { stats, run_date } = scannerData;
  const refiltered = refilterPipeline();

  el.innerHTML = `
    <div class="page-header">
      <h1>RK Deep Value Scanner</h1>
      <div class="meta">
        Run: ${run_date || '—'} &middot;
        Universe: ${stats?.stocks_screened?.toLocaleString() || 0} &middot;
        Runtime: ${stats?.runtime_seconds || 0}s
      </div>
    </div>

    ${renderControls()}
    ${renderLiveFunnel(refiltered)}

    <div style="margin-top:24px;">
      <h2 style="font-size:16px; margin-bottom:12px;">
        Candidates (${refiltered.scored.length})
      </h2>
      <div class="filter-bar">
        <select id="filter-tier" onchange="renderCandidatesList()">
          <option value="">All tiers</option>
          <option value="Exceptional">Exceptional</option>
          <option value="High Conviction">High Conviction</option>
          <option value="Speculative">Speculative</option>
          <option value="Watch Only">Watch Only</option>
        </select>
        <select id="filter-sort" onchange="renderCandidatesList()">
          <option value="score">Sort by score</option>
          <option value="fcf_yield">Sort by FCF yield</option>
          <option value="price_to_tbv">Sort by P/TBV (low first)</option>
          <option value="drawdown">Sort by drawdown (deepest first)</option>
        </select>
      </div>
      <div id="candidates-list" class="candidates-list"></div>
    </div>
  `;

  renderCandidatesList();
}

// ─── Re-filter Layer 2 stocks client-side with user's parameters ───
function refilterPipeline() {
  const pipeline = scannerData.pipeline || {};
  const l2Stocks = pipeline.layer2_price?.stocks || [];

  // Re-apply Layer 3 filters with active params
  const l3Passed = l2Stocks.filter(s => {
    const ptbv = s.price_to_tbv;
    const fcfYield = s.fcf_yield;
    const rev = s.revenue_ttm;
    const oh = s.net_overhang_fcf_ratio;
    // Must have fundamentals data
    if (ptbv == null || fcfYield == null) return false;
    if (ptbv > activeParams.maxPTBV) return false;
    if (rev != null && rev < activeParams.minRevenue) return false;
    if (fcfYield <= 0) return false; // positive FCF required
    if (oh != null && oh > activeParams.maxOverhang) return false;
    return true;
  });

  // Score them
  const scored = l3Passed.map(s => {
    const score = quickScore(s);
    return { ...s, ...score };
  });
  scored.sort((a, b) => (b.score_total || 0) - (a.score_total || 0));

  return {
    l2: l2Stocks,
    l3: l3Passed,
    scored: scored,
  };
}

// Quick client-side scoring (simplified version of RKScorer)
function quickScore(stock) {
  let insider = 0, bonds = 0, fcf = 0, institutional = 0, technical = 0;

  // Insider
  const buyAmt = stock.insider_buy_amount || 0;
  const isCeo = stock.insider_is_ceo_cfo || false;
  if (buyAmt >= 2000000) insider = 30;
  else if (buyAmt >= 500000 && isCeo) insider = 22;
  else if (buyAmt >= 200000 && isCeo) insider = 15;
  else if (buyAmt >= 50000) insider = 8;
  if (stock.insider_is_10b51_plan && insider > 0) insider = Math.floor(insider / 2);
  insider = Math.min(insider, 30);

  // Bonds
  const tier = stock.bond_tier || 'unavailable';
  const ratio = stock.net_overhang_fcf_ratio || 0;
  if (tier === 'unavailable') bonds = ratio < 2 ? 25 : 15;
  else if (tier === 'safe') bonds = ratio < 5 ? 25 : 20;
  else if (tier === 'caution') bonds = 18;
  else if (tier === 'elevated') bonds = 10;
  else if (tier === 'high_risk') bonds = 4;
  if (stock.bond_is_stale && tier !== 'unavailable') bonds = Math.max(0, bonds - 5);
  bonds = Math.min(bonds, 25);

  // FCF
  const fy = stock.fcf_yield || 0;
  const ptbv = stock.price_to_tbv || 99;
  if (fy >= 0.25 || (fy >= 0.15 && ptbv < 0.5)) fcf = 20;
  else if (fy >= 0.15 || ptbv < 0.5) fcf = 14;
  else if (fy >= 0.10 || ptbv < 1.0) fcf = 10;
  else if (fy >= 0.05) fcf = 8;
  else if (fy > 0) fcf = 2;
  fcf = Math.min(fcf, 20);

  // Institutional
  const fund = stock.value_fund_name;
  const fundPct = stock.value_fund_pct || 0;
  const insOwn = stock.insider_ownership_pct || 0;
  if (fund && fundPct >= 0.05) institutional = 10;
  else if (insOwn >= 0.20) institutional = 8;
  else if (fund) institutional = 5;
  else institutional = 2;
  institutional = Math.min(institutional, 15);

  // Technical
  const rsi = stock.rsi_weekly;
  const trend = stock.rsi_trend || 'neutral';
  const weeks = stock.weeks_rsi_improving || 0;
  if (rsi && rsi < 30 && trend === 'improving' && weeks >= 3) technical = 10;
  else if (rsi && rsi < 35 && trend === 'improving') technical = 7;
  else if (trend === 'improving') technical = 5;
  else if (trend === 'neutral') technical = 4;
  else technical = 1;
  technical = Math.min(technical, 10);

  const sectorMod = stock.sector_context_modifier || 0;
  const total = Math.min(100, Math.max(0, insider + bonds + fcf + institutional + technical + sectorMod));

  let tierLabel, tierColor;
  if (total >= 80) { tierLabel = 'Exceptional'; tierColor = 'exceptional'; }
  else if (total >= 65) { tierLabel = 'High Conviction'; tierColor = 'high_conviction'; }
  else if (total >= 40) { tierLabel = 'Speculative'; tierColor = 'speculative'; }
  else { tierLabel = 'Watch Only'; tierColor = 'watch'; }

  return {
    score_total: Math.round(total * 10) / 10,
    score_tier: tierLabel,
    score_color: tierColor,
    score_label: tierLabel,
    components: {
      insider: { points: insider, max: 30 },
      bonds: { points: bonds, max: 25 },
      fcf: { points: fcf, max: 20 },
      institutional: { points: institutional, max: 15 },
      technical: { points: technical, max: 10 },
    },
    top_signal: fy >= 0.15 ? `FCF yield ${(fy*100).toFixed(1)}%` :
                buyAmt > 0 ? `Insider buy $${(buyAmt/1000).toFixed(0)}K` :
                rsi ? `RSI ${rsi.toFixed(0)}, ${trend}` : '',
  };
}

// ─── Controls Panel ───
function renderControls() {
  return `
    <div class="card controls-card">
      <h2 style="font-size:16px; margin-bottom:14px;">Adjust Filters (live re-filtering)</h2>
      <div class="controls-grid">
        <div class="control-item">
          <label>Min Drawdown</label>
          <div class="control-input-row">
            <input type="range" min="20" max="80" step="5" value="${activeParams.drawdown}"
                   id="ctrl-drawdown" oninput="onParamChange()">
            <span class="control-value" id="val-drawdown">${activeParams.drawdown}%</span>
          </div>
          <div class="control-desc">Stock must be down this % from 3yr high</div>
        </div>
        <div class="control-item">
          <label>Max P/TBV</label>
          <div class="control-input-row">
            <input type="range" min="0.5" max="5" step="0.25" value="${activeParams.maxPTBV}"
                   id="ctrl-ptbv" oninput="onParamChange()">
            <span class="control-value" id="val-ptbv">${activeParams.maxPTBV}x</span>
          </div>
          <div class="control-desc">Price / tangible book value ceiling</div>
        </div>
        <div class="control-item">
          <label>Min Revenue</label>
          <div class="control-input-row">
            <input type="range" min="0" max="500" step="10" value="${activeParams.minRevenue / 1e6}"
                   id="ctrl-rev" oninput="onParamChange()">
            <span class="control-value" id="val-rev">$${(activeParams.minRevenue/1e6).toFixed(0)}M</span>
          </div>
          <div class="control-desc">Minimum trailing 12-month revenue</div>
        </div>
        <div class="control-item">
          <label>Max Overhang/FCF</label>
          <div class="control-input-row">
            <input type="range" min="1" max="30" step="1" value="${activeParams.maxOverhang}"
                   id="ctrl-oh" oninput="onParamChange()">
            <span class="control-value" id="val-oh">${activeParams.maxOverhang}x</span>
          </div>
          <div class="control-desc">Net debt / free cash flow ceiling</div>
        </div>
      </div>
      <div style="margin-top:12px; display:flex; gap:8px;">
        <button class="btn btn--primary" onclick="applyParams()">Apply Filters</button>
        <button class="btn" onclick="resetParams()">Reset to Defaults</button>
      </div>
      <div id="preview-count" style="margin-top:8px; font-size:13px; color:var(--text-muted);"></div>
    </div>
  `;
}

function onParamChange() {
  const d = parseFloat(document.getElementById('ctrl-drawdown').value);
  const p = parseFloat(document.getElementById('ctrl-ptbv').value);
  const r = parseFloat(document.getElementById('ctrl-rev').value);
  const o = parseFloat(document.getElementById('ctrl-oh').value);

  document.getElementById('val-drawdown').textContent = d + '%';
  document.getElementById('val-ptbv').textContent = p + 'x';
  document.getElementById('val-rev').textContent = '$' + r.toFixed(0) + 'M';
  document.getElementById('val-oh').textContent = o + 'x';

  // Preview count
  const tempParams = { drawdown: d, maxPTBV: p, minRevenue: r * 1e6, maxOverhang: o };
  const oldParams = activeParams;
  activeParams = tempParams;
  const preview = refilterPipeline();
  activeParams = oldParams;

  const el = document.getElementById('preview-count');
  if (el) el.textContent = `Preview: ${preview.l3.length} stocks pass filters, ${preview.scored.length} scored`;
}

function applyParams() {
  activeParams.drawdown = parseFloat(document.getElementById('ctrl-drawdown').value);
  activeParams.maxPTBV = parseFloat(document.getElementById('ctrl-ptbv').value);
  activeParams.minRevenue = parseFloat(document.getElementById('ctrl-rev').value) * 1e6;
  activeParams.maxOverhang = parseFloat(document.getElementById('ctrl-oh').value);
  renderFullPage();
}

function resetParams() {
  const p = scannerData.parameters || {};
  activeParams = {
    drawdown: p.LAYER2_MIN_DRAWDOWN_PCT || 40,
    maxPTBV: p.LAYER3_MAX_PTBV || 1.5,
    minRevenue: p.LAYER3_MIN_REVENUE || 50000000,
    maxOverhang: p.LAYER3_MAX_OVERHANG_RATIO || 15,
  };
  renderFullPage();
}

// ─── Live Funnel ───
function renderLiveFunnel(refiltered) {
  const pipeline = scannerData.pipeline || {};
  const universeCount = pipeline.layer1_universe?.count || 0;
  const l2Count = refiltered.l2.length;
  const l3Count = refiltered.l3.length;
  const scoredCount = refiltered.scored.length;

  const layers = [
    { label: 'Universe', desc: 'All US-listed stocks (SEC EDGAR)', count: universeCount, color: 'var(--accent)', key: null },
    { label: 'Price Pain', desc: `Down ${activeParams.drawdown}%+ from 3yr high`, count: l2Count, filtered: universeCount - l2Count, color: 'var(--yellow)', key: 'layer2_price' },
    { label: 'Fundamentals', desc: `P/TBV < ${activeParams.maxPTBV}, +FCF, Rev > $${(activeParams.minRevenue/1e6).toFixed(0)}M, OH < ${activeParams.maxOverhang}x`, count: l3Count, filtered: l2Count - l3Count, color: 'var(--orange)', key: null, stocks: refiltered.l3 },
    { label: 'Scored', desc: 'Conviction + bonds + technical scoring applied', count: scoredCount, filtered: 0, color: 'var(--exceptional)', key: null, stocks: refiltered.scored },
  ];

  const maxCount = Math.max(universeCount, 1);

  let html = `
    <div class="card">
      <h2 style="font-size:16px; margin-bottom:16px;">Pipeline Funnel</h2>
      <div class="funnel">
  `;

  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    const pct = Math.max(3, (layer.count / maxCount) * 100);
    const hasExpandable = layer.key || layer.stocks;
    const expandId = `funnel-expand-${i}`;

    html += `
      <div class="funnel-layer">
        <div class="funnel-bar-row">
          <div class="funnel-label">
            <span class="funnel-step" style="background:${layer.color};">${i + 1}</span>
            <div>
              <span class="funnel-name"><strong>${layer.label}</strong></span>
              <span class="funnel-desc">${layer.desc}</span>
            </div>
          </div>
          <div class="funnel-count">
            <strong>${layer.count.toLocaleString()}</strong>
            ${layer.filtered ? `<span class="funnel-filtered">(-${layer.filtered.toLocaleString()})</span>` : ''}
          </div>
        </div>
        <div class="funnel-bar-track">
          <div class="funnel-bar-fill" style="width:${pct}%; background:${layer.color};"></div>
        </div>
        ${hasExpandable ? `
          <button class="btn funnel-expand-btn" onclick="toggleExpand('${expandId}', this)">
            Show ${layer.count} stocks
          </button>
          <div id="${expandId}" class="layer-stocks" style="display:none;"
               data-layer-key="${layer.key || ''}" data-layer-idx="${i}"></div>
        ` : ''}
      </div>
    `;
  }

  html += '</div></div>';
  return html;
}

function toggleExpand(id, btn) {
  const el = document.getElementById(id);
  if (el.style.display === 'none') {
    // Populate if empty
    if (!el.innerHTML) {
      const key = el.dataset.layerKey;
      const idx = parseInt(el.dataset.layerIdx);
      let stocks;
      if (key && scannerData.pipeline[key]) {
        stocks = scannerData.pipeline[key].stocks || [];
      } else {
        const refiltered = refilterPipeline();
        if (idx === 2) stocks = refiltered.l3;
        else if (idx === 3) stocks = refiltered.scored;
        else stocks = [];
      }
      el.innerHTML = renderLayerTable(stocks, key || (idx === 3 ? 'scored' : 'layer3'));
    }
    el.style.display = 'block';
    btn.textContent = btn.textContent.replace('Show', 'Hide');
  } else {
    el.style.display = 'none';
    btn.textContent = btn.textContent.replace('Hide', 'Show');
  }
}

function renderLayerTable(stocks, layerKey) {
  if (!stocks.length) return '<p style="color:var(--text-muted);padding:8px;">No stocks at this layer.</p>';

  let columns = [
    { key: 'ticker', label: 'Ticker' },
    { key: 'company_name', label: 'Company', fmt: v => (v||'').substring(0,25) },
    { key: 'price', label: 'Price', fmt: v => v != null ? '$'+v.toFixed(2) : '—' },
    { key: 'pct_below_3yr_high', label: 'Drawdown', fmt: v => v != null ? (v*100).toFixed(1)+'%' : '—' },
  ];

  if (layerKey !== 'layer2_price') {
    columns.push(
      { key: 'price_to_tbv', label: 'P/TBV', fmt: v => v != null ? v.toFixed(2) : '—' },
      { key: 'fcf_yield', label: 'FCF Yield', fmt: v => v != null ? (v*100).toFixed(1)+'%' : '—' },
      { key: 'revenue_ttm', label: 'Revenue', fmt: v => v != null ? Format.money(v) : '—' },
      { key: 'net_overhang_fcf_ratio', label: 'OH/FCF', fmt: v => v != null ? v.toFixed(1)+'x' : '—' },
    );
  }

  if (layerKey === 'scored') {
    columns.push(
      { key: 'score_total', label: 'Score', fmt: v => v != null ? v.toFixed(0) : '—' },
      { key: 'score_tier', label: 'Tier', fmt: v => v || '—' },
    );
  }

  let html = '<div class="layer-table-wrap"><table class="layer-table"><thead><tr>';
  for (const col of columns) html += `<th>${col.label}</th>`;
  html += '</tr></thead><tbody>';
  for (const stock of stocks) {
    html += '<tr>';
    for (const col of columns) {
      const val = stock[col.key];
      html += `<td>${col.fmt ? col.fmt(val) : (val != null ? val : '—')}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table></div>';
  return html;
}

function renderCandidatesList() {
  const refiltered = refilterPipeline();
  let candidates = [...refiltered.scored];

  const tierFilter = document.getElementById('filter-tier')?.value;
  if (tierFilter) candidates = candidates.filter(c => c.score_tier === tierFilter);

  const sortBy = document.getElementById('filter-sort')?.value || 'score';
  candidates.sort((a, b) => {
    if (sortBy === 'fcf_yield') return (b.fcf_yield || 0) - (a.fcf_yield || 0);
    if (sortBy === 'price_to_tbv') return (a.price_to_tbv || 99) - (b.price_to_tbv || 99);
    if (sortBy === 'drawdown') return (a.pct_below_3yr_high || 0) - (b.pct_below_3yr_high || 0);
    return (b.score_total || 0) - (a.score_total || 0);
  });

  const listEl = document.getElementById('candidates-list');
  if (!listEl) return;
  if (candidates.length === 0) {
    listEl.innerHTML = '<div class="card"><p>No candidates match these filters. Try relaxing the parameters above.</p></div>';
    return;
  }
  listEl.innerHTML = candidates.map(c => renderScoreCard(c)).join('');
}
