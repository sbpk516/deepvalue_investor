// App initialization and navigation
document.addEventListener('DOMContentLoaded', () => {
  // Set up navigation
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      const page = tab.getAttribute('href').replace('#', '');
      navigateTo(page);
    });
  });

  // How it works modal
  const howLink = document.getElementById('how-it-works-link');
  const modal = document.getElementById('how-it-works-modal');
  if (howLink && modal) {
    howLink.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('modal-body').innerHTML = `
        <h2 id="modal-title">How the RK Screener Works</h2>
        <p style="margin-top:12px;">This screener applies a 6-layer filter inspired by Roaring Kitty's investment methodology:</p>
        <ol style="padding-left:20px; margin-top:12px;">
          <li><strong>Universe:</strong> ~6,000 US-listed stocks from SEC EDGAR</li>
          <li><strong>Price Pain:</strong> Down 40%+ from 3-year high (~400)</li>
          <li><strong>Fundamentals:</strong> P/TBV &lt; 1.5, positive FCF, revenue &gt; $50M (~100)</li>
          <li><strong>Conviction:</strong> Insider buying OR value fund holder (~30)</li>
          <li><strong>Bonds:</strong> Not in credit distress (~15-25)</li>
          <li><strong>Technical:</strong> RSI + sector context added (~10-15)</li>
        </ol>
        <p style="margin-top:12px;">Each candidate is scored 0-100 across 5 components:
           Insider (30), Bonds (25), FCF (20), Institutional (15), Technical (10).</p>
        <p style="margin-top:8px; font-style:italic; color:var(--text-muted);">
          Educational only — not financial advice.</p>
      `;
      modal.style.display = 'flex';
    });
    modal.querySelector('.modal-close').addEventListener('click', () => {
      modal.style.display = 'none';
    });
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.style.display = 'none';
    });
  }

  // Check for hash navigation
  const hash = window.location.hash.replace('#', '') || 'scanner';
  navigateTo(hash);
});

function navigateTo(page) {
  // Hide all pages
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  // Remove active from all tabs
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));

  // Show target page
  const pageEl = document.getElementById(page);
  if (pageEl) pageEl.style.display = 'block';

  // Activate tab
  const tabEl = document.getElementById('nav-' + page);
  if (tabEl) tabEl.classList.add('active');

  // Init page
  switch (page) {
    case 'scanner':  initScanner(); break;
    case 'watchlist': initWatchlist(); break;
    case 'deepdive': initDeepDive(); break;
    case 'swing':    initSwing(); break;
  }

  window.location.hash = page;
}
