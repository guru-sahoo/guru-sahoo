"""Generate dark-theme contribution SVGs for the GitHub profile README.

Outputs:
  assets/contribution-heatmap.svg  - last 12 months, full-width heatmap
  assets/activity-30d.svg          - daily contributions, last 30 days, bar chart
  assets/activity-12m.svg          - monthly contributions, last 12 months, bar chart

Uses only the Python standard library. Reads GH_PAT (preferred) or GITHUB_TOKEN.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "guru-sahoo")
OUT_DIR = os.environ.get("OUT_DIR", "assets")

BG, BORDER = "#0d1117", "#30363d"
TEXT, MUTED = "#c9d1d9", "#8b949e"
ACCENT, ACCENT_2 = "#58a6ff", "#1f6feb"
LEVELS = ["#161b22", "#0c2d6b", "#1158c7", "#388bfd", "#79c0ff"]
FONT = "font-family=\"-apple-system,Segoe UI,Helvetica,Arial,sans-serif\""

QUERY = """query($login:String!){user(login:$login){contributionsCollection{
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch_days():
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Set GH_PAT or GITHUB_TOKEN")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [d for w in weeks for d in w["contributionDays"]]


def level(count, peak):
    if count == 0:
        return 0
    for i, cut in enumerate((0.25, 0.5, 0.75), start=1):
        if count <= peak * cut:
            return i
    return 4


def heatmap(days):
    days = sorted(days, key=lambda d: d["date"])
    first = dt.date.fromisoformat(days[0]["date"])
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # align to Sunday
    cell, gap, left, top = 11, 3, 34, 26
    counts = {d["date"]: d["contributionCount"] for d in days}
    peak = max(counts.values()) or 1
    n_weeks = ((dt.date.fromisoformat(days[-1]["date"]) - start).days // 7) + 1
    width = left + n_weeks * (cell + gap) + 10
    height = top + 7 * (cell + gap) + 24

    parts, last_month = [], None
    for w in range(n_weeks):
        for dow in range(7):
            day = start + dt.timedelta(days=w * 7 + dow)
            key = day.isoformat()
            if key not in counts:
                continue
            x, y = left + w * (cell + gap), top + dow * (cell + gap)
            c = counts[key]
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{LEVELS[level(c, peak)]}"><title>{c} on {day:%b %d, %Y}</title></rect>'
            )
            if dow == 0 and day.month != last_month and day.day <= 14 and w < n_weeks - 2:
                parts.append(f'<text x="{x}" y="{top - 8}" class="t">{day:%b}</text>')
                last_month = day.month
    for dow, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="2" y="{top + dow * (cell + gap) + 9}" class="t">{name}</text>')

    total = sum(counts.values())
    ly = height - 16
    legend = [f'<text x="{left}" y="{ly + 9}" class="t">{total:,} contributions in the last year</text>',
              f'<text x="{width - 150}" y="{ly + 9}" class="t">Less</text>']
    for i, col in enumerate(LEVELS):
        legend.append(f'<rect x="{width - 120 + i * 15}" y="{ly}" width="{cell}" height="{cell}" rx="2" fill="{col}"/>')
    legend.append(f'<text x="{width - 42}" y="{ly + 9}" class="t">More</text>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f'<style>.t{{fill:{MUTED};font-size:10px}}</style>'
        f'<rect width="100%" height="100%" rx="8" fill="{BG}" stroke="{BORDER}"/>'
        f'<g {FONT}>{"".join(parts)}{"".join(legend)}</g></svg>'
    )


def nice_step(raw):
    """Round a tick step up to 1, 2, 2.5 or 5 x 10^n so axis labels stay clean."""
    mag = 10 ** (len(str(int(raw))) - 1)
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return int(m * mag) if m * mag >= 1 else 1
    return int(10 * mag)


def bar_chart(labels, values, title, stats, width=1000, label_size=11):
    W, H, pl, pr, pt, pb = width, 320, 50, 20, 64, 40
    cw, ch = W - pl - pr, H - pt - pb
    peak = max(max(values), 4)
    step = nice_step(peak / 5)
    ticks = -(-peak // step)  # ceil: fewest gridlines that still clear the tallest bar
    ymax = step * ticks
    slot = cw / len(values)
    bw = slot * 0.62

    grid = []
    for i in range(ticks + 1):
        y = pt + ch - i * ch / ticks
        grid.append(f'<line x1="{pl}" x2="{W - pr}" y1="{y:.1f}" y2="{y:.1f}" stroke="{BORDER}" stroke-dasharray="3 4"/>')
        grid.append(f'<text x="{pl - 10}" y="{y + 4:.1f}" text-anchor="end" class="t">{i * step:,}</text>')

    bars, xl = [], []
    for i, (lab, v) in enumerate(zip(labels, values)):
        cx = pl + slot * i + slot / 2
        x = cx - bw / 2
        if v:
            h = max(v / ymax * ch, 3)
            y = pt + ch - h
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="url(#b)">'
                f'<title>{lab}: {v:,}</title></rect>'
                f'<text x="{cx:.1f}" y="{y - 6:.1f}" text-anchor="middle" class="v">{v:,}</text>'
            )
        else:
            bars.append(f'<rect x="{x:.1f}" y="{pt + ch - 2}" width="{bw:.1f}" height="2" rx="1" fill="{BORDER}">'
                        f'<title>{lab}: 0</title></rect>')
        xl.append(f'<text x="{cx:.1f}" y="{H - pb + 20}" text-anchor="middle" class="x">{lab}</text>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f'<defs><linearGradient id="b" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{ACCENT}"/><stop offset="1" stop-color="{ACCENT_2}"/></linearGradient></defs>'
        f'<style>.t{{fill:{MUTED};font-size:12px}}.x{{fill:{MUTED};font-size:{label_size}px}}'
        f'.v{{fill:{TEXT};font-size:10px;font-weight:600}}</style>'
        f'<rect width="100%" height="100%" rx="8" fill="{BG}" stroke="{BORDER}"/>'
        f'<g {FONT}>'
        f'<text x="{pl}" y="32" fill="{TEXT}" font-size="16" font-weight="600">{title}</text>'
        f'<text x="{W - pr}" y="32" text-anchor="end" class="t">{stats}</text>'
        f'{"".join(grid)}{"".join(bars)}{"".join(xl)}</g></svg>'
    )


def daily_chart(days, span=30):
    days = sorted(days, key=lambda d: d["date"])[-span:]
    labels = [f"{dt.date.fromisoformat(d['date']).day}/{dt.date.fromisoformat(d['date']).month}" for d in days]
    vals = [d["contributionCount"] for d in days]
    active = sum(1 for v in vals if v)
    stats = f"{sum(vals):,} contributions  ·  {active}/{len(vals)} active days  ·  peak {max(vals)}/day"
    return bar_chart(labels, vals, f"Daily contributions · last {len(vals)} days", stats, label_size=10)


def monthly_chart(days, months=12):
    totals = {}
    for d in days:
        key = d["date"][:7]
        totals[key] = totals.get(key, 0) + d["contributionCount"]
    last = dt.date.fromisoformat(max(d["date"] for d in days))
    keys = []
    y, m = last.year, last.month
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    keys.reverse()
    labels = [f"{int(k[5:])}/{k[2:4]}" for k in keys]
    vals = [totals.get(k, 0) for k in keys]
    best = labels[vals.index(max(vals))]
    stats = f"{sum(vals):,} contributions  ·  avg {round(sum(vals) / len(vals)):,}/month  ·  best {best}"
    return bar_chart(labels, vals, f"Monthly contributions · last {len(vals)} months", stats, label_size=12)


def main():
    if len(sys.argv) > 1:  # local testing: python generate_graphs.py sample.json
        days = json.load(open(sys.argv[1]))
    else:
        days = fetch_days()
    # Today is usually incomplete; drop it so the line doesn't dip to 0 every morning.
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date().isoformat()
    days = [d for d in days if d["date"] < today] or days
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "contribution-heatmap.svg"), "w") as f:
        f.write(heatmap(days))
    with open(os.path.join(OUT_DIR, "activity-30d.svg"), "w") as f:
        f.write(daily_chart(days))
    with open(os.path.join(OUT_DIR, "activity-12m.svg"), "w") as f:
        f.write(monthly_chart(days))
    print(f"Wrote graphs for {USER} ({len(days)} days)")


if __name__ == "__main__":
    main()
