const Format = {
  score: (n) => n != null ? Math.round(n) : '—',
  pct: (n) => n != null ? (n * 100).toFixed(1) + '%' : '—',
  money: (n) => {
    if (n == null) return '—';
    if (Math.abs(n) >= 1e9) return '$' + (n / 1e9).toFixed(1) + 'B';
    if (Math.abs(n) >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
    if (Math.abs(n) >= 1e3) return '$' + (n / 1e3).toFixed(0) + 'K';
    return '$' + n.toFixed(0);
  },
  price: (n) => n != null ? '$' + n.toFixed(2) : '—',
  date: (s) => s || '—',
  multiple: (n) => n != null ? n.toFixed(1) + 'x' : '—',
};
