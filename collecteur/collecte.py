"""Collecte quotidienne : lit toutes les sources, nettoie, et écrit docs/data.json.

Lancement : python collecteur/collecte.py
Variables d'environnement (facultatives) :
  ANTHROPIC_API_KEY      clé pour lire les pages ordinaires avec l'IA (sinon ces sources sont sautées)
  PROPOSITIONS_CSV_URL   feuille Google publiée en CSV : événements proposés par le public
  CALENDRIERS_CSV_URL    feuille Google publiée en CSV : calendriers ajoutés par les salles
  CONTACT                courriel du projet, envoyé à OpenStreetMap avec les recherches d'adresse
"""
from __future__ import annotations

import json
import time
import os
import re
import sys
import signal
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
import agenda  # noqa: E402
import autoentretien  # noqa: E402
import archives  # noqa: E402
import decouverte  # noqa: E402
import festivals as fest  # noqa: E402
import geo  # noqa: E402
import ia  # noqa: E402
import qualite  # noqa: E402
from connecteurs import CONNECTEURS, sauver_memoire, calendriers_soumis, heure_page, resume_page, telecharger, texte_page  # noqa: E402
import connecteurs  # noqa: E402
from normalisation import PAS_DES_SALLES, Lieux, classer, corriger_heure_festapp, dans_ile, dedoublonner, disciplines_aussi, est_non_culturel, hors_ile, plat, style_musique, doublons_du_jour, doublons_expos  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "docs" / "data.json"
RAPPORT = RACINE / "docs" / "rapport.json"
LIEUX = Path(__file__).parent / "lieux.json"
SOURCES = Path(__file__).parent / "sources.yaml"
CACHE = Path(__file__).parent / "cache"
VOCATION_SALLES = {"cabaret mado": "humour", "wiggle room": "humour", "comedy nest": "humour", "bordel comedie": "humour",
                   "le studio jazz": "musique", "upstairs": "musique", "diese onze": "musique", "balattou": "musique"}
MANUELS = Path(__file__).parent / "manuels.json"  # programmes saisis à la main
MTL = ZoneInfo("America/Toronto")

JEUNE = re.compile(r"\b\d+\s*(à|a|-)\s*\d+\s*ans\b|jeune public|famille|enfants|tout-petits|\(\d+\s*ans", re.I)


# Textes et images : on ne reprend que ce qu'on a le droit de reprendre.
SOURCES_CONSENTANTES = {"formulaire", "calendrier", "ville"}  # salles qui envoient leurs données ; Ville = licence CC-BY


def _propre(t: str, n: int) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def details(b: dict) -> dict:
    """Résumé, prix, billetterie et image, selon ce que la source permet."""
    out = {}
    src = b.get("source", "")
    desc = b.get("resume") or b.get("description") or ""
    if desc:
        # Résumés écrits par l'IA : courts et originaux. Descriptions fournies par la salle ou la Ville : extrait court.
        out["resume"] = _propre(desc, 260 if src in SOURCES_CONSENTANTES else 200)
    if b.get("prix"):
        out["prix"] = _propre(str(b["prix"]), 40)
    if b.get("billets", "").startswith("http"):
        out["billets"] = b["billets"]
    if b.get("image", "").startswith("http") and src in {"formulaire", "calendrier"}:
        out["image"] = b["image"]  # photos seulement quand la salle les fournit elle-même
    elif b.get("image", "").startswith("https://"):
        out["_image_src"] = b["image"]  # image des données structurées (ex. photo de l'artiste) : dernier recours, vérifiée
    return out


TYPES_LISIBLES = {"ville_csv": "données ouvertes", "ics": "calendrier iCal", "jsonld": "données structurées",
                  "gancio": "agenda Gancio", "page_ia": "page lue par l'IA", "auto": "calendrier soumis",
                  "propositions": "formulaire"}


RE_IMPRO = re.compile(r"(?i)\bimpro\b|improvis(?:ation|ed|ée?s?)\b(?! libre)|\bLIMM?\b|\bLNI\b|ligue d.impro|match d.impro")


def ecrire_liste_sources(conf: dict, rapport: list) -> None:
    """docs/sources.json : la liste publique des sources consultées, pour la page « Nos sources »."""
    par_nom = {r["source"]: r for r in rapport}
    liste = []
    for s in conf.get("sources", []):
        if not s.get("actif", True):
            continue
        brute = s.get("url") or ""  # certaines sources n'ont pas d'adresse (ex. rendez-vous hebdomadaires vérifiés)
        url = re.sub(r"\{[^}]+\}", "", brute).replace("?page=", "").rstrip("/?&") or brute
        r = par_nom.get(s["nom"], {})
        liste.append({"nom": s["nom"], "url": url, "type": TYPES_LISIBLES.get(s["type"], s["type"]),
                      "evenements": r.get("evenements", 0) + r.get("series", 0), "erreur": bool(r.get("erreur"))})
    (SORTIE.parent / "sources.json").write_text(json.dumps(liste, ensure_ascii=False, indent=1), encoding="utf-8")


_MOTS_EN = re.compile(r"(?i)\b(the|and|with|of|for|show|by|from|this|will|featuring|tickets|join us|your)\b")
_MOTS_FR = re.compile(r"(?i)\b(le|la|les|et|avec|des|du|une|un|pour|par|dans|est|sur|au|aux)\b")


# Sites qui refusent que leurs images s'affichent ailleurs (vérifié dans un vrai navigateur, 3 nov. 2026 :
# outils/verifier_affiches.py). On respecte ce refus : on ne copie pas leurs images, on cherche l'affiche ailleurs.
HOTES_BLOQUES = decouverte.HOTES_BLOQUES


def affiches_bloquees(elements: list[dict]) -> None:
    """Une affiche hébergée sur un site qui bloque l'affichage est remplacée par celle du même spectacle venant
    d'une autre source, ou retirée (pour ne pas montrer une case vide qui clignote)."""
    from urllib.parse import urlparse
    def hote(a):
        return urlparse((a or {}).get("url", "")).hostname or ""
    bonnes = {}
    for e in elements:
        a = e.get("affiche")
        if a and a.get("url") and hote(a) not in HOTES_BLOQUES:
            bonnes.setdefault(plat(e.get("titre", "")), a)
    remplacees = retirees = 0
    for e in elements:
        if hote(e.get("affiche")) in HOTES_BLOQUES:
            autre = bonnes.get(plat(e.get("titre", "")))
            if autre:
                e["affiche"] = autre
                remplacees += 1
            else:
                e.pop("affiche")
                retirees += 1
    print(f"Affiches bloquées par leur site : {remplacees} remplacées par une autre source, {retirees} retirées.")


AGREGATEURS = ("sorstu.ca", "songkick.com", "facebook.com", "eventbrite", "lepointdevente", "thepointofsale", "ticketpro",
               "ticketmaster", "evenko", "universe.com", "festapp", "montreal.ca", "spectaculos", "askapunk", "ra.co",
               "bandsintown", "mtl.org", "caligram", "tourisme", "instagram.com", "linktr.ee", "google.", "billet", "ticket",
               "mpourmontreal", "funnation", "admission", "dice.fm", "showpass", "zeffy", "lepointdevente", "uqam.ca",
               "venuepilot", "tixr", "seetickets", "yapla", "eventzilla", "allevents", "meetup")


def images_des_salles(events: list[dict], aujourd, permises=None) -> None:
    """Événement sans aucune affiche : l'image de partage du site de la salle (son logo ou sa photo), étiquetée
    comme image de la salle. Le site de la salle est déduit des adresses de ses propres événements."""
    from collections import Counter
    from urllib.parse import urlparse
    f = CACHE / "images_salles.json"
    memo = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    hotes: dict[str, Counter] = {}
    for e in events:
        h = (urlparse(e.get("url", "")).hostname or "").replace("www.", "")
        if h and not any(a in h for a in AGREGATEURS) and e.get("lieu") not in ("", "Lieu à confirmer"):
            hotes.setdefault(e["lieu"], Counter())[h] += 1
    site = {lieu: c.most_common(1)[0][0] for lieu, c in hotes.items()}
    # un même site pour 4 salles ou plus : un diffuseur ou une ville, pas le site de la salle
    par_site = Counter(site.values())
    site = {l: h for l, h in site.items() if par_site[h] < 4}
    besoin = {e["lieu"] for e in events if not e.get("affiche") and not e.get("image") and e.get("lieu") in site}
    vieux = (aujourd - timedelta(days=30)).isoformat()
    lus = 0
    for lieu in sorted(besoin):
        h = site[lieu]
        m = memo.get(h)
        if (not m or m["le"] < vieux) and lus < 60:
            lus += 1
            accueil = f"https://{h}/"
            try:
                html = telecharger(accueil, "text/html").text
            except Exception as exc:
                html = None
                if "403" in str(exc):
                    # refusée aux serveurs de GitHub : lue par le Pi à Montréal (pages_a_lire.json), reprise ici ensuite
                    connecteurs.BLOQUEES.add(accueil)
                    html = connecteurs.page_mac(accueil)
                    if html is None:
                        continue  # pas mémorisé : on réessaie demain, quand le Pi l'aura lue
            a = decouverte.affiche_page(html, accueil) if html else None
            memo[h] = {"image": a["url"] if a else None, "le": aujourd.isoformat()}
    n = 0
    # 9 nov. 2026 : l'image de la page d'accueil d'une salle montre souvent UN AUTRE spectacle (ex. Espace Le Vrai
    # Monde?) : seulement pour les salles dont l'image est vérifiée (logo, façade, la salle elle-même),
    # liste « images_de_salle » de sources.yaml
    permises = set(permises or [])
    for e in events:
        if not e.get("affiche") and not e.get("image") and e.get("lieu") in site and e.get("lieu") in permises:
            im = (memo.get(site[e["lieu"]]) or {}).get("image")
            if im and not decouverte.bloquee(im):
                e["affiche"] = {"url": im, "credit": site[e["lieu"]], "lien": f"https://{site[e['lieu']]}/", "salle": True}
                n += 1
    f.write_text(json.dumps(memo, ensure_ascii=False), encoding="utf-8")
    # la liste des pages à lire depuis Montréal inclut maintenant les sites de salles refusés
    (SORTIE.parent / "pages_a_lire.json").write_text(json.dumps(sorted(connecteurs.BLOQUEES), ensure_ascii=False),
                                                     encoding="utf-8")
    print(f"Images de salle : {n} événements sans affiche reçoivent l'image de leur salle ({lus} sites lus).")


def lieu_jsonld(html: str) -> dict:
    """Salle et adresse d'un événement d'après ses données schema.org (location.name, location.address)."""
    for bloc in re.findall(r'(?s)<script[^>]*ld\+json[^>]*>(.*?)</script>', html or ""):
        try:
            d = json.loads(bloc)
        except Exception:
            continue
        for x in (d if isinstance(d, list) else d.get("@graph", [d]) if isinstance(d, dict) else []):
            loc = x.get("location") if isinstance(x, dict) else None
            loc = loc[0] if isinstance(loc, list) and loc else loc
            if isinstance(loc, dict) and loc.get("name"):
                a = loc.get("address") or {}
                adr = a if isinstance(a, str) else ", ".join(str(a.get(k)) for k in ("streetAddress", "postalCode") if a.get(k))
                return {"lieu": str(loc["name"]).strip(), "adresse": adr}
    return {}


def liens_billets(html: str, page: str) -> list[str]:
    """Liens d'une page de spectacle qui mènent à la billetterie (texte ou adresse « billet », « ticket », « réserv »)."""
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    out = []
    for a in BeautifulSoup(html or "", "html.parser").find_all("a", href=True):
        texte = a.get_text(" ", strip=True).lower()
        href = urljoin(page, a["href"])
        if not href.startswith("http") or "facebook.com" in href or "mailto:" in href \
                or re.search(r"(?i)mon-compte|my-account|/compte|account|login|connexion|panier|cart|abonn|subscri|carte-cadeau|gift", href):
            continue
        if re.search(r"billet|ticket|r[ée]serv|achet|acheter|buy", texte + " " + href.lower()) and href not in out:
            out.append(href)
    return out[:5]


def nettoyer_resumes(elements: list[dict]) -> None:
    """Résumés propres pour la section française : balises et entités HTML retirées, adresses web retirées,
    phrases automatiques de Songkick (« X at Y at 2026-… ») supprimées, résumés anglais traduits en français
    (l'original anglais devient resume_en)."""
    import html as _html
    for e in elements:
        r = e.get("resume")
        if not r:
            continue
        for _ in range(3):
            r = _html.unescape(r)
        r = re.sub(r"<[^>]*>", " ", r)
        r = re.sub(r"https?://\S+|\S*[?&]lang=\w+\S*", " ", r)
        r = re.sub(r"\s+", " ", r).strip(" -–|")
        if re.match(r".+ at .+ at \d{4}-\d{2}-\d{2}", r) or len(r) < 8:
            e.pop("resume", None)
        else:
            e["resume"] = r
    f_fr = CACHE / "traductions_fr.json"
    memo = json.loads(f_fr.read_text(encoding="utf-8")) if f_fr.exists() else {}
    anglais = [e for e in elements if e.get("resume")
               and len(_MOTS_EN.findall(e["resume"])) >= 3 > len(_MOTS_FR.findall(e["resume"]))]
    a_faire = list(dict.fromkeys(e["resume"] for e in anglais if e["resume"] not in memo))[:240]  # le reste suit les jours suivants
    if a_faire and ia.disponible():
        for i in range(0, len(a_faire), 60):
            part = a_faire[i:i + 60]
            try:
                for k, t in ia.traduire_lot(part, vers="fr").items():
                    memo[part[k]] = t
            except Exception as exc:
                print(f"Traduction vers le français en échec : {exc}")
    n = 0
    for e in anglais:
        t = memo.get(e["resume"])
        if t and t != e["resume"]:
            e["resume_en"], e["resume"] = e["resume"], t
            n += 1
    f_fr.write_text(json.dumps({e["resume_en"]: e["resume"] for e in anglais if e.get("resume_en")} |
                               {k: v for k, v in memo.items() if k in a_faire}, ensure_ascii=False), encoding="utf-8")
    print(f"Résumés : {n} résumés anglais traduits en français ; {len(anglais) - n} encore en anglais.")


def traduire_resumes(elements: list[dict]) -> None:
    """Version anglaise du site : chaque résumé reçoit sa traduction (resume_en), gardée en cache pour ne traduire
    que les nouveaux. Sans IA disponible, le site anglais affiche le résumé original."""
    f_tr = CACHE / "traductions_en.json"
    memo = json.loads(f_tr.read_text(encoding="utf-8")) if f_tr.exists() else {}
    a_faire = list(dict.fromkeys(e["resume"] for e in sorted(elements, key=lambda x: x.get("date") or x.get("debut") or "")
                                 if e.get("resume") and not e.get("resume_en") and e["resume"] not in memo))
    faits = 0
    if a_faire and ia.disponible():
        from concurrent.futures import ThreadPoolExecutor
        # les plus proches d'abord (ordre du calendrier) ; au plus 1500 par jour, le reste suit le lendemain
        parts = [a_faire[i:i + 60] for i in range(0, min(len(a_faire), 600), 60)]  # 11 nov. 2026 : 1500 d'un coup dépassait le temps permis

        def un(part):
            try:
                return part, ia.traduire_lot(part)
            except Exception as exc:
                print(f"Traduction en échec : {exc}")
                return part, {}
        with ThreadPoolExecutor(4) as pool:
            for part, rep in pool.map(un, parts):
                for k, t in rep.items():
                    memo[part[k]] = t
                    faits += 1
    utiles = set()
    for e in elements:
        t = None if e.get("resume_en") else memo.get(e.get("resume") or "")
        if t:
            utiles.add(e["resume"])
            if t != e["resume"]:
                e["resume_en"] = t
    # le cache ne garde que les résumés encore au calendrier (plus les traductions du jour)
    f_tr.write_text(json.dumps({k: v for k, v in memo.items() if k in utiles}, ensure_ascii=False), encoding="utf-8")
    print(f"Traductions : {faits} nouveaux résumés traduits, {len(a_faire) - faits} restants ; "
          f"{sum(1 for e in elements if e.get('resume_en'))} éléments avec résumé anglais.")


class SourceTropLongue(Exception):
    pass


def _trop_long(*_):
    raise SourceTropLongue("source abandonnée après 10 minutes sans fin de lecture")


def main() -> int:
    conf = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    reglages = conf.get("reglages", {})
    aujourd = datetime.now(MTL).date()
    fin = aujourd + timedelta(days=int(reglages.get("horizon_jours", 60)))
    ua = f'CalendrierCulturelMTL/1.0 ({os.environ.get("CONTACT") or "contact non configuré"})'
    lieux = Lieux(json.loads(LIEUX.read_text(encoding="utf-8")) if LIEUX.exists() else {})
    ancien = json.loads(SORTIE.read_text(encoding="utf-8")) if SORTIE.exists() else None

    sources = [dict(s, cle_source=s.get("cle", "ia")) for s in conf.get("sources", []) if s.get("actif", True)]
    if os.environ.get("PROPOSITIONS_CSV_URL"):
        sources.append({"nom": "Formulaire : événements proposés", "type": "propositions",
                        "url": os.environ["PROPOSITIONS_CSV_URL"], "cle_source": "formulaire"})
    if os.environ.get("CALENDRIERS_CSV_URL"):
        try:
            sources += calendriers_soumis({"url": os.environ["CALENDRIERS_CSV_URL"]})
        except Exception as exc:
            print(f"Formulaire des calendriers illisible : {exc}")

    # Festivals : leurs programmations sont lues autour de leurs dates
    festivals = fest.charger(aujourd)
    try:
        n = fest.chercher_dates(festivals, aujourd, telecharger, texte_page)
        if n:
            print(f"Festivals : dates de {n} prochaine(s) édition(s) trouvées.")
    except Exception as exc:
        print(f"Recherche des dates de festivals en échec : {exc}")
    sources += fest.sources(festivals, aujourd)
    # Adresses réparées et sources découvertes automatiquement (collecteur/autoentretien.py)
    sources = autoentretien.appliquer(sources)

    bruts, series, rapport = [], [], []
    CACHE.mkdir(exist_ok=True)
    force = os.environ.get("TOUT_RELIRE") == "1"
    # Collecte en deux temps (11 nov. 2026) : ETAPE_COLLECTE=lecture lit les sources et garde chaque lecture en cache,
    # puis ETAPE_COLLECTE=assemblage bâtit le site à partir de ces lectures, sans relire. Chaque temps a sa propre limite
    # de durée : une lecture trop longue n'empêche plus la mise en ligne.
    etape = os.environ.get("ETAPE_COLLECTE", "")
    f_bloq = CACHE / "bloquees_lecture.json"
    if etape == "assemblage" and f_bloq.exists():
        connecteurs.BLOQUEES.update(json.loads(f_bloq.read_text(encoding="utf-8")))
    for i_src, s in enumerate(sources):
        print(f"→ {s['nom']} ({s['type']})")
        fichier_cache = CACHE / (re.sub(r"[^a-z0-9]+", "-", plat(s["nom"]))[:60] + ".json")
        if etape == "lecture" and i_src % 20 == 19:
            sauver_memoire(aujourd)  # une lecture interrompue garde ce que l'IA a déjà lu
        jours = s.get("jours_semaine")  # ex. [0, 3] = lundi et jeudi seulement (économise l'IA)
        deja_lue = False
        if fichier_cache.exists() and not force:  # déjà lue aujourd'hui (collecte relancée) : pas relue
            try:
                deja_lue = json.loads(fichier_cache.read_text(encoding="utf-8")).get("date") == aujourd.isoformat()
            except ValueError:
                pass
        if (etape == "assemblage" or deja_lue or jours and aujourd.weekday() not in jours and not force) and fichier_cache.exists():
            c = json.loads(fichier_cache.read_text(encoding="utf-8"))
            bruts += c["evenements"]
            series += c["series"]
            rapport.append({"source": s["nom"], "evenements": len(c["evenements"]), "series": len(c["series"]),
                            "erreur": None, "note": f"repris du {c['date']}",
                            **({"diagnostic": c["diagnostic"]} if c.get("diagnostic") else {})})
            print(f"  repris du cache ({c['date']})")
            continue
        try:
            connecteurs.DIAG.clear()
            # garde-fou : une source qui ne répond plus (page ou navigateur bloqué) est abandonnée après 10 minutes,
            # et sa dernière lecture réussie est reprise, au lieu de bloquer toute la collecte
            signal.signal(signal.SIGALRM, _trop_long)
            signal.alarm(600)
            try:
                e, sr = CONNECTEURS[s["type"]](s, aujourd, fin)
            finally:
                signal.alarm(0)
            # Page momentanément illisible (ex. « 504 Gateway Time-out » de la billetterie) : on garde la dernière
            # lecture réussie de moins de 7 jours plutôt que de faire disparaître tous ses spectacles
            if not e and not sr and any("illisible" in d for d in connecteurs.DIAG) and fichier_cache.exists():
                c = json.loads(fichier_cache.read_text(encoding="utf-8"))
                if c.get("date", "") >= (aujourd - timedelta(days=7)).isoformat():
                    e, sr = c["evenements"], c["series"]
                    connecteurs.DIAG.append(f"page illisible : données du {c['date']} conservées")
                    print(f"  page illisible : données du {c['date']} conservées")
            if s.get("festival"):
                # seulement ce qui tombe pendant le festival : le site d'un festival est parfois celui de la salle qui
                # l'organise (ex. les Sommets du cinéma d'animation sur cinematheque.qc.ca), qui annonce aussi le reste
                d1, d2 = s.get("fest_debut") or "", s.get("fest_fin") or ""
                for x in e + sr:
                    a = str(x.get("date") or x.get("debut") or "")[:10]
                    b = str(x.get("date") or x.get("fin") or a)[:10]
                    if not (d1 and d2 and a) or (a <= d2 and b >= d1):
                        x["festival"] = s["festival"]
            bruts += e
            series += sr
            rapport.append({"source": s["nom"], "evenements": len(e), "series": len(sr), "erreur": None,
                            **({"diagnostic": connecteurs.DIAG[:3]} if connecteurs.DIAG else {})})
            print(f"  {len(e)} événements, {len(sr)} séries")
            if e or sr:
                fichier_cache.write_text(json.dumps({"date": aujourd.isoformat(), "evenements": e, "series": sr,
                                                     "diagnostic": connecteurs.DIAG[:12]}, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            traceback.print_exc(limit=1)
            note = None
            if fichier_cache.exists():  # source en panne : on garde sa dernière lecture réussie
                c = json.loads(fichier_cache.read_text(encoding="utf-8"))
                bruts += c["evenements"]
                series += c["series"]
                note = f"en panne, données du {c['date']} conservées"
            rapport.append({"source": s["nom"], "evenements": 0, "series": 0, "erreur": str(exc)[:300], "note": note})

    if etape == "lecture":
        sauver_memoire(aujourd)
        f_bloq.write_text(json.dumps(sorted(connecteurs.BLOQUEES), ensure_ascii=False), encoding="utf-8")
        print(f"Lecture terminée : {len(bruts)} événements et {len(series)} séries en cache ; l'assemblage suit.")
        return 0

    # ---- Réparation automatique des sources devenues muettes (nouvelle adresse cherchée sur leur propre site)
    journal_rep = []
    try:
        etat_sante = json.loads((CACHE / "sante.json").read_text(encoding="utf-8")) if (CACHE / "sante.json").exists() else {}
        e_rep, s_rep, journal_rep = autoentretien.reparer(sources, rapport, CONNECTEURS["page_ia"], connecteurs.page_rendue,
                                                          telecharger, aujourd, fin, etat_sante.get("sources_ok", {}))
        bruts += e_rep
        series += s_rep
        for ligne in journal_rep:
            print(f"Réparation : {ligne}")
    except Exception as exc:
        print(f"Réparation automatique en échec : {exc}")

    # ---- Nettoyage
    nouveaux_lieux, geo_restants = [], int(reglages.get("max_geolocalisations", 40))
    geo_reessais, deja_reessayes = [int(reglages.get("max_relocalisations", 40))], set()  # salles connues sans position

    def lieu_canon(nom: str, adresse: str, ville: str) -> str | None:
        """Nom canonique de la salle, ou None si elle est hors de l'île."""
        nonlocal geo_restants
        nom = (nom or "").strip() or (adresse or "").split(",")[0].strip()
        if not nom or plat(nom) in PAS_DES_SALLES:
            return ""
        m = re.fullmatch(r"@(-?[\d.]+),(-?[\d.]+)", nom)
        if m:  # seulement des coordonnées : la salle connue la plus proche (moins de 150 m), sinon « à confirmer »
            return lieux.plus_proche(float(m.group(1)), float(m.group(2)), 0.15) or ""
        if hors_ile(nom, adresse, ville):
            return None
        c = lieux.trouver(nom)
        if c:
            # Salle connue mais jamais localisée (première recherche ratée) : on réessaie, avec l'adresse si on l'a
            ancien = lieux.data.get(c)
            if not (ancien or {}).get("lat") and geo_reessais[0] > 0 and c not in deja_reessayes \
                    and plat(c) not in PAS_DES_SALLES and c != "Lieu à confirmer":
                deja_reessayes.add(c)
                geo_reessais[0] -= 1
                connue = (ancien or {}).get("adresse", "") if isinstance(ancien, dict) else ""  # adresse notée dans lieux.json
                essais = ([f"{connue}, Montréal"] if connue else []) \
                    + ([f"{adresse}, Montréal"] if adresse and re.search(r"\d", adresse) else []) + [f"{c}, Montréal"]
                for requete in essais:
                    info = geo.localiser(requete, ua)
                    if info and not info.get("hors_ile") and dans_ile(info.get("lat"), info.get("lon")):
                        info["alias"] = (ancien or {}).get("alias", []) if isinstance(ancien, dict) else []
                        if connue:
                            info["adresse"] = connue
                        lieux.data[c] = info
                        print(f"  salle localisée au 2e essai : {c}")
                        break
            return c
        info = None
        if geo_restants > 0:
            geo_restants -= 1
            requete = f"{adresse}, Montréal" if adresse and re.search(r"\d", adresse) else f"{nom}, Montréal"
            info = geo.localiser(requete, ua)
            if info and info.get("hors_ile"):
                return None
            if info and not dans_ile(info.get("lat"), info.get("lon")):
                return None
        nom_propre = re.sub(r"\s*\(.*?\)\s*$", "", nom).strip() or nom
        nouveaux_lieux.append(nom_propre)
        return lieux.ajouter(nom_propre, info, alias=nom)

    events = []
    for b in bruts:
        try:
            d = date.fromisoformat(b["date"])
        except ValueError:
            continue
        if b["annule"] or d < aujourd or d > fin or not b["titre"]:
            continue
        if est_non_culturel(b["titre"], b["categorie"]):
            continue
        lieu = lieu_canon(b["lieu"], b["adresse"], b["ville"])
        if lieu is None and b["source"] == "formulaire" and b["lieu"]:
            # Proposition déjà jugée (vous ou le tri automatique) : une adresse imprécise ne la fait pas disparaître
            print(f"  formulaire : lieu « {b['lieu']} » non confirmé sur l'île par la carte ; gardé quand même")
            lieu = b["lieu"].strip()
        if lieu is None:
            continue
        if not lieu and b["source"] == "sorstu":
            continue  # Sors-tu? couvre tout le Québec et le Canada : sans salle, impossible de savoir si c'est à Montréal
        if b["discipline"] == "jeune":
            b["jeune_public"], b["discipline"] = True, ""
        disc = b["discipline"] if b["discipline"] in {"theatre", "musique", "danse", "cirque", "humour", "cinema", "lettres", "poesie", "conference", "atelier", "fete", "quiz", "social", "expo"} \
            else classer(b["titre"], b["categorie"], description=b.get("description", ""), defaut=b["discipline"])
        heure = b["heure"] if b["heure"] and re.fullmatch(r"\d{2}:\d{2}", b["heure"]) else None
        if "festapp.io" in (b["url"] or ""):
            heure = corriger_heure_festapp(b["date"], heure)
        e = {"date": b["date"], "heure": heure, "discipline": disc, "titre": b["titre"],
             "lieu": lieu or "Lieu à confirmer", "url": b["url"], "complet": bool(b["complet"]),
             "jeunePublic": bool(b["jeune_public"] or JEUNE.search(b["titre"])), "source": b["source"]}
        e.update(details(b))
        if b.get("aussi"):  # disciplines cochées en plus dans le formulaire
            e["aussi"] = [d for d in b["aussi"] if d != disc]
        if b.get("festival"):
            e["festival"] = b["festival"]
        e["_cat"] = b.get("categorie") or ""
        events.append(e)

    # Ville de Montréal : la salle, l'heure et la billetterie manquent souvent dans le fichier ouvert ; on lit la fiche
    # montreal.ca (une seule fois par page, mémoire cache/ville_pages.json), dates les plus proches d'abord.
    f_vp = CACHE / "ville_pages.json"
    memo_v = json.loads(f_vp.read_text(encoding="utf-8")) if f_vp.exists() else {}
    a_lire = sorted((e for e in events if e["source"] == "ville" and e["url"].startswith("http")
                     and (e["lieu"] == "Lieu à confirmer" or not e["heure"])), key=lambda e: e["date"])
    # Fiches lues depuis un ordinateur à Montréal (docs/mac/ville_mac.py) : montreal.ca refuse les serveurs de GitHub
    f_mac = CACHE / "ville_mac.json"
    mac = json.loads(f_mac.read_text(encoding="utf-8")) if f_mac.exists() else {}
    lues_v, fin_v, erreurs_v, par_mac = 0, time.time() + 10 * 60, [], 0
    for e in a_lire:
        if e["url"] in mac:
            m = mac[e["url"]]
            faux = "".join(f'<script type="application/ld+json">{j}</script>' for j in m.get("jsonld", [])) \
                + (f'<a href="{m["billets"]}">Billetterie</a>' if m.get("billets") else "")
            det_mac = connecteurs.details_ville(faux, e["date"])
            if det_mac:
                par_mac += 1
                if e["lieu"] == "Lieu à confirmer" and det_mac.get("lieu"):
                    e["lieu"] = lieu_canon(det_mac["lieu"], det_mac.get("adresse", ""), "Montréal") or "Lieu à confirmer"
                if not e["heure"] and det_mac.get("heure"):
                    e["heure"] = det_mac["heure"]
                if not e.get("billets") and det_mac.get("billets"):
                    e["billets"] = det_mac["billets"]
                if not e.get("prix") and det_mac.get("prix"):
                    e["prix"] = det_mac["prix"]
                if not e.get("affiche") and not e.get("image") and det_mac.get("image"):
                    # image de la fiche de la Ville (format carré ou 16:9 de leur banque d'images), avec le crédit
                    im = det_mac["image"]
                    e["affiche"] = {"url": im.replace("w_1920,", "w_1000,"), "petit": im.replace("w_1920,", "w_240,"),
                                    "credit": "Ville de Montréal", "lien": e["url"]}
                if det_mac.get("statut"):
                    e["statut"] = det_mac["statut"]  # « annule » (retiré plus bas) ou « reporte » (affiché)
                continue
        det = memo_v.get(e["url"])
        if det and det.get("_err") and det.get("le") != aujourd.isoformat():
            det = None  # échec un autre jour : on réessaie
        if det is None and lues_v < int(reglages.get("max_pages_ville", 500)) and time.time() < fin_v:
            lues_v += 1
            try:
                det = memo_v[e["url"]] = connecteurs.details_ville(telecharger(e["url"], "text/html").text, e["date"])
                time.sleep(0.3)
            except Exception as exc:
                det = memo_v[e["url"]] = {"_err": str(exc)[:120], "le": aujourd.isoformat()}
                erreurs_v.append(str(exc)[:120])
                if len(erreurs_v) >= 15 and not any("_err" not in v for v in memo_v.values()):
                    break  # le site refuse tout : inutile d'insister aujourd'hui
        if not det or det.get("_err"):
            continue
        if e["lieu"] == "Lieu à confirmer" and det.get("lieu"):
            e["lieu"] = lieu_canon(det["lieu"], det.get("adresse", ""), "Montréal") or "Lieu à confirmer"
        if not e["heure"] and det.get("heure"):
            e["heure"] = det["heure"]
        if not e.get("billets") and det.get("billets"):
            e["billets"] = det["billets"]
        if det.get("statut"):
            e["statut"] = det["statut"]
    f_vp.write_text(json.dumps(memo_v, ensure_ascii=False), encoding="utf-8")
    # Événements annoncés « annulé » par la Ville : retirés du calendrier
    annules = [e for e in events if e.get("statut") == "annule"]
    if annules:
        events[:] = [e for e in events if e.get("statut") != "annule"]
        print(f"Fiches de la Ville : {len(annules)} événements annulés retirés.")
    # Pages des sources refusées aux serveurs de GitHub (403), pour l'ordinateur à Montréal
    (SORTIE.parent / "pages_a_lire.json").write_text(json.dumps(sorted(connecteurs.BLOQUEES), ensure_ascii=False),
                                                     encoding="utf-8")
    # Liste des fiches encore incomplètes, pour l'ordinateur à Montréal (dates les plus proches d'abord)
    (SORTIE.parent / "ville_a_lire.json").write_text(json.dumps(list(dict.fromkeys(
        e["url"] for e in a_lire if (e["lieu"] == "Lieu à confirmer" or not e["heure"])
        and e["url"] not in mac and "montreal.ca/evenements/" in e["url"])), ensure_ascii=False), encoding="utf-8")
    notes = {"fiches_ville": {"lues": lues_v, "erreurs": len(erreurs_v), "exemples_erreurs": sorted(set(erreurs_v))[:3],
                              "completees_par_mac": par_mac,
                              "heures_trouvees": sum(1 for e in a_lire if e["heure"]),
                              "salles_trouvees": sum(1 for e in a_lire if e["lieu"] != "Lieu à confirmer")}}
    print(f"Fiches de la Ville : {notes['fiches_ville']}")
    if connecteurs.FORMULAIRE_RESUME:
        notes["formulaire"] = connecteurs.FORMULAIRE_RESUME
    if connecteurs.MODERATION:
        notes["formulaire_tri"] = connecteurs.MODERATION
        print(f"Formulaire, tri automatique : {connecteurs.MODERATION}")

    # Salles dont on connaît la vocation : un spectacle « autre » y prend la discipline de la salle
    for e in events:
        if e["discipline"] == "autre":
            l = plat(e["lieu"])
            for k, v in VOCATION_SALLES.items():
                if k in l:
                    e["discipline"] = v
                    break

    # Les « autre » : on lit la page de l'événement (le titre seul ne suffit pas, ex. « Marcia », « Feu Toute! »),
    # on reclasse avec sa description, puis l'IA tranche les cas qui restent, si elle est disponible.
    autres = [e for e in events if e["discipline"] == "autre"][:int(reglages.get("max_pages_autre", 80))]
    lus = 0
    for e in autres:
        if not e["url"].startswith("http"):
            continue
        try:
            resume = resume_page(telecharger(e["url"], "text/html").text)
            lus += 1
        except Exception:
            continue
        e["_extrait"] = resume
        d2 = classer(e["titre"], "", description=resume)
        if d2 != "autre":
            e["discipline"] = d2
    restants = [e for e in autres if e["discipline"] == "autre"]
    if restants and ia.disponible():
        try:
            lot = [{"titre": e["titre"], "lieu": e["lieu"],
                    "extrait": (f"(festival : {e['festival']}) " if e.get("festival") else "") + e.get("_extrait", "")}
                   for e in restants]
            for i, disc in ia.classer_lot(lot).items():
                if 0 <= i < len(restants):
                    restants[i]["discipline"] = disc
        except Exception as exc:
            print(f"Classement IA en échec : {exc}")
    # Encore « autre » mais rattaché à un festival : la discipline principale du festival (Casteliers → théâtre)
    disc_fest = {f["id"]: (f.get("disciplines") or [""])[0] for f in festivals}
    for e in events:
        if e["discipline"] == "autre" and disc_fest.get(e.get("festival") or ""):
            e["discipline"] = disc_fest[e["festival"]]
    for e in events:
        e.pop("_extrait", None)
    print(f"« Autre » : {len(autres)} à préciser, {lus} pages lues, {sum(e['discipline'] == 'autre' for e in events)} restent.")

    # Heures manquantes : on lit la page de l'événement (gratuit, sans IA). Songkick n'affiche pas d'heure,
    # mais le même concert trouvé sur le site de la salle (avec l'heure) remplace celui de Songkick au dédoublonnage.
    def completer_heures(events):
        """Heures manquantes lues sur la page de chaque événement (sans IA). Renvoie (sans heure, pages lues, rendues)."""
        f_heures = CACHE / "heures.json"
        memo = json.loads(f_heures.read_text(encoding="utf-8")) if f_heures.exists() else {}
        sans = [e for e in events if not e["heure"] and e["url"].startswith("http")
                and not any(d in e["url"] for d in reglages.get("sites_sans_heure", ["songkick.com"]))]
        # Mémoire par page ET par date (une page peut lister plusieurs représentations). Une page sans heure trouvée est
        # relue dans le navigateur (heure souvent affichée par JavaScript), puis réessayée après 7 jours.
        lues, rendues, vieux_h = 0, 0, (aujourd - timedelta(days=7)).isoformat()
        for e in sans:
            cle = e["url"] + "|" + e["date"]
            v = memo.get(cle)
            if isinstance(v, str):
                e["heure"] = v
                continue
            if isinstance(v, dict) and v.get("le", "") >= vieux_h:
                continue  # cherchée récemment, sans succès
            if lues >= int(reglages.get("max_pages_heure", 300)):
                continue
            try:
                try:
                    h = heure_page(telecharger(e["url"], "text/html").text, e["date"])
                except Exception:
                    h = None  # page refusée (403) ou en panne : le navigateur peut quand même l'afficher
                lues += 1
                if not h and rendues < int(reglages.get("max_pages_heure_nav", 60)):
                    rendues += 1
                    h = heure_page(connecteurs.page_rendue(e["url"]), e["date"])
                memo[cle] = h or {"le": aujourd.isoformat()}
                if h:
                    e["heure"] = h
                time.sleep(0.5)
            except Exception:
                memo[cle] = {"le": aujourd.isoformat()}
                continue
        # anciennes entrées (clé = page seule) : retirées
        memo = {k: v for k, v in memo.items() if "|" in k}
        f_heures.write_text(json.dumps(memo, ensure_ascii=False), encoding="utf-8")
        return sans, lues, rendues

    sans, lues, rendues = completer_heures(events)

    # Dernier recours, automatique : Claude lit la page des fiches encore sans heure ou sans salle (au plus 80 par nuit,
    # chaque page une seule fois par date ; Ville et Songkick exclues, leurs pages ne le disent pas ou sont bloquées)
    f_ia = CACHE / "champs_ia.json"
    memo_ia = json.loads(f_ia.read_text(encoding="utf-8")) if f_ia.exists() else {}
    corriges_ia, lus_ia = 0, 0
    if ia.disponible():
        for e in events:
            if (e["heure"] and e["lieu"] != "Lieu à confirmer") or not e["url"].startswith("http") \
                    or any(d in e["url"] for d in ("montreal.ca", "songkick.com", "facebook.com", "instagram.com")):
                continue
            cle = e["url"] + "|" + e["date"]
            r = memo_ia.get(cle)
            if r is not None and (r.get("_err") or (not r.get("heure") and not r.get("v"))):
                r = None  # échec technique, ou lu avant la 2e version (navigateur, heures d'ouverture) : on réessaie
            if r is not None and e["lieu"] == "Lieu à confirmer" and not r.get("lieu") and r.get("v", 0) < 4:
                r = None  # salle introuvable : relu dans le navigateur (3e version), puis données schema.org (4e)
            if r is None and lus_ia < int(reglages.get("max_pages_ia_champs", 80)):
                lus_ia += 1
                try:
                    try:
                        html = telecharger(e["url"], "text/html").text
                    except Exception:
                        html = ""
                    texte = texte_page(html, e["url"]) if html else ""
                    if len(texte) < 400 or e["lieu"] == "Lieu à confirmer":  # page en JavaScript, refusée, ou salle à trouver
                        html = connecteurs.page_rendue(e["url"])
                        texte = texte_page(html, e["url"])
                    r = dict(ia.champs_page(e["titre"], e["date"], texte) or {}, v=4)
                    if not r.get("lieu"):  # la salle est souvent dans les données schema.org de la page (ex. UdeM)
                        r.update({k: v for k, v in lieu_jsonld(html).items() if v})
                    memo_ia[cle] = r
                except Exception as exc:
                    r = memo_ia[cle] = {"_err": str(exc)[:80]}
            if not r or r.get("_err"):
                continue
            if not e["heure"] and r.get("heure"):
                e["heure"] = r["heure"]
                corriges_ia += 1
            if e["lieu"] == "Lieu à confirmer" and r.get("lieu"):
                e["lieu"] = lieu_canon(r["lieu"], r.get("adresse", ""), "Montréal") or "Lieu à confirmer"
                corriges_ia += 1
        f_ia.write_text(json.dumps(memo_ia, ensure_ascii=False), encoding="utf-8")
    print(f"Fiches complétées par l'IA : {corriges_ia} champs ({lus_ia} pages lues).")

    # Heures par la billetterie (11 nov. 2026) : une billetterie affiche forcément l'heure de la représentation.
    # 1) dans l'adresse elle-même (Tuxedo : …/voyage-voyage/20261111200000 = le 11 nov. à 20 h) ;
    # 2) sinon la page de billetterie lue (navigateur si besoin), puis par Claude. Au plus 80 pages par nuit.
    f_bil = CACHE / "heures_billetterie.json"
    memo_b = json.loads(f_bil.read_text(encoding="utf-8")) if f_bil.exists() else {}
    trouvees_b, lues_b = 0, 0
    BLOQUEES_BIL = ("zeffy.com", "ra.co", "facebook.com", "instagram.com", "ticketmaster", "eventbrite")
    for e in events:
        if e["heure"]:
            continue
        liens = [u for u in [e.get("billets") or "", *(e.get("_autres_urls") or [])]
                 if u.startswith("http") and u != e["url"] and not any(b in u for b in BLOQUEES_BIL)]
        for u in liens:
            m = re.search(r"/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})\d{2}/?(?:\?|$)", u)
            if m and f"{m[1]}-{m[2]}-{m[3]}" == e["date"] and 8 <= int(m[4]) <= 23:
                e["heure"] = f"{m[4]}:{m[5]}"
                trouvees_b += 1
                break
            cle = u + "|" + e["date"]
            r = memo_b.get(cle)
            if r is None and lues_b < int(reglages.get("max_billetteries", 80)):
                lues_b += 1
                r = {}
                try:
                    try:
                        html = telecharger(u, "text/html").text
                    except Exception:
                        html = ""
                    h = heure_page(html, e["date"]) if html else None
                    if not h:
                        html = connecteurs.page_rendue(u)
                        h = heure_page(html, e["date"])
                    if not h and ia.disponible():
                        h = (ia.champs_page(e["titre"], e["date"], texte_page(html, u)) or {}).get("heure")
                    r = {"heure": h} if h else {"le": aujourd.isoformat()}
                except Exception as exc:
                    r = {"_err": str(exc)[:80]}
                memo_b[cle] = r
            if r and r.get("heure"):
                e["heure"] = r["heure"]
                trouvees_b += 1
                break
    f_bil.write_text(json.dumps(memo_b, ensure_ascii=False), encoding="utf-8")
    print(f"Heures par la billetterie : {trouvees_b} trouvées ({lues_b} pages lues).")
    print(f"Heures : {len(sans)} événements sans heure, {lues} pages lues ({rendues} dans le navigateur), "
          f"{sum(1 for e in sans if e['heure'])} heures trouvées.")

    # Plusieurs disciplines possibles (ex. une performance : théâtre ET danse)
    for e in events:
        if e["discipline"] in ("expo", "cinema", "lettres", "poesie", "conference", "atelier", "fete", "quiz", "humour") or e.get("aussi"):
            continue
        e["discipline"], aussi = disciplines_aussi(e["titre"], e.get("resume", ""), e["discipline"], e["lieu"])
        if aussi:
            e["aussi"] = aussi

    # Affiches fournies à la main (collecteur/affiches.yaml → docs/affiches/)
    f_aff = Path(__file__).parent / "affiches.yaml"
    for a in (yaml.safe_load(f_aff.read_text(encoding="utf-8")) or []) if f_aff.exists() else []:
        for e in events:
            if e["date"] == str(a["date"]) and plat(a["titre_contient"]) in plat(e["titre"]):
                if a.get("image"):
                    e["image"] = "https://ccmtl.ca/" + a["image"]
                if a.get("aussi"):
                    e["aussi"] = list(dict.fromkeys([*(e.get("aussi") or []), *[d for d in a["aussi"] if d != e["discipline"]]]))[:2]

    # Improvisation (LNI, LIM, LIMM, ligues de bar) : Humour et cabaret, et aussi Théâtre ; la LIMM aussi Musique
    for e in events:
        if e["discipline"] in ("theatre", "humour", "autre") and RE_IMPRO.search(e["titre"]):
            aussi = [d for d in (e.get("aussi") or []) if d not in ("humour", "theatre")]
            if re.search(r"(?i)\bLIMM\b|impro\w* musical", e["titre"]):
                aussi = ["musique"] + aussi
            e["discipline"], e["aussi"] = "humour", (["theatre"] + aussi)[:2]

    # Ciné-concert, ciné-piano, projection avec musique en direct : Musique ET Cinéma
    for e in events:
        if re.search(r"(?i)ciné[- ]?(piano|concert|musique)|cine[- ]?concert|film[- ]concert", e["titre"]):
            autre = "cinema" if e["discipline"] == "musique" else "musique" if e["discipline"] == "cinema" else None
            if autre and autre not in (e.get("aussi") or []):
                e["aussi"] = ([autre] + (e.get("aussi") or []))[:2]

    # Jeune public : catégorie à part entière (la discipline d'origine est gardée dans « sous »)
    for e in events:
        if e["jeunePublic"] and e["discipline"] != "jeune":
            e["sous"], e["discipline"] = e["discipline"], "jeune"

    # Programmes saisis à la main (collecteur/manuels.json) : ajoutés à chaque collecte, dates passées exclues.
    manuels = json.loads(MANUELS.read_text(encoding="utf-8")) if MANUELS.exists() else {}
    for e in manuels.get("events", []):
        if aujourd.isoformat() <= e["date"] <= fin.isoformat():
            events.append(dict(e))
    print(f"Saisies à la main : {sum(1 for e in manuels.get('events', []) if aujourd.isoformat() <= e['date'] <= fin.isoformat())} événements.")

    events = dedoublonner(events)
    # 2e passage des heures après le dédoublonnage (fiches arrivées ou changées d'adresse en cours de route)
    try:
        sans2, lues2, _ = completer_heures(events)
        print(f"Heures, 2e passage : {len(sans2)} sans heure, {lues2} pages lues, {sum(1 for e in sans2 if e['heure'])} trouvées.")
    except Exception as exc:
        print(f"Heures, 2e passage en échec : {exc}")
    # Heure du même soir (12 nov. 2026) : un spectacle venu d'un agrégateur (Songkick, JamBase, ma.to…) sans heure, dans une
    # salle dont le site ou la billetterie n'annonce qu'UN spectacle ce soir-là, avec son heure : c'est presque sûrement
    # le même (ex. Club Soda le 18 nov. : « Koriass, Mara Tremblay… » chez Songkick = le concert-bénéfice de CIBL à 20 h).
    try:
        agreg = ("songkick.com", "jambase.com", "ma.to", "bandsintown.com", "allevents", "mtl.org", "montrealsecret")
        par_soir: dict = {}
        for e in events:
            if e.get("heure") and not any(a in e.get("url", "") for a in agreg):
                par_soir.setdefault((e["date"], plat(e["lieu"])), set()).add(e["heure"])
        n_soir = 0
        for e in events:
            if not e.get("heure") and any(a in e.get("url", "") for a in agreg):
                h = par_soir.get((e["date"], plat(e["lieu"])))
                if h and len(h) == 1:
                    e["heure"] = next(iter(h))
                    n_soir += 1
        print(f"Heures du même soir (seul spectacle annoncé par la salle) : {n_soir}.")
    except Exception as exc:
        print(f"Heures du même soir en échec : {exc}")
    # Dernier contrôle : un même spectacle vivant (pas un film ni une expo) ne doit pas apparaître deux fois le même jour
    import normalisation as _norm
    for f in festivals:
        _norm.SERIES_CONNUES.update({plat(f["nom"]), plat(f.get("court", ""))} - {""})
    events, redites = doublons_du_jour(events)
    notes["redites_retirees"] = redites[:200]
    print(f"Redites du même jour retirées : {len(redites)}")

    expos = []
    vus = set()
    for s in series:
        try:
            d1, d2 = date.fromisoformat(s["debut"]), date.fromisoformat(s["fin"])
        except ValueError:
            continue
        if d2 < aujourd or d1 > fin or est_non_culturel(s["titre"]):
            continue
        lieu = lieu_canon(s["lieu"], s.get("adresse", ""), s.get("ville", ""))
        if lieu is None:
            continue
        k = plat(s["titre"])[:40] + "|" + plat(lieu or "")[:20]
        if k in vus:
            continue
        vus.add(k)
        disc_s = s.get("discipline") or "expo"
        if disc_s == "autre":  # période sans discipline : on la devine ; une longue période inconnue est une exposition
            disc_s = classer(s["titre"], "", defaut="autre")  # titre seul : la description cite souvent le lieu (« Atelier de l'Île »)
            if disc_s == "autre":
                disc_s = "expo" if (d2 - d1).days >= 7 else classer(s["titre"], "", description=s.get("resume", ""), defaut="autre")
        x = {"titre": s["titre"], "lieu": lieu or "Lieu à confirmer", "debut": s["debut"], "fin": s["fin"],
             "discipline": disc_s, "url": s["url"]}
        x.update(details(s))
        if s.get("festival"):
            x["festival"] = s["festival"]
        if x["discipline"] not in ("expo", "jeune"):
            x["discipline"], aussi = disciplines_aussi(x["titre"], x.get("resume", ""), x["discipline"], x["lieu"])
            if aussi:
                x["aussi"] = aussi
        expos.append(x)
    for x in manuels.get("expos", []):
        k = plat(x["titre"])[:40] + "|" + plat(x["lieu"])[:20]
        if x["fin"] >= aujourd.isoformat() and x["debut"] <= fin.isoformat() and k not in vus:
            vus.add(k)
            expos.append(dict(x))
    # Pièces, films, concerts « à l'affiche du … au … » : le site les montre chaque jour de la période.
    # On les retire quand les dates précises sont déjà connues (même titre parmi les événements), quand la période
    # est celle d'un festival (ex. un film de CINEMANIA « du 2 au 15 nov. »), ou quand la même page est déjà là.
    titres = {plat(e["titre"])[:25] for e in events}
    pages, gardees = set(), []
    for x in expos:
        if x["discipline"] != "expo":
            if x.get("festival") or plat(x["titre"])[:25] in titres:
                continue
            if x.get("url") and x["url"] in pages:
                continue
            pages.add(x.get("url"))
        gardees.append(x)
    expos = gardees
    # La même exposition annoncée deux fois (« Exposition : X » à « Lieu à confirmer » et « X » à la bibliothèque) :
    # même titre (sans « Exposition : »), même date de fin -> on garde la version qui a une vraie salle.
    def _cle_expo(x):
        return plat(re.sub(r"(?i)^\s*exposition\s*[:\-–]\s*", "", x["titre"]))[:40] + "|" + x["fin"]
    meilleures: dict[str, dict] = {}
    for x in expos:
        k = _cle_expo(x)
        if k not in meilleures or (meilleures[k]["lieu"] == "Lieu à confirmer" and x["lieu"] != "Lieu à confirmer"):
            meilleures[k] = x
    expos = [x for x in expos if meilleures[_cle_expo(x)] is x]
    expos = doublons_expos(expos)  # même exposition sous plusieurs titres dans le même lieu
    expos.sort(key=lambda x: x["fin"])
    fest.etiqueter(events, festivals)
    # Un événement « autre » d'un festival d'une seule discipline prend celle du festival (ex. Casteliers → théâtre)
    disc_fest = {f["id"]: f["disciplines"][0] for f in festivals if len(f.get("disciplines", [])) == 1}
    for e in events:
        if e["discipline"] == "autre" and e.get("festival") in disc_fest:
            e["discipline"] = disc_fest[e["festival"]]

    # Style de musique (large) : indices sûrs d'abord (catégorie, titre, festival, salle), puis l'IA pour le reste.
    f_styles = CACHE / "styles.json"
    memo_s = json.loads(f_styles.read_text(encoding="utf-8")) if f_styles.exists() else {}
    a_demander = []
    for e in events:
        cat = e.pop("_cat", "")
        if "musique" not in (e["discipline"], *(e.get("aussi") or []), e.get("sous")):
            continue
        st = style_musique(e["titre"], cat, e["lieu"], e.get("resume", ""), e.get("festival"))
        cle = plat(e["titre"])[:40] + "|" + plat(e["lieu"])[:20]
        if not st and cle in memo_s:
            st = memo_s[cle] or None
        if st:
            e["style"] = st
        elif cle not in memo_s:
            a_demander.append((cle, e))
    if a_demander and ia.disponible():
        lot = a_demander[:int(reglages.get("max_styles_ia", 200))]
        try:
            for i in range(0, len(lot), 50):
                part = lot[i:i + 50]
                rep = ia.styles_lot([{"titre": e["titre"], "lieu": e["lieu"], "resume": e.get("resume", "")} for _, e in part])
                for j, (cle, e) in enumerate(part):
                    memo_s[cle] = rep.get(j, "")
                    if rep.get(j):
                        e["style"] = rep[j]
        except Exception as exc:
            print(f"Styles IA en échec : {exc}")
    f_styles.write_text(json.dumps(memo_s, ensure_ascii=False), encoding="utf-8")
    print(f"Styles : {sum(1 for e in events if e.get('style'))} concerts avec un style.")
    fest.etiqueter(expos, festivals)
    fest.publier(festivals, SORTIE.parent / "festivals.json")
    # Noms d'artistes extraits des titres par l'IA (« X présente : Kiwi Jr. » → Kiwi Jr.), gardés en mémoire
    f_art = Path(__file__).parent / "cache" / "artistes.json"
    memo_a = json.loads(f_art.read_text(encoding="utf-8")) if f_art.exists() else {}
    concerts = [e for e in events if "musique" in (e["discipline"], *(e.get("aussi") or []), e.get("sous"))]
    a_lire = list(dict.fromkeys(e["titre"] for e in concerts if plat(e["titre"]) not in memo_a))
    if a_lire and ia.disponible():
        try:
            for i in range(0, min(len(a_lire), int(reglages.get("max_artistes_ia", 1200))), 80):
                part = a_lire[i:i + 80]
                rep = ia.artistes_lot(part)
                for j, t in enumerate(part):
                    if j in rep:
                        memo_a[plat(t)] = rep[j]
        except Exception as exc:
            print(f"Artistes IA en échec : {exc}")
        f_art.write_text(json.dumps(memo_a, ensure_ascii=False), encoding="utf-8")
    for e in concerts:
        if plat(e["titre"]) in memo_a:
            e["_artistes"] = memo_a[plat(e["titre"])]
    print(f"Artistes : {sum(1 for e in concerts if e.get('_artistes'))} concerts avec des noms d'artistes extraits.")
    affiches_bloquees(events)  # avant la découverte : elle cherchera l'affiche sur la billetterie
    print(f"[{datetime.now():%H:%M:%S}] découverte (affiches, billets, liens d'écoute)…", flush=True)
    # Dans un processus séparé, arrêté de l'extérieur après 35 minutes quoi qu'il arrive (12 nov. 2026 : un arrêt
    # programmé à l'intérieur ne suffisait pas, l'assemblage a été annulé deux fois). Voir decouverte_seule.py.
    import subprocess
    cache = Path(__file__).parent / "cache"
    (cache / "_decouverte_resultat.json").unlink(missing_ok=True)
    (cache / "_decouverte_evenements.json").write_text(json.dumps(events, ensure_ascii=False, default=lambda o: list(o) if isinstance(o, (set, frozenset)) else str(o)), encoding="utf-8")
    delai = 35
    proc = subprocess.Popen([sys.executable, "-u", str(Path(__file__).parent / "decouverte_seule.py"),
                             str(int(reglages.get("max_recherches_decouverte", 500))), str(delai), aujourd.isoformat()])
    try:
        proc.wait(timeout=delai * 60)
    except subprocess.TimeoutExpired:
        print(f"Découverte arrêtée après {delai} minutes ; la suite reprendra à la prochaine collecte.", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    try:
        notes["catalogues"] = json.loads((cache / "_decouverte_resultat.json").read_text(encoding="utf-8"))["catalogues"]
    except Exception:
        pass
    # Ce qui a été trouvé (la mémoire, enregistrée en cours de route) est appliqué aux événements, sans réseau.
    try:
        n = decouverte.enrichir(events, aujourd, telecharger, 0, max_affiches=0, page_rendue=None)
        print(f"Découverte appliquée : {n} concerts ou films avec des liens vérifiés.")
    except Exception as exc:
        print(f"Découverte : application de la mémoire en échec : {exc}")
    (cache / "_decouverte_evenements.json").unlink(missing_ok=True)
    (cache / "_decouverte_resultat.json").unlink(missing_ok=True)
    print(f"[{datetime.now():%H:%M:%S}] découverte terminée", flush=True)
    try:
        images_des_salles(events, aujourd, reglages.get("images_de_salle"))
    except Exception as exc:
        print(f"Images de salle en échec : {exc}")
    # Liens ajoutés à la main (collecteur/liens_manuels.json) : passent avant les liens trouvés.
    fichier_liens = Path(__file__).parent / "liens_manuels.json"
    if fichier_liens.exists():
        for regle in json.loads(fichier_liens.read_text(encoding="utf-8")).get("liens", []):
            for e in events:
                if plat(regle["titre"]) in plat(e["titre"]):
                    ajout = [dict(l, source="manuel") for l in regle["liens"]]
                    e["liens"] = (ajout + [l for l in e.get("liens", []) if l["url"] not in {a["url"] for a in ajout}])[:8]
    for e in events:
        e.pop("_artistes", None)
        e.pop("_autres_urls", None)
        e.pop("_image_src", None)
    sauver_memoire(aujourd)

    # ---- Garde-fou : une collecte anormalement maigre ne remplace pas la précédente
    minimum = int(reglages.get("minimum_evenements", 30))
    if ancien and len(events) < max(minimum, 0.4 * len([e for e in ancien.get("events", []) if e["date"] >= aujourd.isoformat()])):
        print(f"ARRÊT : seulement {len(events)} événements; les données précédentes sont conservées.")
        RAPPORT.write_text(json.dumps({"date": aujourd.isoformat(), "statut": "conservé", "alerte": ia.ALERTE, "sources": rapport},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
        return 1

    # Corrections vérifiées à la main (collecteur/corrections.json) : heure, date ou retrait d'une sortie précise, et
    # horaire d'un spectacle à l'affiche (clé : son adresse). Elles passent avant ce que la collecte a lu.
    f_corr = Path(__file__).parent / "corrections.json"
    corr = json.loads(f_corr.read_text(encoding="utf-8")) if f_corr.exists() else {}
    n_corr, retires = 0, set()
    for c in corr.get("evenements", []):
        for e in events:
            if e["date"] == c["date"] and e["lieu"] == c["lieu"] and c["titre"].lower() in e["titre"].lower():
                n_corr += 1
                if c.get("retirer"):
                    retires.add(id(e))
                if "heure" in c:  # "" : heure lue par erreur (ex. heure de fin), retirée
                    e["heure"] = c["heure"] or None
                if c.get("nouvelle_date"):
                    e["date"] = c["nouvelle_date"]
    events = [e for e in events if id(e) not in retires]
    series_manuelles = corr.get("series", {})
    expos = [x for x in expos if x.get("url") not in corr.get("series_retirees", [])]  # doublons repérés à la main
    print(f"Corrections à la main : {n_corr} sorties corrigées ou retirées.")

    # Pièces, danse, cirque « à l'affiche du X au Y » : l'horaire de la semaine (relâches comprises), lu une fois par
    # Claude sur la page du spectacle. Le site s'en sert pour placer chaque représentation à la bonne heure.
    f_hor = CACHE / "horaires.json"
    memo_h = json.loads(f_hor.read_text(encoding="utf-8")) if f_hor.exists() else {}
    lus_h = 0
    for x in expos:
        if x.get("discipline") in (None, "", "expo") or not str(x.get("url", "")).startswith("http") \
                or "montreal.ca" in x["url"] or x.get("fin", "") < aujourd.isoformat():
            continue
        cle = f'{x["url"]}|{x["debut"]}|{x["fin"]}'
        # 2e méthode (v2) pour les pages où l'horaire n'a pas été trouvé : la page affichée dans le navigateur (calendrier
        # de représentations en JavaScript ou dans un cadre de billetterie), puis la page de la billetterie elle-même.
        # Horaire déjà lu mais périmé (la page ne montrait que la première représentation, ex. Centaur) alors que le
        # spectacle est encore à l'affiche : relu une fois, en passant par la billetterie
        ancien = memo_h.get(cle) or {}
        # (relu tous les 3 jours tant que le spectacle est à l'affiche, pas une seule fois)
        if ancien and not ancien.get("jours") and ancien.get("dates") and max(ancien["dates"]) < aujourd.isoformat() \
                and str(memo_h.get(cle + "|v5")) < (aujourd - timedelta(days=3)).isoformat():
            memo_h[cle] = {}
            memo_h[cle + "|v5"] = aujourd.isoformat()
            memo_h.pop(cle + "|v4", None)
        if memo_h.get(cle) == {} and not memo_h.get(cle + "|v2"):
            del memo_h[cle]
            memo_h[cle + "|v2"] = True
            essai_v2 = True
        elif memo_h.get(cle) == {} and not memo_h.get(cle + "|v3"):  # 3e essai : dates hors période acceptées
            del memo_h[cle]
            memo_h[cle + "|v3"] = True
            essai_v2 = True
        elif memo_h.get(cle) == {} and not memo_h.get(cle + "|v4"):  # 4e essai : les liens « Billets » de la page
            del memo_h[cle]
            memo_h[cle + "|v4"] = True
            essai_v2 = True
        elif memo_h.get(cle) == {} and str(memo_h.get(cle + "|v6")) < (aujourd - timedelta(days=7)).isoformat():
            # 5e essai, puis chaque semaine tant que rien n'est trouvé (une billetterie peut ouvrir ses dates plus tard)
            del memo_h[cle]
            memo_h[cle + "|v6"] = aujourd.isoformat()
            essai_v2 = True
        else:
            essai_v2 = bool(memo_h.get(cle + "|v2"))
        if cle not in memo_h and ia.disponible() and lus_h < int(reglages.get("max_horaires_ia", 60)):
            lus_h += 1
            try:
                html = telecharger(x["url"], "text/html").text
                texte = texte_page(html, x["url"])
                if len(texte) < 800 or essai_v2:  # page affichée par JavaScript (et, au 5e essai, en cliquant)
                    texte = texte_page(connecteurs.page_rendue(x["url"]), x["url"])
                h = ia.horaire_serie(x["titre"], x["debut"], x["fin"], texte)
                if not h and essai_v2:
                    # La billetterie : le lien connu, sinon les liens « Billets / Réserver » de la page du spectacle
                    # (ex. Théâtre d'Aujourd'hui : les dates et heures ne sont que dans la section billets)
                    cibles = [x["billets"]] if str(x.get("billets", "")).startswith("http") and x["billets"] != x["url"] else []
                    cibles += [u for u in liens_billets(html, x["url"]) if u not in cibles and u != x["url"]]
                    for u in cibles[:3]:
                        try:
                            # 12 s d'attente : les calendriers de billetterie (ex. TNM) se remplissent lentement ; à 2,5 s,
                            # la page était encore vide (12 nov. 2026 : vérifié, tout l'horaire apparaît à 15 s)
                            tb = texte_page(connecteurs.page_rendue(u, 12000), u)
                        except Exception as exc:
                            tb = ""
                            if "403" in str(exc):
                                connecteurs.BLOQUEES.add(u)  # lue demain par le Pi à Montréal
                                tb = texte_page(connecteurs.page_mac(u) or "", u)
                        if len(tb) > 200:
                            h = ia.horaire_serie(x["titre"], x["debut"], x["fin"], tb)
                            if h:
                                print(f"  horaire « {x['titre'][:30]} » trouvé sur la billetterie : {u[:70]}")
                                break
                memo_h[cle] = h
            except Exception as exc:
                print(f"  horaire « {x['titre'][:30]} » : {exc}")
        hm = series_manuelles.get(x["url"])
        if hm and hm.get("_titre") and plat(hm["_titre"]) not in plat(x["titre"]):
            hm = None  # même adresse pour plusieurs spectacles (page d'accueil d'une salle) : le titre doit correspondre
        h = ({k: v for k, v in hm.items() if not k.startswith("_")} if hm else None) or memo_h.get(cle)
        # Une liste de dates qui ne contient plus aucune représentation à venir (page qui ne montre que la première,
        # par exemple) ne sert pas : on n'en tient pas compte plutôt que de faire disparaître le spectacle.
        # Dates de la page toutes hors de la période annoncée (ex. agenda de la salle erroné) : la page du spectacle
        # fait foi, la période est corrigée.
        dts = sorted((h or {}).get("dates", {}))
        if h and not h.get("jours") and dts and (dts[-1] < x["debut"] or dts[0] > x["fin"]):
            x["debut"], x["fin"] = dts[0], dts[-1]
        elif h and dts:
            h = dict(h, dates={k: v for k, v in h["dates"].items() if x["debut"] <= k <= x["fin"]})
        if h and not h.get("jours") and not any(d >= aujourd.isoformat() for d in h.get("dates", {})):
            h = None
        if h:
            x["horaire"] = h
    f_hor.write_text(json.dumps(memo_h, ensure_ascii=False), encoding="utf-8")
    print(f"Horaires : {sum(1 for x in expos if x.get('horaire'))} spectacles à l'affiche avec leur horaire ({lus_h} pages lues).")

    # Séries qui encombrent sans informer : une « saison » sans salle de plus d'une semaine (ex. page Facebook d'un
    # festival), ou la page d'accueil d'un organisme dont les soirées sont déjà au calendrier avec leur date et leur heure.
    hotes_dates = {urlparse(e["url"]).netloc for e in events if e.get("heure") and e["url"].startswith("http")}
    avant_n = len(expos)
    expos = [x for x in expos if x.get("discipline") in (None, "", "expo") or not (
        (x["lieu"] in ("", "Lieu à confirmer") and x["debut"] < (date.fromisoformat(x["fin"]) - timedelta(days=7)).isoformat())
        or (urlparse(x.get("url", "")).path in ("", "/") and urlparse(x.get("url", "")).netloc in hotes_dates)
        # annonce de saison ou communiqué (« Espace Libre dévoile la série Mythologie ») : chaque spectacle a sa fiche
        or (re.search(r"(?i)d[ée]voil|communiqu|/actualit|/news/|/blogu?e?/|/presse/", x.get("url", "")) and not x.get("horaire")))]
    print(f"Séries retirées (sans salle, saison déjà détaillée ou annonce de saison) : {avant_n - len(expos)}")

    affiches_bloquees(events + expos)
    print(f"[{datetime.now():%H:%M:%S}] résumés…", flush=True)
    nettoyer_resumes(events + expos)
    print(f"[{datetime.now():%H:%M:%S}] exactitude…", flush=True)

    # ---- Exactitude (collecteur/qualite.py) : règles, contre-vérification des 3 prochains jours, contrôle du lundi
    try:
        events, expos, journal_q = qualite.regles(events, expos, lieux.coord)
        events, j2, stats_cv = qualite.contre_verifier(events, aujourd, telecharger, texte_page)
        journal_q += j2
        import normalisation as _norm
        journal_q += _norm.CONFLITS  # désaccords entre sources (heures différentes, heure par défaut écartée)
        controle = qualite.controle_aleatoire(events, aujourd, telecharger, texte_page, ia) if aujourd.weekday() == 0 else None
        a_surveiller = qualite.fiabilite(events, journal_q, controle, aujourd)
        qualite.ecrire(aujourd, journal_q, stats_cv, controle, a_surveiller)
        try:  # sorties annoncées par 2 sites ou plus (recoupées), pour le rapport du lundi
            fq = SORTIE.parent / "qualite.json"
            q = json.loads(fq.read_text(encoding="utf-8"))
            q["recoupees"] = {"total": len(events), "deux_sources_ou_plus": sum(1 for e in events if e.get("confirmations", 1) >= 2)}
            fq.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as exc:
            print(f"Recoupement : {exc}")
        notes["qualite"] = {"regles": len(journal_q), "contreverif": stats_cv,
                            "controle": controle and f"{controle['exactes']}/{controle['verifiees']} exactes"}
        print(f"Exactitude : {len(journal_q)} corrections ou alertes ; contre-vérification {stats_cv}"
              + (f" ; contrôle aléatoire {controle['exactes']}/{controle['verifiees']}" if controle else ""))
    except Exception as exc:
        traceback.print_exc(limit=2)
        print(f"Exactitude : contrôles en échec ({exc}) ; publication quand même")
    print(f"[{datetime.now():%H:%M:%S}] traductions…", flush=True)
    traduire_resumes(events + expos)
    print(f"[{datetime.now():%H:%M:%S}] écriture du site…", flush=True)

    utilises = {e["lieu"] for e in events} | {x["lieu"] for x in expos}
    noms_sources = conf.get("noms_sources", {})
    data = {
        "version": 3,
        "licence": "CC BY-NC 4.0 (https://creativecommons.org/licenses/by-nc/4.0/) : réutilisation non commerciale en citant ccmtl.ca",
        "miseAJour": aujourd.isoformat(),
        "debut": aujourd.isoformat(),
        "fin": fin.isoformat(),
        "completJusqua": (aujourd + timedelta(days=int(reglages.get("horizon_complet_jours", 14)) - 1)).isoformat(),
        "sources": {k: v for k, v in noms_sources.items() if any(e["source"] == k for e in events)},
        "events": events,
        "expos": expos,
        "lieux": {n: lieux.coord(n) for n in sorted(utilises)},
    }
    if ancien:  # les événements passés de la publication précédente rejoignent les archives du mois
        try:
            n_arch = archives.ajouter(ancien.get("events", []), aujourd.isoformat(), SORTIE.parent / "archives", ancien.get("lieux"))
            print(f"Archives : {n_arch} événements passés ajoutés.")
        except Exception as exc:
            print(f"Archives en échec : {exc}")
    agenda.publier(events, SORTIE.parent / "ics")  # un fichier .ics par événement (ajout direct au calendrier)
    SORTIE.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    try:  # page « Nos sources » : une erreur ici ne doit pas empêcher le rapport et la mémoire des salles
        ecrire_liste_sources(conf, rapport)
    except Exception as exc:
        print(f"Liste des sources en échec : {exc}")
    LIEUX.write_text(json.dumps(lieux.data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    if journal_rep:
        notes["reparations"] = journal_rep
    # ---- Découverte de nouvelles sources : une fois par semaine (dimanche), ou sur demande (DECOUVERTE=1)
    if aujourd.weekday() == 6 or os.environ.get("DECOUVERTE") == "1":
        try:
            notes["decouverte"] = autoentretien.decouvrir(events, sources, rapport, CONNECTEURS["page_ia"], telecharger,
                                                          aujourd, fin)
            for ligne in notes["decouverte"]:
                print(f"Découverte : {ligne}")
        except Exception as exc:
            print(f"Découverte en échec : {exc}")
    if connecteurs.ROBOTS_REFUS:  # pages que leur site demande aux robots de ne pas lire (mode observer)
        notes["robots_refus"] = dict(sorted(connecteurs.ROBOTS_REFUS.items(), key=lambda x: -x[1])[:60])
    RAPPORT.write_text(json.dumps({"date": aujourd.isoformat(), "statut": "publié", "evenements": len(events),
                                   "expositions": len(expos), "nouvelles_salles": sorted(set(nouveaux_lieux)),
                                   "notes": notes, "alerte": ia.ALERTE, "sources": rapport}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK : {len(events)} événements, {len(expos)} expositions/pièces à l'affiche, "
          f"{len(set(nouveaux_lieux))} nouvelles salles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
