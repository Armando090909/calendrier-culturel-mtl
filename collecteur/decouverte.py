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


def enrichir(events: list[dict], aujourd: date, telecharger, max_recherches: int = 120, max_affiches: int = 600) -> int:
    """Ajoute e["liens"] (écouter, bande-annonce) et e["affiche"] (image de la page officielle). Renvoie le nombre
    d'événements enrichis. Chaque page et chaque artiste ne sont lus qu'une fois (mémoire)."""
    memo = json.loads(MEMOIRE.read_text(encoding="utf-8")) if MEMOIRE.exists() else {}
    ua_json = lambda url: telecharger(url, "application/json").json()  # noqa: E731
    n, cherches = 0, 0
    fin_budget = time.time() + 25 * 60  # au plus 25 minutes par collecte ; la suite reprend le lendemain
    vieux = (aujourd - timedelta(days=30)).isoformat()
    lues_affiche, fin_affiches = 0, time.time() + 12 * 60  # affiches : au plus 12 minutes
    for e in events:
        url = e.get("url", "")
        html = None
        # 1. Affiche : l'image de partage de la page de l'événement (site de la salle, du festival, ou agenda).
        if url.startswith("http") and "facebook.com" not in url:
            pm = memo.get("page:" + url)
            if (not pm or "billets" not in pm or (not pm.get("affiche") and pm["le"] < vieux)) and lues_affiche < max_affiches and time.time() < fin_affiches:
                lues_affiche += 1
                try:
                    html = telecharger(url, "text/html").text
                    pm = memo["page:" + url] = {"affiche": affiche_page(html, url), "billets": billets_page(html, url),
                                                "le": aujourd.isoformat()}
                except Exception:
                    pm = memo["page:" + url] = {"affiche": None, "billets": None, "le": aujourd.isoformat()}
    fin_budget = time.time() + 20 * 60  # liens d'écoute : au plus 20 minutes
    # Une même image pour 3 spectacles différents ou plus, c'est un logo, une image par défaut ou la carte du festival :
    # on l'écarte. (Compté par titre, pas par page : une page de programmation sert à des dizaines de spectacles.)
    titres_par_image: dict[str, set] = {}
    for e in events:
        pm = memo.get("page:" + e.get("url", ""))
        if pm and pm.get("affiche"):
            titres_par_image.setdefault(pm["affiche"]["url"], set()).add(plat(e["titre"])[:30])
    freq = Counter({u: len(t) for u, t in titres_par_image.items()})
    # Un même lien « billets » sur 25 pages ou plus : la page d'accueil de la billetterie, pas celle du spectacle.
    freq_b = Counter(v.get("billets") for k, v in memo.items() if k.startswith("page:") and v.get("billets"))
    for e in events:
        pm = memo.get("page:" + e.get("url", ""))
        if pm and pm.get("affiche") and freq[pm["affiche"]["url"]] < 3 and not e.get("image") \
                and "og.festapp.io" not in pm["affiche"]["url"]:
            e["affiche"] = dict(pm["affiche"], **agrandir(pm["affiche"]["url"]))
        if pm and pm.get("billets") and not e.get("billets") and freq_b[pm["billets"]] < 25:
            e["billets"] = pm["billets"]
    for e in events:
        url = e.get("url", "")
        html = None
        # 2. Écouter / bande-annonce
        discs = {e.get("discipline"), *(e.get("aussi") or []), e.get("sous")}
        film = "cinema" in discs
        if not (film or "musique" in discs):
            continue
        noms = [re.sub(r"\(.*?\)", "", e["titre"]).split(" — ")[0].strip()] if film else noms_artistes(e["titre"])
        cle = ("film:" if film else "mus:") + "|".join(plat(x) for x in noms)
        m = memo.get(cle)
        frais = m and (m["liens"] or m["le"] >= vieux)
        if not frais and cherches < max_recherches and time.time() < fin_budget:
            cherches += 1
            liens = []
            try:
                # La page de l'événement, même sur un agenda (Sors-tu?, ma.to…) : seuls les liens qui portent
                # le nom de l'artiste sont gardés.
                if url.startswith("http") and "songkick.com" not in url:
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
                        if not any(l.get("nom") == nom or l["source"] == "page" for l in liens):
                            try:
                                liens += bandcamp(nom, lambda u: telecharger(u, "text/html").text)
                            except Exception:
                                pass
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
