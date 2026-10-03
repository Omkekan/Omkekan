#!/usr/bin/env python3
"""Generate assets/telemetry.svg from the GitHub GraphQL API (stdlib only).

Env:  GITHUB_TOKEN (required unless --placeholder/--demo)   GH_USER (default: repo owner)
Flags: --placeholder  write the "awaiting first sync" card
       --demo         write a card from random data (local look-and-feel testing only)
"""
import datetime, json, math, os, random, sys, urllib.request
from collections import defaultdict

LOGIN = os.environ.get("GH_USER", "Omkekan")
OUT = os.environ.get("OUT", "assets/telemetry.svg")

W = 830
BG, PANEL, LINE = "#1a1c1a", "#151615", "#2a2d2a"
TEXT, KEY, HI, WHITE, MUTED = "#a3b68a", "#8ab6a3", "#d3b58d", "#e6e6e6", "#5c6356"
LEVELS = ["#222522", "#3a4630", "#5e7248", "#829a66", "#a3b68a"]
FONT = "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono','Courier New',monospace"
BAR_COLORS = [KEY, HI, TEXT, "#7f9d8f", "#b79f7a"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliation: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount languages(first: 6, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
    contributionsCollection {
      totalCommitContributions totalPullRequestContributions totalIssueContributions
      contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } }
    }
  }
}"""

def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "telemetry-svg"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload or not payload.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {payload.get('errors') or 'user not found'}")
    return payload["data"]["user"]

def summarize(u):
    repos = u["repositories"]["nodes"]
    langs = defaultdict(int)
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
    total = sum(langs.values()) or 1
    top = [(n, 100 * s / total) for n, s in sorted(langs.items(), key=lambda kv: -kv[1])[:5]]
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0: i -= 1          # today may not have commits yet
    while i >= 0 and counts[i]: cur += 1; i -= 1
    return dict(repos=u["repositories"]["totalCount"], stars=sum(r["stargazerCount"] for r in repos),
                commits=cc["totalCommitContributions"], prs=cc["totalPullRequestContributions"],
                issues=cc["totalIssueContributions"], followers=u["followers"]["totalCount"],
                langs=top, weeks=cc["contributionCalendar"]["weeks"],
                total=cc["contributionCalendar"]["totalContributions"], cur=cur, longest=longest)

def demo():
    random.seed(3)
    weeks, d0 = [], datetime.date.today() - datetime.timedelta(days=370)
    for w in range(53):
        weeks.append({"contributionDays": [{"contributionCount": random.choice([0, 0, 0, 1, 2, 3, 6, 9]), "date": str(d0 + datetime.timedelta(days=w * 7 + k))} for k in range(7)]})
    return dict(repos=12, stars=34, commits=412, prs=18, issues=6, followers=21,
                langs=[("Python", 62.0), ("Jupyter Notebook", 18.5), ("TypeScript", 10.2), ("JavaScript", 5.8), ("CSS", 3.5)],
                weeks=weeks, total=1337, cur=5, longest=23)

def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render(d):
    pending = d is None
    H = 352
    p = [f'<rect width="{W}" height="{H}" fill="{BG}"/>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="8" fill="{BG}" stroke="{LINE}"/>',
         f'<path d="M0.5 34 V8.5 a8 8 0 0 1 8 -8 H{W-8.5} a8 8 0 0 1 8 8 V34 Z" fill="{PANEL}"/><line x1="0" x2="{W}" y1="34" y2="34" stroke="{LINE}"/>',
         f'<circle cx="20" cy="17" r="5" fill="#d38d8d"/><circle cx="38" cy="17" r="5" fill="{HI}"/><circle cx="56" cy="17" r="5" fill="{TEXT}"/>']
    stamp = "awaiting first sync" if pending else f"synced {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d} UTC"
    p.append(f'<text x="{W/2}" y="21" text-anchor="middle" font-size="12" fill="{MUTED}">telemetry.dat &#183; {esc(LOGIN)} &#183; {stamp}</text>')

    # key/value block
    rows = [("repos", "repos"), ("stars", "stars earned"), ("commits", "commits / yr"), ("prs", "pull requests"), ("issues", "issues"), ("followers", "followers")]
    for i, (k, label) in enumerate(rows):
        y = 70 + i * 24
        val = "--" if pending else f"{d[k]:,}"
        p.append(f'<text x="28" y="{y}" font-size="13" fill="{TEXT}">{label}</text>')
        p.append(f'<line x1="{28 + len(label) * 7.8 + 8:.0f}" x2="288" y1="{y-4}" y2="{y-4}" stroke="{LINE}" stroke-dasharray="2 4"/>')
        p.append(f'<text x="300" y="{y}" font-size="13" fill="{WHITE}" text-anchor="end">{val}</text>')

    # languages
    p.append(f'<text x="360" y="52" font-size="11" fill="{MUTED}">top languages (by bytes, public repos)</text>')
    langs = [] if pending else d["langs"]
    for i in range(5):
        y = 78 + i * 25
        if i < len(langs):
            n, pct = langs[i]; bw = max(2, 260 * pct / 100)
            p.append(f'<text x="360" y="{y}" font-size="13" fill="{TEXT}">{esc(n[:16])}</text>')
            p.append(f'<rect x="498" y="{y-10}" width="260" height="8" rx="2" fill="{LINE}"/>')
            p.append(f'<rect x="498" y="{y-10}" width="0" height="8" rx="2" fill="{BAR_COLORS[i]}"><animate attributeName="width" from="0" to="{bw:.0f}" dur="0.9s" begin="{0.2+i*0.12:.2f}s" fill="freeze"/></rect>')
            p.append(f'<text x="806" y="{y}" font-size="12" fill="{WHITE}" text-anchor="end">{pct:.1f}%</text>')
        elif pending and i == 0:
            p.append(f'<text x="360" y="{y}" font-size="13" fill="{MUTED}">run the "Update telemetry" workflow once</text>')

    # contribution heatmap
    weeks = [] if pending else d["weeks"][-53:]
    flat = [x["contributionCount"] for w in weeks for x in w["contributionDays"]]
    mx = max(flat) if flat else 1
    hx, hy, cs, gp = 28, 206, 11, 2
    for wi in range(53):
        cells = []
        for di in range(7):
            c = weeks[wi]["contributionDays"][di]["contributionCount"] if wi < len(weeks) and di < len(weeks[wi]["contributionDays"]) else 0
            lvl = 0 if c == 0 else min(4, max(1, math.ceil(4 * c / (mx or 1))))
            cells.append(f'<rect x="{hx + wi*(cs+gp)}" y="{hy + di*(cs+gp)}" width="{cs}" height="{cs}" rx="2" fill="{LEVELS[lvl]}"/>')
        p.append(f'<g opacity="0">{"".join(cells)}<animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{0.4 + wi*0.02:.2f}s" fill="freeze"/></g>')
    foot = "contributions: -- &#183; streak: -- &#183; longest: --" if pending else \
        f'contributions in the last year: <tspan fill="{WHITE}">{d["total"]:,}</tspan> &#183; current streak: <tspan fill="{WHITE}">{d["cur"]}d</tspan> &#183; longest: <tspan fill="{WHITE}">{d["longest"]}d</tspan>'
    p.append(f'<text x="28" y="{H-16}" font-size="12" fill="{MUTED}">{foot}</text>')
    legend_x = W - 28 - 5 * 13 - 62
    p.append(f'<text x="{legend_x}" y="{H-16}" font-size="11" fill="{MUTED}">less</text>')
    for i, c in enumerate(LEVELS):
        p.append(f'<rect x="{legend_x + 30 + i*13}" y="{H-26}" width="11" height="11" rx="2" fill="{c}"/>')
    p.append(f'<text x="{legend_x + 30 + 5*13 + 4}" y="{H-16}" font-size="11" fill="{MUTED}">more</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="GitHub telemetry for {esc(LOGIN)}"><g font-family="{FONT}">{"".join(p)}</g></svg>')

def main():
    if "--placeholder" in sys.argv: data = None
    elif "--demo" in sys.argv: data = demo()
    else:
        token = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set")
        data = summarize(fetch(LOGIN, token))
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(render(data))
    print("wrote", OUT)

if __name__ == "__main__":
    main()
