#!/usr/bin/env python3
"""Build profile/contributions.svg (weekly bars) and profile/streak.svg from the GraphQL contribution calendar."""
import json, os, urllib.request
from datetime import date, datetime, timedelta

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "NemesisHubris")
FONT = "Segoe UI,Ubuntu,sans-serif"
BG, BORDER, TITLE, MUTED, TEXT, ACCENT = "#0d1117", "#30363d", "#a371f7", "#8b949e", "#c9d1d9", "#58a6ff"

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{contributionCount date}}}}}}"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        {"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req, timeout=30))
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def bars(cal):
    weekly = [(w["contributionDays"][0]["date"], sum(d["contributionCount"] for d in w["contributionDays"])) for w in cal["weeks"]]
    W, H, pl, pr, pt, pb = 800, 260, 50, 20, 45, 45
    cw, ch = W - pl - pr, H - pt - pb
    n, top, gap = len(weekly), max(c for _, c in weekly) or 1, 2
    bw = (cw - gap * (n - 1)) / n

    def color(c):
        return "#161b22" if c == 0 else "#0e4429" if c < top * .25 else "#006d32" if c < top * .5 else "#26a641" if c < top * .75 else "#39d353"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
           f'<text x="{pl}" y="26" font-family="{FONT}" font-size="14" font-weight="600" fill="{TITLE}">Contributions per week</text>',
           f'<text x="{W - pr}" y="26" text-anchor="end" font-family="{FONT}" font-size="13" fill="{MUTED}">{cal["totalContributions"]:,} in the last year</text>']
    for i in range(5):
        v = int(top * i / 4)
        y = pt + ch - v / top * ch
        out.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{W - pr}" y2="{y:.1f}" stroke="#21262d" stroke-dasharray="4,4"/>')
        out.append(f'<text x="{pl - 8}" y="{y + 4:.1f}" text-anchor="end" font-family="monospace" font-size="11" fill="#484f58">{v}</text>')
    seen = set()
    for i, (d, c) in enumerate(weekly):
        x = pl + i * (bw + gap)
        h = max(1, c / top * ch)
        out.append(f'<rect x="{x:.1f}" y="{pt + ch - h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{color(c)}" rx="1.5"><title>{d}: {c}</title></rect>')
        if d[:7] not in seen:
            seen.add(d[:7])
            out.append(f'<text x="{x + bw / 2:.1f}" y="{H - 14}" text-anchor="middle" font-family="{FONT}" font-size="11" fill="#484f58">{datetime.strptime(d, "%Y-%m-%d").strftime("%b")}</text>')
    out.append("</svg>")
    return "\n".join(out)


def streaks(cal):
    days = sorted((d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"] if d["date"] <= date.today().isoformat())
    best = run = 0
    best_end = None
    for d, c in days:
        run = run + 1 if c else 0
        if run > best:
            best, best_end = run, d
    cur, i = 0, len(days) - 1
    if i >= 0 and days[i][1] == 0:  # today may not have a commit yet
        i -= 1
    while i >= 0 and days[i][1]:
        cur += 1
        i -= 1
    total = sum(c for _, c in days)
    cols = [("Current streak", f"{cur}", "days"), ("Longest streak", f"{best}", "days"), ("Last 12 months", f"{total:,}", "contributions")]
    W, H = 800, 130
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>']
    for k, (label, val, unit) in enumerate(cols):
        cx = W / 6 + k * W / 3
        out.append(f'<text x="{cx:.0f}" y="62" text-anchor="middle" font-family="{FONT}" font-size="38" font-weight="700" fill="{TITLE if k == 0 else ACCENT if k == 1 else TEXT}">{val}</text>')
        out.append(f'<text x="{cx:.0f}" y="88" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{TEXT}">{label}</text>')
        out.append(f'<text x="{cx:.0f}" y="106" text-anchor="middle" font-family="{FONT}" font-size="11" fill="{MUTED}">{unit}</text>')
        if k:
            out.append(f'<line x1="{W / 3 * k:.0f}" y1="25" x2="{W / 3 * k:.0f}" y2="{H - 25}" stroke="{BORDER}"/>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    cal = fetch()
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "contributions.svg"), "w").write(bars(cal))
    open(os.path.join(here, "streak.svg"), "w").write(streaks(cal))
    print("ok", cal["totalContributions"])
