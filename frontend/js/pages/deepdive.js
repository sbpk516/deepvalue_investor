async function initDeepDive(ticker) {
  const el = document.getElementById('deepdive');

  if (!ticker) {
    el.innerHTML = `
      <div class="page-header">
        <h1>Analyse a Stock</h1>
      </div>
      <div class="card">
        <p>Enter a ticker to see the full deep-dive analysis.</p>
        <div style="margin-top:12px; display:flex; gap:8px;">
          <input type="text" id="deepdive-ticker" placeholder="e.g. GME"
                 style="text-transform:uppercase; width:120px;"
                 onkeydown="if(event.key==='Enter') showDeepDive(this.value)">
          <button class="btn btn--primary"
                  onclick="showDeepDive(document.getElementById('deepdive-ticker').value)">
            Analyse
          </button>
        </div>
      </div>
    `;
    return;
  }

  let candidate = null;
  try {
    let resp = await fetch('output/results.json').catch(() => null);
    if (!resp || !resp.ok) resp = await fetch('../output/results.json');
    const data = await resp.json();
    candidate = data.candidates.find(c => c.ticker === ticker.toUpperCase());
  } catch (e) {}

  if (!candidate) {
    el.innerHTML = `
      <div class="page-header">
        <h1>Analyse: ${ticker.toUpperCase()}</h1>
      </div>
      <div class="card">
        <p>${ticker.toUpperCase()} was not found in the latest scan results.
           Run the pipeline with <code>--ticker ${ticker.toUpperCase()}</code> for a single-stock deep dive.</p>
      </div>
    `;
    return;
  }

  const c = candidate;
  const t = c.transparency || {};
  const comps = c.components || {};

  el.innerHTML = `
    <div class="page-header">
      <h1>${c.ticker} — ${c.company_name || ''}</h1>
      <div class="meta">
        ${c.score_tier} &middot; Score: ${Format.score(c.score_total)}/100 &middot;
        ${c.score_label || ''}
      </div>
    </div>

    <div class="card">
      <h3>Score Breakdown</h3>
      <p style="margin:8px 0; font-size:14px;">${t.total_explanation || ''}</p>
      <p style="font-family:var(--mono); font-size:13px; color:var(--text-muted);">
        ${t.arithmetic || ''}
      </p>
      ${Object.entries(comps).map(([name, comp]) => `
        <div style="margin-top:12px; padding:8px; border:1px solid var(--border); border-radius:var(--radius);">
          <div style="display:flex; justify-content:space-between;">
            <strong>${name.charAt(0).toUpperCase() + name.slice(1)}</strong>
            <span style="font-family:var(--mono);">${comp.points}/${comp.max}</span>
          </div>
          <div style="font-size:13px; margin-top:4px;">${comp.reasoning}</div>
        </div>
      `).join('')}
    </div>

    ${c.risk_flags && c.risk_flags.length > 0 ? `
    <div class="card">
      <h3>Risk Flags</h3>
      ${c.risk_flags.map(f => `
        <div class="risk-flag risk-flag--${f.severity}">${f.text}</div>
      `).join('')}
    </div>
    ` : ''}

    ${c.action_steps && c.action_steps.length > 0 ? `
    <div class="card">
      <h3>Next Steps</h3>
      <ol style="padding-left:20px;">
        ${c.action_steps.slice(0, 3).map(s => `
          <li style="margin-bottom:8px;">
            <strong>${s.text}</strong>
            <div style="font-size:13px; color:var(--text-muted);">${s.detail}</div>
            ${s.link_url ? `<a href="${s.link_url}" target="_blank">${s.link_label}</a>` : ''}
          </li>
        `).join('')}
      </ol>
    </div>
    ` : ''}

    <div class="card">
      <h3>Upside Estimates</h3>
      <div style="display:flex; gap:24px; font-size:14px;">
        <div>Conservative: <strong>${Format.multiple(c.conservative_upside)}</strong></div>
        <div>Bull case: <strong>${Format.multiple(c.bull_upside)}</strong></div>
        <div>Diluted: <strong>${Format.multiple(c.diluted_upside)}</strong></div>
      </div>
    </div>

    <div class="card">
      <h3>Key Metrics</h3>
      <table style="width:100%; font-size:13px;">
        <tr><td>Price</td><td>${Format.price(c.price)}</td></tr>
        <tr><td>Market Cap</td><td>${Format.money(c.market_cap)}</td></tr>
        <tr><td>FCF Yield</td><td>${Format.pct(c.fcf_yield)}</td></tr>
        <tr><td>P/TBV</td><td>${c.price_to_tbv != null ? c.price_to_tbv.toFixed(2) : '—'}</td></tr>
        <tr><td>Bond Tier</td><td>${c.bond_tier || '—'}</td></tr>
        <tr><td>Weekly RSI</td><td>${c.rsi_weekly != null ? c.rsi_weekly.toFixed(1) : '—'}</td></tr>
        <tr><td>RSI Trend</td><td>${c.rsi_trend || '—'}</td></tr>
        <tr><td>Insider Buy</td><td>${Format.money(c.insider_buy_amount)}</td></tr>
        <tr><td>Decline Type</td><td>${c.decline_type || '—'}</td></tr>
      </table>
    </div>
  `;
}

function showDeepDive(ticker) {
  if (!ticker) return;
  navigateTo('deepdive');
  initDeepDive(ticker.toUpperCase());
}
