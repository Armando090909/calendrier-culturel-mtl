"""Bilan de santé après chaque collecte : repère ce qui cloche, et ouvre un avis (issue GitHub, donc un courriel)
seulement quand un problème DURE et que le programme n'a pas su le régler seul. L'avis se ferme tout seul quand le
problème disparaît.

Problèmes suivis :
- une source qui donnait des événements et n'en donne plus (ou est en erreur) depuis 3 collectes ;
- un site dont la moitié des fiches (au moins 10) restent sans heure ou sans salle depuis 3 collectes ;
- une chute de plus de 25 % du nombre total d'événements ;
- des sites qui demandent aux robots de ne pas lire certaines pages (robots.txt) : signalé une fois.

Mémoire : collecteur/cache/sante.json. Lancé par la collecte (GH_TOKEN fourni), avant l'enregistrement.
"""
import json
import re
import subprocess
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

RACINE = Path(__file__).resolve().parent.parent
F_ETAT = RACINE / "collecteur" / "cache" / "sante.json"
JOURS_AVANT_AVIS = 3


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    return r.returncode, (r.stdout or r.stderr).strip()


def problemes(rapport, data, etat):
    out = {}  # clé -> (titre, détail, action suggérée)
    for s in rapport.get("sources", []):
        nom = s["source"]
        vide = (s.get("evenements", 0) + s.get("series", 0)) == 0
        avant = etat.get("sources_ok", {}).get(nom, 0)
        if (s.get("erreur") or vide) and avant > 0:
            diag = s.get("erreur") or "; ".join(s.get("diagnostic", [])) or "aucun événement trouvé"
            out[f"source:{nom}"] = (f"Source muette : {nom}",
                                    f"Cette source donnait encore des événements récemment ; elle n'en donne plus.\n\nDiagnostic : {diag[:400]}",
                                    "Vérifier si le site a changé d'adresse ou de présentation, ou s'il bloque le robot.")
    par_site = defaultdict(lambda: [0, 0, 0])
    for e in data.get("events", []):
        h = urlparse(e.get("url", "")).netloc.replace("www.", "")
        if not h or e.get("serie"):
            continue
        par_site[h][0] += 1
        par_site[h][1] += not e.get("heure")
        par_site[h][2] += e.get("lieu") == "Lieu à confirmer"
    for h, (n, sh, sl) in par_site.items():
        if h in ("songkick.com",) or n < 10:
            continue
        for champ, k in (("heure", sh), ("salle", sl)):
            if k / n >= 0.5:
                out[f"champ:{h}:{champ}"] = (f"Fiches sans {champ} : {h}",
                                             f"{k} fiches sur {n} venant de {h} n'ont pas de {champ}, malgré la lecture de la page, "
                                             "le navigateur et l'IA.",
                                             "Regarder une page de ce site : l'information est-elle affichée ? Si oui, me l'envoyer "
                                             "(capture ou fichier .html) pour adapter la lecture.")
    total = len(data.get("events", []))
    maxi = max([total] + list(etat.get("totaux", {}).values())[-7:])
    if maxi and total < 0.75 * maxi:
        out["total"] = ("Baisse du nombre d'événements",
                        f"{total} événements aujourd'hui, contre {maxi} récemment (−{round(100 * (1 - total / maxi))} %).",
                        "Regarder les sources en erreur dans le rapport de collecte.")
    robots = (rapport.get("notes") or {}).get("robots_refus") or {}
    sites = sorted({k.split("/")[0] for k in robots})
    if sites:
        out["robots:" + ",".join(sites)] = ("Sites qui demandent aux robots de ne pas lire certaines pages",
                                            "robots.txt : " + ", ".join(sites[:20]),
                                            "Décider si on cesse de lire ces pages (ROBOTS_MODE=respecter), source par source.")
    return out


def main():
    rapport = json.loads((RACINE / "docs" / "rapport.json").read_text(encoding="utf-8"))
    data = json.loads((RACINE / "docs" / "data.json").read_text(encoding="utf-8"))
    etat = json.loads(F_ETAT.read_text(encoding="utf-8")) if F_ETAT.exists() else {}
    jour = rapport.get("date") or date.today().isoformat()
    if etat.get("dernier_jour") == jour:
        print("Bilan déjà fait pour cette collecte.")
        return
    ouverts = etat.get("ouverts", {})  # clé -> {"depuis", "jours", "issue"}
    actuels = problemes(rapport, data, etat)
    for cle, (titre, detail, action) in actuels.items():
        p = ouverts.setdefault(cle, {"depuis": jour, "jours": 0, "issue": None})
        p["jours"] += 1
        seuil = 1 if cle.startswith(("robots:", "total")) else JOURS_AVANT_AVIS
        if p["jours"] >= seuil and not p["issue"]:
            corps = (f"{detail}\n\n**Depuis** : {p['depuis']} ({p['jours']} collecte(s)).\n\n**Ce que le programme a déjà essayé** : "
                     "relecture de la page, navigateur, lecture par l'IA, dernière lecture réussie conservée.\n\n"
                     f"**À faire** : {action}\n\nCet avis se fermera tout seul quand le problème aura disparu.")
            code, sortie = gh("issue", "create", "--title", f"[Santé] {titre}"[:120], "--body", corps)
            m = re.search(r"/issues/(\d+)", sortie)
            p["issue"] = int(m.group(1)) if m else None
            print(f"Avis ouvert : {titre} → {sortie}")
    for cle in list(ouverts):
        if cle not in actuels:
            n = ouverts[cle].get("issue")
            if n:
                gh("issue", "close", str(n), "--comment", f"Réglé : le problème n'apparaît plus dans la collecte du {jour}.")
                print(f"Avis fermé : {cle}")
            del ouverts[cle]
    etat["ouverts"] = ouverts
    etat["sources_ok"] = {s["source"]: s.get("evenements", 0) + s.get("series", 0)
                          for s in rapport.get("sources", []) if not s.get("erreur")
                          and s.get("evenements", 0) + s.get("series", 0) > 0} or etat.get("sources_ok", {})
    totaux = etat.get("totaux", {})
    totaux[jour] = len(data.get("events", []))
    etat["totaux"] = dict(sorted(totaux.items())[-14:])
    etat["dernier_jour"] = jour
    F_ETAT.parent.mkdir(exist_ok=True)
    F_ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Bilan : {len(actuels)} problème(s) suivi(s), {sum(1 for p in ouverts.values() if p.get('issue'))} avis ouvert(s).")


if __name__ == "__main__":
    main()
