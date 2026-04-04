async function initWatchlist() {
  const el = document.getElementById('watchlist');
  const watched = Storage.getWatchlist();

  if (watched.length === 0) {
    el.innerHTML = `
      <div class="page-header">
        <h1>My Watchlist</h1>
      </div>
      <div class="card">
        <p>No stocks on your watchlist yet. Click "+ Watch" on any stock to add it here.</p>
      </div>
    `;
    return;
  }

  let candidates = [];
  try {
    let resp = await fetch('output/results.json').catch(() => null);
    if (!resp || !resp.ok) resp = await fetch('../output/results.json');
    const data = await resp.json();
    candidates = data.candidates.filter(c => watched.includes(c.ticker));
  } catch (e) {}

  el.innerHTML = `
    <div class="page-header">
      <h1>My Watchlist</h1>
      <div class="meta">${watched.length} stocks tracked</div>
    </div>
    <div class="candidates-list">
      ${candidates.length > 0
        ? candidates.map(c => renderScoreCard(c)).join('')
        : watched.map(t => `
            <div class="card">
              <strong>${t}</strong>
              <span style="color:var(--text-muted);"> — not in latest scan results</span>
              <button class="btn" onclick="Storage.removeFromWatchlist('${t}'); initWatchlist();"
                      style="margin-left:8px;">Remove</button>
            </div>
          `).join('')
      }
    </div>
  `;
}
