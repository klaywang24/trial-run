"""Tiny deterministic SVG charts (standard library only). Mid-tone colors so they read on both GitHub themes.
The same input always yields byte-identical output, so an unchanged ledger never creates a commit."""
from __future__ import annotations
import math

INK = "#8b949e"
COLORS = ["#a0392f", "#2b5f8f", "#6b4c9a", "#8a7a3a", "#3f7f5f", "#b06a2c"]
FONT = 'font-family="ui-sans-serif,system-ui,-apple-system,sans-serif"'


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _nice_ticks(lo, hi, n=5):
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=raw)
    start = math.ceil(lo / step) * step
    out, v = [], start
    while v <= hi + 1e-9:
        out.append(round(v, 10)); v += step
    return out


def smooth_path(pts):
    """Monotone cubic (Fritsch-Carlson) through pixel points: a smooth curve that never overshoots the data,
    so no drawn value is higher or lower than a recorded one between two closes."""
    n = len(pts)
    if n < 3:
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    h = [pts[i + 1][0] - pts[i][0] for i in range(n - 1)]
    d = [(pts[i + 1][1] - pts[i][1]) / h[i] if h[i] else 0.0 for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            r = a * a + b * b
            if r > 9:
                t = 3 / math.sqrt(r); m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    out = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for i in range(n - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        k = h[i] / 3
        out.append(f"C{x0 + k:.1f},{y0 + m[i] * k:.1f} {x1 - k:.1f},{y1 - m[i + 1] * k:.1f} {x1:.1f},{y1:.1f}")
    return " ".join(out)


def line_chart(path, title, subtitle, dates, series: dict, log=False, base=None, fmt="{:.0f}", note=None,
               W=860, H=400, area=True):
    """series: {label: [values...]} aligned with dates (ISO strings). Optional base line (e.g. 100)."""
    ML, MR, MT, MB = 62, 175, 74, 36
    vals = [v for s in series.values() for v in s if v is not None]
    if base is not None:
        vals.append(base)
    tr = (lambda v: math.log10(v)) if log else (lambda v: v)
    lo, hi = min(map(tr, vals)), max(map(tr, vals))
    pad = (hi - lo) * 0.06 or 0.5
    lo, hi = lo - pad, hi + pad
    n = len(dates)
    x = lambda i: ML + (W - ML - MR) * (i / max(n - 1, 1))
    y = lambda v: MT + (H - MT - MB) * (1 - (tr(v) - lo) / (hi - lo))
    e = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" {FONT}>',
         f'<text x="{ML}" y="24" font-size="15" font-weight="600" fill="{INK}">{_esc(title)}</text>',
         f'<text x="{ML}" y="43" font-size="12" fill="{INK}" opacity="0.8">{_esc(subtitle)}</text>']
    if note:
        e.append(f'<text x="{ML}" y="61" font-size="11.5" fill="{INK}" opacity="0.62">{_esc(note)}</text>')
    if log:
        ticks = [10 ** k * m for k in range(-1, 6) for m in (1, 2, 5) if lo <= math.log10(10 ** k * m) <= hi]
    else:
        ticks = _nice_ticks(lo, hi)
    for v in ticks:
        e.append(f'<line x1="{ML}" y1="{y(v):.1f}" x2="{W - MR}" y2="{y(v):.1f}" stroke="{INK}" stroke-opacity="0.16"/>')
        e.append(f'<text x="{ML - 8}" y="{y(v) + 4:.1f}" font-size="11" fill="{INK}" text-anchor="end">{fmt.format(v)}</text>')
    if base is not None:
        e.append(f'<line x1="{ML}" y1="{y(base):.1f}" x2="{W - MR}" y2="{y(base):.1f}" stroke="{INK}" stroke-opacity="0.5" stroke-dasharray="4 4"/>')
    # x ticks: years if long, else ~6 evenly spaced dates (always keep last, drop crowded neighbours)
    if n > 400:
        idx = [i for i in range(1, n) if dates[i][:4] != dates[i - 1][:4]]
        lab = lambda i: dates[i][:4]
    else:
        step = max(1, (n - 1) // 6)
        idx = sorted(set(range(0, n, step)) | {n - 1})
        lab = lambda i: dates[i][5:] if n < 260 else dates[i][:7]
    kept, last_x = [], -1e9
    for i in idx:
        if x(i) - last_x >= 58 or i == n - 1:
            if kept and x(i) - x(kept[-1]) < 58:
                kept.pop()
            kept.append(i); last_x = x(i)
    for i in kept:
        e.append(f'<text x="{x(i):.1f}" y="{H - 12}" font-size="11" fill="{INK}" text-anchor="middle">{_esc(lab(i))}</text>')
    labels = []
    floor = y(base) if base is not None else H - MB   # shade toward the base line, like an intraday chart
    for c, (name, s) in enumerate(reversed(list(series.items()))):
        c = len(series) - 1 - c                      # draw the main series last, on top
        col = COLORS[c % len(COLORS)]
        pts = [(x(i), y(v)) for i, v in enumerate(s) if v is not None]
        dpath = smooth_path(pts)
        if c == 0 and area:
            gid = "g" + "".join(ch for ch in title if ch.isalnum())[:12]
            e.append(f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
                     f'<stop offset="0" stop-color="{col}" stop-opacity="0.24"/>'
                     f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient></defs>')
            e.append(f'<path d="{dpath} L{pts[-1][0]:.1f},{floor} L{pts[0][0]:.1f},{floor} Z" fill="url(#{gid})" stroke="none"/>')
        wdt = 2.2 if c == 0 else 1.4
        e.append(f'<path d="{dpath}" fill="none" stroke="{col}" stroke-width="{wdt}" stroke-linejoin="round" stroke-linecap="round"/>')
        if c == 0:
            e.append(f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3.2" fill="{col}"/>')
        last = [(i, v) for i, v in enumerate(s) if v is not None][-1]
        labels.append([y(last[1]), col, f"{name} {fmt.format(last[1])}"])
    labels.sort()
    for k in range(1, len(labels)):  # de-overlap end labels
        if labels[k][0] - labels[k - 1][0] < 14:
            labels[k][0] = labels[k - 1][0] + 14
    for yy, col, txt in labels:
        e.append(f'<text x="{W - MR + 8}" y="{yy + 4:.1f}" font-size="11.5" fill="{col}">{_esc(txt)}</text>')
    e.append("</svg>")
    open(path, "w").write("\n".join(e) + "\n")


def placeholder(path, title, text, W=860, H=160):
    e = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" {FONT}>',
         f'<text x="40" y="40" font-size="15" font-weight="600" fill="{INK}">{_esc(title)}</text>',
         f'<text x="40" y="80" font-size="13" fill="{INK}" opacity="0.8">{_esc(text)}</text></svg>']
    open(path, "w").write("\n".join(e) + "\n")


def hbar_chart(path, title, subtitle, rows, fmt="{:+.0f}%", W=860, row_h=24, marks=None, legend=None):
    """rows: [(label, value, color, tag)] top to bottom. marks: {row_index: text} dashed separator above that row."""
    ML, MR, MT = 170, 260, 70
    H = MT + row_h * len(rows) + 30
    vals = [r[1] for r in rows] + [0]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    x = lambda v: ML + (W - ML - MR) * ((v - lo) / span)
    e = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" {FONT}>',
         f'<text x="20" y="24" font-size="15" font-weight="600" fill="{INK}">{_esc(title)}</text>',
         f'<text x="20" y="43" font-size="12" fill="{INK}" opacity="0.8">{_esc(subtitle)}</text>']
    if legend:
        lx = 20
        for col, txt in legend:
            e.append(f'<rect x="{lx}" y="52" width="10" height="10" fill="{col}"/>')
            e.append(f'<text x="{lx + 14}" y="61" font-size="11" fill="{INK}">{_esc(txt)}</text>')
            lx += 24 + 7 * len(txt)
    e.append(f'<line x1="{x(0):.1f}" y1="{MT - 4}" x2="{x(0):.1f}" y2="{H - 26}" stroke="{INK}" stroke-opacity="0.5"/>')
    for i, (label, v, col, tag) in enumerate(rows):
        yy = MT + i * row_h
        if marks and i in marks:
            e.append(f'<line x1="20" y1="{yy - 2:.1f}" x2="{W - 20}" y2="{yy - 2:.1f}" stroke="{INK}" stroke-opacity="0.55" stroke-dasharray="5 4"/>')
            e.append(f'<text x="{W - 20}" y="{yy - 5:.1f}" font-size="10.5" fill="{INK}" text-anchor="end" opacity="0.8">{_esc(marks[i])}</text>')
        x0, x1 = sorted((x(0), x(v)))
        e.append(f'<rect x="{x0:.1f}" y="{yy + 3}" width="{max(x1 - x0, 1):.1f}" height="{row_h - 8}" fill="{col}" rx="2"/>')
        e.append(f'<text x="{ML - 8}" y="{yy + row_h / 2 + 3:.1f}" font-size="12" fill="{INK}" text-anchor="end">{_esc(label)}</text>')
        e.append(f'<text x="{max(x1, x(0)) + 5:.1f}" y="{yy + row_h / 2 + 3:.1f}" font-size="11" fill="{INK}" text-anchor="start">{_esc(fmt.format(v))}{_esc(tag)}</text>')
    e.append("</svg>")
    open(path, "w").write("\n".join(e) + "\n")
