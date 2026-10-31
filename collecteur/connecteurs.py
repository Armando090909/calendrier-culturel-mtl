"""Connecteurs : chacun lit une source et renvoie des événements « bruts » (dicts) et des séries.

Format brut d'un événement :
  titre, date (AAAA-MM-JJ), heure (HH:MM ou None), lieu, adresse, ville, url, categorie,
  discipline (optionnelle), complet, annule, jeune_public, source
Format d'une série (exposition ou pièce « à l'affiche ») :
  titre, lieu, adresse, ville, debut, fin, discipline, url, source
"""
from __future__ import annotations

import hashlib
import atexit
import csv
import io
import json
import re
from pathlib import Path
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

import ia
from ics import parse_ics
from normalisation import PAS_DES_SALLES, plat

MTL = ZoneInfo("America/Toronto")
# Format habituel des robots (« Mozilla/5.0 (compatible; Nom/version; +site) ») : certains sites refusent les autres.
UA = "Mozilla/5.0 (compatible; CalendrierCulturelMTL/1.0; +https://ccmtl.ca; projet bénévole sans but lucratif)"
MOIS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre",
           "novembre", "decembre"]
MOIS_EN = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
           "november", "december"]


# robots.txt de chaque site. Mode « observer » (par défaut) : on note les pages que le site demande aux robots de ne pas
# lire (rapport : notes.robots_refus) ; mode « respecter » (ROBOTS_MODE=respecter) : on ne les lit pas.
_ROBOTS: dict = {}
ROBOTS_REFUS: dict[str, int] = {}


def robots_permet(url: str) -> bool:
    from urllib.robotparser import RobotFileParser
    u = urlparse(url)
    hote = f"{u.scheme}://{u.netloc}"
    if hote not in _ROBOTS:
        rp = None
        try:
            r = requests.get(hote + "/robots.txt", timeout=10, headers={"User-Agent": UA})
            if r.status_code == 200 and "text" in r.headers.get("Content-Type", "text"):
                rp = RobotFileParser()
                rp.parse(r.text.splitlines())
        except Exception:
            rp = None
        _ROBOTS[hote] = rp
    rp = _ROBOTS[hote]
    return rp is None or rp.can_fetch("CalendrierCulturelMTL", url)


def telecharger(url: str, accept: str = "*/*") -> requests.Response:
    import os
    if not robots_permet(url):
        cle = urlparse(url).netloc + urlparse(url).path[:40]
        ROBOTS_REFUS[cle] = ROBOTS_REFUS.get(cle, 0) + 1
        if os.environ.get("ROBOTS_MODE") == "respecter":
            raise PermissionError(f"robots.txt du site : lecture non souhaitée ({url})")
    r = requests.get(url, timeout=40, headers={"User-Agent": UA, "Accept": accept, "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.5"})
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r


def brut(**kw) -> dict:
    base = dict(titre="", date="", heure=None, lieu="", adresse="", ville="", url="", categorie="",
                discipline="", complet=False, annule=False, jeune_public=False, source="",
                description="", prix="", billets="", image="", aussi=[])
    base.update({k: v for k, v in kw.items() if v is not None})
    base["titre"] = re.sub(r"\s+", " ", str(base["titre"])).strip()
    return base


def _heure(dt) -> str | None:
    if isinstance(dt, datetime):
        h = dt.astimezone(MTL) if dt.tzinfo else dt
        return None if (h.hour, h.minute) == (0, 0) else f"{h.hour:02d}:{h.minute:02d}"
    return None


def _jour(dt) -> date:
    if isinstance(dt, datetime):
        return (dt.astimezone(MTL) if dt.tzinfo else dt).date()
    return dt


def _iso(s: str):
    """Date/heure ISO tolérante : '2026-10-28', '2026-10-28 19:30:00', '2026-10-28T19:30:00-04:00'."""
    s = (s or "").strip().replace("Z", "+00:00")
    if not s:
        return None
    try:
        if len(s) == 10:
            return date.fromisoformat(s)
        dt = datetime.fromisoformat(s.replace(" ", "T", 1))
        return dt.astimezone(MTL) if dt.tzinfo else dt.replace(tzinfo=MTL)
    except ValueError:
        return None


# ---------------------------------------------------------------- Ville de Montréal (CSV ouvert)
DIAG: list[str] = []  # remarques pour le rapport de collecte (raisons d'un résultat vide, colonnes lues…)


def _col(row: dict, *noms: str) -> str:
    cles = {plat(k): k for k in row}
    for n in noms:
        k = cles.get(plat(n))
        if k is not None and row[k] and str(row[k]).strip().lower() not in ("nan", "none", "null", "n/a", "-"):
            return str(row[k]).strip()
    return ""


def ville_csv(cfg: dict, debut: date, fin: date, **_) -> tuple[list, list]:
    r = telecharger(cfg["url"], "text/csv")
    texte = r.content.decode("utf-8-sig", errors="replace")
    lecteur = csv.DictReader(io.StringIO(texte))
    print(f"  colonnes : {lecteur.fieldnames}")
    DIAG.append(f"colonnes du fichier : {', '.join(lecteur.fieldnames or [])}"[:600])
    evs, series = [], []
    for row in lecteur:
        titre = _col(row, "titre", "title", "nom")
        d1 = _iso(_col(row, "date_debut", "debut", "date_de_debut", "start_date", "date"))
        d2 = _iso(_col(row, "date_fin", "fin", "date_de_fin", "end_date")) or d1
        if not titre or d1 is None:
            continue
        # « emplacement » = En salle / À l'extérieur / En ligne (pas un nom de salle) ; le nom est dans « titre_adresse »
        emplacement = plat(_col(row, "emplacement"))
        if emplacement == "en ligne":
            continue  # activité en ligne : pas une sortie
        lieu = _col(row, "titre_adresse", "lieu", "nom_lieu", "nom_emplacement", "lieu_nom", "titre_lieu",
                    "nom_du_lieu", "installation", "nom_installation")
        if plat(lieu) == "en ligne":
            continue
        if plat(lieu) in PAS_DES_SALLES:  # « En salle », « À l'extérieur » : pas un nom de salle (vu le 28 oct. 2026)
            lieu = ""
        lat, lon = _col(row, "lat", "latitude", "y"), _col(row, "long", "lon", "longitude", "x")
        if not lieu and re.fullmatch(r"-?\d+\.\d+", lat or "") and re.fullmatch(r"-?\d+\.\d+", lon or ""):
            lieu = f"@{lat},{lon}"  # pas de nom : la collecte cherche la salle connue la plus proche
        adresse = _col(row, "adresse_principale", "adresse", "address")
        typ = _col(row, "type_evenement", "type", "categorie")
        url = _col(row, "url_fiche", "url", "lien")
        statut = plat(_col(row, "statut", "etat", "status"))
        annule = any(m in statut for m in ["annule", "reporte"]) or bool(re.search(r"\((annul|report)", titre, re.I))
        complet = "complet" in statut or "(complet)" in titre.lower()
        titre = re.sub(r"\s*\((complet|annul[ée]+|report[ée]+)\)\s*", " ", titre, flags=re.I).strip()
        j1, j2 = _jour(d1), _jour(d2)
        if j2 < debut or j1 > fin:
            continue
        duree = (j2 - j1).days
        if duree >= 2:
            if "expos" in plat(typ + " " + titre) or "art public" in plat(typ):
                series.append(dict(titre=titre, lieu=lieu, adresse=adresse, ville="Montréal", debut=j1.isoformat(),
                                   fin=j2.isoformat(), discipline="expo", url=url, source="ville"))
            continue  # longues séries de cours, etc. : ignorées
        evs.append(brut(titre=titre, date=j1.isoformat(), heure=_heure(d1), lieu=lieu, adresse=adresse,
                        ville="Montréal", url=url, categorie=typ, complet=complet, annule=annule,
                        jeune_public=bool(re.search(r"\b\d+\s*(à|-)\s*\d+\s*ans\b|enfant|famille|0-5|tout-petits",
                                                    titre + " " + _col(row, "public_cible"), re.I)),
                        description=_col(row, "description", "resume", "description_courte"),
                        prix=_col(row, "cout", "coût", "prix", "tarif"), source="ville"))
    return evs, series


# ---------------------------------------------------------------- Calendriers iCal
def url_calendrier(url: str) -> str:
    """Accepte webcal://, un lien Google Agenda « intégrer » ou « partager », ou un lien .ics direct."""
    url = url.strip()
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    p = urlparse(url)
    if "calendar.google.com" in p.netloc and "/ical/" not in p.path:
        q = parse_qs(p.query)
        cid = (q.get("src") or q.get("cid") or [""])[0]
        if cid:
            return f"https://calendar.google.com/calendar/ical/{requests.utils.quote(cid, safe='')}/public/basic.ics"
    return url


def ics(cfg: dict, debut: date, fin: date, **_) -> tuple[list, list]:
    texte = telecharger(url_calendrier(cfg["url"]), "text/calendar").text
    return _depuis_ics(texte, cfg, debut, fin), []


def _depuis_ics(texte: str, cfg: dict, debut: date, fin: date) -> list:
    out = []
    for e in parse_ics(texte, debut, fin):
        jour = _jour(e["debut"])
        if jour < debut or jour > fin:
            continue
        lieu = cfg.get("lieu") or (e["lieu"].split(",")[0] if e["lieu"] else "")
        out.append(brut(titre=e["titre"], date=jour.isoformat(), heure=None if e["journee"] else _heure(e["debut"]),
                        lieu=lieu, adresse=cfg.get("adresse") or e["lieu"], ville="",
                        url=e["url"] or cfg.get("page", "") or "", categorie=cfg.get("categorie", ""),
                        discipline=cfg.get("discipline", ""), annule=e["annule"], description=e["description"],
                        source=cfg.get("cle_source", "calendrier")))
    return out


# ---------------------------------------------------------------- Données structurées schema.org (JSON-LD)
TYPES_EVENT = {"event", "musicevent", "theaterevent", "danceevent", "comedyevent", "screeningevent",
               "exhibitionevent", "festival", "socialevent", "visualartsevent", "literaryevent", "childrensevent"}


def _objets_jsonld(html: str):
    soupe = BeautifulSoup(html, "html.parser")
    for s in soupe.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(s.string or s.get_text() or "")
        except (json.JSONDecodeError, TypeError):
            continue
        # Index des objets nommés par « @id » : un lieu peut être décrit une fois et seulement référencé ailleurs
        ids, pile = {}, [data]
        while pile:
            o = pile.pop()
            if isinstance(o, list):
                pile.extend(o)
            elif isinstance(o, dict):
                if o.get("@id") and len(o) > 1:
                    ids.setdefault(o["@id"], o)
                pile.extend(v for v in o.values() if isinstance(v, (dict, list)))

        def resoudre(x):
            if isinstance(x, dict) and set(x) <= {"@id", "@type"} and x.get("@id") in ids:
                return ids[x["@id"]]
            if isinstance(x, str) and x in ids:
                return ids[x]
            return x

        pile = [data]
        while pile:
            o = pile.pop()
            if isinstance(o, list):
                pile.extend(o)
            elif isinstance(o, dict):
                t = o.get("@type")
                types = {plat(x).replace(" ", "") for x in (t if isinstance(t, list) else [t]) if x}
                if types & TYPES_EVENT:
                    if "location" in o:
                        loc = o["location"]
                        o["location"] = [resoudre(x) for x in loc] if isinstance(loc, list) else resoudre(loc)
                    yield o
                for k in ("@graph", "itemListElement", "item", "subEvent", "event", "events"):
                    if k in o:
                        enfants = o[k]
                        # séances d'un festival : elles héritent du lieu de l'événement parent s'il n'en ont pas
                        if k in ("subEvent", "event", "events") and o.get("location"):
                            for c in (enfants if isinstance(enfants, list) else [enfants]):
                                if isinstance(c, dict) and not c.get("location"):
                                    c["location"] = o["location"]
                        pile.append(enfants)


def evenements_jsonld(html: str, page_url: str, cfg: dict, debut: date, fin: date) -> tuple[list, list]:
    evs, series = [], []
    for o in _objets_jsonld(html):
        d1, d2 = _iso(str(o.get("startDate", ""))), _iso(str(o.get("endDate", "")))
        if d1 is None:
            continue
        loc = o.get("location") or {}
        if isinstance(loc, list):
            loc = loc[0] if loc else {}
        lieu = loc.get("name", "") if isinstance(loc, dict) else str(loc)
        adr = loc.get("address", "") if isinstance(loc, dict) else ""
        if isinstance(adr, dict):
            ville = adr.get("addressLocality", "")
            adr = " ".join(str(adr.get(k, "")) for k in ("streetAddress", "addressLocality")).strip()
        else:
            ville = ""
        statut = plat(str(o.get("eventStatus", "")))
        url = urljoin(page_url, o.get("url") or "") or page_url
        j1 = _jour(d1)
        j2 = _jour(d2) if d2 else j1
        titre = o.get("name", "")
        if (j2 - j1).days >= 2 and _heure(d1) is None:
            if j2 >= debut and j1 <= fin:
                series.append(dict(titre=titre, lieu=cfg.get("lieu") or lieu, adresse=adr, ville=ville,
                                   debut=j1.isoformat(), fin=j2.isoformat(), discipline=cfg.get("discipline") or "autre",
                                   url=url, source=cfg.get("cle_source", "calendrier")))
            continue
        if j1 < debut or j1 > fin:
            continue
        offres = o.get("offers") or {}
        if isinstance(offres, list):
            offres = offres[0] if offres else {}
        if not isinstance(offres, dict):
            offres = {}
        dispo = plat(str(offres.get("availability", "")))
        prix = ""
        if offres.get("price") not in (None, ""):
            p = str(offres.get("price"))
            prix = "Gratuit" if p in ("0", "0.0", "0.00") else f'{p} $'
        img = o.get("image") or ""
        if isinstance(img, list):
            img = img[0] if img else ""
        if isinstance(img, dict):
            img = img.get("url", "")
        evs.append(brut(titre=titre, date=j1.isoformat(), heure=_heure(d1), lieu=cfg.get("lieu") or lieu,
                        adresse=adr, ville=ville, url=url, categorie=str(o.get("@type", "")),
                        discipline=cfg.get("discipline", ""), annule="cancel" in statut or "postpon" in statut,
                        complet="soldout" in dispo.replace(" ", ""), description=str(o.get("description") or ""),
                        prix=prix, billets=urljoin(page_url, offres.get("url") or "") if offres.get("url") else "",
                        image=urljoin(page_url, str(img)) if img else "", source=cfg.get("cle_source", "calendrier")))
    return evs, series


def jsonld(cfg: dict, debut: date, fin: date, **_) -> tuple[list, list]:
    html = telecharger(cfg["url"], "text/html").text
    return evenements_jsonld(html, cfg["url"], cfg, debut, fin)


# ---------------------------------------------------------------- Gancio (ex. Ask A Punk)
def gancio(cfg: dict, debut: date, fin: date, **_) -> tuple[list, list]:
    base = cfg["url"].rstrip("/")
    t1 = int(datetime.combine(debut, datetime.min.time(), MTL).timestamp())
    t2 = int(datetime.combine(fin + timedelta(days=1), datetime.min.time(), MTL).timestamp())
    data = telecharger(f"{base}/api/events?start={t1}&end={t2}&show_recurrent=true", "application/json").json()
    return evenements_gancio(data, base, cfg), []


def evenements_gancio(data: list, base: str, cfg: dict) -> list:
    out = []
    for e in data if isinstance(data, list) else []:
        ts = e.get("start_datetime")
        if not ts:
            continue
        dt = datetime.fromtimestamp(int(ts), MTL)
        place = e.get("place") or {}
        out.append(brut(titre=e.get("title", ""), date=dt.date().isoformat(), heure=f"{dt.hour:02d}:{dt.minute:02d}",
                        lieu=place.get("name", ""), adresse=place.get("address", ""), ville="",
                        url=f'{base}/event/{e.get("slug") or e.get("id")}',
                        categorie=" ".join(str(t) for t in e.get("tags", []) if isinstance(t, str)),
                        discipline=cfg.get("discipline", "musique"),
                        description=BeautifulSoup(e.get("description") or "", "html.parser").get_text(" ", strip=True),
                        source=cfg.get("cle_source", "askapunk")))
    return out


# ---------------------------------------------------------------- Pages ordinaires (lecture par l'IA)
def texte_page(html: str, base_url: str) -> str:
    soupe = BeautifulSoup(html, "html.parser")
    for tag in soupe(["script", "style", "noscript", "svg", "iframe", "header", "footer", "form"]):
        tag.decompose()
    for a in soupe.find_all("a", href=True):
        t = a.get_text(" ", strip=True)
        if t:
            a.replace_with(f"{t} <{urljoin(base_url, a['href'])}>")
    texte = soupe.get_text("\n")
    texte = re.sub(r"[ \t]+", " ", texte)
    return re.sub(r"\n\s*\n+", "\n", texte).strip()


def urls_modele(cfg: dict, debut: date, fin: date) -> list[str]:
    """Développe {jour} {mois_fr} {month_en} {annee} {page} selon cfg['repeter'] : jour | mois | (rien)."""
    modele = cfg["url"]
    rep = cfg.get("repeter")
    urls = []
    if rep == "jour":
        n = min(int(cfg.get("jours", 14)), (fin - debut).days + 1)
        for i in range(n):
            d = debut + timedelta(days=i)
            urls.append(modele.format(jour=d.day, mois_fr=MOIS_FR[d.month - 1], month_en=MOIS_EN[d.month - 1],
                                      annee=d.year, page=1))
    elif rep == "mois":
        d = debut.replace(day=1)
        for _ in range(int(cfg.get("mois", 2))):
            for p in range(1, int(cfg.get("pages", 1)) + 1):
                urls.append(modele.format(jour=1, mois_fr=MOIS_FR[d.month - 1], month_en=MOIS_EN[d.month - 1],
                                          annee=d.year, page=p))
            d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        urls.append(modele)
    return list(dict.fromkeys(urls))


# ---- Mémoire des pages déjà lues par l'IA : une page dont le texte n'a pas changé n'est pas relue (gratuit).
EMPREINTES = Path(__file__).parent / "cache" / "empreintes.json"
_memoire: dict | None = None


def _mem() -> dict:
    global _memoire
    if _memoire is None:
        try:
            _memoire = json.loads(EMPREINTES.read_text(encoding="utf-8"))
        except Exception:
            _memoire = {}
    return _memoire


def sauver_memoire(aujourd: date) -> None:
    """Garde les lectures des 45 derniers jours."""
    if _memoire is None:
        return
    limite = (aujourd - timedelta(days=45)).isoformat()
    garde = {k: v for k, v in _memoire.items() if v.get("vu", "") >= limite}
    EMPREINTES.parent.mkdir(exist_ok=True)
    EMPREINTES.write_text(json.dumps(garde, ensure_ascii=False), encoding="utf-8")


def extraire_avec_memoire(url: str, texte: str, debut: date, fin: date) -> dict:
    cle = hashlib.sha1((url + "\n" + texte).encode()).hexdigest()
    m = _mem().get(cle)
    if m and m.get("debut", "") <= debut.isoformat() and m.get("fin", "") >= (fin - timedelta(days=14)).isoformat():
        m["vu"] = date.today().isoformat()
        return m["data"]
    data = ia.extraire_page(url, texte, debut.isoformat(), fin.isoformat())
    _mem()[cle] = {"data": data, "debut": debut.isoformat(), "fin": fin.isoformat(), "vu": date.today().isoformat()}
    return data


NAV_AUTO = ("zeffy.com",)  # plateformes toujours en JavaScript : navigateur d'office, même pour les festivals
_NAV = {}  # navigateur partagé par toutes les pages d'une collecte


def page_rendue(url: str, attente_ms: int = 2500) -> str:
    """HTML d'une page après exécution de son JavaScript, dans Chrome sans fenêtre (Playwright).
    Le même nom de robot que pour les autres téléchargements. Les images, polices et vidéos ne sont pas chargées."""
    if "page" not in _NAV:
        from playwright.sync_api import sync_playwright  # importé seulement si une source en a besoin
        _NAV["pw"] = sync_playwright().start()
        _NAV["nav"] = _NAV["pw"].chromium.launch()
        ctx = _NAV["nav"].new_context(user_agent=UA, locale="fr-CA", viewport={"width": 1280, "height": 2000})
        ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image", "media", "font") else r.continue_())
        _NAV["page"] = ctx.new_page()
        atexit.register(fermer_navigateur)
    page = _NAV["page"]
    rep = page.goto(url, wait_until="domcontentloaded", timeout=45000)
    if rep is not None and rep.status >= 400:
        raise RuntimeError(f"{rep.status} {rep.status_text} (navigateur)")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass  # certains sites ne se calment jamais (publicité, sondages) : on lit quand même
    for _ in range(3):  # listes chargées au défilement
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(500)
    page.wait_for_timeout(attente_ms)
    html = page.content()
    # Beaucoup de sites (Wix, Squarespace, billetteries intégrées) affichent leur calendrier dans un cadre (iframe) :
    # on ajoute le contenu de chaque cadre à la page.
    for cadre in page.frames[1:]:
        try:
            html += "\n<section data-cadre>" + cadre.content() + "</section>"
        except Exception:
            pass
    return html


def fermer_navigateur() -> None:
    try:
        if "nav" in _NAV:
            _NAV["nav"].close()
            _NAV["pw"].stop()
    except Exception:
        pass
    _NAV.clear()


_MOTS_SALLE = re.compile(r"(?i)\||cin[ée]ma|cineplex|cin[ée]math[èe]que|salle|th[ée][âa]tre|mus[ée]e|centre|onf\b|auditorium|"
                         r"biblioth[èe]que|espace|studio|maison|place des arts|chapelle|église|eglise|cabaret|bar\b")


def lieux_par_texte(html: str, evs: list[dict]) -> int:
    """Salle de chaque séance lue dans le texte affiché : « Titre / 14:00 – 16:05 / Cineplex Quartier Latin | Salle 10 ».
    Les séances d'un même titre reçoivent leurs salles dans l'ordre de la page (seulement si le nombre concorde,
    ou si toutes les séances de ce titre ont la même salle)."""
    lignes = [l.strip() for l in BeautifulSoup(html, "html.parser").get_text("\n").splitlines() if l.strip()]
    vues: dict[str, list] = {}
    for i, l in enumerate(lignes):
        cle = plat(l)
        if len(cle) < 3:
            continue
        for j in range(i + 1, min(i + 8, len(lignes))):
            if re.match(r"^\d{1,2}[:h]\d{2}", lignes[j]):
                for k in range(j + 1, min(j + 4, len(lignes))):
                    if _MOTS_SALLE.search(lignes[k]) and len(lignes[k]) < 90 and not re.match(r"^\d{1,2}[:h]\d{2}", lignes[k]):
                        vues.setdefault(cle, []).append(re.sub(r"\s*-\s*Montr[ée]al$", "", lignes[k].split("|")[0]).strip())
                        break
                break
    n = 0
    par_titre: dict[str, list] = {}
    for e in sorted(evs, key=lambda x: (x["date"], x["heure"] or "")):
        par_titre.setdefault(plat(e["titre"]), []).append(e)
    for t, groupe in par_titre.items():
        salles = vues.get(t, [])
        if not salles:
            continue
        if len(set(salles)) == 1:
            choix = [salles[0]] * len(groupe)
        elif len(salles) == len(groupe):
            choix = salles
        else:
            continue
        for e, salle in zip(groupe, choix):
            if not e["lieu"]:
                e["lieu"] = salle
                n += 1
    return n


def page_ia(cfg: dict, debut: date, fin: date, **_) -> tuple[list, list]:
    if not ia.disponible():
        print("  (sautée : pas de clé ANTHROPIC_API_KEY)")
        return [], []
    evs, series = [], []
    pages = list(urls_modele(cfg, debut, fin))
    vues, suivis = set(pages), set()
    for url in pages:
        try:
            # « navigateur: true » : site en JavaScript ; un vrai navigateur (Chrome invisible) affiche la page d'abord.
            # Les liens suivis (« details ») restent lus normalement, sauf s'ils sont du même site en JavaScript.
            avec_nav = cfg.get("navigateur") or any(d in url for d in NAV_AUTO)
            html = page_rendue(url) if avec_nav else telecharger(url, "text/html").text
        except Exception as exc:
            print(f"  page illisible {url} : {exc}")
            DIAG.append(f"page illisible ({str(exc)[:80]}) : {url}")
            continue
        # Données structurées présentes ? On les préfère (gratuites et exactes).
        e2, s2 = evenements_jsonld(html, url, dict(cfg, cle_source=cfg["cle_source"]), debut, fin)
        if e2 and "festapp.io" in url and sum(1 for e in e2 if not e["lieu"]) > len(e2) / 3:
            try:  # FestApp : la salle de chaque séance n'est affichée que dans la page rendue
                n = lieux_par_texte(page_rendue(url) if not avec_nav else html, e2)
                DIAG.append(f"FestApp : salle retrouvée pour {n} séances sur {len(e2)}")
            except Exception as exc:
                DIAG.append(f"FestApp : salles illisibles ({str(exc)[:60]})")
        if e2 and not cfg.get("toujours_ia"):
            evs += e2
            series += s2
            continue
        texte = texte_page(html, url)
        try:
            data = extraire_avec_memoire(url, texte, debut, fin)
        except Exception as exc:
            print(f"  IA en échec pour {url} : {exc}")
            DIAG.append(f"IA en échec ({str(exc)[:80]}) : {url}")
            continue
        if not data["evenements"] and not data["series"] and url not in suivis:
            DIAG.append(f"page presque vide ({len(texte)} caractères ; site en JavaScript ?) : {url}" if len(texte) < 600
                        else f"aucun événement trouvé dans {len(texte)} caractères de texte : {url}")
        # « details » : une page de programmation qui ne donne pas les heures → on lit la page de chaque spectacle
        if cfg.get("details") and url not in suivis:
            hote = urlparse(url).netloc
            liens = {e.get("url") for e in data["evenements"]} | {s.get("url") for s in data["series"]}
            nouveaux = [l for l in liens if l and l not in vues and urlparse(l).netloc == hote][:int(cfg.get("max_details", 40))]
            if nouveaux:
                vues.update(nouveaux)
                suivis.update(nouveaux)
                pages += nouveaux
                data["evenements"] = [e for e in data["evenements"] if e.get("url") not in nouveaux]
                data["series"] = [s for s in data["series"] if s.get("url") not in nouveaux]
        for e in data["evenements"]:
            if not e.get("titre") or not e.get("date"):
                continue
            evs.append(brut(titre=e.get("titre"), date=str(e.get("date"))[:10], heure=e.get("heure") or None,
                            lieu=e.get("lieu") or cfg.get("lieu", ""), ville=e.get("ville") or "",
                            url=e.get("url") or url, categorie=e.get("categorie") or "",
                            discipline=(e.get("discipline") if e.get("discipline") not in (None, "", "autre") else None)
                            or cfg.get("discipline", "") or e.get("discipline") or "",
                            complet=bool(e.get("complet")), annule=bool(e.get("annule")),
                            jeune_public=bool(e.get("jeune_public")), description=e.get("resume") or "",
                            prix=e.get("prix") or "", billets=e.get("billets") or "", source=cfg["cle_source"]))
        for s in data["series"]:
            if s.get("titre") and s.get("debut") and s.get("fin"):
                series.append(dict(titre=s["titre"], lieu=s.get("lieu") or cfg.get("lieu", ""), adresse="",
                                   ville=s.get("ville") or "", debut=str(s["debut"])[:10], fin=str(s["fin"])[:10],
                                   discipline=s.get("discipline") or "autre", url=s.get("url") or url,
                                   resume=s.get("resume") or "", prix=s.get("prix") or "", billets=s.get("billets") or "",
                                   source=cfg["cle_source"]))
    if cfg.get("garder"):  # page générale : on ne garde que les titres qui correspondent (ex. « quiz|trivia »)
        evs = [e for e in evs if re.search(cfg["garder"], e["titre"] + " " + e.get("description", ""), re.I)]
        series = [x for x in series if re.search(cfg["garder"], x["titre"], re.I)]
    return evs, series


def resume_page(html: str) -> str:
    """Description courte d'une page d'événement : balises meta, puis titre et premiers paragraphes."""
    soupe = BeautifulSoup(html, "html.parser")
    morceaux = []
    for attrs in ({"name": "description"}, {"property": "og:description"}, {"name": "twitter:description"}):
        m = soupe.find("meta", attrs=attrs)
        if m and m.get("content"):
            morceaux.append(m["content"])
    for tag in soupe.find_all(["h1", "h2", "p"])[:12]:
        t = tag.get_text(" ", strip=True)
        if len(t) > 20:
            morceaux.append(t)
    return " ".join(dict.fromkeys(morceaux))[:1500]


_H = r"(\d{1,2})\s*(?:h|:)\s*(\d{2})?\b|(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s?m\b"
_MOTS_SHOW = r"(?:show|spectacle|concert|d[ée]but|start(?:s|ing)?(?: at)?|showtime|heure|à)"
_MOTS_PORTES = r"(?:doors?|portes?|ouverture)"


def _hhmm(m) -> str | None:
    if m.group(1):
        h, mi = int(m.group(1)), int(m.group(2) or 0)
    else:
        h, mi = int(m.group(3)), int(m.group(4) or 0)
        if m.group(5).lower() == "p" and h < 12:
            h += 12
        if m.group(5).lower() == "a" and h == 12:
            h = 0
    if not (0 <= h <= 23 and 0 <= mi <= 59) or (h, mi) == (0, 0):
        return None
    return f"{h:02d}:{mi:02d}"


_MOIS_EN = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
            "november", "december"]


def _heure_du_jour(texte: str, jour: str) -> str | None:
    """Heure écrite juste après la date du spectacle : « mardi 3 novembre 2026 · 19 h 30 », « Nov 3, 2026 – 7:30 PM »,
    « 2026-11-03 19:30 ». Utile sur les pages qui listent plusieurs représentations."""
    a, m, j = (int(x) for x in jour.split("-"))
    t = plat(texte)
    motifs = [rf"\b{j}(?:er)? {_MOIS[m - 1]}(?: {a})?", rf"\b{_MOIS_EN[m - 1]} {j}(?:st|nd|rd|th)?(?: {a})?",
              rf"\b{_MOIS_EN[m - 1][:3]} {j}\b(?: {a})?", rf"\b{j} {_MOIS_EN[m - 1][:3]}\w*(?: {a})?",
              rf"\b{a} {m:02d} {j:02d}\b", rf"\b{j:02d} {m:02d} {a}\b"]
    for motif in motifs:
        for d in re.finditer(motif, t):
            suite = t[d.end():d.end() + 70]
            h = re.search(r"\b(\d{1,2}) ?h ?(\d{2})?\b|\b(\d{1,2}) (\d{2}) ?([ap]) ?m\b|\b(\d{1,2}) ?([ap]) ?m\b|\b(\d{1,2}) (\d{2})\b", suite)
            if not h:
                continue
            g = h.groups()
            if g[0]:
                hh, mm = int(g[0]), int(g[1] or 0)
            elif g[2]:
                hh, mm = int(g[2]) % 12 + (12 if g[4] == "p" else 0), int(g[3])
            elif g[5]:
                hh, mm = int(g[5]) % 12 + (12 if g[6] == "p" else 0), 0
            else:
                hh, mm = int(g[7]), int(g[8])
            if 9 <= hh <= 23 and mm < 60:
                return f"{hh:02d}:{mm:02d}"
    return None


def heure_page(html: str, jour: str | None = None) -> str | None:
    """Heure du spectacle lue sur la page d'un événement : données schema.org d'abord (la représentation du bon jour
    s'il y en a plusieurs), puis l'heure écrite après la date, puis le texte (« spectacle à 20 h 30 », « show 8pm » ;
    à défaut, l'ouverture des portes)."""
    heures = []
    for o in _objets_jsonld(html):
        sd = str(o.get("startDate") or "")
        m = re.search(r"T(\d{2}):(\d{2})", sd)
        if m and (m.group(1), m.group(2)) != ("00", "00"):
            heures.append((sd[:10], f"{m.group(1)}:{m.group(2)}"))
    if jour and any(d == jour for d, _ in heures):
        return next(h for d, h in heures if d == jour)
    if heures and (not jour or len({d for d, _ in heures}) == 1):
        return heures[0][1]
    texte = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    if jour:
        h = _heure_du_jour(texte, jour)
        if h:
            return h
    for mots in (_MOTS_SHOW, _MOTS_PORTES):
        for m in re.finditer(mots + r"\W{0,4}(?:\w+\W+){0,3}?(?:" + _H + ")", texte, re.I):
            h = _hhmm(re.search(_H, m.group(0)[len(re.match(mots, m.group(0), re.I).group(0)):], re.I))
            if h and h >= "10:00":
                return h
    return None


# ---------------------------------------------------------------- Lien soumis par une salle : détection automatique
def auto(cfg: dict, debut: date, fin: date, **_) -> tuple[list, list]:
    url = url_calendrier(cfg["url"])
    r = telecharger(url)
    texte = r.text
    if "BEGIN:VCALENDAR" in texte[:2000]:
        print("  format détecté : iCal")
        return _depuis_ics(texte, cfg, debut, fin), []
    if "<" in texte[:500]:
        e, s = evenements_jsonld(texte, url, cfg, debut, fin)
        if e or s:
            print("  format détecté : données structurées (schema.org)")
            return e, s
        print("  format détecté : page ordinaire" + (" → lecture par l'IA" if ia.disponible() else " (ignorée sans clé IA)"))
        return page_ia(dict(cfg, url=url, repeter=None), debut, fin)
    print("  format non reconnu")
    return [], []


# ---------------------------------------------------------------- Formulaires (Google Forms → feuille publiée en CSV)
def _lire_csv(url: str) -> list[dict]:
    texte = telecharger(url, "text/csv").content.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(texte)))


def _champ(row: dict, *mots: str) -> str:
    """Valeur de la première colonne dont l'intitulé contient le premier mot trouvé (dans l'ordre des mots)."""
    cles = [k for k in row if k and not any(x in plat(k) for x in ("horodat", "timestamp", "courriel", "email"))]
    for m in mots:
        for k in cles:
            if m in plat(k):
                return (row[k] or "").strip()
    return ""


def _approuve(row: dict) -> bool:
    return plat(_champ(row, "approuve", "approved", "valide")) in {"oui", "o", "yes", "y", "x", "1", "ok", "vrai", "true"}


def _refuse(row: dict) -> bool:
    return plat(_champ(row, "approuve", "approved", "valide")) in {"non", "n", "no", "0", "faux", "false"}


# Tri automatique des propositions du public (colonne « Approuvé » vide) : décisions gardées d'une collecte à l'autre
F_MODERATION = Path(__file__).parent / "cache" / "moderation.json"
MODERATION: list[dict] = []  # pour le rapport de collecte
FORMULAIRE_RESUME: dict = {}


def _image_formulaire(url: str) -> str:
    """Lien « image » du formulaire → adresse d'une vraie image affichable, ou "" (on prendra alors l'image de la page
    de l'événement). Facebook et Instagram ne sont pas lisibles par un robot, et leurs liens d'images expirent."""
    url = (url or "").strip()
    if not url.startswith("http"):
        return ""
    hote = urlparse(url).netloc.lower()
    if any(h in hote for h in ("facebook.com", "fb.com", "fb.me", "fbcdn.net", "instagram.com", "cdninstagram.com")):
        return ""
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?(?:export=\w+&)?id=)([\w-]{20,})", url)
    if m:  # Google Drive (fichier partagé « tous les utilisateurs disposant du lien »)
        url = f"https://drive.google.com/thumbnail?id={m.group(1)}&sz=w1200"
    if "dropbox.com" in hote:
        url = re.sub(r"([?&])dl=0", r"\1raw=1", url) if "dl=0" in url else url + ("&" if "?" in url else "?") + "raw=1"
    try:
        r = telecharger(url, "image/*,text/html;q=0.8")
        typ = r.headers.get("Content-Type", "").lower()
        if typ.startswith("image/"):
            return url
        if "html" in typ:  # une page : on prend son image de partage
            from decouverte import affiche_page
            a = affiche_page(r.text, url)
            return (a or {}).get("url", "")
    except Exception:
        pass
    return ""


def _cle_proposition(row: dict) -> str:
    t = "|".join(_champ(row, k) for k in ("horodateur", "titre", "date", "lieu"))
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:16]


def _moderer(rows: list[dict]) -> dict[str, bool]:
    """Décision automatique pour les lignes non tranchées par la personne responsable. Sans IA : rien n'est publié."""
    memo = json.loads(F_MODERATION.read_text(encoding="utf-8")) if F_MODERATION.exists() else {}
    a_juger = [r for r in rows if _cle_proposition(r) not in memo]
    nouveaux: set[str] = set()
    if a_juger and ia.disponible():
        champs = ("titre", "date", "heure", "lieu", "adresse", "discipline", "lien", "description", "prix", "billetterie", "image")
        try:
            rep = ia.moderer_lot([{k: _champ(r, k)[:600] for k in champs} for r in a_juger])
            for i, r in enumerate(a_juger):
                if i in rep:
                    memo[_cle_proposition(r)] = {"publier": rep[i][0], "raison": rep[i][1], "titre": _champ(r, "titre")[:120]}
                    nouveaux.add(_cle_proposition(r))
            F_MODERATION.parent.mkdir(exist_ok=True)
            F_MODERATION.write_text(json.dumps(memo, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as exc:
            print(f"  tri automatique en échec : {exc}")
    out = {}
    for r in rows:
        d = memo.get(_cle_proposition(r))
        out[_cle_proposition(r)] = bool(d and d["publier"])
        MODERATION.append({"titre": _champ(r, "titre")[:120], "decision": ("publié" if d["publier"] else "mis de côté") if d else "en attente",
                           "raison": d["raison"] if d else "pas encore jugé",
                           # jugé à cette collecte : sert à vous prévenir une seule fois (avis GitHub)
                           "nouveau": _cle_proposition(r) in nouveaux,
                           "date": _champ(r, "date")[:20], "lieu": _champ(r, "lieu", "salle")[:120]})
    return out


def _date_formulaire(s: str) -> date | None:
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            pass
    return None


def _heure_formulaire(s: str) -> str | None:
    m = re.search(r"(\d{1,2})\s*[h:]\s*(\d{2})?", s or "") or re.search(r"(\d{1,2})()\s*[ap]\.?\s*m", (s or "").lower())
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if "pm" in (s or "").lower() and h < 12:
        h += 12
    return f"{h:02d}:{mi:02d}" if h < 24 else None


MOTS_FORMULAIRE = (("theatre", "theatre"), ("musique", "musique"), ("danse", "danse"), ("cirque", "cirque"),
                   ("humour", "humour"), ("cinema", "cinema"), ("poesie", "poesie"), ("slam", "poesie"),
                   ("litterature", "lettres"), ("conference", "conference"), ("atelier", "atelier"), ("fete", "fete"),
                   ("quiz", "quiz"), ("exposition", "expo"), ("vernissage", "expo"), ("jeune", "jeune"))


def _disciplines_formulaire(choix: str) -> list[str]:
    """Cases cochées « Discipline » (« Musique, Danse ») → codes, dans l'ordre où ils apparaissent."""
    t = plat(choix)
    trouves = sorted((t.find(mot), code) for mot, code in MOTS_FORMULAIRE if mot in t)
    return list(dict.fromkeys(code for _, code in trouves))


def _discipline_formulaire(choix: str) -> str:
    """Première discipline cochée (vide si on laisse le classement décider)."""
    return next(iter(_disciplines_formulaire(choix)), "")


def propositions(cfg: dict, debut: date, fin: date, **_) -> tuple[list, list]:
    evs = []
    rows = list(_lire_csv(cfg["url"]))
    # « oui » : publié ; « non » : refusé ; vide : tri automatique
    auto = _moderer([r for r in rows if not _approuve(r) and not _refuse(r) and _champ(r, "titre", "nom de l evenement")])
    FORMULAIRE_RESUME.update(lignes=len(rows), oui=sum(map(_approuve, rows)), non=sum(map(_refuse, rows)),
                             acceptees_auto=sum(auto.values()), ia=ia.disponible(),
                             colonnes=[k for k in (rows[0].keys() if rows else []) if k and "courriel" not in plat(k)])
    print(f"  formulaire : {FORMULAIRE_RESUME}")
    for row in rows:
        if not (_approuve(row) or auto.get(_cle_proposition(row))):
            continue
        d = _date_formulaire(_champ(row, "date"))
        if not d or d < debut or d > fin:
            continue
        discs = _disciplines_formulaire(_champ(row, "discipline", "categorie"))
        jeune = "jeune" in discs
        discs = [d for d in discs if d != "jeune"]
        evs.append(brut(titre=_champ(row, "titre", "nom de l evenement"), date=d.isoformat(),
                        heure=_heure_formulaire(_champ(row, "heure")), lieu=_champ(row, "lieu", "salle"),
                        adresse=_champ(row, "adresse"), url=_champ(row, "lien", "url", "billet"),
                        categorie=_champ(row, "discipline", "categorie"), source="formulaire",
                        discipline=(discs[0] if discs else ""), aussi=discs[1:3],
                        jeune_public=jeune or "oui" in plat(_champ(row, "jeune public", "enfants")),
                        description=_champ(row, "description"), prix=_champ(row, "prix", "tarif"),
                        billets=_champ(row, "billetterie", "billets"), image=_image_formulaire(_champ(row, "image", "photo"))))
    return evs, []


def calendriers_soumis(cfg: dict) -> list[dict]:
    """Lignes approuvées du formulaire « Ajouter mon calendrier » → configurations de source « auto »."""
    out = []
    for row in _lire_csv(cfg["url"]):
        lien = _champ(row, "calendrier", "lien", "url", "adresse web")
        if not lien or not _approuve(row):
            continue
        out.append({"nom": _champ(row, "organisme", "nom") or lien, "type": "auto", "url": lien,
                    "lieu": _champ(row, "nom de la salle", "salle", "lieu"), "adresse": _champ(row, "adresse de la salle", "adresse"),
                    "discipline": "", "categorie": _champ(row, "discipline"), "cle_source": "calendrier"})
    return out


def recurrents(cfg: dict, debut: date, fin: date, **_) -> tuple[list, list]:
    """Rendez-vous hebdomadaires vérifiés à la main (collecteur/recurrents.yaml) : une entrée par semaine."""
    import yaml
    from pathlib import Path
    jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    liste = (yaml.safe_load((Path(__file__).parent / cfg.get("fichier", "recurrents.yaml")).read_text(encoding="utf-8"))
             or {}).get(cfg.get("groupe", "quiz"), [])
    evs = []
    for r in liste:
        j = debut + timedelta(days=(int(r["jour"]) - debut.weekday()) % 7)
        while j <= fin:
            if r.get("mois") and j.month not in r["mois"]:  # saison (ex. septembre à mai)
                j += timedelta(days=7)
                continue
            evs.append(brut(titre=r["titre"], date=j.isoformat(), heure=r.get("heure"), lieu=r["lieu"],
                            adresse=r.get("adresse", ""), ville="Montréal", url=r.get("source", ""),
                            discipline=cfg.get("discipline", ""), source=cfg["cle_source"],
                            description=f"Chaque {jours_fr[int(r['jour'])]}, à confirmer auprès du lieu (vérifié le {r.get('verifie')})."))
            j += timedelta(days=7)
    return evs, []


CONNECTEURS = {"recurrents": recurrents, "ville_csv": ville_csv, "ics": ics, "jsonld": jsonld, "gancio": gancio, "page_ia": page_ia,
               "auto": auto, "propositions": propositions}


# ---------------------------------------------------------------- Page d'un événement de la Ville (montreal.ca)
_MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]


def details_ville(html: str, jour: str) -> dict:
    """Salle, adresse, heure et billetterie lues sur la fiche montreal.ca d'un événement.
    Le fichier de données ouvertes ne donne plus toujours la salle ni l'heure (oct. 2026) ; la fiche, elle, les a.
    Données schema.org d'abord, puis le bloc « Renseignements » de la page."""
    out = {}
    for o in _objets_jsonld(html):
        loc = o.get("location") or {}
        if isinstance(loc, list):
            loc = loc[0] if loc else {}
        if isinstance(loc, dict) and loc.get("name"):
            out["lieu"] = str(loc["name"]).strip()
            adr = loc.get("address") or ""
            out["adresse"] = adr.get("streetAddress", "") if isinstance(adr, dict) else str(adr)
        sd = str(o.get("startDate") or "")
        if sd[:10] == jour:
            m = re.search(r"T(\d{2}):(\d{2})", sd)
            if m and (m.group(1), m.group(2)) != ("00", "00"):
                out["heure"] = f"{m.group(1)}:{m.group(2)}"
        off = o.get("offers") or {}
        if isinstance(off, list):
            off = off[0] if off else {}
        if isinstance(off, dict) and str(off.get("url", "")).startswith("http"):
            out["billets"] = off["url"]
    soupe = BeautifulSoup(html, "html.parser")
    if "lieu" not in out:
        titre = soupe.find(lambda t: t.name in ("h2", "h3", "h4", "p", "div", "span") and t.get_text(strip=True) == "Renseignements")
        bloc = titre
        for _ in range(4):  # on remonte jusqu'au conteneur qui a les liens
            if bloc is None or bloc.find_next("a") is None:
                break
            if bloc.parent is not None and bloc.parent.find("a"):
                bloc = bloc.parent
                break
            bloc = bloc.parent
        if bloc is not None:
            for a in bloc.find_all("a"):
                t = a.get_text(" ", strip=True)
                if t and not re.search(r"(?i)voir la carte|billetterie|courriel|t[ée]l[ée]phone|site web|^\+|@", t):
                    out["lieu"] = t
                    suite = a.find_next(string=re.compile(r"\d+.*(rue|av|boul|chemin|place|ch\.|bd|avenue|boulevard)", re.I))
                    if suite:
                        out["adresse"] = suite.strip()
                    break
    if "billets" not in out:
        for a in soupe.find_all("a", href=True):
            if re.search(r"(?i)^\s*(billetterie|r[ée]server|acheter des billets|billets)\s*$", a.get_text(" ", strip=True)) \
                    and a["href"].startswith("http"):
                out["billets"] = a["href"]
                break
    if "heure" not in out:
        try:
            a_, m_, j_ = jour.split("-")
            texte = plat(soupe.get_text(" ", strip=True))
            m = re.search(rf"\b{int(j_)} {_MOIS[int(m_) - 1]}(?: {a_})?\D{{0,40}}?\b(\d{{1,2}}) ?h ?(\d{{2}})?\b", texte)
            if m and 8 <= int(m.group(1)) <= 23:
                out["heure"] = f"{int(m.group(1)):02d}:{m.group(2) or '00'}"
        except (ValueError, IndexError):
            pass
    return out
