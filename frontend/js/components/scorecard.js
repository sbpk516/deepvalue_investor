function renderScoreCard(candidate) {
  const score = candidate.score_total || 0;
  const tier = candidate.score_color || 'watch';
  const color = Colors.forTier(tier);
  const watched = Storage.isWatched(candidate.ticker);

  return `
    <div class="card candidate-card" data-ticker="${candidate.ticker}">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <strong style="font-size:16px;">${candidate.ticker}</strong>
          <span style="color:var(--text-muted); margin-left:8px; font-size:13px;">
            ${candidate.company_name || ''}
          </span>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <span class="tier-badge tier-badge--${tier}">
            ${candidate.score_tier || 'Watch Only'}
          </span>
          <button class="btn btn-watch" onclick="toggleWatch('${candidate.ticker}')"
                  title="${watched ? 'Remove from watchlist' : 'Add to watchlist'}">
            ${watched ? '- Watch' : '+ Watch'}
          </button>
          <button class="btn btn--primary" onclick="showDeepDive('${candidate.ticker}')">
            Analyse
          </button>
        </div>
      </div>
      <div style="margin-top:8px;">
        <div class="score-bar">
          <div style="flex:1; background:var(--border); border-radius:4px; height:8px;">
            <div class="score-bar__fill" style="width:${score}%; background:${color};"></div>
          </div>
          <span class="score-bar__label" style="color:${color};">${Format.score(score)}/100</span>
        </div>
        <div style="font-size:13px; color:var(--text-muted); margin-top:4px;">
          ${candidate.score_label || ''} &middot; ${candidate.top_signal || ''}
        </div>
      </div>
      <div style="display:flex; gap:16px; margin-top:8px; font-size:12px; color:var(--text-muted);">
        <span>Price: ${Format.price(candidate.price)}</span>
        <span>MCap: ${Format.money(candidate.market_cap)}</span>
        <span>FCF Yield: ${Format.pct(candidate.fcf_yield)}</span>
        <span>P/TBV: ${candidate.price_to_tbv != null ? candidate.price_to_tbv.toFixed(2) : '—'}</span>
      </div>
    </div>
  `;
}

function toggleWatch(ticker) {
  if (Storage.isWatched(ticker)) {
    Storage.removeFromWatchlist(ticker);
  } else {
    Storage.addToWatchlist(ticker);
  }
  // Re-render current page
  if (typeof initScanner === 'function' && document.getElementById('scanner').style.display !== 'none') {
    initScanner();
  }
}
