#!/usr/bin/env python3
"""ccmtl.ca : lecture des fiches d'événements de la Ville de Montréal depuis un ordinateur à Montréal.

Pourquoi : montreal.ca refuse les serveurs de GitHub (centres de données à l'étranger), mais accepte notre robot
identifié depuis une connexion montréalaise. Ce programme tourne au plus une fois par jour, quand l'ordinateur est
allumé, et lit seulement les fiches dont le calendrier a besoin (heure, salle, billetterie manquantes).

Règles : robot identifié (« CalendrierCulturelMTL »), robots.txt respecté, une page toutes les 2 secondes,
au plus 400 pages par jour. Le résultat est envoyé au dépôt GitHub du calendrier (collecteur/cache/ville_mac.json).

Fonctionne avec le Python 3.8 de macOS, sans module à installer (les téléchargements passent par « curl »).
Essai sans rien envoyer :  python3 ville_mac.py --essai
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from urllib.robotparser import RobotFileParser

UA = "Mozilla/5.0 (compatible; CalendrierCulturelMTL/1.0; +https://ccmtl.ca; projet bénévole sans but lucratif)"
LISTE = "https://ccmtl.ca/ville_a_lire.json"
DEPOT = "Armando090909/calendrier-culturel-mtl"
CHEMIN = "collecteur/cache/ville_mac.json"
DOSSIER = os.path.expanduser("~/.ccmtl")
MAX_PAGES, PAUSE = 400, 2.0
ESSAI = "--essai" in sys.argv


def journal(msg):
    ligne = f"{time.strftime('%Y-%m-%d %H:%M')}  {msg}"
    print(ligne)
    try:
        with open(os.path.join(DOSSIER, "journal.txt"), "a", encoding="utf-8") as f:
            f.write(ligne + "\n")
    except OSError:
        pass


def curl(url, *options, entree=None):
    """Renvoie (code HTTP, texte)."""
    r = subprocess.run(["curl", "-s", "-L", "--max-time", "40", "-A", UA, "-w", "\n%{http_code}", *options, url],
                       input=entree, capture_output=True, text=True)
    texte, _, code = r.stdout.rpartition("\n")
    return int(code or 0), texte


def extraire(html):
    """Seulement ce dont le calendrier a besoin : les données schema.org et le lien « Billetterie »."""
    jsonld = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, flags=re.S)
    m = None  # lien dont le texte (balises retirées) est « Billetterie », « Réserver »…
    for href, dedans in re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, flags=re.S):
        if re.fullmatch(r"\s*(Billetterie|Réserver|Acheter des billets)\s*", re.sub(r"<[^>]+>", "", dedans)):
            m = href
            break
    return {"jsonld": [j.strip()[:6000] for j in jsonld][:3], "billets": m or ""}


def main():
    os.makedirs(DOSSIER, exist_ok=True)
    fait = os.path.join(DOSSIER, "dernier_jour.txt")
    aujourd = date.today().isoformat()
    if not ESSAI and os.path.exists(fait) and open(fait).read().strip() == aujourd:
        return  # déjà fait aujourd'hui
    jeton = ""
    if not ESSAI:
        try:
            jeton = open(os.path.join(DOSSIER, "jeton"), encoding="utf-8").read().strip()
        except OSError:
            journal("Jeton GitHub introuvable (~/.ccmtl/jeton) : rien à faire.")
            return

    code, txt = curl(LISTE)
    if code != 200:
        journal(f"Liste des fiches illisible ({code}) : on réessaiera plus tard.")
        return
    urls = json.loads(txt)[:5 if ESSAI else MAX_PAGES]  # essai : 5 fiches seulement
    rp = RobotFileParser()
    code, robots = curl("https://montreal.ca/robots.txt")
    rp.parse(robots.splitlines() if code == 200 else [])

    lues, refus, res = 0, 0, {}
    for url in urls:
        if url.startswith("http") and not rp.can_fetch("CalendrierCulturelMTL", url):
            continue
        code, html = curl(url)
        if code == 200:
            res[url] = dict(extraire(html), le=aujourd)
            lues += 1
        else:
            refus += 1
            if refus >= 10 and lues == 0:
                journal("La Ville refuse aussi cette connexion : arrêt pour aujourd'hui.")
                break
        time.sleep(PAUSE)
    journal(f"{lues} fiches lues sur {len(urls)} ({refus} refus).")
    if ESSAI:
        print(json.dumps(res, ensure_ascii=False, indent=1)[:3000])
        return
    if not res:
        return

    # Envoi au dépôt : on complète le fichier existant (fiches de moins de 30 jours)
    api = f"https://api.github.com/repos/{DEPOT}/contents/{CHEMIN}"
    entetes = ["-H", f"Authorization: Bearer {jeton}", "-H", "Accept: application/vnd.github+json"]
    code, txt = curl(api, *entetes)
    ancien, sha = {}, None
    if code == 200:
        d = json.loads(txt)
        sha = d.get("sha")
        try:
            ancien = json.loads(base64.b64decode(d.get("content", "")).decode("utf-8"))
        except ValueError:
            ancien = {}
    limite = date.fromordinal(date.today().toordinal() - 30).isoformat()
    tout = {u: v for u, v in ancien.items() if v.get("le", "") >= limite}
    tout.update(res)
    corps = {"message": f"Fiches de la Ville lues depuis Montréal ({lues})",
             "content": base64.b64encode(json.dumps(tout, ensure_ascii=False).encode("utf-8")).decode("ascii")}
    if sha:
        corps["sha"] = sha
    code, txt = curl(api, "-X", "PUT", *entetes, "-H", "Content-Type: application/json", "--data-binary", "@-",
                     entree=json.dumps(corps))
    if code in (200, 201):
        open(fait, "w").write(aujourd)
        journal("Envoyé au calendrier.")
    else:
        journal(f"Envoi refusé par GitHub ({code}) : {txt[:200]}")


if __name__ == "__main__":
    main()
