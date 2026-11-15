// Positions only. Every figure shown as text is sample data written in each page; nothing here computes a figure.
window.CH = {
  pct(v, min, max) { return (v - min) / (max - min) * 100 + '%'; },
  // vals: numbers or null (missing); labels: optional text per point. The path breaks at a missing value.
  line(vals, min, max, labels) {
    const n = vals.length, P = vals.map((v, i) => v == null ? null : { x: (i + 0.5) / n * 100, y: 100 - (v - min) / (max - min) * 100, t: labels ? labels[i] || '' : '' });
    let d = '', area = '', seg = [];
    const flush = () => {
      if (!seg.length) return;
      let s = 'M' + seg[0].x + ' ' + seg[0].y;
      for (let i = 1; i < seg.length; i++) { const a = seg[i - 1], b = seg[i], dx = (b.x - a.x) * 0.4; s += ' C' + (a.x + dx) + ' ' + a.y + ' ' + (b.x - dx) + ' ' + b.y + ' ' + b.x + ' ' + b.y; }
      d += s + ' ';
      if (seg.length > 1) area += s + ' L' + seg[seg.length - 1].x + ' 100 L' + seg[0].x + ' 100 Z ';
      seg = [];
    };
    P.forEach(p => { if (p) seg.push(p); else flush(); });
    flush();
    return {
      d, area,
      pts: P.filter(Boolean).map(p => ({ x: p.x + '%', y: (100 - p.y) + '%', t: p.t })),
      na: P.map((p, i) => p ? null : { x: (i + 0.5) / n * 100 + '%' }).filter(Boolean)
    };
  },
  // grouped columns. groups: [label, [values or null], [labels]]; series class per index.
  cols(groups, max, cls) {
    return groups.map(g => ({ l: g[0], bars: g[1].map((v, i) => ({ ok: v != null, na: v == null, h: v == null ? '0' : Math.max(v / max * 100, 0.6) + '%', c: (cls || ['', 'b2', 'b3'])[i], t: (g[2] || [])[i] || '' })) }));
  },
  // waterfall. steps: [label, from, to, text, kind] with kind 'tot', 'up', 'dn' or 'na' (missing: from and to are null).
  wf(steps, max) {
    return steps.map(s => ({ l: s[0], ok: s[4] !== 'na', na: s[4] === 'na', t: s[3], c: s[4] === 'up' ? 'bup' : s[4] === 'dn' ? 'bdn' : '',
      bot: s[4] === 'na' ? '0' : Math.min(s[1], s[2]) / max * 100 + '%', h: s[4] === 'na' ? '0' : Math.abs(s[2] - s[1]) / max * 100 + '%' }));
  },
  // table data for the Tbl component. 'n.a.' is styled, 'W' is withheld, 'G' is a gap.
  tbl(head, rows) {
    const cell = (v, i) => ({ k: (i === 0 ? 'l' : '') + (v === 'n.a.' ? ' na' : ''), v: v === 'W' || v === 'G' ? '' : v, w: v === 'W', g: v === 'G' });
    return { head: head.map((v, i) => ({ k: i === 0 ? 'l' : '', v })), rows: rows.map(r => ({ c: r.map(cell) })) };
  },
  ticks(a) { return a.map(t => ({ t })); }
};
