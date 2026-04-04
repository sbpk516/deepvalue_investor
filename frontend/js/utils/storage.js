const Storage = {
  getWatchlist: () => {
    try { return JSON.parse(localStorage.getItem('rk_watchlist') || '[]'); }
    catch { return []; }
  },
  saveWatchlist: (list) => {
    localStorage.setItem('rk_watchlist', JSON.stringify(list));
  },
  addToWatchlist: (ticker) => {
    const list = Storage.getWatchlist();
    if (!list.includes(ticker)) {
      list.push(ticker);
      Storage.saveWatchlist(list);
    }
  },
  removeFromWatchlist: (ticker) => {
    const list = Storage.getWatchlist().filter(t => t !== ticker);
    Storage.saveWatchlist(list);
  },
  isWatched: (ticker) => Storage.getWatchlist().includes(ticker),
};
