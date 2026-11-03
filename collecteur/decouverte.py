"""Liens de découverte vérifiés : écouter un groupe, voir la bande-annonce d'un film.

Trois sources, de la plus sûre à la moins sûre :
1. La page de l'événement elle-même : lecteurs intégrés (Bandcamp, Spotify, YouTube, Vimeo, SoundCloud) et liens
   vers ces sites dont l'adresse ou le texte contient le nom de l'artiste ou du film.
2. MusicBrainz (base musicale ouverte, gratuite) : fiche de l'artiste et ses liens officiels. On ne garde un artiste
   que si le nom correspond exactement ; s'il y a plusieurs homonymes, on préfère celui du Canada, sinon on s'abstient.
3. TMDb (base de films) pour les bandes-annonces, seulement si le secret TMDB_API_KEY est configuré (clé gratuite).

Rien n'est inventé : sans lien vérifié, le site affiche seulement un lien de recherche, présenté comme tel.
Les résultats sont gardés dans cache/decouverte.json (un artiste n'est cherché qu'une fois ; nouvel essai après 30 jours
s'il n'a rien donné).
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from normalisation import plat

MEMOIRE = Path(__file__).parent / "cache" / "decouverte.json"
JOURNAL_CATALOGUES: list = []  # décisions Deezer / Apple Music de la collecte (indices pour et contre), pour le rapport
SITES = {"bandcamp.com": "bandcamp", "open.spotify.com": "spotify", "music.apple.com": "apple", "tidal.com": "tidal",
         "soundcloud.com": "soundcloud", "youtube.com": "youtube", "youtu.be": "youtube", "vimeo.com": "vimeo"}
GENERIQUES = {"lancement", "double", "invites", "invitees", "invite", "guests", "dj", "set", "soiree", "concert", "show",
              "festival", "presente", "presents", "and", "et", "the", "les", "le", "la"}


def type_lien(url: str) -> str | None:
    h = urlparse(url).netloc.lower().replace("www.", "").replace("m.", "")
    for dom, t in SITES.items():
        if h == dom or h.endswith("." + dom):
            if t == "spotify" and not re.search(r"/(artist|album|track|playlist)/", url):
                return None
            if t == "youtube" and not re.search(r"(watch\?v=|youtu\.be/|/embed/|/@|/channel/)", url):
                return None
            return t
    return None


def noms_artistes(titre: str) -> list[str]:
    """« Jonquille (lancement) + Chloé Jara-Buto » → ["Jonquille", "Chloé Jara-Buto"]."""
    t = re.sub(r"\(.*?\)", " ", titre)
    t = re.split(r"\s[–—|:]\s|\s-\s|:\s|\s@\s", t)[0]
    t = re.sub(r"\s+", " ", t)
    morceaux = re.split(r"\s\+\s|\s/\s|,|\savec\s|\swith\s|\sw/\s|\set\s(?=[A-ZÉ])|\s&\s|\sx\s", t)
    out = []
    for m in morceaux:
        m = m.strip(" .·-")
        if m and len(plat(m)) >= 2 and plat(m) not in GENERIQUES and not re.match(r"(?i)invit", m):
            out.append(m)
    return out[:3]


def _correspond(nom: str, texte: str) -> bool:
    n, t = plat(nom).replace(" ", ""), plat(texte).replace(" ", "")
    return len(n) >= 4 and n in t


def depuis_page(html: str, page_url: str, noms: list[str], lecteurs: bool = True) -> list[dict]:
    """Lecteurs intégrés (iframes) et liens nommés vers les plateformes, sur la page de l'événement.
    lecteurs=False : page partagée par plusieurs spectacles, ses lecteurs intégrés ne sont pas forcément les bons."""
    soupe = BeautifulSoup(html, "html.parser")
    liens = []
    for f in (soupe.find_all("iframe", src=True) if lecteurs else []):
        src = urljoin(page_url, f["src"])
        t = type_lien(src)
        if t:
            liens.append({"type": t, "url": src.replace("/embed/", "/watch?v=") if "youtube.com/embed/" in src else src,
                          "source": "page"})
    for a in soupe.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        t = type_lien(href)
        if t and any(_correspond(n, href + " " + a.get_text(" ")) for n in noms):
            liens.append({"type": t, "url": href, "source": "page"})
    vus, out = set(), []
    for l in liens:
        if l["url"] not in vus:
            vus.add(l["url"])
            out.append(l)
    return out[:4]


AGREGATEURS = ("songkick.com", "festapp.io", "jambase.com", "ma.to", "sorstu.ca", "quoifaire.com", "mtl.org",
               "bandsintown.com", "eventbrite.", "facebook.com", "lepointdevente.com", "ticketmaster.")


def page_officielle(url: str) -> bool:
    h = urlparse(url or "").netloc.lower()
    return url.startswith("http") and not any(a in h for a in AGREGATEURS)


def agrandir(url: str) -> dict:
    """Version grand format d'une image quand le site en publie une vignette (« _100x100 », « -300x200 »…).
    Renvoie {"url": grande, "petit": vignette} ; le site revient à la vignette si la grande n'existe pas."""
    grand = url
    if "sorstu.ca/wp-content/uploads/artists/square/" in url:
        grand = re.sub(r"/artists/square/(new/)?(.+?)_\d+x\d+\.(jpe?g|png|webp)$", r"/artists/\1\2_662x0.\3", url)
    else:
        grand = re.sub(r"-\d{2,4}x\d{2,4}(\.(?:jpe?g|png|webp))(\?.*)?$", r"\1", url)  # WordPress : -300x200.jpg
        grand = re.sub(r"([?&](?:w|width|h|height|resize|fit)=)\d{2,3}\b", lambda m: m.group(1) + "1200", grand)
    return {"url": grand, "petit": url} if grand != url else {"url": url}


def affiche_page(html: str, page_url: str) -> dict | None:
    """Image de promotion choisie par l'organisateur pour sa page (balise og:image / twitter:image / schema.org).
    L'image n'est pas copiée : le site l'affiche depuis la page d'origine, avec le crédit et le lien."""
    soupe = BeautifulSoup(html, "html.parser")
    src = None
    for attrs in ({"property": "og:image"}, {"name": "og:image"}, {"name": "twitter:image"}, {"property": "twitter:image"}):
        m = soupe.find("meta", attrs=attrs)
        if m and m.get("content"):
            src = m["content"]
            break
    if not src:
        for s in soupe.find_all("script", type="application/ld+json"):
            m = re.search(r'"image"\s*:\s*(?:\[\s*)?"([^"]+)"', s.string or "")
            if m:
                src = m.group(1)
                break
    if not src:
        return None
    src = urljoin(page_url, src.strip())
    if not src.startswith("https://") or re.search(r"(logo|favicon|placeholder|default[-_]?(share|og)|sprite)", src, re.I):
        return None
    return {"url": src, "credit": urlparse(page_url).netloc.replace("www.", ""), "lien": page_url}


_PAS_AFFICHE = re.compile(r"(?i)(logo|favicon|icon|sprite|badge|pixel|placeholder|partenaire|partner|commanditaire|sponsor|"
                         r"donateur|facebook\.com/tr|googletagmanager|google-analytics|maps\.google|doubleclick|\.svg|^data:|/w_\d{1,2},|[-_x]\d{2}x\d{2}\.|arrow|loader)")
MOTS_VIDES_IMG = {"avec", "pour", "dans", "show", "soiree", "concert", "spectacle", "lancement", "montreal", "presente",
                  "presents", "with", "from", "night", "edition", "tournee", "tour", "live", "hommage", "festival"}


def images_page(html: str, page_url: str) -> list[tuple[str, str]]:
    """Images de contenu de la page (adresse, texte alternatif), sans logos, icônes ni pixels de suivi."""
    out = []
    for i in BeautifulSoup(html, "html.parser").find_all("img"):
        src = i.get("src") or i.get("data-src") or (i.get("srcset") or "").split(" ")[0]
        if not src or _PAS_AFFICHE.search(src):
            continue
        src = urljoin(page_url, src.strip())
        if src.startswith("http://"):
            src = "https://" + src[7:]
        if src.startswith("https://") and src not in [o[0] for o in out]:
            out.append((src, (i.get("alt") or "").strip()))
    return out


def _nom_fichier(src: str) -> str:
    """« …/1792351291TracyTrashShow-261101.jpg » → « tracy trash show 261101 jpg » (aussi pour les images /_next/image)."""
    from urllib.parse import unquote
    u = unquote(unquote(src))
    m = re.search(r"[?&]url=([^&]+)", u)
    chemin = urlparse(m.group(1) if m else u).path.rsplit("/", 1)[-1] or urlparse(u).path
    chemin = re.sub(r"([a-zà-ÿ])([A-ZÀ-Ý])", r"\1 \2", chemin)  # TracyTrashShow → Tracy Trash Show
    return plat(chemin)


def image_du_titre(titre: str, noms: list[str], imgs: list[tuple[str, str]], seul: bool) -> str | None:
    """L'image qui porte le titre du spectacle : texte alternatif = titre (FestApp, Le Point de vente…), ou nom de fichier
    qui contient le titre ou l'artiste (« FullGisele », « LMC_OISEAU »). Sans correspondance, une page consacrée à un seul
    spectacle qui n'a qu'une image de contenu : c'est la sienne. Sinon rien."""
    t = plat(titre)
    mots = [w for w in t.split() if len(w) >= 4 and w not in MOTS_VIDES_IMG]
    for src, alt in imgs:
        a, f = plat(alt), _nom_fichier(src)
        if a and (a == t or (len(t) >= 6 and t in a) or (len(a) >= 8 and a in t and len(a) >= 0.6 * len(t))):
            return src
        fs = f.replace(" ", "")
        if any(len(plat(n)) >= 5 and (plat(n) in a or plat(n).replace(" ", "") in fs) for n in noms):
            return src
        if (len(mots) >= 2 and all(w in fs for w in mots[:3])) or (len(mots) == 1 and len(mots[0]) >= 5 and mots[0] in f.split()):
            return src
    if seul and len(imgs) == 1:
        return imgs[0][0]
    return None


_GRATUIT = re.compile(r"(?i)\b(gratuit|entr[ée]e libre|admission gratuite|free admission|free entry|entr[ée]e gratuite)\b")
_CONTRIB = re.compile(r"(?i)\b(contribution volontaire|pwyc|pay what you can|prix libre)\b")
_MONTANT = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{2})?)\s?\$|\$\s?(\d{1,3}(?:[.,]\d{2})?)(?![\d.,])")
_MOTS_PRIX = re.compile(r"(?i)(prix|tarifs?|billets?|admission|entr[ée]e|tickets?|price|cost|cover|r[ée]gulier|[ée]tudiant|g[ée]n[ée]ral|pr[ée]vente|porte)")


def prix_page(html: str) -> str | None:
    """Prix lu sur la page d'un événement : données schema.org d'abord, puis le texte près des mots « prix », « billets »,
    « admission »… (« 25 $ », « 20 à 35 $ », « Gratuit », « Contribution volontaire »). Rien si ce n'est pas clair."""
    m = re.search(r'"price"\s*:\s*"?(\d+(?:[.,]\d+)?)', html)
    if m:
        v = float(m.group(1).replace(",", "."))
        return "Gratuit" if v == 0 else (f"{v:.0f}" if v.is_integer() else f"{v:.2f}").replace(".", ",") + " $"
    texte = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    if _CONTRIB.search(texte):
        return "Contribution volontaire"
    montants = []
    for mm in _MONTANT.finditer(texte):
        avant = texte[max(0, mm.start() - 70):mm.start()]
        if _MOTS_PRIX.search(avant) and not re.search(r"(?i)(rabais|off|économ|frais de service|service fee|bière|beer|drink)", avant[-30:]):
            v = float((mm.group(1) or mm.group(2)).replace(",", "."))
            if 3 <= v <= 400:
                montants.append(v)
    if montants:
        a, b = min(montants), max(montants)
        f = lambda x: (f"{x:.0f}" if x.is_integer() else f"{x:.2f}").replace(".", ",")  # noqa: E731
        return f"{f(a)} $" if a == b else f"{f(a)} à {f(b)} $"
    if _GRATUIT.search(texte[:6000]):
        return "Gratuit"
    return None


BILLETTERIES = ("lepointdevente.com", "ticketmaster.", "admission.com", "eventbrite.", "tuxedobillet", "tuxedo.ca",
                "showpass.com", "dice.fm", "ra.co/events", "zeffy.com", "evenko.ca", "ovation", "ticketpro", "eventim",
                "universe.com", "lavitrine.com", "billetterie", "billets", "tickets", "ticketweb", "seetickets",
                "fever", "sortiesbillets", "ticketsource", "yapla", "goout", "eventzilla", "shotgun.live", "/tickets")
_MOTS_BILLET = re.compile(r"\b(billets?|billetterie|tickets?|acheter|achat|r[ée]server|r[ée]servation|buy|book now|get tickets)\b", re.I)


def billets_page(html: str, page_url: str) -> str | None:
    """Lien d'achat de billets sur la page de l'événement : un lien vers une billetterie connue,
    ou un bouton dont le texte parle de billets (« Billets », « Acheter », « Réserver », « Tickets »)."""
    soupe = BeautifulSoup(html, "html.parser")
    candidats = []
    for a in soupe.find_all("a", href=True):
        href = urljoin(page_url, a["href"]).split("#")[0]
        if not href.startswith("http") or href.rstrip("/") == page_url.rstrip("/"):
            continue
        texte = a.get_text(" ", strip=True)[:60]
        h = href.lower()
        if any(b in h for b in BILLETTERIES) and not any(x in h for x in ("facebook.", "instagram.", "/help", "/aide", "faq")):
            candidats.append((0, href))
        elif _MOTS_BILLET.search(texte) and not re.search(r"(?i)politique|conditions|cadeau|gift|abonnement|newsletter|infolettre", texte):
            candidats.append((1, href))
    return sorted(candidats)[0][1] if candidats else None


def musicbrainz(nom: str, get_json) -> list[dict]:
    """Liens officiels d'un artiste sur MusicBrainz (correspondance exacte du nom seulement)."""
    r = get_json(f"https://musicbrainz.org/ws/2/artist/?query=artist:%22{quote(nom)}%22&fmt=json&limit=5")
    cands = [a for a in (r or {}).get("artists", []) if int(a.get("score", 0)) >= 95 and plat(a.get("name", "")) == plat(nom)]
    if not cands:
        return []
    ca = [a for a in cands if a.get("country") == "CA" or "canada" in plat(json.dumps(a.get("area") or {}))
          or "montreal" in plat(json.dumps(a.get("begin-area") or {}))]
    if len(ca) == 1 or len(cands) == 1:
        art = (ca or cands)[0]
        time.sleep(1.1)  # règle de MusicBrainz : une requête par seconde
        fiche = get_json(f"https://musicbrainz.org/ws/2/artist/{art['id']}?inc=url-rels&fmt=json") or {}
    else:
        # Homonymes (ex. plusieurs « Sting ») : on garde celui qui est nettement le mieux documenté
        # (au moins 3 liens d'écoute et deux fois plus que le suivant). Sinon on s'abstient.
        fiches = []
        for a in cands[:4]:
            time.sleep(1.1)
            f = get_json(f"https://musicbrainz.org/ws/2/artist/{a['id']}?inc=url-rels&fmt=json") or {}
            n = sum(1 for r in f.get("relations", []) if type_lien((r.get("url") or {}).get("resource", "")))
            fiches.append((n, a, f))
        fiches.sort(key=lambda x: -x[0])
        if fiches[0][0] < 3 or (len(fiches) > 1 and fiches[0][0] < 2 * fiches[1][0]):
            return []
        _, art, fiche = fiches[0]
    out = []
    for rel in fiche.get("relations", []):
        url = (rel.get("url") or {}).get("resource", "")
        t = type_lien(url) or ("site" if rel.get("type") == "official homepage" else None)
        if t:
            out.append({"type": t, "url": url, "source": "musicbrainz", "nom": art.get("name", nom)})
    return out[:4]


def wikidata(nom: str, get_json) -> list[dict]:
    """Liens d'écoute inscrits sur Wikidata (Spotify, Bandcamp, YouTube, SoundCloud) pour un nom identique.
    Plusieurs fiches du même nom : on garde la seule qui est canadienne, sinon on s'abstient."""
    lit = json.dumps(nom)
    q = f"""SELECT ?item ?sp ?bc ?yt ?sc ?ca WHERE {{
      VALUES ?lab {{ {lit}@en {lit}@fr {lit}@mul }}
      ?item rdfs:label ?lab .
      OPTIONAL {{ ?item wdt:P1902 ?sp }} OPTIONAL {{ ?item wdt:P3283 ?bc }}
      OPTIONAL {{ ?item wdt:P2397 ?yt }} OPTIONAL {{ ?item wdt:P3040 ?sc }}
      OPTIONAL {{ VALUES ?pays {{ wdt:P27 wdt:P495 wdt:P740 }} ?item ?pays ?ca . FILTER(?ca = wd:Q16 || ?ca = wd:Q340 || ?ca = wd:Q176) }}
      FILTER(BOUND(?sp) || BOUND(?bc) || BOUND(?yt) || BOUND(?sc))
    }} LIMIT 40"""
    r = get_json("https://query.wikidata.org/sparql?format=json&query=" + quote(q)) or {}
    fiches: dict[str, dict] = {}
    for b in r.get("results", {}).get("bindings", []):
        f = fiches.setdefault(b["item"]["value"], {"ca": False, "liens": {}})
        f["ca"] = f["ca"] or "ca" in b
        for k, gabarit, t in (("sp", "https://open.spotify.com/artist/{}", "spotify"), ("bc", "https://{}.bandcamp.com/", "bandcamp"),
                              ("yt", "https://www.youtube.com/channel/{}", "youtube"), ("sc", "https://soundcloud.com/{}", "soundcloud")):
            if k in b:
                f["liens"].setdefault(t, gabarit.format(b[k]["value"]))
    choix = list(fiches.values())
    if len(choix) > 1:
        choix = [f for f in choix if f["ca"]]
    if len(choix) != 1:
        return []
    return [{"type": t, "url": u, "source": "wikidata", "nom": nom} for t, u in choix[0]["liens"].items()]


_JETON_SPOTIFY: dict = {}


def spotify(nom: str) -> list[dict]:
    """Recherche d'artiste sur l'API Spotify (seulement si SPOTIFY_CLIENT_ID et SPOTIFY_CLIENT_SECRET sont fournis).
    Nom identique exigé. Plusieurs homonymes : le plus suivi, seulement s'il l'est nettement plus (10 fois et 1 000 abonnés)."""
    cid, secret = os.environ.get("SPOTIFY_CLIENT_ID"), os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not cid or not secret:
        return []
    import requests
    if _JETON_SPOTIFY.get("fin", 0) < time.time():
        r = requests.post("https://accounts.spotify.com/api/token", data={"grant_type": "client_credentials"},
                          auth=(cid, secret), timeout=20)
        r.raise_for_status()
        j = r.json()
        _JETON_SPOTIFY.update(jeton=j["access_token"], fin=time.time() + int(j.get("expires_in", 3600)) - 60)
    r = requests.get("https://api.spotify.com/v1/search", params={"q": nom, "type": "artist", "limit": 10, "market": "CA"},
                     headers={"Authorization": "Bearer " + _JETON_SPOTIFY["jeton"]}, timeout=20)
    if r.status_code == 429:
        time.sleep(min(int(r.headers.get("Retry-After", "5")), 30))
        return []
    r.raise_for_status()
    cands = [a for a in r.json().get("artists", {}).get("items", []) if plat(a.get("name", "")) == plat(nom)]
    cands.sort(key=lambda a: -((a.get("followers") or {}).get("total") or 0))
    if not cands:
        return []
    if len(cands) > 1:
        f0, f1 = ((cands[0].get("followers") or {}).get("total") or 0), ((cands[1].get("followers") or {}).get("total") or 0)
        if f0 < 1000 or f0 < 10 * max(f1, 1):
            return []
    url = (cands[0].get("external_urls") or {}).get("spotify")
    return [{"type": "spotify", "url": url, "source": "spotify", "nom": cands[0]["name"]}] if url else []


def _nom_assez_distinctif(nom: str) -> bool:
    """Un nom court ou d'un seul mot courant (« Kim », « Moon ») a trop d'homonymes : on ne cherche pas dans les catalogues."""
    mots = plat(nom).split()
    return bool(mots) and (len(mots) >= 2 and len("".join(mots)) >= 6 or (len(mots) == 1 and len(mots[0]) >= 6))


# ---- Catalogues Deezer et Apple Music : un nom identique ne suffit pas, il faut un indice qui confirme ----
ETIQUETTES_QC_CA = ["bonsound", "audiogram", "simone records", "secret city", "constellation", "arbutus", "dare to care",
                    "grosse boite", "spectra musique", "musicor", "analekta", "atma classique", "justin time", "effendi",
                    "l abe", "coyote records", "indica", "lisbon lux", "mothland", "arts crafts", "art crafts", "royal mountain",
                    "last gang", "dine alone", "bravo musique", "la tribu", "117 records", "ambiances magnetiques", "dame",
                    "joy ride records", "7ieme ciel", "duprince", "grosse boîte", "productions j", "disques 7ieme ciel",
                    "label cinq7", "cinq7", "outside music", "maple music", "paper bag records", "hidden pony", "six shooter",
                    "next door records", "ste 4", "sainte 4", "disques victoire", "le pantheon", "ad litteram",
                    "costume records", "montreal", "quebec", ]
COMPATIBLES = {"rock": {"rock", "metal", "pop", "folk", "experimental"}, "pop": {"pop", "rock", "folk", "hiphop", "electro", "monde"},
               "hiphop": {"hiphop", "pop", "electro"}, "electro": {"electro", "hiphop", "pop", "experimental"},
               "jazz": {"jazz", "monde", "classique", "experimental", "folk"}, "classique": {"classique", "jazz", "experimental"},
               "monde": {"monde", "jazz", "pop", "folk", "hiphop"}, "folk": {"folk", "pop", "rock", "monde"},
               "metal": {"metal", "rock", "experimental"}, "experimental": {"experimental", "electro", "jazz", "classique", "rock", "metal"}}
_TITRES_VIDES = {"live", "remixes", "remix", "demo", "demos", "intro", "outro", "untitled", "greatest hits", "best of", "single"}


def _nom_assez_distinctif(nom: str) -> bool:
    """Un nom court ou d'un seul mot courant (« Kim », « Moon ») a trop d'homonymes : on ne cherche pas dans les catalogues."""
    mots = plat(nom).split()
    return bool(mots) and (len(mots) >= 2 and len("".join(mots)) >= 6 or (len(mots) == 1 and len(mots[0]) >= 6))


def _titre_oeuvre(t: str) -> str:
    return plat(re.sub(r"\(.*?\)|\[.*?\]|\s-\s(ep|single|deluxe.*)$", "", t or "", flags=re.I))


_ITUNES_DERNIER = [0.0]


def _fiche_deezer(nom: str, get_json) -> dict | None:
    r = get_json(f"https://api.deezer.com/search/artist?q={quote(nom)}&limit=25") or {}
    cands = [a for a in r.get("data", []) if plat(a.get("name", "")) == plat(nom)]
    if len(cands) != 1 or not cands[0].get("nb_album") or not str(cands[0].get("link", "")).startswith("https://"):
        return None
    a = cands[0]
    albums = (get_json(f"https://api.deezer.com/artist/{a['id']}/albums?limit=50") or {}).get("data", [])
    fiche = {"lien": {"type": "deezer", "url": a["link"], "source": "deezer", "nom": a["name"]},
             "oeuvres": {_titre_oeuvre(x.get("title", "")) for x in albums}, "dates": [x.get("release_date", "") for x in albums],
             "genres": [], "etiquettes": []}
    for x in sorted(albums, key=lambda x: x.get("release_date", ""), reverse=True)[:3]:  # étiquette et genres des 3 derniers
        al = get_json(f"https://api.deezer.com/album/{x['id']}") or {}
        fiche["etiquettes"].append(al.get("label", ""))
        fiche["genres"] += [g.get("name", "") for g in (al.get("genres") or {}).get("data", [])]
    return fiche


_JETON_TIDAL: dict = {}


def _fiche_tidal(nom: str, get_json=None) -> dict | None:
    """Fiche Tidal (API officielle, clé TIDAL_CLIENT_ID et TIDAL_CLIENT_SECRET) : un seul artiste au nom identique,
    avec ses albums, leurs dates et leurs maisons de disques (Tidal ne donne pas de genres)."""
    cid, sec = os.environ.get("TIDAL_CLIENT_ID"), os.environ.get("TIDAL_CLIENT_SECRET")
    if not cid or not sec:
        return None
    import requests
    if _JETON_TIDAL.get("fin", 0) < time.time():
        t = requests.post("https://auth.tidal.com/v1/oauth2/token", data={"grant_type": "client_credentials"}, auth=(cid, sec), timeout=20)
        t.raise_for_status()
        _JETON_TIDAL.update(jeton=t.json()["access_token"], fin=time.time() + int(t.json().get("expires_in", 3600)) - 60)
    h = {"Authorization": "Bearer " + _JETON_TIDAL["jeton"], "accept": "application/vnd.api+json"}
    r = requests.get("https://openapi.tidal.com/v2/searchResults", headers=h, timeout=20,
                     params={"filter[query]": nom, "countryCode": "CA", "include": "artists", "explicitFilter": "INCLUDE"})
    if r.status_code == 429:
        time.sleep(5)
        return None
    r.raise_for_status()
    cands = [a for a in r.json().get("included", []) if a.get("type") == "artists"
             and plat((a.get("attributes") or {}).get("name", "")) == plat(nom)]
    if len(cands) != 1:
        return None  # aucun ou plusieurs artistes de ce nom : on s'abstient
    a = cands[0]
    al = requests.get(f"https://openapi.tidal.com/v2/artists/{a['id']}/relationships/albums", headers=h, timeout=20,
                      params={"countryCode": "CA", "include": "albums"})
    al.raise_for_status()
    albums = [x.get("attributes") or {} for x in al.json().get("included", []) if x.get("type") == "albums"]
    if not albums:
        return None
    url = next((l["href"] for l in (a.get("attributes") or {}).get("externalLinks", []) if l.get("href", "").startswith("https://")),
               f"https://tidal.com/browse/artist/{a['id']}")
    return {"lien": {"type": "tidal", "url": url, "source": "tidal", "nom": a["attributes"]["name"]},
            "oeuvres": {_titre_oeuvre(x.get("title", "")) for x in albums}, "dates": [x.get("releaseDate", "") for x in albums],
            "genres": [], "etiquettes": [re.sub(r"^\W*(?:\(p\)|℗|©)?\s*\d{4}\s*", "", (x.get("copyright") or {}).get("text", ""), flags=re.I)
                                         for x in albums]}


def _fiche_apple(nom: str, get_json) -> dict | None:
    def appel(url):
        attente = 3.2 - (time.time() - _ITUNES_DERNIER[0])  # Apple : environ 20 recherches par minute
        if attente > 0:
            time.sleep(attente)
        _ITUNES_DERNIER[0] = time.time()
        return get_json(url) or {}
    r = appel(f"https://itunes.apple.com/search?term={quote(nom)}&entity=musicArtist&country=CA&limit=25")
    cands = [a for a in r.get("results", []) if plat(a.get("artistName", "")) == plat(nom)]
    if len(cands) != 1 or not str(cands[0].get("artistLinkUrl", "")).startswith("https://"):
        return None
    a = cands[0]
    albums = [x for x in appel(f"https://itunes.apple.com/lookup?id={a['artistId']}&entity=album&limit=50&country=CA").get("results", [])
              if x.get("wrapperType") == "collection"]
    return {"lien": {"type": "apple", "url": a["artistLinkUrl"].split("?")[0], "source": "itunes", "nom": a["artistName"]},
            "oeuvres": {_titre_oeuvre(x.get("collectionName", "")) for x in albums},
            "dates": [x.get("releaseDate", "")[:10] for x in albums],
            "genres": [a.get("primaryGenreName", "")] + [x.get("primaryGenreName", "") for x in albums[:5]],
            "etiquettes": [x.get("copyright", "") for x in albums[:5]]}


def _indices(fiche: dict, nom: str, ctx: dict) -> tuple[list[str], list[str]]:
    """(indices qui confirment, indices qui contredisent) pour une fiche de catalogue et le contexte de la soirée."""
    pour, contre = [], []
    texte = " " + ctx.get("texte", "") + " "
    oeuvres = {o for o in fiche["oeuvres"] if len(o) >= 5 and o != plat(nom) and o not in _TITRES_VIDES}
    vues = [o for o in oeuvres if f" {o} " in texte]
    if vues:
        pour.append("album nommé sur la page : " + vues[0])
    etiq = " ".join(plat(x) for x in fiche["etiquettes"])
    qc = [l for l in ETIQUETTES_QC_CA if re.search(rf"\b{re.escape(plat(l))}\b", etiq)]
    if qc:
        pour.append("maison de disques : " + qc[0])
    styles = {st for g in fiche["genres"] if g and (st := style_genre(g))}
    if ctx.get("style") and styles:
        if ctx["style"] in styles:
            pour.append("genre concordant : " + ctx["style"])
        elif not any(st in COMPATIBLES.get(ctx["style"], {ctx["style"]}) for st in styles):
            contre.append(f"genre {'/'.join(sorted(styles))} ≠ {ctx['style']}")
    if ctx.get("lancement") and ctx.get("date"):
        d0 = date.fromisoformat(ctx["date"])
        if any(d and abs((date.fromisoformat(d[:10]) - d0).days) <= 120 for d in fiche["dates"] if re.match(r"\d{4}-\d{2}-\d{2}", d or "")):
            pour.append("album sorti autour du lancement")
    return pour, contre


GENRES_CATALOGUE = [("metal", r"metal|punk|hardcore|grind"), ("classique", r"classi|opera|baroque|orchestr|choral"),
                    ("jazz", r"jazz|blues|swing"), ("hiphop", r"hip.?hop|rap|r ?b|soul|funk|trap"),
                    ("electro", r"electr|dance|house|techno|dubstep|drum|trance|ambient|edm|disco"),
                    ("monde", r"world|afri|latin|reggae|brazil|arab|cumbia|salsa|kompa|zouk|celtic|bollywood|tango|flamenco"),
                    ("folk", r"folk|country|bluegrass|americana|singer|songwriter|auteur"),
                    ("experimental", r"experiment|avant|noise|improv|electroacoust"),
                    ("rock", r"rock|alternati|indie|grunge|garage|shoegaze|emo"), ("pop", r"pop|variet|chanson|francophon|easy")]


def style_genre(genre: str) -> str | None:
    """Genre d'un catalogue (« Alternative », « R&B/Soul », « Classique ») → style du calendrier, ou None (bande sonore…)."""
    g = plat(genre)
    for st, motif in GENRES_CATALOGUE:
        if re.search(motif, g):
            return st
    return None


def catalogues(nom: str, ctx: dict, get_json, journal: list | None = None) -> list[dict]:
    """Liens Deezer et Apple Music d'un artiste, seulement si : nom distinctif et identique, un seul artiste de ce nom dans
    le catalogue, aucun indice contraire (genre incompatible avec la soirée), et au moins un indice qui confirme
    (album ou chanson nommé sur la page, maison de disques québécoise ou canadienne, genre concordant, album sorti autour
    d'un lancement). Un catalogue confirmé confirme l'autre s'ils ont un album en commun (même artiste)."""
    if not _nom_assez_distinctif(nom):
        return []
    fiches = {}
    for cle, f in (("deezer", _fiche_deezer), ("apple", _fiche_apple), ("tidal", _fiche_tidal)):
        try:
            fiches[cle] = f(nom, get_json)
        except Exception as exc:
            print(f"  {cle} « {nom[:30]} » : {exc}")
    fiches = {k: v for k, v in fiches.items() if v}
    lfm = None
    if fiches:
        try:
            lfm = fiche_lastfm(nom, get_json)
        except Exception as exc:
            print(f"  Last.fm « {nom[:30]} » : {exc}")
    ok = {}
    for k, f in fiches.items():
        pour, contre = _indices(f, nom, ctx)
        if lfm:
            # Last.fm cite un album du catalogue dans sa biographie, ou présente un artiste d'ici du même genre
            cites = [o for o in f["oeuvres"] if len(o) >= 6 and o != plat(nom) and o not in _TITRES_VIDES and f" {o} " in f" {lfm['bio']} "]
            styles_f = {st for g in f["genres"] if g and (st := style_genre(g))}
            styles_l = {st for g in lfm["tags"] if g and (st := style_genre(g))}
            if cites:
                pour.append("Last.fm cite l'album : " + cites[0])
            elif lfm["ici"] and styles_f & styles_l:
                pour.append("Last.fm : artiste d'ici, même genre (" + "/".join(sorted(styles_f & styles_l)) + ")")
        ok[k] = (bool(pour) and not contre, pour, contre)
    # Même artiste dans deux catalogues (un album en commun) : la confirmation de l'un vaut pour l'autre
    for _ in range(2):
        for k1 in list(ok):
            for k2 in list(ok):
                if k1 == k2 or not ok[k1][0] or ok[k2][0] or ok[k2][2]:
                    continue
                communs = {o for o in fiches[k1]["oeuvres"] & fiches[k2]["oeuvres"] if len(o) >= 4 and o not in _TITRES_VIDES}
                if communs:
                    ok[k2] = (True, ok[k2][1] + [f"même artiste que sur {k1} (album {sorted(communs)[0]})"], ok[k2][2])
    if journal is not None:
        journal.append({"nom": nom, **{k: {"ok": v[0], "pour": v[1], "contre": v[2]} for k, v in ok.items()}})
    return [fiches[k]["lien"] for k, v in ok.items() if v[0]]


def bandcamp(nom: str, get_html) -> list[dict]:
    """Recherche d'artiste sur Bandcamp (sans clé). On garde un résultat au nom identique, situé à Montréal,
    au Québec ou au Canada ; ou le seul résultat au nom identique s'il n'y en a qu'un."""
    html = get_html(f"https://bandcamp.com/search?q={quote(nom)}&item_type=b")
    soupe = BeautifulSoup(html, "html.parser")
    exacts = []
    for li in soupe.select("li.searchresult"):
        a = li.select_one(".heading a")
        if not a or plat(a.get_text(" ", strip=True)) != plat(nom):
            continue
        lieu = plat((li.select_one(".subhead") or li).get_text(" ", strip=True))
        url = (li.select_one(".itemurl") or a).get_text(strip=True) if li.select_one(".itemurl") else a.get("href", "")
        url = url.split("?")[0]
        if url.startswith("http"):
            exacts.append((any(m in lieu for m in ("montreal", "quebec", "canada", " qc")), url))
    locaux = [u for loc, u in exacts if loc]
    choix = locaux[0] if len(locaux) == 1 else (exacts[0][1] if len(exacts) == 1 else None)
    return [{"type": "bandcamp", "url": choix, "source": "bandcamp", "nom": nom}] if choix else []


def bande_annonce_tmdb(titre: str, annee: int, get_json) -> list[dict]:
    cle = os.environ.get("TMDB_API_KEY")
    if not cle:
        return []
    titre = re.sub(r"\(.*?\)|^(gala[^:]*|projection(?:[- ]discussion)?|cin[ée][- ]?(?:club|r[ée]pertoire|parc|famille)"
                   r"|soir[ée]e[^:]*|avant[- ]premi[èe]re)\s*:\s*", "", titre, flags=re.I).strip()
    r = get_json(f"https://api.themoviedb.org/3/search/movie?api_key={cle}&language=fr-CA&query={quote(titre)}") or {}
    films = [f for f in r.get("results", []) if plat(f.get("title", "")) == plat(titre) or plat(f.get("original_title", "")) == plat(titre)]
    if len(films) > 1:
        # Plusieurs films du même nom : un film récent (festival, sortie) d'abord ; sinon un classique nettement plus connu
        # (ciné-club, répertoire : « Thelma & Louise ») ; sinon on s'abstient.
        recents = [f for f in films if f.get("release_date") and abs(int(f["release_date"][:4]) - annee) <= 2]
        if len(recents) == 1:
            films = recents
        else:
            films.sort(key=lambda f: -(f.get("vote_count") or 0))
            if (films[0].get("vote_count") or 0) >= 10 * max(films[1].get("vote_count") or 0, 1) \
                    and (films[0].get("vote_count") or 0) >= 100:
                films = films[:1]
    if len(films) != 1:
        return []  # aucun ou plusieurs films du même nom : on s'abstient
    v = get_json(f"https://api.themoviedb.org/3/movie/{films[0]['id']}/videos?api_key={cle}&include_video_language=fr,en,null") or {}
    vids = [x for x in v.get("results", []) if x.get("site") == "YouTube" and x.get("type") in ("Trailer", "Teaser")]
    vids.sort(key=lambda x: (x.get("iso_639_1") != "fr", x.get("type") != "Trailer"))
    out = [{"type": "bande-annonce", "url": f"https://www.youtube.com/watch?v={vids[0]['key']}", "source": "tmdb"}] if vids else []
    if films[0].get("poster_path"):
        out.append({"type": "affiche", "url": "https://image.tmdb.org/t/p/w342" + films[0]["poster_path"], "source": "tmdb",
                    "lien": f"https://www.themoviedb.org/movie/{films[0]['id']}"})
    return out


# ---------------------------------------------------------------- YouTube : bandes-annonces (API officielle, clé gratuite)
# Quota gratuit : 10 000 unités par jour ; une recherche en coûte 100, la fiche des vidéos 1. On s'en tient à 80
# recherches par jour (compteur dans la mémoire) ; les films restants passent les jours suivants.
YT_PAR_JOUR = 80
DISTRIBUTEURS = ("maison 4 3", "maison 4:3", "immina", "axia films", "tva films", "metropole films", "entract", "sphere films",
                 "les films seville", "films seville", "h264", "mk2 mile end", "mk2", "funfilm", "fun film", "remstar",
                 "onf", "nfb", "office national du film", "national film board", "telefilm", "a24", "neon", "mubi",
                 "elevation pictures", "mongrel media", "vvs films", "pathe", "gaumont", "le pacte", "diaphana", "ad vitam",
                 "haut et court", "memento", "wild bunch", "studiocanal", "warner", "universal", "paramount", "sony pictures",
                 "focus features", "searchlight", "lionsgate", "magnolia", "ifc films", "kino lorber", "janus", "criterion",
                 "cinemania", "ridm", "fnc", "festival du nouveau cinema", "rvqc", "cinematheque", "tiff", "sbiff",
                 "festival", "film society", "berlinale", "cannes", "sundance", "trailers", "bandes annonces", "filmsactu")
_PAS_BA = re.compile(r"(?i)\b(review|critique|reaction|réaction|explained|expliqu|fan.?made|parod|analys|recap|résumé|"
                     r"interview|entrevue|making.?of|behind|coulisses|scene|scène|clip|extrait|featurette|podcast|ending|fin expliqu)")
_EST_BA = re.compile(r"(?i)bande[- ]?annonce|trailer|teaser|\bba\b")


def _duree_s(iso: str) -> int:
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)) if m else 0


def bande_annonce_youtube(titre: str, annee: int, get_json, memo: dict, aujourd: date) -> list[dict]:
    """Bande-annonce sur YouTube, seulement si tout concorde : le titre du film dans celui de la vidéo (mots entiers),
    « bande-annonce / trailer / teaser », ni critique ni extrait, moins de 4 min 30, et une chaîne de distributeur ou
    de festival (ou portant le titre du film) — ou une seule vidéo qui remplit tout le reste. Titre d'un seul mot
    (« Paradis ») : chaîne de confiance et vidéo de moins de 3 ans exigées."""
    cle = os.environ.get("YOUTUBE_API_KEY")
    if not cle or len(plat(titre)) < 4:
        return []
    compteur = memo.setdefault("_youtube", {})
    if compteur.get("jour") != aujourd.isoformat():
        compteur.update(jour=aujourd.isoformat(), n=0)
    if compteur["n"] >= YT_PAR_JOUR:
        return []
    compteur["n"] += 1
    r = get_json("https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=10&regionCode=CA"
                 f"&q={quote(titre + ' bande-annonce trailer')}&key={cle}") or {}
    t = plat(titre)
    cands = []
    for it in r.get("items", []):
        sn = it.get("snippet") or {}
        vt = sn.get("title", "")
        if f" {t} " not in f" {plat(vt)} " or not _EST_BA.search(vt) or _PAS_BA.search(vt):
            continue
        cands.append({"id": (it.get("id") or {}).get("videoId"), "titre": vt, "chaine": sn.get("channelTitle", ""),
                      "date": sn.get("publishedAt", "")[:10]})
    cands = [c for c in cands if c["id"]]
    if not cands:
        return []
    v = get_json("https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id="
                 + ",".join(c["id"] for c in cands) + f"&key={cle}") or {}
    durees = {x["id"]: _duree_s((x.get("contentDetails") or {}).get("duration", "")) for x in v.get("items", [])}
    cands = [c for c in cands if 20 <= durees.get(c["id"], 0) <= 270]
    confiance = lambda c: any(d in plat(c["chaine"]) for d in DISTRIBUTEURS) or t in plat(c["chaine"])  # noqa: E731
    recent = lambda c: c["date"] and int(c["date"][:4]) >= annee - 3  # noqa: E731
    surs = [c for c in cands if confiance(c)]
    mots = len([w for w in t.split() if w not in {"le", "la", "les", "l", "un", "une", "des", "du", "de", "d", "au", "aux",
                                                  "the", "a", "an", "of", "et", "and"}])  # mots qui distinguent
    if mots == 1:  # « Paradis » : chaîne de confiance et vidéo récente
        surs = [c for c in surs if recent(c)]
        choix = surs[0] if surs else None
    elif mots == 2:  # « Les yeux verts » : chaîne de confiance, ou une seule vidéo possible
        choix = surs[0] if surs else (cands[0] if len(cands) == 1 else None)
    else:  # titre de 3 mots ou plus (« Mille secrets, mille dangers ») : peu d'ambiguïté, la chaîne de confiance d'abord
        choix = surs[0] if surs else (cands[0] if cands else None)
    if not choix:
        return []
    return [{"type": "bande-annonce", "url": f"https://www.youtube.com/watch?v={choix['id']}", "source": "youtube",
             "chaine": choix["chaine"]}]


# ---------------------------------------------------------------- Last.fm : un témoin de plus pour Deezer et Apple Music
_ICI = re.compile(r"(?i)montr[ée]al|qu[ée]bec|canad")


def fiche_lastfm(nom: str, get_json) -> dict | None:
    """Étiquettes (genres) et biographie Last.fm d'un nom d'artiste (clé gratuite LASTFM_API_KEY). Last.fm regroupe
    parfois des homonymes sous un même nom : cette fiche ne sert jamais seule, seulement à confirmer un catalogue."""
    cle = os.environ.get("LASTFM_API_KEY")
    if not cle:
        return None
    r = get_json(f"https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={quote(nom)}&autocorrect=0"
                 f"&api_key={cle}&format=json") or {}
    a = r.get("artist")
    if not a or plat(a.get("name", "")) != plat(nom):
        return None
    tags = [x.get("name", "") for x in ((a.get("tags") or {}).get("tag") or [])]
    bio = re.sub(r"<[^>]+>", " ", (a.get("bio") or {}).get("content") or (a.get("bio") or {}).get("summary") or "")
    return {"tags": tags, "bio": plat(bio), "ici": bool(_ICI.search(bio + " " + " ".join(tags)))}


def enrichir(events: list[dict], aujourd: date, telecharger, max_recherches: int = 500, max_affiches: int = 1200,
             page_rendue=None) -> int:
    """Ajoute e["liens"] (écouter, bande-annonce) et e["affiche"] (image de la page officielle). Renvoie le nombre
    d'événements enrichis. Chaque page et chaque artiste ne sont lus qu'une fois (mémoire)."""
    memo = json.loads(MEMOIRE.read_text(encoding="utf-8")) if MEMOIRE.exists() else {}
    ua_json = lambda url: telecharger(url, "application/json").json()  # noqa: E731
    n, cherches = 0, 0
    fin_budget = time.time() + 25 * 60  # au plus 25 minutes par collecte ; la suite reprend le lendemain
    vieux = (aujourd - timedelta(days=30)).isoformat()
    lues_affiche, fin_affiches = 0, time.time() + 20 * 60  # affiches, billets et prix : au plus 20 minutes
    rendues = 0
    # Titres servis par chaque page (une page de programmation sert à plusieurs spectacles)
    titres_page: dict[str, dict] = {}
    for e in events:
        for u in [e.get("url", "")] + (e.get("_autres_urls") or [])[:2]:
            titres_page.setdefault(u, {})[plat(e["titre"])[:40]] = (e["titre"], e.get("_artistes") or noms_artistes(e["titre"]))
    for e in events:
      # la page de l'événement, puis celles des doublons fusionnés (ex. Songkick + site de la salle)
      for url in [e.get("url", "")] + (e.get("_autres_urls") or [])[:2]:
        html = None
        # 1. Affiche : l'image de partage de la page de l'événement (site de la salle, du festival, ou agenda).
        if url.startswith("http") and "facebook.com" not in url:
            pm = memo.get("page:" + url)
            # (v2 : images portant le titre, lecture dans le navigateur ; une relecture des pages lues avant)
            if (not pm or "prix" not in pm or not pm.get("v2") or (not pm.get("affiche") and pm["le"] < vieux)) \
                    and lues_affiche < max_affiches and time.time() < fin_affiches:
                lues_affiche += 1
                try:
                    try:
                        html = telecharger(url, "text/html").text
                    except Exception:
                        html = ""  # refusée (403) : le navigateur peut l'afficher
                    imgs = images_page(html, url)
                    if page_rendue and rendues < 80 and not affiche_page(html, url) and not imgs \
                            and urlparse(url).path not in ("", "/"):
                        rendues += 1
                        html = page_rendue(url)
                        imgs = images_page(html, url)
                    ts = titres_page.get(url, {})
                    par_titre = {k: im for k, (t, noms) in ts.items()
                                 if (im := image_du_titre(t, noms, imgs, len(ts) == 1 and urlparse(url).path not in ("", "/")))}
                    pm = memo["page:" + url] = {"affiche": affiche_page(html, url) if html else None,
                                                "billets": billets_page(html, url) if html else None,
                                                "prix": prix_page(html) if html else None, "par_titre": par_titre,
                                                "le": aujourd.isoformat(), "v2": 1}
                except Exception:
                    pm = memo["page:" + url] = {"affiche": None, "billets": None, "prix": None, "le": aujourd.isoformat(), "v2": 1}
    fin_budget = time.time() + 30 * 60  # liens d'écoute : au plus 30 minutes
    # Une même image pour 3 spectacles différents ou plus, c'est un logo, une image par défaut ou la carte du festival :
    # on l'écarte. (Compté par titre, pas par page : une page de programmation sert à des dizaines de spectacles.)
    titres_par_image: dict[str, set] = {}
    for e in events:
        pm = memo.get("page:" + e.get("url", ""))
        if pm and pm.get("affiche"):
            titres_par_image.setdefault(pm["affiche"]["url"], set()).add(plat(e["titre"])[:30])
    freq = Counter({u: len(t) for u, t in titres_par_image.items()})
    titres_par_page: dict[str, set] = {}
    for e in events:
        titres_par_page.setdefault(e.get("url", ""), set()).add(plat(e["titre"])[:30])
    # Un même lien « billets » sur 25 pages ou plus : la page d'accueil de la billetterie, pas celle du spectacle.
    freq_b = Counter(v.get("billets") for k, v in memo.items() if k.startswith("page:") and v.get("billets"))
    for e in events:
      for u in [e.get("url", "")] + (e.get("_autres_urls") or [])[:2]:
        pm = memo.get("page:" + u)
        if pm and pm.get("affiche") and freq[pm["affiche"]["url"]] < 3 and not e.get("image") and not e.get("affiche") \
                and "og.festapp.io" not in pm["affiche"]["url"]:
            e["affiche"] = dict(pm["affiche"], **agrandir(pm["affiche"]["url"]))
        # Image de la page qui porte le titre du spectacle (FestApp, billetteries, sites sans image de partage)
        im = (pm or {}).get("par_titre", {}).get(plat(e["titre"])[:40])
        if im and not e.get("image") and not e.get("affiche"):
            e["affiche"] = {"credit": urlparse(u).netloc.replace("www.", ""), "lien": u, **agrandir(im)}
        if pm and pm.get("billets") and not e.get("billets") and freq_b[pm["billets"]] < 25:
            e["billets"] = pm["billets"]
        # prix : seulement si la page est celle d'un seul spectacle (pas une page de programmation partagée)
        if pm and pm.get("prix") and not e.get("prix") and len(titres_par_page.get(u, ())) < 3:
            e["prix"] = pm["prix"]
    import requests
    for e in events:
        src = e.get("_image_src")
        if not src or e.get("affiche") or e.get("image") or freq.get(src, 0) >= 3:
            continue
        cle = "img:" + src
        if cle not in memo:
            try:
                r = requests.get(src, timeout=20, stream=True, headers={"User-Agent": "CalendrierCulturelMTL/1.0 (+https://ccmtl.ca)"})
                taille = len(r.raw.read(4096, decode_content=True)) if r.ok else 0
                memo[cle] = taille >= 4096  # image par défaut de Songkick : environ 130 octets
            except Exception:
                continue
        if memo[cle]:
            e["affiche"] = {"url": src, "credit": urlparse(e["url"]).netloc.replace("www.", ""), "lien": e["url"]}
    for e in events:
        url = e.get("url", "")
        html = None
        # 2. Écouter / bande-annonce
        discs = {e.get("discipline"), *(e.get("aussi") or []), e.get("sous")}
        film = "cinema" in discs
        if not (film or "musique" in discs):
            continue
        noms = [re.sub(r"\(.*?\)", "", e["titre"]).split(" — ")[0].strip()] if film \
            else (e["_artistes"] if e.get("_artistes") is not None else noms_artistes(e["titre"]))
        if not noms:
            continue
        cle = ("film:" if film else "mus:") + "|".join(plat(x) for x in noms)
        m = memo.get(cle)
        # v3 : billetterie, cinéaste retiré, Deezer, Apple ; v4 : YouTube (films) et Last.fm (musique), retentés une fois
        version = "v4" if (os.environ.get("YOUTUBE_API_KEY") if film else os.environ.get("LASTFM_API_KEY")) else "v3"
        frais = m and (m["liens"] or (m["le"] >= vieux and m.get(version)))
        if not frais and cherches < max_recherches and time.time() < fin_budget:
            cherches += 1
            liens = []
            echec = False
            contexte = plat(e["titre"] + " " + e.get("resume", ""))
            try:
                # La page de l'événement, même sur un agenda (Sors-tu?, ma.to…) : seuls les liens qui portent
                # le nom de l'artiste sont gardés.
                for u2 in [url] + (e.get("_autres_urls") or [])[:2] + ([e["billets"]] if str(e.get("billets", "")).startswith("http") else []):
                    if u2.startswith("http") and "songkick.com" not in u2 and len(liens) < 4:
                        try:
                            seul = len(titres_page.get(u2, {})) <= 1 and urlparse(u2).path not in ("", "/")
                            h2 = telecharger(u2, "text/html").text
                            liens += depuis_page(h2, u2, noms, lecteurs=seul)
                            if seul:  # texte d'une page consacrée au spectacle : sert à confirmer un artiste de catalogue
                                contexte += " " + plat(BeautifulSoup(h2, "html.parser").get_text(" "))[:20000]
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                if film:
                    if not any(l["type"] in ("youtube", "vimeo") for l in liens):
                        trouves = bande_annonce_tmdb(noms[0], aujourd.year, ua_json)
                        # « Soundtrack to a Coup d'État de Johan Grimonprez », « Mille secrets, mille dangers - Philippe
                        # Falardeau » : sans résultat, on retire le nom du cinéaste (2 ou 3 mots à majuscule en fin de titre)
                        court = re.sub(r"\s+(?:de|by|[-–—])\s+(?:[A-ZÉ][\w'’.-]+\s?){2,3}$", "", noms[0]).strip()
                        if not trouves and court != noms[0] and len(court) >= 4:
                            trouves = bande_annonce_tmdb(court, aujourd.year, ua_json)
                        if not trouves:
                            for t in dict.fromkeys([noms[0], court]):
                                if len(t) >= 4 and not trouves:
                                    try:
                                        trouves = bande_annonce_youtube(t, aujourd.year, ua_json, memo, aujourd)
                                    except Exception as exc:
                                        print(f"  YouTube « {t[:30]} » : {exc}")
                        liens += trouves
                else:
                    for nom in noms:
                        if not any(l.get("nom") == nom for l in liens):
                            liens += musicbrainz(nom, ua_json)
                            time.sleep(1.1)
                        if not any(plat(l.get("nom", "")) == plat(nom) or l["source"] == "page" for l in liens):
                            try:
                                liens += wikidata(nom, ua_json)
                            except Exception:
                                pass
                        if not any(l["type"] == "spotify" for l in liens if plat(l.get("nom", "")) == plat(nom)):
                            try:
                                liens += spotify(nom)
                            except Exception as exc:
                                print(f"  Spotify « {nom[:30]} » : {exc}")
                        # Catalogues Deezer et Apple Music : seulement si rien de vérifié n'a été trouvé pour ce nom,
                        # et seulement avec un indice qui confirme (voir catalogues())
                        if not any(plat(l.get("nom", "")) == plat(nom) or l["source"] == "page" for l in liens):
                            liens += catalogues(nom, {"texte": contexte, "style": e.get("style"), "date": e.get("date"),
                                                      "lancement": bool(re.search(r"(?i)lancement|album release|release show",
                                                                                  e["titre"] + " " + e.get("resume", "")))},
                                                ua_json, JOURNAL_CATALOGUES)
                        # Recherche Bandcamp retirée (31 oct. 2026) : le robots.txt de Bandcamp demande de ne pas lire ses
                        # pages de recherche. Les liens Bandcamp viennent encore des pages des salles, de MusicBrainz et Wikidata.
            except Exception as exc:
                print(f"  découverte « {e['titre'][:40]} » : {exc}")
                echec = True
            if echec and not liens:
                # Panne passagère (ex. MusicBrainz 503) : rien n'est mémorisé, la recherche sera refaite demain.
                m = None
            else:
                m = memo[cle] = {"liens": liens[:7], "le": aujourd.isoformat(), "v3": 1, version: 1}
        if m and m["liens"]:
            aff = [l for l in m["liens"] if l["type"] == "affiche"]
            if aff and not e.get("affiche") and not e.get("image"):
                e["affiche"] = {"url": aff[0]["url"], "credit": "TMDb", "lien": aff[0]["lien"]}
            liens = [l for l in m["liens"] if l["type"] != "affiche"]
            if liens:
                e["liens"] = liens
            n += 1
    MEMOIRE.parent.mkdir(exist_ok=True)
    MEMOIRE.write_text(json.dumps(memo, ensure_ascii=False), encoding="utf-8")
    return n
