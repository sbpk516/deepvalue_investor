const Colors = {
  forTier: (tier) => {
    const map = {
      'exceptional': 'var(--exceptional)',
      'high_conviction': 'var(--high-conviction)',
      'speculative': 'var(--speculative)',
      'watch': 'var(--watch)',
    };
    return map[tier] || map['watch'];
  },
  forScore: (score) => {
    if (score >= 80) return 'var(--exceptional)';
    if (score >= 65) return 'var(--high-conviction)';
    if (score >= 40) return 'var(--speculative)';
    return 'var(--watch)';
  },
  forSeverity: (severity) => {
    const map = {
      'danger': 'var(--red)',
      'warning': 'var(--yellow)',
      'info': 'var(--accent)',
      'note': 'var(--text-muted)',
    };
    return map[severity] || map['note'];
  },
};
