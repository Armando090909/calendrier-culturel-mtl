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
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import agenda  # noqa: E402
import archives  # noqa: E402
import decouverte  # noqa: E402
import festivals as fest  # noqa: E402
import geo  # noqa: E402
import ia  # noqa: E402
from connecteurs import CONNECTEURS, sauver_memoire, calendriers_soumis, heure_page, resume_page, telecharger, texte_page  # noqa: E402
import connecteurs  # noqa: E402
from normalisation import Lieux, classer, corriger_heure_festapp, dans_ile, dedoublonner, disciplines_aussi, est_non_culturel, hors_ile, plat, style_musique, doublons_du_jour, doublons_expos  # noqa: E402

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

    bruts, series, rapport = [], [], []
    CACHE.mkdir(exist_ok=True)
    force = os.environ.get("TOUT_RELIRE") == "1"
    for s in sources:
        print(f"→ {s['nom']} ({s['type']})")
        fichier_cache = CACHE / (re.sub(r"[^a-z0-9]+", "-", plat(s["nom"]))[:60] + ".json")
        jours = s.get("jours_semaine")  # ex. [0, 3] = lundi et jeudi seulement (économise l'IA)
        if jours and aujourd.weekday() not in jours and not force and fichier_cache.exists():
            c = json.loads(fichier_cache.read_text(encoding="utf-8"))
            bruts += c["evenements"]
            series += c["series"]
            rapport.append({"source": s["nom"], "evenements": len(c["evenements"]), "series": len(c["series"]),
                            "erreur": None, "note": f"repris du {c['date']}"})
            print(f"  repris du cache ({c['date']})")
            continue
        try:
            connecteurs.DIAG.clear()
            e, sr = CONNECTEURS[s["type"]](s, aujourd, fin)
            # Page momentanément illisible (ex. « 504 Gateway Time-out » de la billetterie) : on garde la dernière
            # lecture réussie de moins de 7 jours plutôt que de faire disparaître tous ses spectacles
            if not e and not sr and any("illisible" in d for d in connecteurs.DIAG) and fichier_cache.exists():
                c = json.loads(fichier_cache.read_text(encoding="utf-8"))
                if c.get("date", "") >= (aujourd - timedelta(days=7)).isoformat():
                    e, sr = c["evenements"], c["series"]
                    connecteurs.DIAG.append(f"page illisible : données du {c['date']} conservées")
                    print(f"  page illisible : données du {c['date']} conservées")
            if s.get("festival"):
                for x in e + sr:
                    x["festival"] = s["festival"]
            bruts += e
            series += sr
            rapport.append({"source": s["nom"], "evenements": len(e), "series": len(sr), "erreur": None,
                            **({"diagnostic": connecteurs.DIAG[:3]} if connecteurs.DIAG else {})})
            print(f"  {len(e)} événements, {len(sr)} séries")
            if e or sr:
                fichier_cache.write_text(json.dumps({"date": aujourd.isoformat(), "evenements": e, "series": sr},
                                                    ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            traceback.print_exc(limit=1)
            note = None
            if fichier_cache.exists():  # source en panne : on garde sa dernière lecture réussie
                c = json.loads(fichier_cache.read_text(encoding="utf-8"))
                bruts += c["evenements"]
                series += c["series"]
                note = f"en panne, données du {c['date']} conservées"
            rapport.append({"source": s["nom"], "evenements": 0, "series": 0, "erreur": str(exc)[:300], "note": note})

    # ---- Nettoyage
    nouveaux_lieux, geo_restants = [], int(reglages.get("max_geolocalisations", 40))

    def lieu_canon(nom: str, adresse: str, ville: str) -> str | None:
        """Nom canonique de la salle, ou None si elle est hors de l'île."""
        nonlocal geo_restants
        nom = (nom or "").strip() or (adresse or "").split(",")[0].strip()
        if not nom:
            return ""
        m = re.fullmatch(r"@(-?[\d.]+),(-?[\d.]+)", nom)
        if m:  # seulement des coordonnées : la salle connue la plus proche (moins de 150 m), sinon « à confirmer »
            return lieux.plus_proche(float(m.group(1)), float(m.group(2)), 0.15) or ""
        if hors_ile(nom, adresse, ville):
            return None
        c = lieux.trouver(nom)
        if c:
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
        disc = b["discipline"] if b["discipline"] in {"theatre", "musique", "danse", "cirque", "humour", "cinema", "lettres", "poesie", "conference", "atelier", "fete", "quiz", "expo"} \
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
    f_vp.write_text(json.dumps(memo_v, ensure_ascii=False), encoding="utf-8")
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
            h = heure_page(telecharger(e["url"], "text/html").text, e["date"])
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
            if r is not None and r.get("_err"):
                r = None  # échec technique (réponse illisible, site en panne) : on réessaie
            if r is None and lus_ia < int(reglages.get("max_pages_ia_champs", 80)):
                lus_ia += 1
                try:
                    html = telecharger(e["url"], "text/html").text
                    r = memo_ia[cle] = ia.champs_page(e["titre"], e["date"], texte_page(html, e["url"])) or {}
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
    try:
        n = decouverte.enrichir(events, aujourd, telecharger, int(reglages.get("max_recherches_decouverte", 500)))
        print(f"Découverte : {n} concerts ou films avec des liens vérifiés.")
    except Exception as exc:
        print(f"Liens de découverte en échec : {exc}")
    for e in events:
        e.pop("_artistes", None)
        e.pop("_autres_urls", None)
    sauver_memoire(aujourd)

    # ---- Garde-fou : une collecte anormalement maigre ne remplace pas la précédente
    minimum = int(reglages.get("minimum_evenements", 30))
    if ancien and len(events) < max(minimum, 0.4 * len([e for e in ancien.get("events", []) if e["date"] >= aujourd.isoformat()])):
        print(f"ARRÊT : seulement {len(events)} événements; les données précédentes sont conservées.")
        RAPPORT.write_text(json.dumps({"date": aujourd.isoformat(), "statut": "conservé", "alerte": ia.ALERTE, "sources": rapport},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
        return 1

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
        if cle not in memo_h and ia.disponible() and lus_h < int(reglages.get("max_horaires_ia", 40)):
            lus_h += 1
            try:
                html = telecharger(x["url"], "text/html").text
                texte = texte_page(html, x["url"])
                if len(texte) < 800:  # page affichée par JavaScript
                    texte = texte_page(connecteurs.page_rendue(x["url"]), x["url"])
                memo_h[cle] = ia.horaire_serie(x["titre"], x["debut"], x["fin"], texte)
            except Exception as exc:
                print(f"  horaire « {x['titre'][:30]} » : {exc}")
        h = memo_h.get(cle)
        # Une liste de dates qui ne contient plus aucune représentation à venir (page qui ne montre que la première,
        # par exemple) ne sert pas : on n'en tient pas compte plutôt que de faire disparaître le spectacle.
        if h and not h.get("jours") and not any(d >= aujourd.isoformat() for d in h.get("dates", {})):
            h = None
        if h:
            x["horaire"] = h
    f_hor.write_text(json.dumps(memo_h, ensure_ascii=False), encoding="utf-8")
    print(f"Horaires : {sum(1 for x in expos if x.get('horaire'))} spectacles à l'affiche avec leur horaire ({lus_h} pages lues).")

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
