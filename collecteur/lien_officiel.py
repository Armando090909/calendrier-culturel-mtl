"""Lien vers la salle (28 nov. 2026, Alexandre : « cliquer sur un événement devrait toujours envoyer au site de la
salle. La musique a déjà ses liens d'écoute et il y a déjà un lien pour la billetterie. Si tu ne trouves pas la salle,
lie vers l'agrégateur. »).

Pour chaque événement dont l'adresse est un agrégateur ou une billetterie (Sorstu, Songkick, Askapunk, ma.to, Eventbrite,
Le Point de vente…) :
  - la page de l'événement sur le site de la salle, si on la connaît déjà (autre source du même événement, page de
    l'affiche, billetterie de la salle, lien de la page de l'agrégateur vers le site de la salle) ;
  - sinon la page d'accueil du site de la salle ;
  - sinon l'agrégateur reste.
Site de la salle : celui de ses propres événements, de sa source (sources.yaml) ou de outils/diag/contacts.json ;
à défaut, le lien de la page de l'agrégateur qui porte le nom de la salle, ou le site connu de l'IA, gardé seulement si
sa page d'accueil nomme la salle. Les pages de la Ville (montreal.ca) et des producteurs (evenko) restent.
Une billetterie remplacée reste le lien « billets » si l'événement n'en avait pas.
Mémoire (cache/lien_officiel.json) : salle → site (ou rien, réessayé après 30 jours).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from normalisation import plat

MEMOIRE = Path(__file__).parent / "cache" / "lien_officiel.json"
CONTACTS = Path(__file__).resolve().parent.parent / "outils" / "diag" / "contacts.json"
BILLETTERIES = ("eventbrite", "lepointdevente", "thepointofsale", "tuxedobillet", "ticketmaster", "ticketpro", "admission.com",
                "seetickets", "tixr", "venuepilot", "yapla", "zeffy", "dice.fm", "showpass", "universe.com", "luma.com", "lu.ma",
                "eventzilla", "ticketsource", "simpletix", "tickettailor", "fnacspectacles", "omniwebticketing")
AGREGATEURS = ("sorstu.ca", "songkick.com", "bandsintown", "askapunk", "ma.to", "ra.co", "allevents", "spectaculos",
               "quoifaire", "mtl.org", "jambase", "festapp", "facebook.com", "instagram.com", "meetup", "caligram",
               "linktr.ee", "google.", "residentadvisor", "tourisme", "narcity", "mtlblog", "panm360")
JAMAIS = ("facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com", "youtube.com", "youtu.be", "spotify.com",
          "apple.com", "bandcamp.com", "soundcloud.com", "wikipedia.org", "google.", "linktr.ee", "mailto:", "tel:")
VIDES = {"avec", "pour", "dans", "sous", "les", "des", "une", "the", "and", "with", "show", "spectacle", "concert", "montreal",
         "theatre", "presente", "presents", "live", "tour", "tournee", "lancement", "soiree", "night", "edition"}
SALLE_VIDES = {"de", "du", "la", "le", "les", "des", "l", "d", "et", "the", "of", "montreal", "salle", "centre", "center",
               "theatre", "cafe", "bar", "club", "espace", "a"}


def _hote(u: str) -> str:
    return (urlparse(u or "").hostname or "").lower().removeprefix("www.")


def intermediaire(u: str) -> bool:
    h = _hote(u)
    return bool(h) and any(a in h for a in AGREGATEURS + BILLETTERIES)


def _billetterie(u: str) -> bool:
    return any(a in _hote(u) for a in BILLETTERIES)


def _exclu(u: str) -> bool:
    return not str(u).startswith("http") or any(a in u for a in JAMAIS) or intermediaire(u) or "montreal.ca" in _hote(u)


def _profonde(u: str) -> bool:
    return len(urlparse(u).path.strip("/")) > 1


def _accueil(u: str) -> str:
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}/"


def _sur(u: str, site: str) -> bool:
    h, s = _hote(u), _hote(site)
    return bool(h and s) and (h == s or h.endswith("." + s))


def _mots(titre: str) -> list[str]:
    t = re.sub(r"\(.*?\)|\s[|·:–—-]\s.*$", "", titre) or titre
    return [m for m in plat(t).split() if len(m) >= 4 and m not in VIDES]


def _nomme_la_salle(texte: str, lieu: str) -> bool:
    mots = [m for m in plat(lieu).split() if m not in SALLE_VIDES and len(m) > 1]
    t = plat(texte)
    return bool(mots) and all(m in t for m in mots)


def _ressemble(site: str, lieu: str) -> bool:
    """Le nom de domaine reprend le nom de la salle (cabaretliondor.com ↔ Cabaret Lion d'Or, sat.qc.ca ↔ SAT)."""
    h = _hote(site)
    etiquettes = set(h.split("."))
    colle = re.sub(r"[^a-z0-9]", "", h)
    mots = [m for m in plat(lieu).split() if m not in SALLE_VIDES]
    return any((len(m) >= 4 and m in colle) or (len(m) >= 3 and m in etiquettes) for m in mots)


def sites_connus(events: list[dict], sources: list[dict]) -> dict[str, str]:
    """Salle → page d'accueil de son site."""
    site: dict[str, str] = {}  # sources et contacts d'abord (vérifiés), puis les événements de la salle
    for s in sources:
        u, lieu = str(s.get("url") or ""), s.get("lieu")
        if lieu and u.startswith("http") and not _exclu(u):
            site.setdefault(lieu, _accueil(u))
    if CONTACTS.exists():
        for r in json.loads(CONTACTS.read_text(encoding="utf-8")):
            if r.get("salle") and str(r.get("site") or "").startswith("http") and not _exclu(r["site"]):
                site.setdefault(r["salle"], _accueil(r["site"]))
    par: dict[str, Counter] = {}
    for e in events:
        u = e.get("url", "")
        # (28 nov. 2026) un domaine qui ne reprend pas le nom de la salle est celui d'un festival ou d'un producteur qui
        # y présente (casteliers.ca au Théâtre Outremont, ridm.ca à la Maison Théâtre) : pas le site de la salle
        if u.startswith("http") and not _exclu(u) and e.get("lieu") and _ressemble(u, e["lieu"]):
            par.setdefault(e["lieu"], Counter())[_accueil(u)] += 1
    par_ev = {l: c.most_common(1)[0][0] for l, c in par.items()}
    n = Counter(par_ev.values())
    for l, s_ in par_ev.items():
        if n[s_] <= 3:  # un site partagé par 4 salles ou plus : un diffuseur
            site.setdefault(l, s_)
    return site


def _liens(html: str, base: str):
    for a in BeautifulSoup(html or "", "html.parser").find_all("a", href=True):
        yield urljoin(base, a["href"].strip()), a.get_text(" ", strip=True)


def _page_de_l_evenement(e: dict, site: str, html: str) -> str | None:
    """Page de l'événement sur le site de la salle, si elle est déjà connue ou citée par l'agrégateur."""
    for u in [*(e.get("_autres_urls") or []), (e.get("affiche") or {}).get("lien") or ""]:
        if u and _sur(u, site) and _profonde(u):
            return u
    mots = _mots(e["titre"])
    for u, texte in _liens(html, e["url"]):
        if not _sur(u, site) or not _profonde(u):
            continue
        chemin = plat(re.sub(r"[-_/.]", " ", urlparse(u).path))
        t = plat(texte)
        if (mots and sum(m in chemin for m in mots) >= min(2, len(mots))) or (len(t) >= 4 and t in plat(e["titre"])):
            return u
    return None


def officialiser(events: list[dict], sources: list[dict], telecharger, aujourd: date, lectures: int = 120,
                 ia_ok: bool = False) -> dict:
    memo = json.loads(MEMOIRE.read_text(encoding="utf-8")) if MEMOIRE.exists() else {}
    vieux = (aujourd - timedelta(days=30)).isoformat()
    sites = sites_connus(events, sources)
    memo = {k: v for k, v in memo.items() if "site" in v}  # (anciennes entrées par événement : abandonnées)
    for lieu, m in memo.items():
        if m.get("site"):
            sites.setdefault(lieu, m["site"])
    stats = Counter()
    a_faire = [e for e in events if intermediaire(e.get("url", "")) and e.get("lieu") and plat(e["lieu"]) != "lieu a confirmer"]
    stats["agregateur"] = len(a_faire)
    pages: dict[str, str] = {}

    def lire(u: str) -> str:
        if u not in pages:
            if len(pages) >= lectures:
                return ""
            try:
                pages[u] = telecharger(u, "text/html").text
            except Exception:
                pages[u] = ""
        return pages[u]

    # salles sans site connu : le lien de l'agrégateur qui porte le nom de la salle, puis l'IA (vérifiés)
    inconnues = sorted({e["lieu"] for e in a_faire if e["lieu"] not in sites
                        and (memo.get(e["lieu"]) or {}).get("le", "") < vieux})
    for lieu in inconnues:
        for e in [x for x in a_faire if x["lieu"] == lieu][:2]:
            if _billetterie(e["url"]):
                continue
            for u, texte in _liens(lire(e["url"]), e["url"]):
                if not _exclu(u) and plat(texte) == plat(lieu):
                    sites[lieu] = _accueil(u)
                    break
            if lieu in sites:
                break
    reste = [l for l in inconnues if l not in sites]
    if reste and ia_ok:
        try:
            import ia
            for lieu, u in ia.sites_officiels(reste[:30]).items():
                if lieu in reste and not _exclu(u) and _nomme_la_salle(re.sub(r"<[^>]+>", " ", lire(_accueil(u))), lieu):
                    sites[lieu] = _accueil(u)
        except Exception as exc:
            print(f"  sites des salles (IA) : {exc}")
    if lectures:  # (28 nov. 2026) mode rapide sans lecture : pas un essai, rien n'est noté
        for lieu in inconnues:
            memo[lieu] = {"site": sites.get(lieu, ""), "le": aujourd.isoformat()}

    for e in a_faire:
        site = sites.get(e["lieu"])
        if not site:
            stats["salle introuvable : agrégateur gardé"] += 1
            continue
        b = str(e.get("billets") or "")
        page = _page_de_l_evenement(e, site, "" if _billetterie(e["url"]) else lire(e["url"]))
        if not page and b and _sur(b, site) and _profonde(b):
            page = b
        ancien = e["url"]
        e["url"] = page or site
        if _billetterie(ancien) and not e.get("billets"):
            e["billets"] = ancien
        stats["page de l'événement chez la salle" if page else "accueil du site de la salle"] += 1
    MEMOIRE.write_text(json.dumps(memo, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    stats["pages lues"] = len(pages)
    return dict(stats)
