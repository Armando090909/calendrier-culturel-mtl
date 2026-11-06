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


def _cfemail(code: str) -> str:
    """Adresse protégée par Cloudflare (data-cfemail) : décodage XOR."""
    try:
        k = int(code[:2], 16)
        return "".join(chr(int(code[i:i + 2], 16) ^ k) for i in range(2, len(code), 2))
    except ValueError:
        return ""


def _devoiler(html: str) -> str:
    """Rend lisibles les adresses masquées : Cloudflare, « info [at] site [dot] ca », « info(at)site.ca »."""
    html = html or ""
    extra = [_cfemail(c) for c in re.findall(r'data-cfemail="([0-9a-f]+)"', html)]
    extra += [_cfemail(c) for c in re.findall(r"/cdn-cgi/l/email-protection#([0-9a-f]+)", html)]
    t = re.sub(r"\s*[\[(]\s*(?:at|arobase|@)\s*[\])]\s*", "@", html, flags=re.I)
    t = re.sub(r"\s*[\[(]\s*(?:dot|point)\s*[\])]\s*", ".", t, flags=re.I)
    return t + " " + " ".join(extra)


def courriels(html: str) -> list[str]:
    html = _devoiler(html)
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


CHEMINS = ("contact", "contact/", "nous-joindre", "nous-joindre/", "contactez-nous", "fr/contact", "en/contact",
           "contact-us", "a-propos", "about", "infos")


def completer(r: dict) -> dict:
    """2e passage pour un site sans courriel : sa page de contact et les adresses habituelles, lues aussi dans le
    navigateur (adresses écrites par JavaScript ou masquées), en respectant robots.txt."""
    if r.get("courriels"):
        return r
    base = r["site"] if r["site"].count("/") <= 3 else f"{urlparse(r['site']).scheme}://{urlparse(r['site']).netloc}/"
    essais = list(dict.fromkeys([r.get("contact") or "", r["site"]] + [base + c for c in CHEMINS]))
    lus = 0
    for u in [x for x in essais if x]:
        if lus >= 6 or not c.robots_permet(u):
            continue
        html = ""
        try:
            html = c.telecharger(u, "text/html").text
        except Exception:
            pass
        if not courriels(html):
            try:
                html = c.page_rendue(u)
            except Exception:
                html = html or ""
        lus += 1
        trouves = courriels(html)
        if trouves:
            r["courriels"], r["contact"] = trouves, r.get("contact") or u
            r.pop("erreur", None)
            break
        time.sleep(1)
    print(r["nom"], r["courriels"][:2])
    return r


def main():
    d = RACINE / "outils" / "diag"
    for nom in ("contacts.json", "contacts_medias.json"):
        f = d / nom
        if f.exists():
            rs = [completer(r) for r in json.loads(f.read_text(encoding="utf-8"))]
            f.write_text(json.dumps(rs, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{nom} : {sum(1 for r in rs if r['courriels'])} / {len(rs)} avec une adresse")


if __name__ == "__main__":
    main()
