"""Comptes Instagram à identifier dans la publication du lundi : la salle et l'artiste de chaque sortie choisie.
Cherchés seulement sur les pages officielles (site de la salle, page de l'événement, billetterie), jamais devinés.
- salle : le compte Instagram le plus présent sur le site de la salle (adresse connue dans collecteur/sources.yaml) ;
- artiste : un compte trouvé sur la page de l'événement, autre que celui de la salle, et dont le nom ressemble au titre.
Un compte « sûr » est identifié automatiquement ; un compte « à confirmer » est proposé dans l'aperçu du dimanche et
n'est utilisé que si Alexandre l'écrit (consigne `tag danse : @compte`)."""
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "collecteur"))

RE_IG = re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,30})/?(?=[\"'?#\s<]|$)")
PAS_DES_COMPTES = {"p", "reel", "reels", "explore", "accounts", "stories", "tv", "sharer", "share", "direct", "about",
                   "developer", "legal", "instagram", "ccmtl.ca", "ccmtl", "web", "privacy", "help"}
# agrégateurs et billetteries : leur compte n'est ni la salle ni l'artiste
AGREGATEURS = {"sorstu", "sorstu.ca", "songkick", "eventbrite", "lepointdevente", "ticketmaster", "ticketmasterca",
               "evenko", "festapp", "tuxedobillet", "ra.co", "residentadvisor", "showpass", "dice.fm", "zeffy",
               "villedemontreal", "mtlville", "panm360", "spectaculos", "admission", "ticketpro", "sorstuca",
               "pointdevente", "festivalfinder", "quoifaire", "mtlblog", "narcity", "tourismemontreal"}


def comptes(html: str) -> list[str]:
    """Comptes Instagram présents dans une page, du plus fréquent au moins fréquent."""
    c = Counter(h.lower().rstrip(".") for h in RE_IG.findall(html or ""))
    plat_ = lambda x: re.sub(r"[._]", "", x)  # noqa: E731
    agr = {plat_(a) for a in AGREGATEURS}
    return [h for h, _ in c.most_common() if h not in PAS_DES_COMPTES and not any(a in plat_(h) for a in agr)]


def _lire(url: str) -> str:
    import connecteurs
    try:
        return connecteurs.telecharger(url, "text/html").text
    except Exception:
        return ""


def _ressemble(compte: str, titre: str) -> bool:
    """Le nom du compte reprend un mot significatif du titre (ex. « catherineleducmusique » pour « Catherine Leduc »)."""
    from normalisation import plat
    c = plat(compte).replace(" ", "")
    mots = [m for m in plat(titre).split() if len(m) >= 4 and m not in ("avec", "spectacle", "concert", "lancement", "soiree",
                                                                          "montreal", "theatre", "festival", "musique")]
    return any(m in c for m in mots)


def sites_des_salles() -> dict:
    """Nom de salle → page d'accueil de son site (sources.yaml, champ « lieu »)."""
    import yaml
    conf = yaml.safe_load((RACINE / "collecteur" / "sources.yaml").read_text(encoding="utf-8"))
    out = {}
    for s in conf if isinstance(conf, list) else conf.get("sources", []):
        u, lieu = str(s.get("url") or ""), s.get("lieu")
        if lieu and u.startswith("http") and not any(a in u for a in ("songkick", "sorstu", "ra.co", "ma.to", "luma.com",
                                                                        "zeffy", "eventbrite", "montreal.ca")):
            out.setdefault(lieu, f"{urlparse(u).scheme}://{urlparse(u).netloc}/")
    f = RACINE / "outils" / "diag" / "contacts.json"
    if f.exists():
        import json
        for r in json.loads(f.read_text(encoding="utf-8")):
            if r.get("salle") and r.get("site"):
                out.setdefault(r["salle"], r["site"])
    return out


def _festivals() -> list:
    import json
    f = RACINE / "docs" / "festivals.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


FESTIVALS = _festivals()


def trouver(picks: list[dict]) -> dict:
    """{discipline: {"salle": {"compte", "sur", "source"}, "artiste": {...}}} pour chaque sortie."""
    sites = sites_des_salles()
    out = {}
    for p in picks:
        e, k = p["e"], p["k"]
        r = {}
        # la salle : son propre site
        site = sites.get(e["lieu"])
        if site:
            cs = comptes(_lire(site))
            if cs:
                r["salle"] = {"compte": cs[0], "sur": True, "source": site}
        # l'artiste : page de l'événement, billetterie, page d'où vient l'affiche
        pages = [u for u in dict.fromkeys([e.get("url"), e.get("billets"), (e.get("affiche") or {}).get("lien")])
                 if str(u or "").startswith("http") and "montreal.ca" not in str(u)]
        salle = (r.get("salle") or {}).get("compte")
        for u in pages[:3]:
            cs = [c for c in comptes(_lire(u)) if c != salle]
            if "salle" not in r:  # compte au nom de la salle sur la page de l'événement (ex. maison de la culture)
                s_ = next((c for c in cs if _ressemble(c, e["lieu"])), None)
                if s_:
                    r["salle"] = {"compte": s_, "sur": True, "source": u}
                    salle = s_
                    cs = [c for c in cs if c != s_]
            proches = [c for c in cs if _ressemble(c, e["titre"])]
            if proches:
                r["artiste"] = {"compte": proches[0], "sur": True, "source": u}
                break
            if cs and "artiste" not in r and urlparse(u).netloc != urlparse(site or "").netloc:
                r["artiste"] = {"compte": cs[0], "sur": False, "source": u}
        # le festival, si la sortie en fait partie : son propre site
        if e.get("festival"):
            fest = next((f for f in FESTIVALS if f.get("id") == e["festival"]), None)
            if fest and str(fest.get("site") or "").startswith("http"):
                cs = [c for c in comptes(_lire(fest["site"])) if c not in {(v or {}).get("compte") for v in r.values()}]
                if cs:
                    r["festival"] = {"compte": cs[0], "sur": True, "source": fest["site"]}
                    if (r.get("artiste") or {}).get("compte") == cs[0]:
                        del r["artiste"]
        out[k] = r
        print(f"  identification {k} : " + ", ".join(f"{q} @{v['compte']}{'' if v['sur'] else ' (à confirmer)'}"
                                                    for q, v in r.items()) or "rien")
    return out


def comptes_retenus(s: dict, k: str) -> list[str]:
    """Comptes à identifier pour la sortie « k » : les sûrs, plus ceux confirmés ou ajoutés par Alexandre."""
    t = (s.get("tags") or {}).get(k) or {}
    if t.get("aucun"):
        return []
    out = [v["compte"] for q, v in t.items() if isinstance(v, dict) and v.get("compte") and (v.get("sur") or v.get("confirme"))]
    return list(dict.fromkeys(out + list(t.get("ajouts") or [])))[:3]


if __name__ == "__main__":  # essai : la dernière sélection enregistrée
    import json
    f = sorted((RACINE / "outils" / "reseaux" / "selections").glob("*.json"))[-1]
    s = json.loads(f.read_text(encoding="utf-8"))
    r = trouver(s["picks"])
    (RACINE / "outils" / "diag" / "identification.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
