#!/usr/bin/env python3
"""ccmtl.ca : lecture des fiches d'événements de la Ville de Montréal depuis un ordinateur à Montréal.

Pourquoi : montreal.ca refuse les serveurs de GitHub (centres de données à l'étranger), mais accepte notre robot
identifié depuis une connexion montréalaise. Ce programme tourne au plus une fois par jour, quand l'ordinateur est
allumé, et lit seulement les fiches dont le calendrier a besoin (heure, salle, billetterie manquantes).

Règles : robot identifié (« CalendrierCulturelMTL »), robots.txt respecté, une page toutes les 2 secondes,
au plus 50 minutes par jour (la liste raccourcit une fois le retard rattrapé). Le résultat est envoyé au dépôt GitHub du calendrier (collecteur/cache/ville_mac.json).

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
MAX_PAGES, PAUSE = 1500, 2.0  # la liste ne contient que les fiches incomplètes : longue au début, courte ensuite
DUREE_MAX = 50 * 60  # au plus 50 minutes de lecture par jour
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


def mise_a_jour():
    """Le programme se met à jour tout seul depuis ccmtl.ca (la version publiée avec le site), puis redémarre."""
    if ESSAI or os.environ.get("CCMTL_A_JOUR"):
        return
    code, nouveau = curl("https://ccmtl.ca/mac/ville_mac.py")
    moi = os.path.abspath(__file__)
    if code == 200 and nouveau.startswith("#!/usr/bin/env python3") and "def main" in nouveau \
            and nouveau != open(moi, encoding="utf-8").read():
        with open(moi, "w", encoding="utf-8") as f:
            f.write(nouveau)
        journal("Programme mis à jour.")
        os.environ["CCMTL_A_JOUR"] = "1"
        os.execv(sys.executable, [sys.executable, moi] + sys.argv[1:])


def main():
    os.makedirs(DOSSIER, exist_ok=True)
    mise_a_jour()
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
    debut_lecture = time.time()
    for url in urls:
        if time.time() - debut_lecture > DUREE_MAX:
            journal("Durée maximale atteinte : la suite demain.")
            break
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
    ok = envoyer(jeton, CHEMIN, res, 30, f"Fiches de la Ville lues depuis Montréal ({lues})") if res else True
    ok = pages_bloquees(jeton, aujourd) and ok
    if ok:
        open(fait, "w").write(aujourd)


def envoyer(jeton, chemin, res, jours_gardes, message):
    """Complète le fichier « chemin » du dépôt avec « res » (entrées de moins de « jours_gardes » jours)."""
    api = f"https://api.github.com/repos/{DEPOT}/contents/{chemin}"
    entetes = ["-H", f"Authorization: Bearer {jeton}", "-H", "Accept: application/vnd.github+json"]
    code, txt = curl(api, *entetes)
    ancien, sha = {}, None
    if code == 200:
        d = json.loads(txt)
        sha = d.get("sha")
        try:
            if d.get("content"):
                ancien = json.loads(base64.b64decode(d["content"]).decode("utf-8"))
            elif d.get("download_url"):  # fichier de plus de 1 Mo : l'API ne donne pas le contenu
                c2, brut = curl(d["download_url"])
                ancien = json.loads(brut) if c2 == 200 else {}
        except ValueError:
            ancien = {}
    limite = date.fromordinal(date.today().toordinal() - jours_gardes).isoformat()
    tout = {u: v for u, v in ancien.items() if isinstance(v, dict) and v.get("le", "") >= limite}
    tout.update(res)
    corps = {"message": message,
             "content": base64.b64encode(json.dumps(tout, ensure_ascii=False).encode("utf-8")).decode("ascii")}
    if sha:
        corps["sha"] = sha
    code, txt = curl(api, "-X", "PUT", *entetes, "-H", "Content-Type: application/json", "--data-binary", "@-",
                     entree=json.dumps(corps))
    if code in (200, 201):
        journal(f"Envoyé au calendrier : {chemin.split('/')[-1]} ({len(res)}).")
        return True
    journal(f"Envoi refusé par GitHub ({code}) : {txt[:200]}")
    return False


def pages_bloquees(jeton, aujourd):
    """Pages de programmation de salles qui refusent les serveurs de GitHub : lues d'ici, allégées (sans scripts ni
    styles), compressées et envoyées. Le robots.txt de chaque site est respecté."""
    import gzip
    code, txt = curl("https://ccmtl.ca/pages_a_lire.json")
    if code != 200:
        return True
    robots, res = {}, {}
    for url in json.loads(txt)[:60]:
        hote = "/".join(url.split("/")[:3])
        if hote not in robots:
            rp = RobotFileParser()
            c, t = curl(hote + "/robots.txt")
            rp.parse(t.splitlines() if c == 200 and "<html" not in t[:500].lower() else [])
            robots[hote] = rp
        if not robots[hote].can_fetch("CalendrierCulturelMTL", url):
            continue
        c, html = curl(url)
        if c == 200 and len(html) > 500:
            html = re.sub(r"(?is)<(script|style|svg|noscript)\b.*?</\1>", "", html)
            res[url] = {"le": aujourd, "html": base64.b64encode(gzip.compress(html.encode("utf-8"))).decode("ascii")}
        time.sleep(PAUSE)
    journal(f"Pages de salles lues : {len(res)}.")
    return envoyer(jeton, "collecteur/cache/pages_mac.json", res, 3, f"Pages de salles lues depuis Montréal ({len(res)})") \
        if res else True


if __name__ == "__main__":
    main()
