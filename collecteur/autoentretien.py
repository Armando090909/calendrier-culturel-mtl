"""Entretien automatique des sources : le programme se répare et s'enrichit seul, et n'écrit à une personne qu'en
dernier recours (avis « [Santé] », voir outils/sante.py).

1. Réparation (chaque nuit) : une source qui ne donne plus rien (page introuvable, site refait, page vide) est
   cherchée de nouveau sur son propre site : redirection, liens « Programmation », « Calendrier », « Événements »…,
   adresses habituelles (/programmation, /evenements…). La meilleure page trouvée remplace l'ancienne adresse
   (collecteur/cache/reparations.json) et sert dès la collecte suivante.
2. Découverte (chaque semaine, le dimanche) : les salles qui reviennent souvent dans les agendas (Le Point de vente,
   ma.to, Sors-tu?, Songkick…) mais n'ont pas leur propre source sont cherchées ; leur page de programmation devient
   une nouvelle source si elle donne vraiment des événements (collecteur/cache/sources_auto.json). Une source
   découverte qui ne donne plus rien pendant 4 semaines est retirée.

Garde-fous : jamais pour les pages refusées (403, l'ordinateur à Montréal s'en charge), ni les festivals hors saison,
ni plus de 4 réparations par nuit et 8 essais de découverte par semaine ; le robots.txt de chaque site est vérifié
par telecharger().
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from normalisation import plat

CACHE = Path(__file__).parent / "cache"
F_REP = CACHE / "reparations.json"
F_AUTO = CACHE / "sources_auto.json"

MOTS = re.compile(r"(?i)programm|calendri|agenda|[ée]v[ée]nement|events?\b|spectacles?|shows?\b|concerts?|billett|"
                  r"tickets?|saison|season|whats-on|a-l-affiche|à l.affiche|expositions?|activit|conf[ée]rences?|horaire|lineup")
CHEMINS = ("/programmation", "/calendrier", "/evenements", "/events", "/spectacles", "/agenda", "/shows", "/fr/programmation",
           "/fr/evenements", "/concerts")
AGREGATEURS = ("songkick.com", "sorstu.ca", "lepointdevente.com", "thepointofsale.com", "ma.to", "montreal.ca",
               "festapp.io", "eventbrite.", "zeffy.com", "facebook.com", "instagram.com", "ra.co", "mtl.org",
               "sortirauquebec.com", "jambase.com", "exclaim.ca", "bandsintown.com", "myscena.org", "lavitrine.com",
               "google.com", "goo.gl", "linktr.ee", "youtube.com", "spotify.com", "bandcamp.com")


def _lire(f: Path) -> dict:
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except ValueError:
        return {}


def appliquer(sources: list[dict]) -> list[dict]:
    """Adresses réparées et sources découvertes, ajoutées à la liste de la collecte."""
    rep = _lire(F_REP)
    for s in sources:
        r = rep.get(s["nom"])
        if r and r.get("url") and "{" not in s.get("url", ""):
            s["url_origine"], s["url"] = s["url"], r["url"]
            if r.get("navigateur"):
                s["navigateur"] = True
    noms = {s["nom"] for s in sources}
    for nom, cfg in _lire(F_AUTO).items():
        if nom not in noms and cfg.get("url"):
            sources.append(dict(cfg, nom=nom, cle_source=cfg.get("cle", "salles")))
    return sources


def _candidats(url: str, telecharger, page_rendue) -> list[str]:
    """Pages du même site qui ressemblent à une programmation."""
    u = urlparse(url)
    racine = f"{u.scheme}://{u.netloc}/"
    hote = u.netloc.replace("www.", "")
    out: list[tuple[int, str]] = []
    html = ""
    try:
        r = telecharger(racine, "text/html")
        html = r.text
        if r.url and r.url.rstrip("/") != url.rstrip("/") and urlparse(r.url).netloc.replace("www.", "") != hote:
            out.append((5, r.url))  # le site a déménagé (redirection vers un autre domaine)
        if len(BeautifulSoup(html, "html.parser").get_text(" ", strip=True)) < 400:
            html = page_rendue(racine)
    except Exception:
        try:
            html = page_rendue(racine)
        except Exception:
            html = ""
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        lien = urljoin(racine, a["href"]).split("#")[0]
        if urlparse(lien).netloc.replace("www.", "") != hote or lien.rstrip("/") == url.rstrip("/"):
            continue
        texte = a.get_text(" ", strip=True)
        score = (2 if MOTS.search(texte) else 0) + (1 if MOTS.search(urlparse(lien).path) else 0)
        if score:
            out.append((score, lien))
    for chemin in CHEMINS:
        out.append((1, racine.rstrip("/") + chemin))
    vus, liste = set(), []
    for _, lien in sorted(out, key=lambda x: -x[0]):
        if lien not in vus:
            vus.add(lien)
            liste.append(lien)
    return liste[:8]


def _essayer(cfg: dict, urls: list[str], page_ia, debut: date, fin: date, telecharger) -> tuple[str, int, list, list]:
    meilleur = ("", 0, [], [])
    essais = 0
    for url in urls:
        if essais >= 5:
            break
        try:
            r = telecharger(url, "text/html")  # adresse habituelle inexistante : on passe sans dépenser d'IA
            if r.status_code >= 400:
                continue
        except Exception:
            continue
        essais += 1
        try:
            e, s = page_ia(dict(cfg, url=url, repeter=None, details=False), debut, fin)
        except Exception:
            continue
        n = len(e) + len(s)
        if n > meilleur[1]:
            meilleur = (url, n, e, s)
    return meilleur


def reparer(sources: list[dict], rapport: list[dict], page_ia, page_rendue, telecharger, aujourd: date, fin: date,
            sources_ok: dict) -> tuple[list, list, list[str]]:
    """Cherche une nouvelle adresse pour les sources devenues muettes. Renvoie (événements, séries, journal)."""
    rep = _lire(F_REP)
    par_nom = {r["source"]: r for r in rapport}
    evs, series, journal = [], [], []
    essais = 0
    for s in sources:
        r = par_nom.get(s["nom"]) or {}
        diag = " ".join(r.get("diagnostic") or []) + " " + str(r.get("erreur") or "")
        n = (r.get("evenements") or 0) + (r.get("series") or 0)
        mort = re.search(r"\b(404|410)\b", diag)
        if n or s["nom"].startswith("Festival ·") or s.get("type") not in ("page_ia", "auto") or "{" in s.get("url", "") \
                or "403" in diag or "lue depuis Montréal" in diag or not s.get("url", "").startswith("http"):
            if n and s["nom"] in rep:
                rep[s["nom"]]["dernier_ok"] = aujourd.isoformat()
            continue
        if not (mort or sources_ok.get(s["nom"]) or s["nom"] in rep):
            continue  # jamais rien donné et pas d'adresse morte : sans doute rien d'annoncé (ex. lieu saisonnier)
        dernier = (rep.get(s["nom"]) or {}).get("essai", "")
        if dernier >= (aujourd - timedelta(days=7)).isoformat() or essais >= 4:
            continue
        essais += 1
        cands = _candidats(s.get("url_origine") or s["url"], telecharger, page_rendue)
        url, nb, e, sr = _essayer(s, cands, page_ia, aujourd, fin, telecharger)
        info = rep.setdefault(s["nom"], {})
        info["essai"] = aujourd.isoformat()
        if url and nb >= 2:
            info.update(url=url, ancienne=s.get("url_origine") or s["url"], le=aujourd.isoformat(), n=nb, echecs=0)
            evs += e
            series += sr
            journal.append(f"réparée : {s['nom']} → {url} ({nb})")
        else:
            info["echecs"] = info.get("echecs", 0) + 1
            journal.append(f"non réparée : {s['nom']} ({len(cands)} pages essayées)")
    F_REP.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return evs, series, journal


def _agregateur(url: str) -> bool:
    h = urlparse(url).netloc.lower()
    return not h or any(a in h for a in AGREGATEURS)


def decouvrir(events: list[dict], sources: list[dict], rapport: list[dict], page_ia, telecharger, aujourd: date,
              fin: date) -> list[str]:
    """Nouvelles sources : salles fréquentes dans les agendas, sans source propre. Une fois par semaine."""
    auto = _lire(F_AUTO)
    journal: list[str] = []
    par_nom = {r["source"]: r for r in rapport}
    # 1. Ménage : une source découverte qui ne donne plus rien depuis 4 semaines est retirée
    for nom, cfg in list(auto.items()):
        r = par_nom.get(nom) or {}
        if (r.get("evenements") or 0) + (r.get("series") or 0):
            cfg["dernier_ok"] = aujourd.isoformat()
        elif cfg.get("dernier_ok", cfg.get("ajoute", "")) < (aujourd - timedelta(days=28)).isoformat():
            del auto[nom]
            journal.append(f"retirée (muette 4 semaines) : {nom}")
    # 2. Salles couvertes : une source les nomme, ou leurs événements viennent déjà de leur propre site
    couvertes = {plat(s.get("lieu", "")) for s in sources if s.get("lieu")}
    couvertes |= {plat(e["lieu"]) for e in events if not _agregateur(e.get("url", ""))}
    compte: dict[str, list[dict]] = {}
    for e in events:
        if e["lieu"] in ("", "Lieu à confirmer") or e.get("source") in ("ville", "recurrents", "formulaire"):
            continue
        if plat(e["lieu"]) not in couvertes:
            compte.setdefault(e["lieu"], []).append(e)
    deja = {plat(c.get("lieu", "")) for c in auto.values()} | {plat(c.get("lieu", "")) for c in _lire(F_AUTO).values()}
    candidats = sorted(((l, evs) for l, evs in compte.items() if len(evs) >= 3 and plat(l) not in deja),
                       key=lambda x: -len(x[1]))[:8]
    for lieu, evs in candidats:
        pages: list[str] = []
        for e in evs[:3]:
            url = e.get("url", "")
            try:
                html = telecharger(url, "text/html").text
            except Exception:
                continue
            pages += re.findall(r"https://(?:lepointdevente|thepointofsale)\.com/(?:lieux/[\w-]+|[\w-]+)(?=[\"'])", html)[:3]
            pages += [m for m in re.findall(r"https://ma\.to/venue/[\w-]+", html)][:2]
            for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):  # lien vers le site de la salle
                if plat(a.get_text(" ", strip=True)) == plat(lieu) and a["href"].startswith("http") and not _agregateur(a["href"]):
                    pages.append(a["href"])
        pages = [p for p in dict.fromkeys(pages) if not re.search(r"/(billets|tickets|organisateurs|creer|login)\b", p)]
        if not pages:
            journal.append(f"sans piste : {lieu} ({len(evs)} événements dans les agendas)")
            continue
        cfg = {"nom": f"{lieu} (découverte)", "type": "page_ia", "cle": "salles", "cle_source": "salles", "lieu": lieu,
               "navigateur": True}
        url, n, _, _ = _essayer(cfg, pages[:5], page_ia, aujourd, fin, telecharger)
        if url and n >= 3:
            auto[cfg["nom"]] = {"type": "page_ia", "cle": "salles", "url": url, "lieu": lieu, "navigateur": True,
                                "jours_semaine": [0, 3], "ajoute": aujourd.isoformat(), "dernier_ok": aujourd.isoformat()}
            journal.append(f"ajoutée : {lieu} → {url} ({n})")
        else:
            journal.append(f"pistes sans résultat : {lieu}")
    F_AUTO.write_text(json.dumps(auto, ensure_ascii=False, indent=1), encoding="utf-8")
    return journal
