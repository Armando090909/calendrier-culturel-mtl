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
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from normalisation import plat

MEMOIRE = Path(__file__).parent / "cache" / "decouverte.json"
SITES = {"bandcamp.com": "bandcamp", "open.spotify.com": "spotify", "music.apple.com": "apple",
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
    t = re.split(r"\s[–—|:]\s|\s-\s", t)[0]
    morceaux = re.split(r"\s\+\s|,|\savec\s|\swith\s|\sw/\s|\set\s(?=[A-ZÉ])|\s&\s|\sx\s", t)
    out = []
    for m in morceaux:
        m = m.strip(" .·-")
        if m and len(plat(m)) >= 2 and plat(m) not in GENERIQUES and not re.match(r"(?i)invit", m):
            out.append(m)
    return out[:3]


def _correspond(nom: str, texte: str) -> bool:
    n, t = plat(nom).replace(" ", ""), plat(texte).replace(" ", "")
    return len(n) >= 4 and n in t


def depuis_page(html: str, page_url: str, noms: list[str]) -> list[dict]:
    """Lecteurs intégrés (iframes) et liens nommés vers les plateformes, sur la page de l'événement."""
    soupe = BeautifulSoup(html, "html.parser")
    liens = []
    for f in soupe.find_all("iframe", src=True):
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


def musicbrainz(nom: str, get_json) -> list[dict]:
    """Liens officiels d'un artiste sur MusicBrainz (correspondance exacte du nom seulement)."""
    r = get_json(f"https://musicbrainz.org/ws/2/artist/?query=artist:%22{quote(nom)}%22&fmt=json&limit=5")
    cands = [a for a in (r or {}).get("artists", []) if int(a.get("score", 0)) >= 95 and plat(a.get("name", "")) == plat(nom)]
    if not cands:
        return []
    ca = [a for a in cands if a.get("country") == "CA" or "canada" in plat(json.dumps(a.get("area") or {}))
          or "montreal" in plat(json.dumps(a.get("begin-area") or {}))]
    if len(cands) > 1 and len(ca) != 1:
        return []  # homonymes : on ne devine pas
    art = (ca or cands)[0]
    time.sleep(1.1)  # règle de MusicBrainz : une requête par seconde
    fiche = get_json(f"https://musicbrainz.org/ws/2/artist/{art['id']}?inc=url-rels&fmt=json") or {}
    out = []
    for rel in fiche.get("relations", []):
        url = (rel.get("url") or {}).get("resource", "")
        t = type_lien(url) or ("site" if rel.get("type") == "official homepage" else None)
        if t:
            out.append({"type": t, "url": url, "source": "musicbrainz", "nom": art.get("name", nom)})
    return out[:4]


def bande_annonce_tmdb(titre: str, annee: int, get_json) -> list[dict]:
    cle = os.environ.get("TMDB_API_KEY")
    if not cle:
        return []
    titre = re.sub(r"\(.*?\)|^(gala[^:]*|projection)\s*:\s*", "", titre, flags=re.I).strip()
    r = get_json(f"https://api.themoviedb.org/3/search/movie?api_key={cle}&language=fr-CA&query={quote(titre)}") or {}
    films = [f for f in r.get("results", []) if plat(f.get("title", "")) == plat(titre) or plat(f.get("original_title", "")) == plat(titre)]
    films = [f for f in films if not f.get("release_date") or abs(int(f["release_date"][:4]) - annee) <= 2]
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


def enrichir(events: list[dict], aujourd: date, telecharger, max_recherches: int = 120) -> int:
    """Ajoute e["liens"] (écouter, bande-annonce) et e["affiche"] (image de la page officielle). Renvoie le nombre
    d'événements enrichis. Chaque page et chaque artiste ne sont lus qu'une fois (mémoire)."""
    memo = json.loads(MEMOIRE.read_text(encoding="utf-8")) if MEMOIRE.exists() else {}
    ua_json = lambda url: telecharger(url, "application/json").json()  # noqa: E731
    n, cherches = 0, 0
    vieux = (aujourd - timedelta(days=30)).isoformat()
    for e in events:
        url = e.get("url", "")
        html = None
        # 1. Affiche : page officielle de l'événement (pas les agrégateurs)
        if page_officielle(url):
            pm = memo.get("page:" + url)
            if (not pm or (not pm.get("affiche") and pm["le"] < vieux)) and cherches < max_recherches:
                cherches += 1
                try:
                    html = telecharger(url, "text/html").text
                    pm = memo["page:" + url] = {"affiche": affiche_page(html, url), "le": aujourd.isoformat()}
                except Exception:
                    pm = memo["page:" + url] = {"affiche": None, "le": aujourd.isoformat()}
            if pm and pm.get("affiche") and not e.get("image"):
                e["affiche"] = pm["affiche"]
        # 2. Écouter / bande-annonce
        discs = {e.get("discipline"), *(e.get("aussi") or []), e.get("sous")}
        film = "cinema" in discs
        if not (film or "musique" in discs):
            continue
        noms = [re.sub(r"\(.*?\)", "", e["titre"]).split(" — ")[0].strip()] if film else noms_artistes(e["titre"])
        cle = ("film:" if film else "mus:") + "|".join(plat(x) for x in noms)
        m = memo.get(cle)
        frais = m and (m["liens"] or m["le"] >= vieux)
        if not frais and cherches < max_recherches:
            cherches += 1
            liens = []
            try:
                if page_officielle(url):
                    html = html or telecharger(url, "text/html").text
                    liens += depuis_page(html, url, noms)
            except Exception:
                pass
            try:
                if film:
                    if not any(l["type"] in ("youtube", "vimeo") for l in liens):
                        liens += bande_annonce_tmdb(noms[0], aujourd.year, ua_json)
                else:
                    for nom in noms:
                        if not any(l.get("nom") == nom for l in liens):
                            liens += musicbrainz(nom, ua_json)
                            time.sleep(1.1)
            except Exception as exc:
                print(f"  découverte « {e['titre'][:40]} » : {exc}")
            m = memo[cle] = {"liens": liens[:7], "le": aujourd.isoformat()}
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
