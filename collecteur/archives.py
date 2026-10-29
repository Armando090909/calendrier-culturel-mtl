"""Archives : les événements passés, rangés par mois (docs/archives/AAAA-MM.json) + un index (docs/archives/index.json).

À chaque collecte, les événements de la veille et d'avant, encore présents dans la publication précédente, sont
ajoutés à leur mois. Rien n'est jamais retiré d'une archive ; une même activité n'y figure qu'une fois.
"""
from __future__ import annotations

import json
from pathlib import Path

GARDER = ("date", "heure", "discipline", "aussi", "sous", "titre", "lieu", "url", "festival", "style", "prix", "resume", "source")


def cle(e: dict) -> str:
    return f"{e['date']}|{e.get('heure') or ''}|{e['titre']}|{e['lieu']}"


def ajouter(evenements: list[dict], avant: str, dossier: Path, lieux: dict | None = None) -> int:
    """Archive les événements dont la date est antérieure à « avant » (AAAA-MM-JJ). Renvoie le nombre d'ajouts."""
    dossier.mkdir(parents=True, exist_ok=True)
    par_mois: dict[str, list[dict]] = {}
    for e in evenements:
        if e.get("date") and e["date"] < avant and e.get("source") != "recurrents":
            par_mois.setdefault(e["date"][:7], []).append({k: e[k] for k in GARDER if e.get(k)})
    ajouts = 0
    for mois, L in par_mois.items():
        f = dossier / f"{mois}.json"
        ancien = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"mois": mois, "events": [], "lieux": {}}
        vus = {cle(e) for e in ancien["events"]}
        for e in L:
            if cle(e) not in vus:
                vus.add(cle(e))
                ancien["events"].append(e)
                ajouts += 1
                if lieux and e["lieu"] in lieux and e["lieu"] not in ancien["lieux"]:
                    ancien["lieux"][e["lieu"]] = {k: v for k, v in (lieux[e["lieu"]] or {}).items() if k in ("quartier",)}
        # mêmes règles que le calendrier : pas de doublons ni de redites, pas de fausses salles
        from normalisation import PAS_DES_SALLES, dedoublonner, doublons_du_jour, plat
        for e in ancien["events"]:
            if plat(e["lieu"]) in PAS_DES_SALLES:
                e["lieu"] = "Lieu à confirmer"
        ancien["events"], _ = doublons_du_jour(dedoublonner(ancien["events"]))
        ancien["events"].sort(key=lambda e: (e["date"], e.get("heure") or "99", e["titre"]))
        ajouts = ajouts  # (le compte ci-dessus inclut des fiches ensuite fusionnées)
        f.write_text(json.dumps(ancien, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    index = []
    for f in sorted(dossier.glob("????-??.json"), reverse=True):
        d = json.loads(f.read_text(encoding="utf-8"))
        index.append({"mois": d["mois"], "n": len(d["events"])})
    (dossier / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return ajouts
