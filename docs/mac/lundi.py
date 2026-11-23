#!/usr/bin/env python3
"""ccmtl.ca : signal de départ de la publication de la semaine, chaque lundi matin, depuis le Raspberry Pi.

Pourquoi (23 nov. 2026) : la tâche programmée de GitHub (lundi 8 h 23) part souvent avec des heures de retard, ou pas
du tout. Le Pi écrit « tout » et la date du lundi dans outils/reseaux/demande-test.txt ; ce changement lance la
publication de la semaine sur GitHub. Garde-fous (outils/publier.py) : rien n'est publié deux fois, et un « stop »
d'Alexandre dans l'avis d'aperçu est respecté.

Utilise le jeton déjà enregistré sur le Pi (~/.ccmtl/jeton). Essai sans rien envoyer :  python3 lundi.py --essai
"""
import base64
import json
import os
import subprocess
import sys
import time
from datetime import date

DEPOT = "Armando090909/calendrier-culturel-mtl"
CHEMIN = "outils/reseaux/demande-test.txt"
DOSSIER = os.path.expanduser("~/.ccmtl")
ESSAI = "--essai" in sys.argv


def journal(msg):
    ligne = f"{time.strftime('%Y-%m-%d %H:%M')}  lundi : {msg}"
    print(ligne)
    try:
        with open(os.path.join(DOSSIER, "journal.txt"), "a", encoding="utf-8") as f:
            f.write(ligne + "\n")
    except OSError:
        pass


def curl(url, *args, entree=None):
    r = subprocess.run(["curl", "-s", "-m", "60", "-w", "\n%{http_code}", url, *args], input=entree,
                       capture_output=True, text=True)
    corps, _, code = r.stdout.rpartition("\n")
    return int(code or 0), corps


def main():
    auj = date.today()
    if auj.weekday() != 0 and not ESSAI:
        journal("pas lundi, rien à faire.")
        return
    jeton = open(os.path.join(DOSSIER, "jeton")).read().strip()
    api = f"https://api.github.com/repos/{DEPOT}/contents/{CHEMIN}"
    ent = ["-H", f"Authorization: Bearer {jeton}", "-H", "Accept: application/vnd.github+json"]
    code, txt = curl(api, *ent)
    if code != 200:
        journal(f"lecture refusée par GitHub ({code}).")
        return
    d = json.loads(txt)
    contenu = f"tout\n{auj.isoformat()}\n"
    if base64.b64decode(d.get("content", "")).decode("utf-8") == contenu:
        journal("signal déjà envoyé aujourd'hui.")
        return
    if ESSAI:
        journal(f"essai : accès au dépôt OK, le signal serait « {contenu.strip()} » (rien envoyé).")
        return
    corps = {"message": f"Publication de la semaine du {auj.isoformat()} : signal du Pi (lundi matin)",
             "content": base64.b64encode(contenu.encode()).decode(), "sha": d["sha"]}
    code, txt = curl(api, "-X", "PUT", *ent, "-H", "Content-Type: application/json", "--data-binary", "@-",
                     entree=json.dumps(corps))
    journal("signal envoyé : publication lancée." if code in (200, 201) else f"envoi refusé par GitHub ({code}) : {txt[:200]}")


if __name__ == "__main__":
    main()
