"""Dessine « la ligne culture » : une évocation du métro (pas un vrai plan), où les stations portent des noms de salles.

Usage : python outils/carte_metro.py   → réécrit le bloc <svg class="lignemap"> de docs/index.html et docs/salles.html
Pour changer une salle : modifiez STATIONS ci-dessous (nom affiché, position, position de l'étiquette,
et la vraie station de métro la plus proche, affichée au survol). Le dessin est décoratif.
"""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
EP = 20  # épaisseur des lignes

LIGNES = [  # couleur, tracé (x y)
    ("var(--humour)", "M145 22 L145 155 L300 315 L322 345 L322 477"),            # orange
    ("var(--musique)", "M50 92 L350 92 L445 185 L597 185"),                       # bleue
    ("var(--cinema)", "M20 443 L170 443 L300 315 L380 240 L678 240"),            # verte
    ("var(--cirque)", "M300 315 L402 416 L676 416"),                              # jaune
]
# nom affiché, x, y, rayon, (x, y, ancre) de l'étiquette, vraie station (pour filtrer au clic)
STATIONS = [
    ("Sala Rossa", 145, 22, 12, (168, 27, "start"), "Laurier"),
    ("Fairmount", 145, 92, 18, (130, 132, "middle"), "Laurier"),
    ("Ritz PDB", 50, 92, 12, (50, 62, "middle"), "De Castelnau"),
    ("Lumière Collective", 255, 92, 12, (255, 62, "middle"), "De Castelnau"),
    ("Eastern Bloc", 445, 185, 12, (426, 220, "end"), "De Castelnau"),
    ("L'Esco", 597, 185, 12, (597, 155, "middle"), "Mont-Royal"),
    ("Quai des Brumes", 212, 228, 12, (188, 233, "end"), "Mont-Royal"),
    ("Quartier des spectacles", 300, 315, 22, (222, 359, "middle"), "Place-des-Arts"),
    ("MTELUS", 322, 403, 12, (300, 408, "end"), "Saint-Laurent"),
    ("Beanfield", 322, 477, 12, (300, 482, "end"), "Georges-Vanier"),
    ("Usine C", 48, 443, 12, (48, 413, "middle"), "Papineau"),
    ("Prospero", 170, 443, 12, (170, 413, "middle"), "Beaudry"),
    ("La Chapelle", 485, 240, 12, (485, 280, "middle"), "Sherbrooke"),
    ("TOHU", 678, 240, 12, (678, 210, "middle"), "D'Iberville"),
    ("Lion d'Or", 402, 416, 12, (402, 456, "middle"), "Papineau"),
    ("Tangente", 552, 416, 12, (552, 456, "middle"), "Place-des-Arts"),
    ("Casino", 676, 416, 12, (676, 456, "middle"), "Jean-Drapeau"),
]

out = ['<svg class="lignemap" id="carteMetro" viewBox="-10 -10 720 515" role="img" '
       'aria-label="La ligne culture : un métro imaginaire dont les stations sont des salles de Montréal">']
for c, d in LIGNES:
    out.append(f'<path class="ln" stroke="{c}" stroke-width="{EP}" d="{d}"/>')
for nom, x, y, r, (lx, ly, anc), vraie in STATIONS:
    if nom == "Quartier des spectacles":
        txt = (f'<text class="lb" x="{lx}" y="{ly}" text-anchor="{anc}">Quartier des</text>'
               f'<text class="lb" x="{lx}" y="{ly + 19}" text-anchor="{anc}">spectacles</text>')
    else:
        txt = f'<text class="lb" x="{lx}" y="{ly}" text-anchor="{anc}">{nom}</text>'
    out.append(f'<g class="stn-g"><title>{nom} · métro {vraie}</title><circle cx="{x}" cy="{y}" r="{r}" class="stn has"/>{txt}</g>')
out.append('<text class="tag" x="700" y="30" text-anchor="end" transform="rotate(-3 700 30)">la ligne culture</text>')
out.append("</svg>")
svg = "\n      ".join(out)
for f in ("index.html", "salles.html"):
    p = RACINE / "docs" / f
    h = re.sub(r'<svg class="lignemap.*?</svg>', lambda m: svg, p.read_text(encoding="utf-8"), count=1, flags=re.S)
    p.write_text(h, encoding="utf-8")
print(len(STATIONS), "stations dessinées")
