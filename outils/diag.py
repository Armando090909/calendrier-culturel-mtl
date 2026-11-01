"""Diagnostic : lit chaque adresse de outils/diag/urls.txt comme la collecte (téléchargement simple, puis navigateur)
et garde ce qui sert à comprendre pourquoi une heure ou un horaire manque : statut, texte visible, données schema.org,
heures repérées. Résultat : outils/diag/resultat.json. Lancé par .github/workflows/diagnostic.yml."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collecteur"))
import connecteurs as c  # noqa: E402

D = Path(__file__).resolve().parent / "diag"
HEURE = re.compile(r"(?i)\b\d{1,2}\s?(?:h|:)\s?\d{0,2}\s?(?:am|pm)?\b|\b\d{1,2}\s?(?:am|pm)\b")
out = {}
for url in [l.strip() for l in (D / "urls.txt").read_text().splitlines() if l.strip().startswith("http")]:
    r = {}
    for mode in ("simple", "navigateur"):
        try:
            if mode == "simple":
                rep = c.telecharger(url, "text/html")
                html, r["statut"] = rep.text, rep.status_code
            else:
                html = c.page_rendue(url)
            txt = c.texte_page(html, url)
            r[mode] = {"taille": len(txt), "texte": txt[:5000],
                       "jsonld": re.findall(r'(?s)<script[^>]*ld\+json[^>]*>(.*?)</script>', html)[:2],
                       "heures": [txt[max(0, m.start() - 60):m.end() + 20] for m in HEURE.finditer(txt)][:15],
                       "liens": sorted({a for a in re.findall(r'href="(https?://[^"]+)"', html)
                                        if any(k in a for k in ("event", "evenement", "spectacle", "show", "billet", "ticket"))})[:30]}
        except Exception as exc:
            r[mode] = {"erreur": str(exc)[:300]}
    out[url] = r
    print(url, {k: (v.get("taille") if isinstance(v, dict) else v) for k, v in r.items()})
(D / "resultat.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
