"""Dessine le logo « MTL » de l'accueil : M en ligne bleue, T en ligne orange, L en ligne verte, souligné en jaune.
Les stations portent des noms de salles. Décoratif.

Usage : python outils/carte_mtl.py   → réécrit le bloc <svg class="lignemap"> de docs/index.html et docs/salles.html
(L'ancien plan imaginaire reste disponible : python outils/carte_metro.py)
Pour changer une salle : modifiez STATIONS (nom, x, y, rayon, position de l'étiquette).
"""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
EP = 24  # épaisseur des lignes

LIGNES = [
    ("var(--musique)", "M70 330 L70 80 L170 215 L270 80 L270 330"),     # M bleu
    ("var(--humour)", "M330 80 L510 80 M420 80 L420 330"),              # T orange
    ("var(--cinema)", "M575 80 L575 330 L705 330"),                     # L vert
    ("var(--cirque)", "M40 392 L730 392"),                               # soulignement jaune
]
# nom, x, y, rayon, (x, y, ancre) de l'étiquette
STATIONS = [
    ("Sala Rossa", 70, 80, 12, (70, 50, "middle")),
    ("Quai des Brumes", 170, 215, 12, (170, 252, "middle")),
    ("L'Esco", 270, 80, 12, (262, 50, "middle")),
    ("Lion d'Or", 70, 330, 12, (70, 366, "middle")),
    ("Ritz PDB", 270, 330, 12, (270, 366, "middle")),
    ("Fairmount", 330, 80, 12, (350, 50, "middle")),
    ("Lumière Collective", 510, 80, 12, (490, 50, "middle")),
    ("MTELUS", 420, 205, 12, (440, 210, "start")),
    ("Beanfield", 420, 330, 12, (420, 366, "middle")),
    ("TOHU", 575, 80, 12, (597, 86, "start")),
    ("La Chapelle", 575, 205, 12, (597, 210, "start")),
    ("Casino", 705, 330, 12, (705, 366, "middle")),
    ("Usine C", 150, 392, 13, (150, 428, "middle")),
    ("Quartier des spectacles", 420, 392, 17, (420, 430, "middle")),
    ("Tangente", 640, 392, 13, (640, 428, "middle")),
]

out = ['<svg class="lignemap mtl" id="carteMetro" viewBox="0 10 770 435" role="img" '
       'aria-label="MTL écrit en lignes de métro : M bleu, T orange, L vert, souligné en jaune ; les stations portent des noms de salles">']
for c, d in LIGNES:
    out.append(f'<path class="ln" stroke="{c}" stroke-width="{EP}" d="{d}"/>')
for nom, x, y, r, (lx, ly, anc) in STATIONS:
    out.append(f'<g class="stn-g"><title>{nom}</title><circle cx="{x}" cy="{y}" r="{r}" class="stn has"/>'
               f'<text class="lb" x="{lx}" y="{ly}" text-anchor="{anc}">{nom}</text></g>')
out.append("</svg>")
svg = "\n      ".join(out)
for f in ("index.html", "salles.html"):
    p = RACINE / "docs" / f
    h = re.sub(r'<svg class="lignemap.*?</svg>', lambda m: svg, p.read_text(encoding="utf-8"), count=1, flags=re.S)
    p.write_text(h, encoding="utf-8")
print(len(STATIONS), "stations dessinées")
