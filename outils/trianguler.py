"""Triangulation de la semaine (20 nov. 2026, demande de l'équipe).

Liste les sorties des N prochains jours à qui il manque l'heure ou la salle, avec tous leurs liens, pour qu'une
personne (ou Claude, chaque dimanche) les vérifie sur d'autres sources : site de la salle, billetterie, fiche de la
Ville, site du festival, réseaux publics de l'organisateur. Ce qui est confirmé va dans collecteur/corrections.json
(champs : date, lieu, titre, et heure / nouveau_lieu + adresse / nouvelle_date / retirer, avec la « source »).

Usage : python3 outils/trianguler.py [jours=7] [debut=AAAA-MM-JJ]
Écrit outils/diag/trianguler.json (la liste) et l'affiche.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "docs" / "data.json"
CORR = RACINE / "collecteur" / "corrections.json"
SORTIE = RACINE / "outils" / "diag" / "trianguler.json"

# Pages que le robot ne lit pas (robots.txt ou blocage) : à vérifier par d'autres sources, jamais en contournant
BLOQUEES = ("zeffy.com", "ra.co", "facebook.com", "instagram.com", "ticketmaster", "eventbrite")


def main() -> int:
    jours = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    debut = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
    fin = (debut + timedelta(days=jours)).isoformat()
    d = json.loads(DATA.read_text(encoding="utf-8"))
    deja = {(c["date"], c["titre"].lower()) for c in json.loads(CORR.read_text(encoding="utf-8")).get("evenements", [])}
    ev = [e for e in d["events"] if debut.isoformat() <= e["date"] <= fin]
    rep = Counter((e["titre"], e.get("heure")) for e in ev if e["lieu"] == "Lieu à confirmer")
    a_voir = []
    for e in sorted(ev, key=lambda x: (x["date"], x.get("heure") or "")):
        manque = [m for m, ok in (("heure", e.get("heure")), ("salle", e["lieu"] != "Lieu à confirmer")) if not ok]
        if not manque:
            continue
        autres = e.get("liens") if isinstance(e.get("liens"), list) else []
        autres = [x.get("url", "") if isinstance(x, dict) else x for x in autres]
        liens = list(dict.fromkeys(u for u in [e["url"], e.get("billets") or "", *autres]
                                   if isinstance(u, str) and u.startswith("http")))
        a_voir.append({
            "date": e["date"], "titre": e["titre"], "lieu": e["lieu"], "heure": e.get("heure"), "manque": manque,
            "source": e.get("source"), "festival": e.get("festival", ""), "liens": liens,
            "bloquees": [u for u in liens if any(b in u for b in BLOQUEES)],
            "deja_corrigee": any(t in e["titre"].lower() for (dd, t) in deja if dd == e["date"]),
            "suspect": rep[(e["titre"], e.get("heure"))] >= 3,
        })
    SORTIE.write_text(json.dumps({"du": debut.isoformat(), "au": fin, "total": len(a_voir), "a_voir": a_voir},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Du {debut} au {fin} : {len(a_voir)} sorties à trianguler "
          f"({sum('heure' in x['manque'] for x in a_voir)} sans heure, {sum('salle' in x['manque'] for x in a_voir)} sans salle)")
    for x in a_voir:
        drap = ("  [déjà corrigée]" if x["deja_corrigee"] else "") + ("  [répétée : suspecte]" if x["suspect"] else "")
        print(f"- {x['date']} | {x['titre'][:60]} | {x['lieu']} | manque : {', '.join(x['manque'])}{drap}")
        for u in x["liens"]:
            print(f"    {u}" + ("   (bloquée : chercher ailleurs)" if u in x["bloquees"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
