"""Pages lisibles par les moteurs de recherche et les aperçus de partage, générées à chaque publication.

- docs/e/<id>.html     : une page par événement (texte, affiche, billets, données « Event » schema.org pour Google)
- docs/jour/<date>.html : la liste du jour, en texte ; docs/jour/index.html : tous les jours
- docs/sitemap.xml et docs/robots.txt
- version anglaise : docs/en/e/<id>.html, docs/en/day/<date>.html, docs/en/day/index.html (liens hreflang entre les deux)

Le calendrier interactif (index.html) reste la page principale : chaque page renvoie vers lui (?e=<id> ou ?d=<date>).
Lancé par la publication après polices.py et le numéro de version : il reprend les liens de police et de style d'index.html.
"""
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SITE = "https://ccmtl.ca"
DOCS = Path(__file__).resolve().parent.parent / "docs"
MTL = ZoneInfo("America/Toronto")
DISC = {"theatre": "Théâtre", "musique": "Musique", "danse": "Danse", "cirque": "Cirque", "humour": "Humour et cabaret",
        "cinema": "Cinéma", "poesie": "Poésie, slam et rap battle", "lettres": "Littérature", "conference": "Conférences",
        "jeune": "Jeune public", "atelier": "Ateliers", "fete": "Fêtes et célébrations", "quiz": "Quiz", "social": "Rencontres sociales", "expo": "Vernissages",
        "autre": "Autre"}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
DISC_EN = {"theatre": "Theatre", "musique": "Music", "danse": "Dance", "cirque": "Circus", "humour": "Comedy & cabaret",
           "cinema": "Film", "poesie": "Poetry, slam & rap battles", "lettres": "Literature", "conference": "Talks",
           "jeune": "Kids & family", "atelier": "Workshops", "fete": "Parties & celebrations", "quiz": "Quiz nights", "social": "Social & meetups",
           "expo": "Openings", "autre": "Other"}
JOURS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MOIS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
EN = False  # langue des pages en cours de génération


def T(fr: str, en: str) -> str:
    return en if EN else fr


def P(chemin: str) -> str:
    """Chemin de la page dans la langue en cours : /e/x.html → /en/e/x.html ; /jour/ → /en/day/."""
    if not EN:
        return chemin
    return "/en" + chemin.replace("/jour/", "/day/")


def autre_langue(chemin: str) -> tuple[str, str]:
    """(chemin français, chemin anglais) d'une page, quelle que soit la langue de chemin."""
    fr = chemin[3:].replace("/day/", "/jour/") if chemin.startswith("/en/") else chemin
    return fr, "/en" + fr.replace("/jour/", "/day/")


def disc_nom(k: str) -> str:
    return (DISC_EN if EN else DISC).get(k, "")


def prix_txt(p: str) -> str:
    """Prix dans la langue de la page : « 25,50 $ » → « $25.50 », « Gratuit » → « Free »."""
    if not EN or not p:
        return p
    p = {"gratuit": "Free", "payant": "Paid", "contribution volontaire": "Pay what you can", "entrée libre": "Free admission"}.get(p.lower(), p)
    p = p.replace("taxes incluses", "taxes included").replace("à la porte", "at the door")
    p = re.sub(r"(\d+)(?:[,.](\d{1,2}))? à (\d+)(?:[,.](\d{1,2}))? ?\$",
               lambda m: f"${m[1]}{'.' + m[2].ljust(2, '0') if m[2] else ''} to ${m[3]}{'.' + m[4].ljust(2, '0') if m[4] else ''}", p)
    p = re.sub(r"(\d+)(?:[,.](\d{1,2}))? ?\$", lambda m: f"${m[1]}{'.' + m[2].ljust(2, '0') if m[2] else ''}", p)
    return p.replace(" à ", " to ")


def lieu(e: dict) -> str:
    return "Venue TBA" if EN and e["lieu"] == "Lieu à confirmer" else e["lieu"]


def resume(e: dict) -> str:
    return (e.get("resume_en") if EN else None) or e.get("resume") or ""
e_ = lambda t: html.escape(str(t or ""), quote=True)


def jour_long(s: str, annee: bool = False) -> str:
    d = date.fromisoformat(s)
    if EN:
        return f"{JOURS_EN[d.weekday()]}, {MOIS_EN[d.month - 1]} {d.day}" + (f", {d.year}" if annee else "")
    return f"{JOURS[d.weekday()]} {d.day}{'er' if d.day == 1 else ''} {MOIS[d.month - 1]}" + (f" {d.year}" if annee else "")


def heure_txt(h: str | None) -> str:
    if not h:
        return T("heure à confirmer", "time TBA")
    if not EN:
        return h.replace(":", " h ")
    a, b = (int(x) for x in h.split(":"))
    return f"{a % 12 or 12}{f':{b:02d}' if b else ''} {'p.m.' if a >= 12 else 'a.m.'}"


def entete_commun() -> str:
    """Liens de police, de style et de statistiques, repris d'index.html (déjà traités par polices.py et la version)."""
    idx = (DOCS / "index.html").read_text(encoding="utf-8")
    morceaux = re.findall(r'<link rel="(?:stylesheet|preconnect|icon)"[^>]*>', idx)
    morceaux += re.findall(r"<!-- Statistiques.*?</script>", idx, flags=re.S)
    # chemins relatifs → absolus (les pages sont dans des sous-dossiers)
    return "\n".join(re.sub(r'href="(?!https?:|data:|/)([^"]+)"', r'href="/\1"', m) for m in morceaux)


CSS = """<style>
.pg{max-width:900px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
.pg-haut{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px}
.fiche{background:var(--c);color:#000;border-radius:28px;padding:26px 28px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px}
.fiche h1{font-weight:900;font-size:clamp(30px,5vw,54px);line-height:.95;letter-spacing:-.045em;margin:0 0 12px;overflow-wrap:normal}
.fiche .quand{font-weight:900;font-size:19px;margin:0}
.fiche .ou{margin:4px 0 0;font-weight:500}.fiche .ou span{opacity:.75}
.fiche .disc{display:inline-block;margin-top:12px;font-size:13px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}
.fiche .resume{margin:14px 0 0;line-height:1.4}
.fiche .px{display:inline-block;margin-top:12px;font-weight:900;font-size:17px;background:var(--bg);border:2px solid #000;border-radius:999px;padding:4px 14px}
.fiche img{width:240px;max-height:340px;object-fit:cover;border-radius:18px}
.boutons{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:10px}
.boutons .btn{text-decoration:none;display:inline-flex;align-items:center;font-family:var(--f-body);font-weight:700;border:2px solid #000;
  border-radius:999px;padding:9px 18px;box-shadow:none;background:#000;color:var(--bg)}
.boutons .btn.ghost{background:transparent;color:#000}
.boutons .btn.ghost:hover{background:#000;color:var(--bg)}
.liste{display:flex;flex-direction:column;gap:8px}
.liste a{display:grid;grid-template-columns:70px minmax(0,1fr);gap:2px 14px;padding:12px 16px;background:var(--c);border-radius:16px;
  text-decoration:none;color:#000}
.liste a:hover{outline:2px solid #000;outline-offset:-2px}
.liste .h{font-size:18px;font-weight:900;font-variant-numeric:tabular-nums}
.liste .t{font-weight:900;font-size:17px;line-height:1.15}.liste .m{grid-column:2;font-size:13px;font-weight:500}
.nav-j{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
.nav-j a{font-weight:700}
h1.pg-t{font-weight:900;font-size:clamp(36px,6vw,64px);letter-spacing:-.05em;line-height:.95;margin:0}
.licence{font-size:13px;color:var(--muted)}
@media(max-width:640px){.fiche{grid-template-columns:minmax(0,1fr);padding:22px}.fiche img{width:100%;max-height:none}
  .liste a{grid-template-columns:minmax(0,1fr)}.liste .m{grid-column:1}}
</style>"""

PARTAGE_JS_FR = """<script>
document.addEventListener("click",ev=>{const b=ev.target.closest("[data-partage]");if(!b)return;
  const d={title:b.dataset.titre,text:b.dataset.texte,url:b.dataset.partage};
  if(navigator.share){navigator.share(d).catch(()=>{});return}
  const fini=()=>{b.textContent="Lien copié ✓";setTimeout(()=>{b.textContent="Partager"},2500)};
  try{navigator.clipboard.writeText(d.url).then(fini,()=>prompt("Copie ce lien :",d.url))}catch(e){prompt("Copie ce lien :",d.url)}});
</script>"""
PARTAGE_JS_EN = (PARTAGE_JS_FR.replace("Lien copié ✓", "Link copied ✓").replace('"Partager"', '"Share"')
                 .replace("Copie ce lien :", "Copy this link:"))


def page(titre: str, description: str, chemin: str, corps: str, image: str = "", jsonld: dict | list | None = None,
         type_og: str = "website") -> str:
    url = SITE + chemin
    img = image or SITE + "/partage.png"
    fr, en = autre_langue(chemin)
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="{T('fr', 'en')}" class="v2">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e_(titre)}</title>
<meta name="description" content="{e_(description)}">
<link rel="canonical" href="{e_(url)}">
<link rel="alternate" hreflang="fr" href="{SITE}{fr}">
<link rel="alternate" hreflang="en" href="{SITE}{en}">
<meta property="og:type" content="{type_og}">
<meta property="og:site_name" content="{T('Calendrier culturel montréalais', "Montreal's cultural calendar")}">
<meta property="og:locale" content="{T('fr_CA', 'en_CA')}">
<meta property="og:title" content="{e_(titre)}">
<meta property="og:description" content="{e_(description)}">
<meta property="og:url" content="{e_(url)}">
<meta property="og:image" content="{e_(img)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="dcterms.rights" content="Calendrier culturel montréalais (ccmtl.ca), projet bénévole sans but lucratif. Compilation et textes sous licence CC BY-NC 4.0 : réutilisation non commerciale permise en citant ccmtl.ca ; usage commercial sur permission (info@ccmtl.ca). Les affiches et descriptions appartiennent à leurs auteurs.">
<link rel="license" href="https://creativecommons.org/licenses/by-nc/4.0/">
<meta name="color-scheme" content="light">
{ENTETE}
{CSS}
{ld}
</head>
<body>
<div class="pg">
<div class="pg-haut"><a class="v2-marque" href="{T('/', '/en/')}">{T('Calendrier culturel<br><span>de Montréal</span>', "Montréal's cultural<br><span>calendar</span>")}</a>
<p class="toplinks"><a href="{T('/', '/en/')}">{T('← Tout le calendrier', '← Full calendar')}</a> <a href="{T(en, fr)}" hreflang="{T('en', 'fr')}" lang="{T('en', 'fr')}">{T('English', 'Français')}</a></p></div>
{corps}
<p class="licence">© 2026 ccmtl.ca · <a href="https://creativecommons.org/licenses/by-nc/4.0/deed.{T('fr', 'en')}" rel="license noopener" target="_blank">CC BY-NC 4.0</a> · <a href="mailto:info@ccmtl.ca">info@ccmtl.ca</a></p>
</div>
{T(PARTAGE_JS_FR, PARTAGE_JS_EN)}
</body>
</html>
"""


def prix_offre(prix: str) -> dict | None:
    t = (prix or "").lower()
    if re.search(r"gratuit|entrée libre|free", t):
        return {"price": "0", "priceCurrency": "CAD"}
    m = re.search(r"(\d+)(?:[,.](\d{2}))?", t)
    return {"price": f"{m.group(1)}.{m.group(2) or '00'}", "priceCurrency": "CAD"} if m else None


def schema_event(e: dict, lieux: dict, url: str, image: str) -> dict:
    j = date.fromisoformat(e["date"])
    if e.get("heure"):
        h, m = (int(x) for x in e["heure"].split(":"))
        debut = datetime(j.year, j.month, j.day, h, m, tzinfo=MTL).isoformat()
    else:
        debut = j.isoformat()
    c = lieux.get(e["lieu"]) or {}
    lieu = {"@type": "Place", "name": e["lieu"],
            "address": {"@type": "PostalAddress", "addressLocality": "Montréal", "addressRegion": "QC", "addressCountry": "CA"}}
    if c.get("lat"):
        lieu["geo"] = {"@type": "GeoCoordinates", "latitude": c["lat"], "longitude": c["lon"]}
    ev = {"@context": "https://schema.org", "@type": "Event", "name": e["titre"], "startDate": debut, "url": url,
          "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
          "eventStatus": "https://schema.org/EventScheduled", "location": lieu, "image": [image]}
    if resume(e):
        ev["description"] = resume(e)
    if EN:
        ev["inLanguage"] = "en"
    o = prix_offre(e.get("prix", ""))
    if o or e.get("billets"):
        ev["offers"] = {"@type": "Offer", "url": e.get("billets") or e.get("url"), **(o or {}),
                        "availability": "https://schema.org/SoldOut" if e.get("complet") else "https://schema.org/InStock"}
    return ev


def page_evenement(e: dict, lieux: dict) -> str:
    chemin = P(f"/e/{e['ics']}.html")
    url = SITE + chemin
    c = lieux.get(e["lieu"]) or {}
    disc = disc_nom(e["discipline"])
    aff = e.get("image") or (e.get("affiche") or {}).get("url") or ""
    aff = re.sub(r"(images\.sk-static\.com/.+/)(?:small|medium)_avatar$", r"\1huge_avatar", aff)  # Songkick : grande version
    quand = f"{(lambda t: t[:1].upper() + t[1:])(jour_long(e['date'], True))} · {heure_txt(e.get('heure'))}"
    description = f"{quand} · {lieu(e)}, Montréal. " + (resume(e) or disc)
    billets = e.get("billets") or e.get("url")
    corps = f"""<article class="fiche" style="--c:var(--{e_(e['discipline'] if e['discipline'] in DISC else 'autre')})">
<div>
<h1>{e_(e['titre'])}</h1>
<p class="quand">{e_(quand)}</p>
<p class="ou">{e_(lieu(e))}{f" <span>· {e_(c['quartier'])}</span>" if c.get('quartier') else ""}</p>
<span class="disc">{e_(disc)}</span>
{f'<p class="resume">{e_(resume(e))}</p>' if resume(e) else ""}
{f'<span class="px">{e_(prix_txt(e["prix"]))}</span>' if e.get("prix") else ""}
</div>
{f'<img src="{e_(aff)}" alt="{T('Affiche', 'Poster')} : {e_(e["titre"])}" referrerpolicy="no-referrer" onerror="this.remove()">' if aff else ""}
<div class="boutons">
{f'<a class="btn" href="{e_(billets)}" target="_blank" rel="noopener">{T("Acheter des billets", "Buy tickets") if e.get("billets") else T("Page de l’événement", "Event page")}</a>' if billets else ""}
<a class="btn ghost" href="/ics/{e_(e['ics'])}.ics">{T('+ mon agenda', '+ my calendar')}</a>
<button type="button" class="btn ghost" data-partage="{e_(url)}" data-titre="{e_(e['titre'])}" data-texte="{e_(quand + ' · ' + lieu(e))}">{T('Partager', 'Share')}</button>
<a class="btn ghost" href="{T('/', '/en/')}?e={e_(e['ics'])}">{T('Voir dans le calendrier', 'View in the calendar')}</a>
</div>
</article>
<p class="nav-j"><a href="{P('/jour/' + e['date'] + '.html')}">{T('Toutes les sorties du ', 'Everything on ')}{e_(jour_long(e['date']))} →</a></p>"""
    titre = f"{e['titre']} · {lieu(e)} · {jour_long(e['date'])}"
    return page(titre, description[:300], chemin, corps, aff, schema_event(e, lieux, url, aff or SITE + "/partage.png"))


def page_jour(j: str, evs: list[dict], lieux: dict, prec: str | None, suiv: str | None) -> str:
    lignes = "\n".join(
        f'<a href="{P("/e/" + e_(e["ics"]) + ".html")}" style="--c:var(--{e_(e["discipline"] if e["discipline"] in DISC else "autre")})">'
        f'<span class="h">{e_(heure_txt(e.get("heure")) if e.get("heure") else "—")}</span><span class="t">{e_(e["titre"])}</span>'
        f'<span class="m">{e_(disc_nom(e["discipline"]))} · {e_(lieu(e))}'
        f'{" · " + e_((lieux.get(e["lieu"]) or {}).get("quartier")) if (lieux.get(e["lieu"]) or {}).get("quartier") else ""}</span></a>'
        for e in evs)
    a_prec = f'<a href="{P("/jour/" + prec + ".html")}">← {e_(jour_long(prec))}</a>' if prec else ""
    a_suiv = f'<a href="{P("/jour/" + suiv + ".html")}">{e_(jour_long(suiv))} →</a>' if suiv else ""
    nav = f'<p class="nav-j"><span>{a_prec}</span><a href="{P("/jour/")}">{T("Tous les jours", "All days")}</a><span>{a_suiv}</span></p>'
    titre = T(f"Sorties culturelles à Montréal · {jour_long(j, True)}", f"Things to do in Montréal · {jour_long(j, True)}")
    corps = f"""<h1 class="pg-t">{T("Quoi faire à Montréal le ", "What's on in Montréal, ")}{e_(jour_long(j, True))}</h1>
<p>{len(evs)} {T("spectacles, concerts, expositions et activités culturelles sur l'île.", "shows, concerts, exhibitions and cultural activities on the island.")} <a href="{T('/', '/en/')}?d={j}">{T("Voir avec les filtres du calendrier", "View with the calendar filters")}</a></p>
{nav}
<div class="liste">{lignes}</div>
{nav}"""
    desc = T(f"{len(evs)} sorties culturelles à Montréal le {jour_long(j, True)} : ",
             f"{len(evs)} things to do in Montréal on {jour_long(j, True)}: ") + ", ".join(e["titre"] for e in evs[:6])
    return page(titre, desc[:300], P(f"/jour/{j}.html"), corps)


def main() -> None:
    global ENTETE
    ENTETE = entete_commun()
    data = json.loads((DOCS / "data.json").read_text(encoding="utf-8"))
    lieux = data.get("lieux") or {}
    evs = [e for e in data["events"] if e.get("ics")]
    for e in evs:
        if e.get("jeunePublic") and e["discipline"] != "jeune":
            e["discipline"] = "jeune"
    global EN
    par_jour: dict[str, list] = {}
    for e in sorted(evs, key=lambda x: (x["date"], x.get("heure") or "99", x["titre"])):
        par_jour.setdefault(e["date"], []).append(e)
    jours = sorted(par_jour)
    for EN in (False, True):
        dos_e, dos_j = (DOCS / "en" / "e", DOCS / "en" / "day") if EN else (DOCS / "e", DOCS / "jour")
        for d in (dos_e, dos_j):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True)
        for e in evs:
            (dos_e / f"{e['ics']}.html").write_text(page_evenement(e, lieux), encoding="utf-8")
        for i, j in enumerate(jours):
            (dos_j / f"{j}.html").write_text(
                page_jour(j, par_jour[j], lieux, jours[i - 1] if i else None, jours[i + 1] if i + 1 < len(jours) else None),
                encoding="utf-8")
        idx = "\n".join(f'<a href="{P("/jour/" + j + ".html")}" style="--c:var(--hl)"><span class="h">{len(par_jour[j])}</span>'
                        f'<span class="t">{e_(jour_long(j, True)[:1].upper() + jour_long(j, True)[1:])}</span></a>' for j in jours)
        (dos_j / "index.html").write_text(page(
            T("Sorties culturelles à Montréal, jour par jour", "Things to do in Montréal, day by day"),
            T("Tous les spectacles, concerts et expositions de l'île de Montréal, jour par jour.",
              "Every show, concert and exhibition on the island of Montréal, day by day."),
            P("/jour/"), f'<h1 class="pg-t">{T("Jour par jour", "Day by day")}</h1>\n<div class="liste">{idx}</div>'), encoding="utf-8")
    EN = False

    maj = data.get("miseAJour") or date.today().isoformat()
    urls = [("/", "daily"), ("/jour/", "daily"), ("/sources.html", "weekly"), ("/salles.html", "monthly"), ("/archives.html", "weekly")]
    urls += [(f"/jour/{j}.html", "daily") for j in jours] + [(f"/e/{e['ics']}.html", "weekly") for e in evs]
    urls += [("/en" + u.replace("/jour/", "/day/"), f) for u, f in urls]
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{maj}</lastmod><changefreq>{f}</changefreq></url>\n" for u, f in urls)
        + "</urlset>\n", encoding="utf-8")
    # robots.txt : écrit à la main dans docs/ (robots d'entraînement d'IA refusés) ; on ne le remplace pas ici
    print(f"Pages : {len(evs)} événements, {len(jours)} jours, sitemap de {len(urls)} adresses.")


ENTETE = ""
if __name__ == "__main__":
    main()
