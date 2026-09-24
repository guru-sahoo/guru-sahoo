"""Generate dark-theme contribution SVGs for the GitHub profile README.

Outputs:
  assets/contribution-heatmap.svg  - last 12 months, full-width heatmap
  assets/activity-30d.svg          - daily contributions, last 30 days, line graph

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


def line_chart(days, span=30):
    days = sorted(days, key=lambda d: d["date"])[-span:]
    vals = [d["contributionCount"] for d in days]
    W, H, pl, pr, pt, pb = 900, 300, 50, 35, 60, 45
    cw, ch = W - pl - pr, H - pt - pb
    ymax = max(max(vals), 4)
    step = max(1, round(ymax / 4))
    ymax = step * 4
    xs = [pl + i * cw / (len(vals) - 1) for i in range(len(vals))]
    ys = [pt + ch - v / ymax * ch for v in vals]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{pl},{pt + ch} {pts} {xs[-1]:.1f},{pt + ch}"

    grid = []
    for i in range(5):
        y = pt + ch - i * ch / 4
        grid.append(f'<line x1="{pl}" x2="{W - pr}" y1="{y:.1f}" y2="{y:.1f}" stroke="{BORDER}" stroke-dasharray="3 4"/>')
        grid.append(f'<text x="{pl - 10}" y="{y + 4:.1f}" text-anchor="end" class="t">{i * step}</text>')
    xl = []
    for i, d in enumerate(days):
        if i % 5 == 0 or i == len(days) - 1:
            day = dt.date.fromisoformat(d["date"])
            xl.append(f'<text x="{xs[i]:.1f}" y="{H - pb + 20}" text-anchor="middle" class="t">{day:%d %b}</text>')
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{BG}" stroke="{ACCENT}" stroke-width="2">'
        f'<title>{v} on {d["date"]}</title></circle>'
        for x, y, v, d in zip(xs, ys, vals, days)
    )
    total, peak = sum(vals), max(vals)
    active = sum(1 for v in vals if v)
    stats = f"{total} contributions  ·  {active}/{len(vals)} active days  ·  peak {peak}/day"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f'<defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{ACCENT_2}" stop-opacity=".45"/>'
        f'<stop offset="1" stop-color="{ACCENT_2}" stop-opacity="0"/></linearGradient></defs>'
        f'<style>.t{{fill:{MUTED};font-size:12px}}</style>'
        f'<rect width="100%" height="100%" rx="8" fill="{BG}" stroke="{BORDER}"/>'
        f'<g {FONT}>'
        f'<text x="{pl}" y="30" fill="{TEXT}" font-size="16" font-weight="600">Daily contributions · last {len(vals)} days</text>'
        f'<text x="{W - pr}" y="30" text-anchor="end" class="t">{stats}</text>'
        f'{"".join(grid)}{"".join(xl)}'
        f'<polygon points="{area}" fill="url(#a)"/>'
        f'<polyline points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linejoin="round"/>'
        f'{dots}</g></svg>'
    )


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
        f.write(line_chart(days))
    print(f"Wrote graphs for {USER} ({len(days)} days)")


if __name__ == "__main__":
    main()
