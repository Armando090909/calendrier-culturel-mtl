"""Diagnostic : charge chaque affiche du calendrier dans un vrai navigateur (Chromium), comme sur ccmtl.ca
(referrerpolicy=no-referrer), et compte les échecs par site d'origine. Résultat : outils/diag/affiches.json."""
import json, collections, pathlib, urllib.parse
from playwright.sync_api import sync_playwright

RACINE = pathlib.Path(__file__).resolve().parent.parent
d = json.loads((RACINE / "docs/data.json").read_text(encoding="utf-8"))
urls = {}
for e in d["events"]:
    a = e.get("affiche") or {}
    u = a.get("url") or e.get("image")
    if u and u.startswith("http"):
        urls.setdefault(u, (a.get("petit"), e.get("discipline")))
liste = list(urls)
html = "<html><body>" + "".join(
    f'<img data-i="{i}" referrerpolicy="no-referrer" src="{u.replace(chr(34), "%22")}">' for i, u in enumerate(liste)) + "</body></html>"
with sync_playwright() as p:
    nav = p.chromium.launch()
    page = nav.new_page()
    page.set_content(html, wait_until="load", timeout=600_000)
    page.wait_for_timeout(5000)
    ok = page.eval_on_selector_all("img", "els => els.map(e => e.complete && e.naturalWidth > 0)")
    nav.close()
par = collections.defaultdict(lambda: [0, 0])
echecs = collections.defaultdict(list)
for u, bon in zip(liste, ok):
    h = urllib.parse.urlparse(u).hostname
    par[h][0] += 1
    if not bon:
        par[h][1] += 1
        echecs[h].append(u)
res = {"total": len(liste), "echecs": sum(v[1] for v in par.values()),
       "par_site": {h: {"affiches": v[0], "echecs": v[1]} for h, v in sorted(par.items(), key=lambda x: -x[1][1])},
       "exemples": {h: l[:3] for h, l in echecs.items()},
       "sans_affiche_par_discipline": collections.Counter(e["discipline"] for e in d["events"]
                                                           if not e.get("affiche") and not e.get("image"))}
(RACINE / "outils/diag/affiches.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: res[k] for k in ("total", "echecs")}))
