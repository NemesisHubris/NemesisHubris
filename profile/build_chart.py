#!/usr/bin/env python3
"""Build profile/contributions.svg (weekly bars) and profile/streak.svg from the GraphQL contribution calendar."""
import base64, json, os, urllib.request
from datetime import date, datetime, timedelta

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "NemesisHubris")
FONT = "Segoe UI,Ubuntu,sans-serif"
BG, BORDER, TITLE, MUTED, TEXT, ACCENT = "#070b14", "#1c2433", "#e6edf3", "#7d8798", "#aab4c3", "#3fb950"

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
        return "#0f1623" if c == 0 else "#0e4429" if c < top * .25 else "#006d32" if c < top * .5 else "#26a641" if c < top * .75 else "#39d353"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
           f'<text x="{pl}" y="26" font-family="{FONT}" font-size="14" font-weight="600" fill="{TITLE}">Contributions per week</text>',
           f'<text x="{W - pr}" y="26" text-anchor="end" font-family="{FONT}" font-size="13" fill="{MUTED}">{cal["totalContributions"]:,} in the last year</text>']
    for i in range(5):
        v = int(top * i / 4)
        y = pt + ch - v / top * ch
        out.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{W - pr}" y2="{y:.1f}" stroke="#141c2b" stroke-dasharray="4,4"/>')
        out.append(f'<text x="{pl - 8}" y="{y + 4:.1f}" text-anchor="end" font-family="monospace" font-size="11" fill="#484f58">{v}</text>')
    seen, last_x = set(), -99
    for i, (d, c) in enumerate(weekly):
        x = pl + i * (bw + gap)
        h = max(1, c / top * ch)
        out.append(f'<rect x="{x:.1f}" y="{pt + ch - h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{color(c)}" rx="1.5"><title>{d}: {c}</title></rect>')
        if d[:7] not in seen:
            seen.add(d[:7])
            if x - last_x < 28:
                continue
            last_x = x
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
        out.append(f'<text x="{cx:.0f}" y="62" text-anchor="middle" font-family="{FONT}" font-size="38" font-weight="700" fill="{ACCENT if k == 0 else TITLE}">{val}</text>')
        out.append(f'<text x="{cx:.0f}" y="88" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{TEXT}">{label}</text>')
        out.append(f'<text x="{cx:.0f}" y="106" text-anchor="middle" font-family="{FONT}" font-size="11" fill="{MUTED}">{unit}</text>')
        if k:
            out.append(f'<line x1="{W / 3 * k:.0f}" y1="25" x2="{W / 3 * k:.0f}" y2="{H - 25}" stroke="{BORDER}"/>')
    out.append("</svg>")
    return "\n".join(out)


STATS_QUERY = """query($login:String!){user(login:$login){avatarUrl(size:200) followers{totalCount}
repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){totalCount nodes{stargazerCount}}
pullRequests{totalCount} issues{totalCount}
contributionsCollection{totalCommitContributions restrictedContributionsCount}}}"""


def gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        {"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]


def stats_card():
    u = gql(STATS_QUERY)
    av = base64.b64encode(urllib.request.urlopen(u["avatarUrl"], timeout=30).read()).decode()
    cc = u["contributionsCollection"]
    rows = [("Stars earned", sum(r["stargazerCount"] for r in u["repositories"]["nodes"])),
            ("Commits, last year", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
            ("Pull requests", u["pullRequests"]["totalCount"]),
            ("Issues", u["issues"]["totalCount"]),
            ("Followers", u["followers"]["totalCount"])]
    W, H = 440, 200
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
           f'<text x="26" y="36" font-family="{FONT}" font-size="16" font-weight="600" fill="{TITLE}">GitHub stats</text>']
    for i, (k, v) in enumerate(rows):
        y = 70 + i * 24
        out.append(f'<circle cx="31" cy="{y - 4}" r="3" fill="{ACCENT}"/>')
        out.append(f'<text x="44" y="{y}" font-family="{FONT}" font-size="13.5" fill="{TEXT}">{k}</text>')
        out.append(f'<text x="235" y="{y}" text-anchor="end" font-family="{FONT}" font-size="13.5" font-weight="600" fill="{TITLE}">{v:,}</text>')
    out += [f'<defs><clipPath id="av"><circle cx="340" cy="100" r="52"/></clipPath></defs>',
            f'<circle cx="340" cy="100" r="58" fill="none" stroke="{ACCENT}" stroke-width="3"/>',
            f'<image x="288" y="48" width="104" height="104" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{av}"/>',
            "</svg>"]
    return "\n".join(out)


if __name__ == "__main__":
    cal = fetch()
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "contributions.svg"), "w").write(bars(cal))
    open(os.path.join(here, "streak.svg"), "w").write(streaks(cal))
    open(os.path.join(here, "stats.svg"), "w").write(stats_card())
    print("ok", cal["totalContributions"])
