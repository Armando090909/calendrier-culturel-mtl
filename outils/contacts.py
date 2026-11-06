"""Coordonnées publiques des salles, festivals et organismes du calendrier, pour leur écrire (promotion de ccmtl).
Pour chaque source de collecteur/sources.yaml (sauf les agrégateurs) : la page d'accueil du site, puis sa page « Contact »
si elle existe ; on garde les adresses courriel publiées (liens mailto: et texte) et l'adresse de la page de contact.
Respecte robots.txt (pas de lecture des pages que le site demande aux robots d'éviter). Une requête par seconde au plus.
Résultat : outils/diag/contacts.json. Lancé par .github/workflows/diagnostic.yml."""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "collecteur"))
import connecteurs as c  # noqa: E402
import yaml  # noqa: E402

AGREGATEURS = ("songkick.com", "sorstu.ca", "ra.co", "eventbrite", "montreal.ca", "festapp.io", "lepointdevente.com",
               "ma.to", "luma.com", "askapunk", "zeffy.com", "restomontreal", "panm360", "tuxedobillet", "facebook.com",
               "instagram.com", "evenko.ca", "spectaculos", "data.montreal", "donneesquebec", "google.com")
COURRIEL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IGNORES = re.compile(r"(?i)\.(png|jpe?g|gif|webp|svg)$|sentry|wixpress|example\.|domain\.|email@|nom@|votre|your|"
                     r"noreply|no-reply|donotreply|@2x|privacy|confidentialit|webmaster")
PREFERES = re.compile(r"(?i)^(info|programmation|programmation|booking|communication|communications|presse|press|media|"
                      r"medias|marketing|bonjour|hello|contact|salut|direction|diffusion)@")


def courriels(html: str) -> list[str]:
    trouves = re.findall(r'mailto:([^"\'?>\s]+)', html or "") + COURRIEL.findall(html or "")
    out = []
    for x in trouves:
        x = x.strip().strip(".").lower()
        if COURRIEL.fullmatch(x) and not IGNORES.search(x) and x not in out:
            out.append(x)
    return sorted(out, key=lambda x: (not PREFERES.search(x), len(x)))[:5]


def page_contact(html: str, base: str) -> str:
    from bs4 import BeautifulSoup
    for a in BeautifulSoup(html or "", "html.parser").find_all("a", href=True):
        t = (a.get_text(" ", strip=True) + " " + a["href"]).lower()
        if re.search(r"contact|nous[- ]joindre|joindre|écrivez|ecrivez|presse|press|medias|média", t):
            u = urljoin(base, a["href"])
            if urlparse(u).netloc == urlparse(base).netloc and not u.startswith("mailto:"):
                return u
    return ""


MEDIAS = [  # médias culturels montréalais (pages d'accueil) : on y cherche le courriel de la rédaction
    ("PAN M 360", "https://panm360.com/"), ("Cult MTL", "https://cultmtl.com/about-contact"),
    ("MTL Blog", "https://www.mtlblog.com/"), ("Narcity Québec", "https://www.narcity.com/quebec"),
    ("Nightlife.ca", "https://nightlife.ca/"), ("Urbania", "https://urbania.ca/"), ("Journal Métro", "https://journalmetro.com/"),
    ("Baron Mag", "https://www.baronmag.com/"), ("Le Devoir (culture)", "https://www.ledevoir.com/culture"),
    ("CIBL 101,5", "https://cibl1015.com/"), ("CISM 89,3", "https://cism893.ca/"), ("CKUT 90,3", "https://ckut.ca/"),
    ("Radio Centre-Ville", "https://radiocentreville.com/"), ("Montréal Campus", "https://montrealcampus.ca/"),
    ("Quartier Libre", "https://quartierlibre.ca/"), ("Le Délit", "https://www.delitfrancais.com/"),
    ("The McGill Daily", "https://www.mcgilldaily.com/"), ("The Link (Concordia)", "https://thelinknewspaper.ca/"),
    ("The Concordian", "https://theconcordian.com/"), ("Le Mouton Noir / Bible urbaine", "https://labibleurbaine.com/"),
    ("Sors-tu? (blogue)", "https://sorstu.ca/"), ("Pieuvre.ca", "https://www.pieuvre.ca/"), ("Mattv", "https://mattv.ca/"),
    ("Tourisme Montréal (mtl.org)", "https://www.mtl.org/fr"),
]


def un_site(nom, url, salle=""):
    accueil = url if url.count("/") > 3 and not url.endswith(".ca/") else f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
    r = {"nom": nom, "salle": salle, "site": accueil, "courriels": [], "contact": ""}
    try:
        html = c.telecharger(accueil, "text/html").text
        r["courriels"] = courriels(html)
        r["contact"] = page_contact(html, accueil)
        if r["contact"] and not r["courriels"]:
            time.sleep(1)
            r["courriels"] = courriels(c.telecharger(r["contact"], "text/html").text)
    except Exception as exc:
        r["erreur"] = str(exc)[:120]
    print(r["nom"], r["courriels"][:2], r["contact"][:60], r.get("erreur", ""))
    time.sleep(1)
    return r


def main():
    medias = [un_site(n, u) for n, u in MEDIAS]
    (RACINE / "outils" / "diag" / "contacts_medias.json").write_text(json.dumps(medias, ensure_ascii=False, indent=1), encoding="utf-8")
    if (RACINE / "outils" / "diag" / "contacts.json").exists():
        return  # salles déjà faites
    conf = yaml.safe_load((RACINE / "collecteur" / "sources.yaml").read_text(encoding="utf-8"))
    sources = conf if isinstance(conf, list) else conf.get("sources", [])
    vus, out = set(), []
    for s in sources:
        url = str(s.get("url") or "")
        hote = urlparse(url).netloc.lower().removeprefix("www.")
        if not url.startswith("http") or any(a in hote for a in AGREGATEURS) or hote in vus:
            continue
        vus.add(hote)
        accueil = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
        r = {"nom": s.get("nom"), "salle": s.get("lieu") or "", "site": accueil, "courriels": [], "contact": ""}
        try:
            html = c.telecharger(accueil, "text/html").text
            r["courriels"] = courriels(html)
            r["contact"] = page_contact(html, accueil)
            if r["contact"] and len(r["courriels"]) < 1:
                time.sleep(1)
                r["courriels"] = courriels(c.telecharger(r["contact"], "text/html").text)
        except Exception as exc:
            r["erreur"] = str(exc)[:120]
        out.append(r)
        print(r["nom"], r["courriels"][:2], r["contact"][:60], r.get("erreur", ""))
        time.sleep(1)
    (RACINE / "outils" / "diag" / "contacts.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} sites ; {sum(1 for r in out if r['courriels'])} avec une adresse courriel ; "
          f"{sum(1 for r in out if not r['courriels'] and r['contact'])} avec une page de contact seulement.")


if __name__ == "__main__":
    main()
