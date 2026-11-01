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
import faits_saillants as fs  # noqa: E402

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


# ---------------------------------------------------------------- Bluesky : un fil de messages (4 images au plus par message)
def _bsky_post(h, did, texte, images, reponse=None):
    b = texte.encode("utf-8")
    i = b.rfind(b"ccmtl.ca")
    post = {"$type": "app.bsky.feed.post", "text": texte, "langs": [fs.LANGUE],
            "createdAt": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "facets": [{"index": {"byteStart": i, "byteEnd": i + 8},
                        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": "https://ccmtl.ca"}]}] if i >= 0 else [],
            "embed": {"$type": "app.bsky.embed.images", "images": [
                {"image": blob, "alt": alt, "aspectRatio": {"width": 1080, "height": 1350}} for blob, alt in images]}}
    if reponse:
        post["reply"] = reponse
    r = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord", headers=h, timeout=30,
                      json={"repo": did, "collection": "app.bsky.feed.post", "record": post})
    r.raise_for_status()
    return {"uri": r.json()["uri"], "cid": r.json()["cid"]}


def bluesky(messages):
    """messages : [(texte, [(jpeg, alt), …]), …] — le premier ouvre le fil, les suivants y répondent."""
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
    racine = parent = None
    for texte, imgs in messages:
        blobs = []
        for jpeg, alt in imgs[:4]:
            u = requests.post("https://bsky.social/xrpc/com.atproto.repo.uploadBlob", data=jpeg,
                              headers={**h, "Content-Type": "image/jpeg"}, timeout=60)
            u.raise_for_status()
            blobs.append((u.json()["blob"], alt))
        ref = _bsky_post(h, s["did"], texte, blobs, {"root": racine, "parent": parent} if racine else None)
        racine = racine or ref
        parent = ref
    return racine["uri"]


# ---------------------------------------------------------------- Instagram (Instagram Login, graph.instagram.com) : carrousel
def _attendre(get_statut, cle="status_code"):
    for _ in range(30):
        st = get_statut()
        if st.get(cle) == "FINISHED":
            return
        if st.get(cle) == "ERROR":
            raise RuntimeError(f"image refusée ({st})")
        time.sleep(5)


def instagram(texte, urls, alts):
    jeton = os.environ.get("INSTAGRAM_JETON")
    page = os.environ.get("FACEBOOK_PAGE_ID")
    if jeton:  # méthode « Instagram Login » (graph.instagram.com)
        base = "https://graph.instagram.com/v26.0"
        moi = requests.get(f"{base}/me", params={"fields": "user_id,username", "access_token": jeton}, timeout=30)
        moi.raise_for_status()
        ig, nom = moi.json()["user_id"], moi.json().get("username", "?")
    elif os.environ.get("FACEBOOK_JETON") and page:
        # méthode « Facebook Login » : le jeton de la page Facebook (qui n'expire pas) publie aussi sur le compte
        # Instagram professionnel relié à la page
        jeton, base = os.environ["FACEBOOK_JETON"], "https://graph.facebook.com/v26.0"
        r = requests.get(f"{base}/{page}", params={"fields": "instagram_business_account{id,username}", "access_token": jeton}, timeout=30)
        r.raise_for_status()
        compte = r.json().get("instagram_business_account") or {}
        if not compte.get("id"):
            raise RuntimeError("aucun compte Instagram professionnel relié à la page Facebook")
        ig, nom = compte["id"], compte.get("username", "?")
    else:
        return None
    if ESSAI:
        return "essai : connexion Instagram réussie (" + nom + ")"
    enfants = []
    for url, alt in zip(urls[:10], alts):
        c = requests.post(f"{base}/{ig}/media", timeout=60, data={"image_url": url, "is_carousel_item": "true",
                                                                  "alt_text": alt, "access_token": jeton})
        c.raise_for_status()
        enfants.append(c.json()["id"])
    for cid in enfants:
        _attendre(lambda: requests.get(f"{base}/{cid}", params={"fields": "status_code", "access_token": jeton}, timeout=30).json())
    c = requests.post(f"{base}/{ig}/media", timeout=60, data={"media_type": "CAROUSEL", "children": ",".join(enfants),
                                                              "caption": texte, "access_token": jeton})
    c.raise_for_status()
    pid = c.json()["id"]
    _attendre(lambda: requests.get(f"{base}/{pid}", params={"fields": "status_code", "access_token": jeton}, timeout=30).json())
    r = requests.post(f"{base}/{ig}/media_publish", data={"creation_id": pid, "access_token": jeton}, timeout=60)
    r.raise_for_status()
    return r.json().get("id")


# ---------------------------------------------------------------- Threads (graph.threads.net) : carrousel
def threads(texte, urls, alts):
    jeton = os.environ.get("THREADS_JETON")
    if not jeton:
        return None
    base = "https://graph.threads.net/v1.0"
    moi = requests.get(f"{base}/me", params={"fields": "id,username", "access_token": jeton}, timeout=30)
    moi.raise_for_status()
    if ESSAI:
        return "essai : connexion Threads réussie (" + moi.json().get("username", "?") + ")"
    uid = moi.json()["id"]
    enfants = []
    for url, alt in zip(urls[:20], alts):
        c = requests.post(f"{base}/{uid}/threads", timeout=60, data={"media_type": "IMAGE", "image_url": url,
                                                                     "is_carousel_item": "true", "alt_text": alt,
                                                                     "access_token": jeton})
        c.raise_for_status()
        enfants.append(c.json()["id"])
    time.sleep(20)
    c = requests.post(f"{base}/{uid}/threads", timeout=60, data={"media_type": "CAROUSEL", "children": ",".join(enfants),
                                                                 "text": texte, "access_token": jeton})
    c.raise_for_status()
    time.sleep(30)  # délai recommandé par Meta avant la publication
    r = requests.post(f"{base}/{uid}/threads_publish", data={"creation_id": c.json()["id"], "access_token": jeton}, timeout=60)
    r.raise_for_status()
    return r.json().get("id")


# ---------------------------------------------------------------- Page Facebook (graph.facebook.com) : publication multi-photos
def facebook(texte, urls, alts):
    jeton, page = os.environ.get("FACEBOOK_JETON"), os.environ.get("FACEBOOK_PAGE_ID")
    if not jeton or not page:
        return None
    base = "https://graph.facebook.com/v26.0"
    moi = requests.get(f"{base}/{page}", params={"fields": "name", "access_token": jeton}, timeout=30)
    moi.raise_for_status()
    if ESSAI:
        return "essai : connexion Facebook réussie (" + moi.json().get("name", "?") + ")"
    photos = []
    for url in urls[:10]:  # photos téléversées sans être publiées, puis rattachées à une seule publication
        r = requests.post(f"{base}/{page}/photos", timeout=60, data={"url": url, "published": "false", "access_token": jeton})
        r.raise_for_status()
        photos.append(r.json()["id"])
    data = {"message": texte, "access_token": jeton}
    for i, pid in enumerate(photos):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    r = requests.post(f"{base}/{page}/feed", data=data, timeout=60)
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


def jpeg(png_path, limite=950_000):
    from PIL import Image
    im = Image.open(png_path).convert("RGB")
    for q in (90, 85, 80, 75, 70):
        t = io.BytesIO()
        im.save(t, "JPEG", quality=q, optimize=True)
        if t.tell() < limite:
            break
    return t.getvalue()


def _alts(s, jpgs):
    """Textes alternatifs (personnes non voyantes), dans la langue courante."""
    out = []
    for j in jpgs:
        nom = j.stem.split("-", 1)[1]
        p = next((p for p in s["picks"] if p["k"] == nom), None)
        if p:
            acc = p.get("accroche_en", "") if fs.LANGUE == "en" else p["accroche"]
            out.append(f"{fs.nom_disc(p['k'])} : {p['e']['titre']}, {fs.quand(p['e'])}, {p['e']['lieu']}. {acc}".strip())
            continue
        titres = " · ".join(f"{p['e']['titre']} ({fs.quand(p['e'])}, {p['e']['lieu']})" for p in s["picks"])
        out.append({"couverture": fs.T(f"Qu'est-ce qu'on fait cette semaine ? Coups de cœur {fs._periode(s)}, ccmtl.ca",
                                       f"What's on in Montréal this week? Picks for {fs._periode(s)}, ccmtl.ca"),
                    "festivals": "Festivals : " + ", ".join(f["nom"] for f in s["festivals"]),
                    "salle": fs.T("La salle de la semaine : ", "Venue of the week: ") + (s["salle"]["lieu"] if s["salle"] else ""),
                    "coups-de-coeur": fs.T("Nos coups de cœur : ", "Our picks: ") + titres,
                    "festivals-salle": "Festivals : " + ", ".join(f["nom"] for f in s["festivals"])
                    + (" · " + fs.T("La salle de la semaine : ", "Venue of the week: ") + s["salle"]["lieu"] if s["salle"] else ""),
                    "fin": f"{s['total']} · ccmtl.ca"}.get(nom, "ccmtl.ca")[:1000])
    return out


def main():
    DOSSIER.mkdir(parents=True, exist_ok=True)
    etat = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    data = json.loads((RACINE / "docs" / "data.json").read_text(encoding="utf-8"))
    debut = visuels.lundi_a_venir()
    semaine = debut.isoformat()
    faits = etat.setdefault("publie", {}).setdefault(semaine, {})
    reseaux = ("bluesky", "instagram", "threads", "facebook")
    langues = ("fr", "en")  # une publication en français, une en anglais (titres, salles et noms dans leur langue d'origine)
    a_faire = [f"{n}-{l}" for l in langues for n in reseaux if FORCER or ESSAI or not faits.get(f"{n}-{l}")]
    if not a_faire:
        print(f"Semaine du {semaine} : déjà publiée partout.")
        return
    s = fs.choisir(data, debut, etat)
    lots = {}
    for langue in langues:
        fs.LANGUE = langue
        dossier = DOSSIER / semaine / langue
        pngs = fs.rendre(fs.slides(s) + fs.condenses(s), dossier)
        jpgs = []
        for p in pngs:
            j = p.with_suffix(".jpg")
            j.write_bytes(jpeg(p))
            p.unlink()
            jpgs.append(j)
        t = fs.textes(s)
        (dossier / "textes.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
        lots[langue] = (jpgs, _alts(s, jpgs), t)
    fs.LANGUE = "fr"
    if not ESSAI and any(not x.startswith("bluesky") for x in a_faire):
        # Instagram, Threads et Facebook vont chercher les images à une adresse publique : on les envoie d'abord au dépôt
        subprocess.run(["git", "add", str((DOSSIER / semaine).relative_to(RACINE))], check=True)
        subprocess.run(["git", "commit", "-m", f"Publication de la semaine du {semaine}"], check=False)
        subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"], check=False)
        subprocess.run(["git", "push"], check=True)
        time.sleep(20)
    erreurs = []
    for langue in langues:
        jpgs, alts, t = lots[langue]
        urls = [url_publique(str(j.relative_to(RACINE))) for j in jpgs]
        complet = [i for i, j in enumerate(jpgs) if not j.stem.startswith("c")]      # carrousel de 10 cartons
        condense = [i for i, j in enumerate(jpgs) if j.stem.startswith("c")]         # 2 cartons condensés
        print(f"[{langue}] images : {len(jpgs)} ; textes : " + ", ".join(f"{k} {len(x)} car." for k, x in t.items()))
        travaux = (("bluesky", bluesky, ([(t["bluesky"], [(jpgs[i].read_bytes(), alts[i]) for i in condense])],)),
                   ("instagram", instagram, (t["instagram"], [urls[i] for i in complet], [alts[i] for i in complet])),
                   ("threads", threads, (t["threads"], [urls[i] for i in condense], [alts[i] for i in condense])),
                   ("facebook", facebook, (t["instagram"].split("\n\n#")[0], [urls[i] for i in complet], [alts[i] for i in complet])))
        for nom, fn, args in travaux:
            cle = f"{nom}-{langue}"
            if cle not in a_faire:
                continue
            try:
                fs.LANGUE = langue
                res = fn(*args)
                if res is None:
                    print(f"{cle} : pas de clé, sauté.")
                    continue
                print(f"{cle} : {res}")
                if not ESSAI:
                    faits[cle] = str(res)
            except Exception as exc:
                detail = getattr(getattr(exc, "response", None), "text", "") or ""
                erreurs.append(f"- **{cle}** : {str(exc)[:200]} {detail[:300]}")
                print(f"{cle} : ÉCHEC {exc} {detail[:300]}")
            finally:
                fs.LANGUE = "fr"
    if not ESSAI and s["salle"] and any(faits.get(x) for x in a_faire):
        sv = etat.setdefault("salles_vedette", [])
        if s["salle"]["lieu"] not in sv[-1:]:
            sv.append(s["salle"]["lieu"])
    for n in prolonger(etat):
        print(n)
    for nom, exp in (etat.get("jetons") or {}).items():
        if exp and exp < (date.today() + timedelta(days=10)).isoformat():
            erreurs.append(f"- **{nom}** : le jeton expire le {exp} et n'a pas pu être prolongé.")
    etat["publie"] = dict(sorted(etat["publie"].items())[-12:])
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    if erreurs:
        avis(f"Publication de la semaine du {semaine} incomplète",
             "Certaines publications ont échoué :\n\n" + "\n".join(erreurs)
             + "\n\nLes autres ont été publiées normalement. Ce qui manque sera retenté au prochain passage.")
        if not ESSAI:
            sys.exit(1)

if __name__ == "__main__":
    main()
