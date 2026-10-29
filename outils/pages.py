"""Pages lisibles par les moteurs de recherche et les aperçus de partage, générées à chaque publication.

- docs/e/<id>.html     : une page par événement (texte, affiche, billets, données « Event » schema.org pour Google)
- docs/jour/<date>.html : la liste du jour, en texte ; docs/jour/index.html : tous les jours
- docs/sitemap.xml et docs/robots.txt

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
        "jeune": "Jeune public", "atelier": "Ateliers", "fete": "Fêtes et célébrations", "quiz": "Quiz", "expo": "Vernissages",
        "autre": "Autre"}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
e_ = lambda t: html.escape(str(t or ""), quote=True)


def jour_long(s: str, annee: bool = False) -> str:
    d = date.fromisoformat(s)
    return f"{JOURS[d.weekday()]} {d.day}{'er' if d.day == 1 else ''} {MOIS[d.month - 1]}" + (f" {d.year}" if annee else "")


def heure_txt(h: str | None) -> str:
    return h.replace(":", " h ") if h else "heure à confirmer"


def entete_commun() -> str:
    """Liens de police, de style et de statistiques, repris d'index.html (déjà traités par polices.py et la version)."""
    idx = (DOCS / "index.html").read_text(encoding="utf-8")
    morceaux = re.findall(r'<link rel="(?:stylesheet|preconnect|icon)"[^>]*>', idx)
    morceaux += re.findall(r"<!-- Statistiques.*?</script>", idx, flags=re.S)
    # chemins relatifs → absolus (les pages sont dans des sous-dossiers)
    return "\n".join(re.sub(r'href="(?!https?:|data:|/)([^"]+)"', r'href="/\1"', m) for m in morceaux)


CSS = """<style>
.pg{max-width:860px;margin:0 auto;display:flex;flex-direction:column;gap:18px}
.pg-haut{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px}
.pg-marque{font-family:var(--f-hand);color:var(--pop);font-size:20px;text-decoration:none}
.pg-marque b{font-family:var(--f-body);background:var(--hl);color:var(--ink);padding:0 6px;border-radius:6px}
.fiche{border:2px solid var(--ink);border-radius:var(--r);box-shadow:5px 5px 0 var(--shadow);background:var(--surface);
  border-left:10px solid var(--c);padding:20px 22px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px}
.fiche h1{font-family:var(--f-display);font-weight:800;font-size:clamp(22px,3.4vw,32px);line-height:1.15;margin:0 0 8px}
.fiche .quand{font-weight:800;font-size:17px;margin:0}
.fiche .ou{margin:4px 0 0;color:var(--ink)}.fiche .ou span{color:var(--muted)}
.fiche .disc{display:inline-block;margin-top:10px;font-size:13px;font-weight:700;color:var(--c)}
.fiche .resume{margin:14px 0 0}
.fiche .px{font-family:var(--f-hand);color:var(--pop);font-size:24px;display:inline-block;transform:rotate(-4deg);margin-top:12px}
.fiche img{width:200px;max-height:280px;object-fit:cover;border-radius:10px;border:2px solid var(--ink)}
.boutons{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:10px}
.boutons .btn{text-decoration:none;display:inline-flex;align-items:center}
.liste{border:2px solid var(--ink);border-radius:var(--r);overflow:hidden;background:var(--surface)}
.liste a{display:grid;grid-template-columns:70px minmax(0,1fr);gap:2px 12px;padding:10px 14px;border-left:6px solid var(--c);
  text-decoration:none;color:var(--ink)}
.liste a+a{border-top:1.5px solid var(--hair)}.liste a:hover{background:var(--paper)}
.liste .h{font-family:var(--f-display);font-size:12px;font-weight:700;padding-top:3px}
.liste .t{font-weight:800}.liste .m{grid-column:2;font-size:13px;color:var(--muted)}
.nav-j{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
.nav-j a{font-weight:700}
h1.pg-t{font-family:var(--f-display);font-weight:800;font-size:clamp(22px,3.4vw,32px);margin:0}
@media(max-width:640px){.fiche{grid-template-columns:minmax(0,1fr)}.fiche img{width:100%;max-height:none}
  .liste a{grid-template-columns:minmax(0,1fr)}.liste .m{grid-column:1}}
</style>"""

PARTAGE_JS = """<script>
document.addEventListener("click",ev=>{const b=ev.target.closest("[data-partage]");if(!b)return;
  const d={title:b.dataset.titre,text:b.dataset.texte,url:b.dataset.partage};
  if(navigator.share){navigator.share(d).catch(()=>{});return}
  const fini=()=>{b.textContent="Lien copié ✓";setTimeout(()=>{b.textContent="Partager"},2500)};
  try{navigator.clipboard.writeText(d.url).then(fini,()=>prompt("Copie ce lien :",d.url))}catch(e){prompt("Copie ce lien :",d.url)}});
</script>"""


def page(titre: str, description: str, chemin: str, corps: str, image: str = "", jsonld: dict | list | None = None,
         type_og: str = "website") -> str:
    url = SITE + chemin
    img = image or SITE + "/partage.png"
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e_(titre)}</title>
<meta name="description" content="{e_(description)}">
<link rel="canonical" href="{e_(url)}">
<meta property="og:type" content="{type_og}">
<meta property="og:site_name" content="Calendrier culturel montréalais">
<meta property="og:locale" content="fr_CA">
<meta property="og:title" content="{e_(titre)}">
<meta property="og:description" content="{e_(description)}">
<meta property="og:url" content="{e_(url)}">
<meta property="og:image" content="{e_(img)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="color-scheme" content="light">
{ENTETE}
{CSS}
{ld}
</head>
<body>
<div class="pg">
<div class="pg-haut"><a class="pg-marque" href="/">calendrier culturel <b>mtl</b></a>
<p class="toplinks"><a href="/">← Tout le calendrier</a></p></div>
{corps}
</div>
{PARTAGE_JS}
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
    if e.get("resume"):
        ev["description"] = e["resume"]
    o = prix_offre(e.get("prix", ""))
    if o or e.get("billets"):
        ev["offers"] = {"@type": "Offer", "url": e.get("billets") or e.get("url"), **(o or {}),
                        "availability": "https://schema.org/SoldOut" if e.get("complet") else "https://schema.org/InStock"}
    return ev


def page_evenement(e: dict, lieux: dict) -> str:
    chemin = f"/e/{e['ics']}.html"
    url = SITE + chemin
    c = lieux.get(e["lieu"]) or {}
    disc = DISC.get(e["discipline"], "")
    aff = e.get("image") or (e.get("affiche") or {}).get("url") or ""
    quand = f"{jour_long(e['date'], True).capitalize()} · {heure_txt(e.get('heure'))}"
    description = f"{quand} · {e['lieu']}, Montréal. " + (e.get("resume") or disc)
    billets = e.get("billets") or e.get("url")
    corps = f"""<article class="fiche" style="--c:var(--{e_(e['discipline'] if e['discipline'] in DISC else 'autre')})">
<div>
<h1>{e_(e['titre'])}</h1>
<p class="quand">{e_(quand)}</p>
<p class="ou">{e_(e['lieu'])}{f" <span>· {e_(c['quartier'])}</span>" if c.get('quartier') else ""}</p>
<span class="disc">{e_(disc)}</span>
{f'<p class="resume">{e_(e["resume"])}</p>' if e.get("resume") else ""}
{f'<span class="px">{e_(e["prix"])}</span>' if e.get("prix") else ""}
</div>
{f'<img src="{e_(aff)}" alt="Affiche : {e_(e["titre"])}" referrerpolicy="no-referrer" onerror="this.remove()">' if aff else ""}
<div class="boutons">
{f'<a class="btn" href="{e_(billets)}" target="_blank" rel="noopener">{"Acheter des billets" if e.get("billets") else "Page de l’événement"}</a>' if billets else ""}
<a class="btn ghost" href="/ics/{e_(e['ics'])}.ics">+ mon agenda</a>
<button type="button" class="btn ghost" data-partage="{e_(url)}" data-titre="{e_(e['titre'])}" data-texte="{e_(quand + ' · ' + e['lieu'])}">Partager</button>
<a class="btn ghost" href="/?e={e_(e['ics'])}">Voir dans le calendrier</a>
</div>
</article>
<p class="nav-j"><a href="/jour/{e['date']}.html">Toutes les sorties du {e_(jour_long(e['date']))} →</a></p>"""
    titre = f"{e['titre']} · {e['lieu']} · {jour_long(e['date'])}"
    return page(titre, description[:300], chemin, corps, aff, schema_event(e, lieux, url, aff or SITE + "/partage.png"))


def page_jour(j: str, evs: list[dict], lieux: dict, prec: str | None, suiv: str | None) -> str:
    lignes = "\n".join(
        f'<a href="/e/{e_(e["ics"])}.html" style="--c:var(--{e_(e["discipline"] if e["discipline"] in DISC else "autre")})">'
        f'<span class="h">{e_(heure_txt(e.get("heure")) if e.get("heure") else "—")}</span><span class="t">{e_(e["titre"])}</span>'
        f'<span class="m">{e_(DISC.get(e["discipline"], ""))} · {e_(e["lieu"])}'
        f'{" · " + e_((lieux.get(e["lieu"]) or {}).get("quartier")) if (lieux.get(e["lieu"]) or {}).get("quartier") else ""}</span></a>'
        for e in evs)
    a_prec = f'<a href="/jour/{prec}.html">← {e_(jour_long(prec))}</a>' if prec else ""
    a_suiv = f'<a href="/jour/{suiv}.html">{e_(jour_long(suiv))} →</a>' if suiv else ""
    nav = f'<p class="nav-j"><span>{a_prec}</span><a href="/jour/">Tous les jours</a><span>{a_suiv}</span></p>'
    titre = f"Sorties culturelles à Montréal · {jour_long(j, True)}"
    corps = f"""<h1 class="pg-t">Quoi faire à Montréal le {e_(jour_long(j, True))}</h1>
<p>{len(evs)} spectacles, concerts, expositions et activités culturelles sur l'île. <a href="/?d={j}">Voir avec les filtres du calendrier</a></p>
{nav}
<div class="liste">{lignes}</div>
{nav}"""
    desc = f"{len(evs)} sorties culturelles à Montréal le {jour_long(j, True)} : " + ", ".join(e["titre"] for e in evs[:6])
    return page(titre, desc[:300], f"/jour/{j}.html", corps)


def main() -> None:
    global ENTETE
    ENTETE = entete_commun()
    data = json.loads((DOCS / "data.json").read_text(encoding="utf-8"))
    lieux = data.get("lieux") or {}
    evs = [e for e in data["events"] if e.get("ics")]
    for e in evs:
        if e.get("jeunePublic") and e["discipline"] != "jeune":
            e["discipline"] = "jeune"
    for d in ("e", "jour"):
        shutil.rmtree(DOCS / d, ignore_errors=True)
        (DOCS / d).mkdir()
    for e in evs:
        (DOCS / "e" / f"{e['ics']}.html").write_text(page_evenement(e, lieux), encoding="utf-8")
    par_jour: dict[str, list] = {}
    for e in sorted(evs, key=lambda x: (x["date"], x.get("heure") or "99", x["titre"])):
        par_jour.setdefault(e["date"], []).append(e)
    jours = sorted(par_jour)
    for i, j in enumerate(jours):
        (DOCS / "jour" / f"{j}.html").write_text(
            page_jour(j, par_jour[j], lieux, jours[i - 1] if i else None, jours[i + 1] if i + 1 < len(jours) else None),
            encoding="utf-8")
    idx = "\n".join(f'<a href="/jour/{j}.html" style="--c:var(--hl)"><span class="h">{len(par_jour[j])}</span>'
                    f'<span class="t">{e_(jour_long(j, True).capitalize())}</span></a>' for j in jours)
    (DOCS / "jour" / "index.html").write_text(page(
        "Sorties culturelles à Montréal, jour par jour", "Tous les spectacles, concerts et expositions de l'île de Montréal, jour par jour.",
        "/jour/", f'<h1 class="pg-t">Jour par jour</h1>\n<div class="liste">{idx}</div>'), encoding="utf-8")

    maj = data.get("miseAJour") or date.today().isoformat()
    urls = [("/", "daily"), ("/jour/", "daily"), ("/sources.html", "weekly"), ("/salles.html", "monthly"), ("/archives.html", "weekly")]
    urls += [(f"/jour/{j}.html", "daily") for j in jours] + [(f"/e/{e['ics']}.html", "weekly") for e in evs]
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{maj}</lastmod><changefreq>{f}</changefreq></url>\n" for u, f in urls)
        + "</urlset>\n", encoding="utf-8")
    (DOCS / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /ics/\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"Pages : {len(evs)} événements, {len(jours)} jours, sitemap de {len(urls)} adresses.")


ENTETE = ""
if __name__ == "__main__":
    main()
