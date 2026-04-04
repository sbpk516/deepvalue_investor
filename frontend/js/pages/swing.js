function initSwing() {
  const el = document.getElementById('swing');
  el.innerHTML = `
    <div class="page-header">
      <h1>Swing Trades</h1>
    </div>
    <div class="card" style="text-align:center; padding:48px;">
      <h2 style="color:var(--text-muted);">Coming Soon in Phase 2</h2>
      <p style="margin-top:12px; color:var(--text-muted);">
        The Swing Trader pipeline identifies short-term momentum opportunities
        using Williams %R, Bollinger Bands, and volume analysis.
      </p>
      <p style="margin-top:8px; color:var(--text-muted);">
        This feature is deferred to Phase 2 of the RK Screener project.
      </p>
    </div>
  `;
}
