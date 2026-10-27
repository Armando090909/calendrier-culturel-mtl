"""Festivals : liste (festivals.yaml), dates des prochaines éditions, sources de programmation et étiquetage.

- Les programmations ne sont lues que pendant la « fenêtre » d'un festival : de 75 jours avant le début à la fin.
- Quand une édition est terminée (ou sans dates), le site du festival est relu une fois par mois pour trouver
  les dates de la suivante (IA, si la clé est configurée). Les dates trouvées sont gardées dans cache/festivals_dates.json.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import yaml

import ia
from normalisation import plat

ICI = Path(__file__).parent
LISTE = ICI / "festivals.yaml"
DATES = ICI / "cache" / "festivals_dates.json"
AVANCE = 75  # jours avant le début où l'on commence à lire la programmation


def _d(x) -> date | None:
    try:
        return date.fromisoformat(str(x)[:10]) if x else None
    except ValueError:
        return None


def charger(aujourd: date) -> list[dict]:
    fests = yaml.safe_load(LISTE.read_text(encoding="utf-8")).get("festivals", [])
    trouvees = json.loads(DATES.read_text(encoding="utf-8")) if DATES.exists() else {}
    for f in fests:
        f.setdefault("court", f["nom"])
        t = trouvees.get(f["id"]) if f["id"] != "_empreintes" else None
        # Une édition trouvée en ligne remplace la précédente si elle est plus récente
        if t and _d(t.get("fin")) and (not _d(f.get("fin")) or _d(t["fin"]) > _d(f["fin"])):
            f["debut"], f["fin"], f["verifier"] = t.get("debut"), t["fin"], True
    return fests


def en_fenetre(f: dict, aujourd: date) -> bool:
    d1, d2 = _d(f.get("debut")) or _d(f.get("fin")), _d(f.get("fin"))
    return bool(d1 and d2 and d1 - timedelta(days=AVANCE) <= aujourd <= d2)


def sources(fests: list[dict], aujourd: date) -> list[dict]:
    """Sources « page_ia » de tous les festivals : relues chaque lundi (veille hebdomadaire), et aussi
    mercredi et vendredi pendant leur fenêtre. Une page qui n'a pas changé depuis la dernière lecture
    ne coûte rien : son résultat est repris de la mémoire (cache/empreintes.json)."""
    out = []
    for f in fests:
        jours = [0, 2, 4] if en_fenetre(f, aujourd) else [0]
        pages = f.get("programmation") or ([f["site"]] if f.get("site") and "mtl.org" not in f["site"] else [])
        for i, url in enumerate(pages):
            out.append({"nom": f"Festival · {f['court']}" + (f" ({i + 1})" if len(pages) > 1 else ""), "type": "page_ia",
                        "url": url, "cle_source": "festival", "festival": f["id"], "lieu": f.get("lieu", ""),
                        "discipline": f["disciplines"][0] if len(f.get("disciplines", [])) == 1 else "",
                        "jours_semaine": jours, "details": True})
    return out


def chercher_dates(fests: list[dict], aujourd: date, telecharger, texte_page) -> int:
    """Chaque lundi, cherche les dates de la prochaine édition des festivals terminés.
    L'IA n'est appelée que si la page d'accueil a changé depuis la semaine précédente."""
    if not ia.disponible() or aujourd.weekday() != 0:
        return 0
    trouvees = json.loads(DATES.read_text(encoding="utf-8")) if DATES.exists() else {}
    n = 0
    for f in fests:
        fin = _d(f.get("fin"))
        if (fin and fin >= aujourd) or not f.get("site") or "mtl.org" in f["site"]:
            continue
        try:
            texte = texte_page(telecharger(f["site"], "text/html").text, f["site"])[:15000]
            emp = hashlib.sha1(texte.encode()).hexdigest()
            if trouvees.get("_empreintes", {}).get(f["id"]) == emp:
                continue  # page inchangée : rien de nouveau à chercher
            trouvees.setdefault("_empreintes", {})[f["id"]] = emp
            r = ia.dates_festival(f["nom"], f["site"], texte, aujourd.isoformat())
        except Exception as exc:
            print(f"  dates de {f['court']} : {exc}")
            continue
        if r and _d(r.get("fin")) and _d(r["fin"]) >= aujourd:
            trouvees[f["id"]] = {"debut": r.get("debut"), "fin": r["fin"], "trouve_le": aujourd.isoformat()}
            f["debut"], f["fin"], f["verifier"] = r.get("debut"), r["fin"], True
            n += 1
    DATES.parent.mkdir(exist_ok=True)
    DATES.write_text(json.dumps(trouvees, ensure_ascii=False, indent=1), encoding="utf-8")
    return n


def etiqueter(items: list[dict], fests: list[dict]) -> None:
    """Rattache un événement à un festival : par sa source, par le nom du festival dans le titre,
    ou par l'adresse de sa page (même site que le festival)."""
    noms = [(f, plat(f["court"])) for f in fests if len(plat(f["court"])) >= 5]
    domaines = {}
    for f in fests:
        h = urlparse(f.get("site", "")).netloc.replace("www.", "")
        if h and "mtl.org" not in h:
            domaines[h] = f["id"]
    for e in items:
        if e.get("festival"):
            continue
        t = f" {plat(e.get('titre', ''))} "
        for f, n in noms:
            if f" {n} " in t and _dans_edition(e, f):
                e["festival"] = f["id"]
                break
        else:
            h = urlparse(e.get("url", "")).netloc.replace("www.", "")
            if h in domaines:
                e["festival"] = domaines[h]


def _dans_edition(e: dict, f: dict) -> bool:
    d = _d(e.get("date") or e.get("debut"))
    d1, d2 = _d(f.get("debut")) or _d(f.get("fin")), _d(f.get("fin"))
    return not (d and d1 and d2) or d1 - timedelta(days=1) <= d <= d2 + timedelta(days=1)


def publier(fests: list[dict], sortie: Path) -> None:
    champs = ("id", "nom", "court", "disciplines", "debut", "fin", "mois", "lieu", "site", "verifier")
    out = [{k: (str(f[k]) if k in ("debut", "fin") and f.get(k) else f[k]) for k in champs if f.get(k) not in (None, "", [])}
           for f in fests]
    sortie.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
