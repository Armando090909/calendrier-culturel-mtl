"""Dessine « la ligne culture » : une évocation du métro (pas un vrai plan), où les stations portent des noms de salles.

Usage : python outils/carte_metro.py   → réécrit le bloc <svg class="lignemap"> de docs/index.html et docs/salles.html
Pour changer une salle : modifiez STATIONS ci-dessous (nom affiché, position, position de l'étiquette,
et la vraie station de métro la plus proche, affichée au survol). Le dessin est décoratif.
"""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
EP = 20  # épaisseur des lignes

# Tracé simplifié mais fidèle : chaque salle est sur la ligne de sa vraie station de métro.
#   bleue (nord, ouest → est) : Outremont, Parc, De Castelnau, Jean-Talon, … D'Iberville
#   orange (Jean-Talon → sud par Saint-Denis → Berri-UQAM → ouest) : Laurier, Mont-Royal, Sherbrooke, … Georges-Vanier
#   verte (centre, ouest → est) : Place-des-Arts, Saint-Laurent, Berri-UQAM, Beaudry, Papineau
#   jaune (Berri-UQAM → Jean-Drapeau)
LIGNES = [  # couleur, tracé (x y)
    ("var(--musique)", "M40 80 L680 80"),                                          # bleue
    ("var(--humour)", "M360 80 L360 330 L320 420 L40 420"),                       # orange
    ("var(--cinema)", "M20 330 L690 330"),                                         # verte
    ("var(--cirque)", "M360 330 L470 450 L680 450"),                               # jaune
]
# nom affiché, x, y, rayon, (x, y, ancre) de l'étiquette, vraie station
STATIONS = [
    ("Fairmount", 65, 80, 12, (65, 50, "middle"), "Outremont"),
    ("Ritz PDB", 175, 80, 12, (175, 50, "middle"), "Parc"),
    ("Eastern Bloc", 285, 80, 12, (285, 50, "middle"), "De Castelnau"),
    ("TOHU", 640, 80, 12, (640, 50, "middle"), "D'Iberville"),
    ("Sala Rossa", 360, 150, 12, (382, 156, "start"), "Laurier"),
    ("L'Esco", 360, 205, 12, (382, 211, "start"), "Mont-Royal"),
    ("Quai des Brumes", 360, 205, 12, (338, 211, "end"), "Mont-Royal"),
    ("La Chapelle", 360, 262, 12, (382, 268, "start"), "Sherbrooke"),
    ("Théâtre St-Denis", 360, 330, 22, (384, 305, "start"), "Berri-UQAM"),
    ("Quartier des spectacles", 165, 330, 18, (165, 372, "middle"), "Place-des-Arts"),
    ("MTELUS", 275, 330, 12, (275, 366, "middle"), "Saint-Laurent"),
    ("Usine C", 480, 330, 12, (480, 366, "middle"), "Beaudry"),
    ("Lion d'Or", 570, 330, 12, (570, 366, "middle"), "Papineau"),
    ("Beanfield", 110, 420, 12, (110, 456, "middle"), "Georges-Vanier"),
    ("Casino", 620, 450, 12, (620, 486, "middle"), "Jean-Drapeau"),
]

out = ['<svg class="lignemap" id="carteMetro" viewBox="-10 -10 720 515" role="img" '
       'aria-label="La ligne culture : un métro imaginaire dont les stations sont des salles de Montréal">']
for c, d in LIGNES:
    out.append(f'<path class="ln" stroke="{c}" stroke-width="{EP}" d="{d}"/>')
out.append('<g class="stn-g"><title>Jean-Talon (correspondance)</title><circle cx="360" cy="80" r="14" class="stn"/></g>')
for nom, x, y, r, (lx, ly, anc), vraie in STATIONS:
    if nom == "Quartier des spectacles":
        txt = (f'<text class="lb" x="{lx}" y="{ly}" text-anchor="{anc}">Quartier des</text>'
               f'<text class="lb" x="{lx}" y="{ly + 19}" text-anchor="{anc}">spectacles</text>')
    else:
        txt = f'<text class="lb" x="{lx}" y="{ly}" text-anchor="{anc}">{nom}</text>'
    out.append(f'<g class="stn-g"><title>{nom} · métro {vraie}</title><circle cx="{x}" cy="{y}" r="{r}" class="stn has"/>{txt}</g>')
out.append('<text class="tag" x="700" y="230" text-anchor="end" transform="rotate(-3 700 230)">la ligne culture</text>')
out.append("</svg>")
svg = "\n      ".join(out)
for f in ("index.html", "salles.html"):
    p = RACINE / "docs" / f
    h = re.sub(r'<svg class="lignemap.*?</svg>', lambda m: svg, p.read_text(encoding="utf-8"), count=1, flags=re.S)
    p.write_text(h, encoding="utf-8")
print(len(STATIONS), "stations dessinées")
