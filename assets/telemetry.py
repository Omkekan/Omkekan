#!/usr/bin/env python3
"""Generate assets/telemetry.svg from the GitHub GraphQL API (stdlib only).

Env:  GITHUB_TOKEN (required unless --placeholder/--demo)   GH_USER (default: repo owner)
Flags: --placeholder  write the "awaiting first sync" card
       --demo         write a card from random data (local look-and-feel testing only)
"""
import datetime, json, os, sys, urllib.request
from collections import defaultdict

LOGIN = os.environ.get("GH_USER", "Omkekan")
OUT = os.environ.get("OUT", "assets/telemetry.svg")

W = 830
BG, PANEL, LINE = "#1a1c1a", "#151615", "#2a2d2a"
TEXT, KEY, HI, WHITE, MUTED = "#a3b68a", "#8ab6a3", "#d3b58d", "#e6e6e6", "#5c6356"
FONT = "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono','Courier New',monospace"
BAR_COLORS = [KEY, HI, TEXT, "#7f9d8f", "#b79f7a", "#6f8f7e", "#b0a07c", "#7898a0", "#9b8f72", "#8ba66f"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    repositories(ownerAffiliations: [OWNER], isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
    contributionsCollection {
      totalCommitContributions
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
    top = [(n, 100 * s / total) for n, s in sorted(langs.items(), key=lambda kv: -kv[1])[:10]]
    cc = u["contributionsCollection"]
    repos_count = u["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in repos)
    commits = cc["totalCommitContributions"]
    score = min(100, repos_count * 2 + stars * 1.5 + commits * 0.05)
    rank = "S" if score >= 90 else "A+" if score >= 75 else "A" if score >= 60 else "B+" if score >= 45 else "B" if score >= 30 else "C"
    created = datetime.date.fromisoformat(u["createdAt"][:10])
    age = datetime.date.today().year - created.year - ((datetime.date.today().month, datetime.date.today().day) < (created.month, created.day))
    return dict(repos=repos_count, stars=stars, rank=rank, age=age, langs=top)

def demo():
    return dict(repos=12, stars=34, rank="A", age=8,
                langs=[("Python", 42.0), ("Jupyter Notebook", 18.5), ("TypeScript", 10.2),
                       ("JavaScript", 8.8), ("CSS", 6.5), ("HTML", 4.5), ("Shell", 3.5),
                       ("Dockerfile", 2.8), ("Java", 2.0), ("C++", 1.2)])

def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render(d):
    pending = d is None
    H = 320
    p = [f'<rect width="{W}" height="{H}" fill="{BG}"/>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="8" fill="{BG}" stroke="{LINE}"/>',
         f'<path d="M0.5 34 V8.5 a8 8 0 0 1 8 -8 H{W-8.5} a8 8 0 0 1 8 8 V34 Z" fill="{PANEL}"/><line x1="0" x2="{W}" y1="34" y2="34" stroke="{LINE}"/>',
         f'<circle cx="20" cy="17" r="5" fill="#d38d8d"/><circle cx="38" cy="17" r="5" fill="{HI}"/><circle cx="56" cy="17" r="5" fill="{TEXT}"/>']
    stamp = "awaiting first sync" if pending else f"synced {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d} UTC"
    p.append(f'<text x="{W/2}" y="21" text-anchor="middle" font-size="12" fill="{MUTED}">telemetry.dat &#183; {esc(LOGIN)} &#183; {stamp}</text>')

    # key/value block
    rows = [("repos", "public repos"), ("stars", "stars earned"), ("rank", "github rank"), ("age", "account age"), ("langs_count", "languages")]
    for i, (k, label) in enumerate(rows):
        y = 70 + i * 24
        if pending:
            val = "--"
        elif k == "age":
            val = f"{d[k]} yrs"
        elif k == "langs_count":
            val = f"{len(d['langs'])}"
        else:
            val = "--" if pending else f"{d[k]:,}" if k != "rank" else d[k]
        p.append(f'<text x="28" y="{y}" font-size="13" fill="{TEXT}">{label}</text>')
        p.append(f'<line x1="{28 + len(label) * 7.8 + 8:.0f}" x2="288" y1="{y-4}" y2="{y-4}" stroke="{LINE}" stroke-dasharray="2 4"/>')
        p.append(f'<text x="300" y="{y}" font-size="13" fill="{WHITE}" text-anchor="end">{val}</text>')

    # languages
    p.append(f'<text x="360" y="52" font-size="11" fill="{MUTED}">top languages (by bytes, public repos)</text>')
    langs = [] if pending else d["langs"]
    for i in range(10):
        y = 63 + i * 23
        if i < len(langs):
            n, pct = langs[i]; bw = max(2, 260 * pct / 100)
            p.append(f'<text x="360" y="{y}" font-size="13" fill="{TEXT}">{esc(n[:16])}</text>')
            p.append(f'<rect x="498" y="{y-10}" width="260" height="8" rx="2" fill="{LINE}"/>')
            p.append(f'<rect x="498" y="{y-10}" width="0" height="8" rx="2" fill="{BAR_COLORS[i]}"><animate attributeName="width" from="0" to="{bw:.0f}" dur="0.9s" begin="{0.2+i*0.12:.2f}s" fill="freeze"/></rect>')
            p.append(f'<text x="806" y="{y}" font-size="12" fill="{WHITE}" text-anchor="end">{pct:.1f}%</text>')
        elif pending and i == 0:
            p.append(f'<text x="360" y="{y}" font-size="13" fill="{MUTED}">run the "Update telemetry" workflow once</text>')

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
