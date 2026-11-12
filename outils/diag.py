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
import hashlib  # noqa: E402
for ligne in [l.strip() for l in (D / "urls.txt").read_text().splitlines() if l.strip().startswith(("http", "IMG ", "JSON ", "FICHIER "))]:
    if ligne.startswith("FICHIER "):  # fichier complet (données ouvertes) gardé dans outils/diag/fichiers/
        url = ligne[8:]
        try:
            rep = c.requests.get(url, timeout=120, headers={"User-Agent": c.UA})
            (D / "fichiers").mkdir(exist_ok=True)
            nom = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("?")[0].rstrip("/").split("/")[-1])[-80:] or "fichier"
            (D / "fichiers" / nom).write_bytes(rep.content)
            out[url] = {"statut": rep.status_code, "octets": len(rep.content), "fichier": nom}
        except Exception as exc:
            out[url] = {"erreur": str(exc)[:200]}
        print(url, out[url])
        continue
    if ligne.startswith("JSON "):  # réponse d'une API publique (extrait)
        url = ligne[5:]
        try:
            rep = c.requests.get(url, timeout=30, headers={"User-Agent": c.UA})
            out[url] = {"statut": rep.status_code, "extrait": rep.text[:2500]}
        except Exception as exc:
            out[url] = {"erreur": str(exc)[:200]}
        print(url, str(out[url])[:200])
        continue
    if ligne.startswith("IMG "):  # image : taille et empreinte (repérer les images par défaut identiques)
        url = ligne[4:]
        try:
            b = c.requests.get(url, timeout=30, headers={"User-Agent": c.UA}).content
            out[url] = {"octets": len(b), "md5": hashlib.md5(b).hexdigest()}
        except Exception as exc:
            out[url] = {"erreur": str(exc)[:200]}
        print(url, out[url])
        continue
    url, attente = ligne, 2500
    if " attente=" in ligne:  # « adresse attente=15000 » : calendrier lent à s'afficher
        url, attente = ligne.split(" attente=")[0].strip(), int(ligne.split(" attente=")[1])
    r = {}
    for mode in ("simple", "navigateur"):
        try:
            if mode == "simple":
                rep = c.telecharger(url, "text/html")
                html, r["statut"] = rep.text, rep.status_code
            else:
                html = c.page_rendue(url, attente)
            txt = c.texte_page(html, url)
            from bs4 import BeautifulSoup
            soupe = BeautifulSoup(html, "html.parser")
            og = soupe.find("meta", attrs={"property": "og:image"})
            r[mode + "_images"] = {"og": og.get("content") if og else None,
                                   "img": [(i.get("src") or i.get("data-src") or "")[:150] + " | " + (i.get("alt") or "")[:60]
                                           for i in soupe.find_all("img")][:25],
                                   "iframes": [f.get("src", "")[:150] for f in soupe.find_all("iframe")][:10],
                                   # calendriers intégrés : l'identifiant du calendrier (Google, eventscalendar.co, ICS…)
                                   "calendriers": [html[max(0, m.start() - 150):m.end() + 250] for m in re.finditer(
                                       r"proj_[A-Za-z0-9]+|eventscalendar\.co[^\"' ]*|calendar\.google\.com[^\"' ]*|[^\"' ]+\.ics\b", html)][:8]}
            r[mode] = {"taille": len(txt), "texte": txt[:8000],
                       "jsonld": re.findall(r'(?s)<script[^>]*ld\+json[^>]*>(.*?)</script>', html)[:2],
                       "heures": [txt[max(0, m.start() - 60):m.end() + 20] for m in HEURE.finditer(txt)][:15],
                       "liens": sorted({a for a in re.findall(r'href="(https?://[^"]+)"', html)
                                        if any(k in a for k in ("event", "evenement", "spectacle", "show", "billet", "ticket"))})[:30],
                       # tous les liens du site (texte + adresse), pour trouver la page de programmation
                       "menu": [((x.get_text(" ", strip=True) or "")[:50] + " → " + c.urljoin(url, x.get("href")))[:200]
                                for x in soupe.find_all("a", href=True)
                                if re.search(r"(?i)program|calend|agenda|horaire|spectacl|event|événement|evenement|concert|show|saison|season|billet|ticket|activit|atelier|lancement|cours|danse|soir",
                                             (x.get("href") or "") + " " + x.get_text(" ", strip=True))][:60]}
        except Exception as exc:
            r[mode] = {"erreur": str(exc)[:300]}
    out[url] = r
    print(url, {k: (v.get("taille") if isinstance(v, dict) else v) for k, v in r.items()})
(D / "resultat.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
