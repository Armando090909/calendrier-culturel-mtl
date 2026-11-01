"""Publication hebdomadaire sur les réseaux de ccmtl.ca : le visuel « Cette semaine sur l'île » et son texte,
sur Bluesky, Instagram et Threads (et Facebook plus tard).

Chaque réseau est indépendant : sans sa clé (secret GitHub), il est simplement sauté ; s'il échoue, les autres
publient quand même et un avis « [Réseaux] » est ouvert (courriel). Une seule publication par semaine et par réseau
(mémoire : outils/reseaux/etat.json).

Secrets GitHub (Settings → Secrets and variables → Actions) :
- BLUESKY_IDENTIFIANT (ex. ccmtl.bsky.social) et BLUESKY_MOT_DE_PASSE (« mot de passe d'application » Bluesky) ;
- INSTAGRAM_JETON (jeton d'accès « Instagram Login », permissions instagram_business_basic et
  instagram_business_content_publish) ;
- THREADS_JETON (jeton d'accès Threads, permissions threads_basic et threads_content_publish).
Les jetons Instagram et Threads durent 60 jours ; ils sont prolongés automatiquement à chaque passage
(et un avis est ouvert s'ils approchent de l'expiration sans pouvoir être prolongés).

Essai sans rien publier : PUBLIER=essai python outils/publier.py
"""
import io
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))
import instagram as visuels  # noqa: E402

DOSSIER = RACINE / "outils" / "reseaux"
ETAT = DOSSIER / "etat.json"
DEPOT = os.environ.get("GITHUB_REPOSITORY", "Armando090909/calendrier-culturel-mtl")
ESSAI = os.environ.get("PUBLIER") == "essai"
FORCER = os.environ.get("FORCER") == "1"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
NOMS = {"theatre": "théâtre", "musique": "musique", "danse": "danse", "cirque": "cirque", "humour": "humour",
        "cinema": "cinéma", "poesie": "poésie et slam", "lettres": "littérature", "conference": "conférences",
        "jeune": "jeune public", "atelier": "ateliers", "fete": "fêtes", "quiz": "quiz", "expo": "vernissages"}


def textes(c, expos, total, debut, fin):
    """(texte long pour Instagram, texte court pour Bluesky et Threads)."""
    periode = f"du {debut.day}{' ' + MOIS[debut.month - 1] if debut.month != fin.month else ''} au {fin.day} {MOIS[fin.month - 1]}"
    top = [f"{NOMS[k]} ({n})" for k, n in c.most_common() if k in NOMS][:4]
    court = (f"Cette semaine sur l'île, {periode} : {total} sorties. "
             f"{', '.join(top).capitalize()}… et {expos} expos en cours.\n"
             "Tout est sur ccmtl.ca")
    long = (court.replace("Tout est sur ccmtl.ca", "Tout est sur ccmtl.ca (lien dans la bio) : par discipline, par date "
                          "ou près de ta station de métro.")
            + "\n\n#MTL #Montréal #sortiesmtl #quoifaireamontreal #culturemtl")
    return long, court


def image_semaine(data, debut):
    """Rend le visuel de la semaine (PNG) puis le convertit en JPEG (exigé par Instagram, < 1 Mo pour Bluesky)."""
    from PIL import Image
    from playwright.sync_api import sync_playwright
    html, total = visuels.semaine(data, debut)
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1350})
        pg.set_content(html, wait_until="networkidle", timeout=60000)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(800)
        png = pg.screenshot()
        nav.close()
    im = Image.open(io.BytesIO(png)).convert("RGB")
    for q in (90, 85, 80, 75):
        tampon = io.BytesIO()
        im.save(tampon, "JPEG", quality=q, optimize=True)
        if tampon.tell() < 950_000:
            break
    return tampon.getvalue()


def url_publique(chemin_depot: str) -> str:
    """Adresse publique d'un fichier du dépôt (dépôt public : disponible dès l'envoi, sans attendre le site)."""
    return f"https://raw.githubusercontent.com/{DEPOT}/main/{chemin_depot}"


# ---------------------------------------------------------------- Bluesky
def bluesky(texte, jpeg, alt):
    ident, mdp = os.environ.get("BLUESKY_IDENTIFIANT"), os.environ.get("BLUESKY_MOT_DE_PASSE")
    if not ident or not mdp:
        return None
    s = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
                      json={"identifier": ident, "password": mdp}, timeout=30)
    s.raise_for_status()
    s = s.json()
    h = {"Authorization": "Bearer " + s["accessJwt"]}
    if ESSAI:
        return "essai : connexion Bluesky réussie (" + s["handle"] + ")"
    blob = requests.post("https://bsky.social/xrpc/com.atproto.repo.uploadBlob", data=jpeg,
                         headers={**h, "Content-Type": "image/jpeg"}, timeout=60)
    blob.raise_for_status()
    # lien cliquable sur « ccmtl.ca » (facette : positions en octets UTF-8)
    b = texte.encode("utf-8")
    i = b.rfind(b"ccmtl.ca")
    facettes = [{"index": {"byteStart": i, "byteEnd": i + 8},
                 "features": [{"$type": "app.bsky.richtext.facet#link", "uri": "https://ccmtl.ca"}]}] if i >= 0 else []
    post = {"$type": "app.bsky.feed.post", "text": texte, "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "langs": ["fr"], "facets": facettes,
            "embed": {"$type": "app.bsky.embed.images", "images": [{"image": blob.json()["blob"], "alt": alt,
                                                                    "aspectRatio": {"width": 1080, "height": 1350}}]}}
    r = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord", headers=h, timeout=30,
                      json={"repo": s["did"], "collection": "app.bsky.feed.post", "record": post})
    r.raise_for_status()
    return r.json().get("uri")


# ---------------------------------------------------------------- Instagram (Instagram Login, graph.instagram.com)
def instagram(texte, url_image, alt):
    jeton = os.environ.get("INSTAGRAM_JETON")
    if not jeton:
        return None
    base = "https://graph.instagram.com/v21.0"
    moi = requests.get(f"{base}/me", params={"fields": "user_id,username", "access_token": jeton}, timeout=30)
    moi.raise_for_status()
    ig = moi.json()["user_id"]
    if ESSAI:
        return "essai : connexion Instagram réussie (" + moi.json().get("username", "?") + ")"
    c = requests.post(f"{base}/{ig}/media", timeout=60,
                      data={"image_url": url_image, "caption": texte, "alt_text": alt, "access_token": jeton})
    c.raise_for_status()
    cid = c.json()["id"]
    for _ in range(20):  # Instagram télécharge et prépare l'image
        st = requests.get(f"{base}/{cid}", params={"fields": "status_code", "access_token": jeton}, timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram : image refusée ({st})")
        time.sleep(6)
    r = requests.post(f"{base}/{ig}/media_publish", data={"creation_id": cid, "access_token": jeton}, timeout=60)
    r.raise_for_status()
    return r.json().get("id")


# ---------------------------------------------------------------- Threads (graph.threads.net)
def threads(texte, url_image, alt):
    jeton = os.environ.get("THREADS_JETON")
    if not jeton:
        return None
    base = "https://graph.threads.net/v1.0"
    moi = requests.get(f"{base}/me", params={"fields": "id,username", "access_token": jeton}, timeout=30)
    moi.raise_for_status()
    if ESSAI:
        return "essai : connexion Threads réussie (" + moi.json().get("username", "?") + ")"
    uid = moi.json()["id"]
    c = requests.post(f"{base}/{uid}/threads", timeout=60, data={"media_type": "IMAGE", "image_url": url_image,
                                                                 "text": texte, "alt_text": alt, "access_token": jeton})
    c.raise_for_status()
    time.sleep(30)  # délai recommandé par Meta avant la publication
    r = requests.post(f"{base}/{uid}/threads_publish", data={"creation_id": c.json()["id"], "access_token": jeton}, timeout=60)
    r.raise_for_status()
    return r.json().get("id")


# ---------------------------------------------------------------- Jetons : prolongation automatique
def prolonger(etat):
    """Prolonge les jetons Instagram et Threads (valides 60 jours). Le jeton reste le même s'il est prolongé ;
    si Meta en renvoie un nouveau, il est enregistré dans les secrets GitHub (secret SECRETS_JETON requis)."""
    notes = []
    for nom, var, url, typ in (("Instagram", "INSTAGRAM_JETON", "https://graph.instagram.com/refresh_access_token", "ig_refresh_token"),
                               ("Threads", "THREADS_JETON", "https://graph.threads.net/refresh_access_token", "th_refresh_token")):
        jeton = os.environ.get(var)
        if not jeton or ESSAI:
            continue
        try:
            r = requests.get(url, params={"grant_type": typ, "access_token": jeton}, timeout=30)
            r.raise_for_status()
            d = r.json()
            etat.setdefault("jetons", {})[nom] = (date.today() + timedelta(seconds=int(d.get("expires_in", 0)))).isoformat()
            if d.get("access_token") and d["access_token"] != jeton:
                if os.environ.get("GH_TOKEN_SECRETS"):
                    subprocess.run(["gh", "secret", "set", var, "--repo", DEPOT, "--body", d["access_token"]],
                                   check=True, env={**os.environ, "GH_TOKEN": os.environ["GH_TOKEN_SECRETS"]})
                    notes.append(f"{nom} : nouveau jeton enregistré")
                else:
                    notes.append(f"{nom} : Meta a fourni un nouveau jeton, mais il n'a pas pu être enregistré (SECRETS_JETON absent)")
        except Exception as exc:
            notes.append(f"{nom} : prolongation du jeton en échec ({str(exc)[:120]})")
    return notes


def avis(titre, corps):
    if ESSAI or not os.environ.get("GH_TOKEN"):
        print(f"[avis] {titre}\n{corps}")
        return
    subprocess.run(["gh", "issue", "create", "--repo", DEPOT, "--title", f"[Réseaux] {titre}"[:120], "--body", corps])


def main():
    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    data = json.loads((RACINE / "docs" / "data.json").read_text(encoding="utf-8"))
    debut = visuels.lundi_a_venir()
    semaine = debut.isoformat()
    faits = etat.setdefault("publie", {}).setdefault(semaine, {})
    a_faire = [n for n in ("bluesky", "instagram", "threads") if FORCER or ESSAI or not faits.get(n)]
    if not a_faire:
        print(f"Semaine du {semaine} : déjà publiée partout.")
        return
    c, expos, total, fin = visuels.compter(data, debut)
    long, court = textes(c, expos, total, debut, fin)
    alt = (f"Visuel « Cette semaine sur l'île », {semaine} : {total} sorties culturelles à Montréal, "
           + ", ".join(f"{NOMS.get(k, k)} {n}" for k, n in c.most_common() if k in NOMS) + f", expos en cours {expos}.")
    jpeg = image_semaine(data, debut)
    chemin = f"outils/reseaux/semaine-{semaine}.jpg"
    (RACINE / chemin).write_bytes(jpeg)
    if not ESSAI and any(n in a_faire for n in ("instagram", "threads")):
        # Instagram et Threads vont chercher l'image à une adresse publique : on l'envoie d'abord dans le dépôt
        subprocess.run(["git", "add", chemin], check=True)
        subprocess.run(["git", "commit", "-m", f"Visuel de la semaine du {semaine}"], check=False)
        subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"], check=False)
        subprocess.run(["git", "push"], check=True)
        time.sleep(20)
    url = url_publique(chemin)
    print(f"Texte court ({len(court)} caractères) :\n{court}\n")
    erreurs = []
    for nom, fn, args in (("bluesky", bluesky, (court, jpeg, alt)), ("instagram", instagram, (long, url, alt)),
                          ("threads", threads, (court, url, alt))):
        if nom not in a_faire:
            continue
        try:
            res = fn(*args)
            if res is None:
                print(f"{nom} : pas de clé, sauté.")
                continue
            print(f"{nom} : {res}")
            if not ESSAI:
                faits[nom] = str(res)
        except Exception as exc:
            detail = getattr(getattr(exc, "response", None), "text", "") or ""
            erreurs.append(f"- **{nom}** : {str(exc)[:200]} {detail[:300]}")
            print(f"{nom} : ÉCHEC {exc} {detail[:300]}")
    notes = prolonger(etat)
    for n in notes:
        print(n)
    for nom, exp in (etat.get("jetons") or {}).items():
        if exp and exp < (date.today() + timedelta(days=10)).isoformat():
            erreurs.append(f"- **{nom}** : le jeton expire le {exp} et n'a pas pu être prolongé.")
    etat["publie"] = dict(sorted(etat["publie"].items())[-12:])
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    if erreurs:
        avis(f"Publication de la semaine du {semaine} incomplète",
             "Certaines publications ont échoué :\n\n" + "\n".join(erreurs)
             + "\n\nLes autres réseaux ont publié normalement. La publication sera retentée au prochain passage.")
        if not ESSAI:
            sys.exit(1)


if __name__ == "__main__":
    main()
