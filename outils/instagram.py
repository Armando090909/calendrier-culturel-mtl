"""Visuels Instagram de ccmtl.ca, dans le style du site (fond blanc, encre noire, jaune, lignes du métro, autocollants).

Produit dans outils/instagram/sortie/ :
- profil.png (1080 × 1080) : photo de profil (lisible en tout petit, dans un cercle) ;
- facebook-couverture.png (1640 × 624) : couverture de la page Facebook (titre + ligne culture du site) ;
- 1-bienvenue.png, 2-comment.png, 3-semaine.png, 4-programmateurs.png (1080 × 1350, format portrait d'Instagram).
Le visuel « semaine » est calculé à partir de docs/data.json (les 7 prochains jours).

Lancé par .github/workflows/instagram.yml (les polices du site sont chargées depuis Google Fonts).
Essai local : python outils/instagram.py (polices de secours si Google Fonts est inaccessible).
"""
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "outils" / "instagram" / "sortie"

DISC = [("theatre", "Théâtre", "#e4002b"), ("musique", "Musique", "#1b73d9"), ("danse", "Danse", "#ff4fa3"),
        ("cirque", "Cirque", "#f7c300"), ("humour", "Humour", "#f47b20"), ("cinema", "Cinéma", "#00a651"),
        ("poesie", "Poésie et slam", "#d6336c"), ("lettres", "Littérature", "#8a4fbf"), ("conference", "Conférences", "#343a40"),
        ("jeune", "Jeune public", "#00a99d"), ("atelier", "Ateliers", "#8d6e63"), ("fete", "Fêtes", "#a61e4d"),
        ("quiz", "Quiz", "#0b7285"), ("expo", "Vernissages", "#e8a317")]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juill.", "août", "sept.", "oct.", "nov.", "déc."]

BASE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@600;800&family=Onest:wght@400;600;700;800&family=Permanent+Marker&family=Caveat:wght@600&display=block">
<style>
:root{--ink:#121212;--hl:#ffe14d;--pop:#e4002b;--muted:#5b616e;--paper:#f3f5f9;
  --vert:#00a651;--orange:#f47b20;--jaune:#f7c300;--bleu:#1b73d9;
  --display:"Unbounded","Arial Black",sans-serif;--body:"Onest",system-ui,sans-serif;--hand:"Permanent Marker","Comic Sans MS",cursive}
*{box-sizing:border-box}html,body{margin:0}
body{width:W;height:H;overflow:hidden;background:#fff;color:var(--ink);font-family:var(--body)}
.ligne{height:22px;border-radius:12px;background:linear-gradient(90deg,var(--vert) 0 25%,var(--orange) 25% 50%,var(--jaune) 50% 75%,var(--bleu) 75%)}
.stn{display:inline-block;border-radius:50%;background:#fff;border:solid var(--ink)}
.hl{position:relative;z-index:0;white-space:nowrap}
.hl::after{content:"";position:absolute;left:-4%;right:-4%;bottom:.04em;height:.42em;background:var(--hl);z-index:-1;border-radius:.3em .5em .2em .6em;transform:rotate(-1.5deg)}
.marque{font-family:var(--hand);color:var(--pop);transform:rotate(-2deg);transform-origin:left}
.marque b{font-weight:400;color:var(--ink);background:var(--hl);padding:0 .25em;border-radius:.15em}
.carte{border:4px solid var(--ink);border-radius:28px;background:#fff;box-shadow:12px 12px 0 var(--ink)}
.url{font-family:var(--display);font-weight:800}
CSS
</style></head><body>BODY</body></html>"""


def page(w, h, corps, css=""):
    return BASE.replace("W", f"{w}px").replace("H", f"{h}px").replace("CSS", css).replace("BODY", corps)


def profil():
    css = """body{background:var(--hl);display:grid;place-items:center}
.rond{width:1080px;height:1080px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:40px;padding-top:30px}
.nom{font-family:var(--display);font-weight:800;font-size:244px;letter-spacing:.015em;line-height:.9}
.nom span{color:var(--pop)}
.rail{display:flex;align-items:center;width:640px;position:relative}
.rail .ligne{position:absolute;left:30px;right:30px;height:34px}
.rail .stn{position:relative;width:96px;height:96px;border-width:22px}
.rail .stn:last-child{margin-left:auto;background:var(--ink)}"""
    return page(1080, 1080, """<div class="rond"><div class="nom">cc<span>mtl</span></div>
<div class="rail"><div class="ligne"></div><span class="stn"></span><span class="stn"></span></div></div>""", css)


def bienvenue():
    css = """body{padding:96px 92px;display:flex;flex-direction:column}
.marque{font-size:58px}
h1{font-family:var(--display);font-weight:800;font-size:112px;line-height:1.04;letter-spacing:-.035em;margin:70px 0 0}
p{font-size:46px;line-height:1.3;font-weight:600;margin:56px 0 0;max-width:880px}
.bas{margin-top:auto}
.rail{display:flex;justify-content:space-between;align-items:center;position:relative;margin-bottom:54px}
.rail .ligne{position:absolute;left:20px;right:20px;top:50%;transform:translateY(-50%)}
.rail .stn{position:relative;width:64px;height:64px;border-width:14px}
.url{font-size:74px;display:inline-block;background:var(--hl);border:4px solid var(--ink);border-radius:20px;padding:14px 30px;box-shadow:10px 10px 0 var(--ink)}"""
    return page(1080, 1350, """<div class="marque">calendrier culturel <b>mtl</b></div>
<h1>Qu'est-ce qu'on fait <span class="hl">ce soir</span>&nbsp;?</h1>
<p>Théâtre, shows, danse, expos, DJ sets, poésie, cinéma… Tout ce qui se passe sur l'île, au même endroit. Gratuit, sans pub, bénévole.</p>
<div class="bas"><div class="rail"><div class="ligne"></div>""" + '<span class="stn"></span>' * 7 + """</div>
<span class="url">ccmtl.ca</span></div>""", css)


def comment():
    css = """body{padding:96px 92px}
.marque{font-size:52px}
h1{font-family:var(--display);font-weight:800;font-size:78px;line-height:1.08;letter-spacing:-.03em;margin:50px 0 60px}
.etapes{position:relative;display:flex;flex-direction:column;gap:46px}
.etapes::before{content:"";position:absolute;left:38px;top:40px;bottom:40px;width:22px;border-radius:12px;
  background:linear-gradient(180deg,var(--vert) 0 33%,var(--orange) 33% 66%,var(--bleu) 66%)}
.e{position:relative;display:flex;gap:44px;align-items:flex-start}
.e .stn{flex:none;width:98px;height:98px;border-width:20px;display:grid;place-items:center;font-family:var(--display);font-weight:800;font-size:34px}
.e h2{font-family:var(--display);font-weight:800;font-size:46px;margin:6px 0 10px;letter-spacing:-.02em}
.e p{font-size:35px;line-height:1.3;margin:0;color:#2b2f36;font-weight:600}
.url{position:absolute;left:92px;bottom:80px;font-size:48px;background:var(--hl);border:4px solid var(--ink);border-radius:16px;padding:8px 20px;box-shadow:6px 6px 0 var(--ink)}"""
    return page(1080, 1350, """<div class="marque">calendrier culturel <b>mtl</b></div>
<h1>Trouver sa sortie en <span class="hl">3 stations</span></h1>
<div class="etapes">
<div class="e"><span class="stn">1</span><div><h2>Ce qui te tente</h2><p>Coche théâtre, musique, danse, humour, cinéma… ou tout.</p></div></div>
<div class="e"><span class="stn">2</span><div><h2>Quand et où</h2><p>Ce soir, cette semaine, ou près de ta station de métro.</p></div></div>
<div class="e"><span class="stn">3</span><div><h2>Vas-y</h2><p>Billets, itinéraire, et ajout à ton agenda en un clic.</p></div></div>
</div><div class="url">ccmtl.ca</div>""", css)


def compter(data, debut):
    """Sorties de la semaine qui commence le lundi « debut » : (par discipline, expos en cours, total, fin)."""
    fin = debut + timedelta(days=6)
    evs = [e for e in data["events"] if debut.isoformat() <= e["date"] <= fin.isoformat()]
    c = Counter()
    for e in evs:
        for k in {e["discipline"], *(e.get("aussi") or [])}:
            c[k] += 1
    # Pièces, danse, cirque « à l'affiche » cette semaine (séries) : un spectacle compte une fois
    series = [x for x in data.get("expos", []) if x.get("discipline") not in (None, "", "expo")
              and x["debut"] <= fin.isoformat() and x["fin"] >= debut.isoformat()]
    for x in series:
        c[x["discipline"]] += 1
    expos = sum(1 for x in data.get("expos", []) if x.get("discipline") in (None, "", "expo")
                and x["debut"] <= fin.isoformat() and x["fin"] >= debut.isoformat())
    return c, expos, len(evs) + len(series), fin


def lundi_a_venir(jour=None):
    """Le lundi de la semaine à annoncer : aujourd'hui si c'est lundi, sinon le lundi suivant."""
    d = jour or date.today()
    return d + timedelta(days=(7 - d.weekday()) % 7)


def semaine(data, debut=None):
    debut = debut or lundi_a_venir()
    c, expos, total, fin = compter(data, debut)
    lignes = "".join(f'<div class="d"><span class="pt" style="background:{coul}"></span><span class="nm">{nom}</span>'
                     f'<span class="n">{c[k]}</span></div>' for k, nom, coul in DISC if c[k])
    if expos:
        lignes += f'<div class="d"><span class="pt" style="background:#e8a317"></span><span class="nm">Expos en cours</span><span class="n">{expos}</span></div>'
    # Le total ferme la grille : il occupe la case libre (ou toute la dernière rangée si le nombre de cases est pair)
    n_cases = lignes.count('class="d"')
    lignes += (f'<div class="d tot{" large" if n_cases % 2 == 0 else ""}"><span class="nm">au total</span>'
               f'<span class="n">{total}</span></div>')
    titre_dates = f"du {debut.day}{' ' + MOIS[debut.month - 1] if debut.month != fin.month else ''} au {fin.day} {MOIS[fin.month - 1]}"
    css = """body{padding:86px 92px}
.marque{font-size:50px}
h1{font-family:var(--display);font-weight:800;font-size:70px;line-height:1.06;letter-spacing:-.03em;margin:40px 0 4px}
.dates{font-family:var(--hand);font-size:46px;color:var(--pop);transform:rotate(-1.5deg);margin:6px 0 32px}
.grille{display:grid;grid-template-columns:1fr 1fr;gap:16px 24px}
.d{display:flex;align-items:center;gap:16px;border:4px solid var(--ink);border-radius:18px;padding:12px 20px;background:#fff;box-shadow:6px 6px 0 var(--ink)}
.pt{width:30px;height:30px;border-radius:50%;flex:none;border:3px solid var(--ink)}
.nm{font-weight:800;font-size:30px;flex:1;line-height:1.1}
.n{font-family:var(--display);font-weight:800;font-size:30px}
.d.tot{background:var(--hl)}
.d.tot .nm{font-family:var(--display);font-size:28px}
.d.tot .n{font-size:36px}
.d.large{grid-column:1 / -1}
.bas{position:absolute;left:92px;right:92px;bottom:72px;display:flex;justify-content:center}
.url{font-size:44px;background:var(--hl);border:4px solid var(--ink);border-radius:16px;padding:8px 20px;box-shadow:6px 6px 0 var(--ink)}"""
    return page(1080, 1350, f"""<div class="marque">calendrier culturel <b>mtl</b></div>
<h1>Cette semaine<br>sur <span class="hl">l'île</span></h1><div class="dates">{titre_dates}</div>
<div class="grille">{lignes}</div>
<div class="bas"><span class="url">ccmtl.ca</span></div>""", css), total


def programmateurs():
    css = """body{background:var(--hl);padding:96px 92px;display:flex;flex-direction:column}
.marque{font-size:52px}
.milieu{flex:1;display:flex;flex-direction:column;justify-content:center;gap:56px;padding-bottom:40px}
.carte{padding:64px 60px}
.carte .stn{width:84px;height:84px;border-width:18px;box-shadow:0 0 0 14px var(--jaune)}
h1{font-family:var(--display);font-weight:800;font-size:66px;line-height:1.1;letter-spacing:-.03em;margin:40px 0 30px}
p{font-size:40px;line-height:1.32;font-weight:600;margin:0}
.bts{display:grid;grid-template-columns:1fr 1fr;gap:26px}
.bt{font-weight:800;font-size:31px;text-align:center;white-space:nowrap;border:4px solid var(--ink);border-radius:999px;padding:22px 10px;
  background:#fff;box-shadow:8px 8px 0 var(--ink)}
.bt.go{background:var(--pop);border-color:var(--pop);color:#fff}"""
    return page(1080, 1350, """<div class="marque">calendrier culturel <b>mtl</b></div>
<div class="milieu"><div class="carte"><span class="stn"></span><h1>Tu fais de la programmation d'événements&nbsp;?</h1>
<p>Salle, bar, festival, galerie, organisme : ajoute tes événements gratuitement, ou partage ton calendrier une fois pour toutes.</p></div>
<div class="bts"><span class="bt go">+ Proposer un événement</span><span class="bt">Partager un calendrier</span></div></div>""", css)


def couverture_facebook():
    """Photo de couverture Facebook (1640 × 624). Le contenu tient dans la zone centrale de 1180 px, la seule visible sur
    téléphone ; les lignes de métro débordent sur les côtés (visibles sur ordinateur)."""
    import re as _re
    index = (RACINE / "docs" / "index.html").read_text(encoding="utf-8")
    svg = _re.search(r'(<svg class="lignemap".*?</svg>)', index, flags=_re.S).group(1)
    css = """body{position:relative;display:flex;align-items:center;justify-content:center}
:root{--humour:#f47b20;--musique:#1b73d9;--cinema:#00a651;--cirque:#f7c300;--surface:#fff;--pop:#e4002b}
.bande{position:absolute;left:0;right:0;bottom:0;height:26px;
  background:linear-gradient(90deg,var(--cinema) 0 25%,var(--humour) 25% 50%,var(--cirque) 50% 75%,var(--musique) 75%)}
.zone{position:relative;width:1180px;height:624px;display:grid;grid-template-columns:600px 1fr;align-items:center;gap:20px;
  padding:0 30px 26px}
.marque{font-size:40px}
h1{font-family:var(--display);font-weight:800;font-size:80px;line-height:1.04;letter-spacing:-.035em;margin:22px 0 22px}
.url{font-family:var(--display);font-weight:800;font-size:40px;display:inline-block;background:var(--hl);border:4px solid var(--ink);
  border-radius:14px;padding:6px 18px;box-shadow:6px 6px 0 var(--ink)}
.lignemap{width:100%;height:auto;display:block;overflow:visible}
.lignemap .ln{fill:none;stroke-width:20;stroke-linecap:round;stroke-linejoin:round}
.lignemap .stn{fill:#fff;stroke:var(--ink);stroke-width:4.5}
.lignemap .lb{font-family:var(--body);font-weight:800;font-size:17px;fill:var(--ink);paint-order:stroke;stroke:#fff;stroke-width:5px;stroke-linejoin:round}
.lignemap .tag{font-family:var(--hand);font-size:26px;fill:var(--pop)}
.lignemap .cnt{display:none}"""
    return page(1640, 624, f"""<div class="bande"></div>
<div class="zone"><div><div class="marque">calendrier culturel <b>mtl</b></div>
<h1>Qu'est-ce qu'on fait <span class="hl">ce soir</span>&nbsp;?</h1><span class="url">ccmtl.ca</span></div>
<div>{svg}</div></div>""", css)


def main():
    from playwright.sync_api import sync_playwright
    SORTIE.mkdir(parents=True, exist_ok=True)
    data = json.loads((RACINE / "docs" / "data.json").read_text(encoding="utf-8"))
    sem, n = semaine(data)
    pages = {"profil": (profil(), 1080, 1080), "1-bienvenue": (bienvenue(), 1080, 1350), "2-comment": (comment(), 1080, 1350),
             "3-semaine": (sem, 1080, 1350), "4-programmateurs": (programmateurs(), 1080, 1350),
             "facebook-couverture": (couverture_facebook(), 1640, 624)}
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for nom, (html, w, h) in pages.items():
            pg = nav.new_page(viewport={"width": w, "height": h})
            pg.set_content(html, wait_until="networkidle", timeout=60000)
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(800)
            deborde = pg.evaluate("""() => [...document.querySelectorAll('h1,h2,p,.d,.url,.bt,.carte,.nom')]
                .filter(e => {const r = e.getBoundingClientRect(); return r.right > innerWidth - 40 || r.bottom > innerHeight - 30
                  || e.scrollWidth > e.clientWidth + 2}).map(e => e.className || e.tagName)""")
            if nom == "profil":  # le nom doit tenir dans le cercle (marge de 60 px de chaque côté à sa hauteur)
                print("  profil, largeur du nom :", pg.evaluate("document.querySelector('.nom').getBoundingClientRect().width"))
            if deborde:
                print(f"  attention, {nom} : déborde ({deborde})")
            pg.screenshot(path=str(SORTIE / f"{nom}.png"))
            print(f"{nom}.png")
        nav.close()
    print(f"Semaine : {n} sorties.")


if __name__ == "__main__":
    main()
