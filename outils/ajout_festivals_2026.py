"""Ajout ponctuel (27 oct. 2026) des programmations publiées : CINEMANIA, Festival Bach, M pour Montréal,
Salon du livre, ELEKTRA. Sources : festapp.io (CINEMANIA), festivalbachmontreal.com/programmation, jambase (M pour Montréal),
mtl.org. Ensuite, la collecte automatique prend le relais (collecteur/festivals.py)."""
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "collecteur"))
from normalisation import dedoublonner  # noqa: E402

D = json.loads((R / "docs/data.json").read_text(encoding="utf-8"))
L = json.loads((R / "collecteur/lieux.json").read_text(encoding="utf-8"))

NOUVEAUX_LIEUX = {
    "Cinémathèque québécoise": (45.5154, -73.5596, "Quartier latin"),
    "Cineplex Quartier Latin": (45.5146, -73.5625, "Quartier latin"),
    "Cinéma du Musée": (45.4985, -73.5795, "Centre-ville"),
    "Cinéma du Parc": (45.5104, -73.5765, "Milton-Parc"),
    "Cinéma Beaubien": (45.5408, -73.6031, "Rosemont"),
    "Cinéma Moderne": (45.5228, -73.5946, "Mile End"),
    "Office national du film (ONF)": (45.5087, -73.5672, "Quartier des spectacles"),
    "Salle Bourgie": (45.4986, -73.5797, "Centre-ville"),
    "Oratoire Saint-Joseph": (45.4925, -73.6178, "Côte-des-Neiges"),
    "Chapelle Notre-Dame-de-Bon-Secours": (45.5093, -73.5507, "Vieux-Montréal"),
    "Église Saint-Léon de Westmount": (45.4855, -73.5925, "Westmount"),
    "Église St. John the Evangelist": (45.5072, -73.5683, "Centre-ville"),
    "Église St. George": (45.4985, -73.5714, "Centre-ville"),
    "Le 9e": (45.5035, -73.5710, "Centre-ville"),
    "Théâtre Paradoxe": (45.4528, -73.5900, "Sud-Ouest"),
    "Espace Off-Bach (3487, boul. Saint-Laurent)": (45.5129, -73.5735, "Plateau"),
    "Palais des congrès de Montréal": (45.5040, -73.5610, "Centre-ville"),
}
for n, (la, lo, q) in NOUVEAUX_LIEUX.items():
    D["lieux"].setdefault(n, {"lat": la, "lon": lo, "quartier": q})
    L.setdefault(n, {"lat": la, "lon": lo, "quartier": q})

SALLES = {"Monument National": "Monument-National", "Monument-National": "Monument-National",
          "Cinémathèque": "Cinémathèque québécoise", "Cineplex Quartier Latin": "Cineplex Quartier Latin",
          "Cinéma du Musée": "Cinéma du Musée", "Cinéma du Parc": "Cinéma du Parc", "Cinéma Beaubien": "Cinéma Beaubien",
          "Cinéma Moderne": "Cinéma Moderne", "ONF": "Office national du film (ONF)", "Théâtre Outremont": "Théâtre Outremont",
          "PDA - Théâtre Maisonneuve": "Théâtre Maisonneuve"}

# ---------------- CINEMANIA (festapp.io) : « JJ | HH:MM | titre | salle » ----------------
CINEMANIA = """
02|19:00|Gala Crave : ouverture des journées de la série francophone — Alice|Théâtre Outremont
04|18:15|Gala d'ouverture : Paradis (Jérémy Comte)|Monument National
04|21:00|La Cité des enfants perdus|Cinéma du Parc
05|10:00|SCHTROUMPFMANIA (exposition)|Cinémathèque
05|10:30|Du concert à l'écran — L'orchestre en mouvement, de Montréal à Liège|Cinémathèque
05|12:30|Vernissage de l'exposition SCHTROUMPFMANIA|Cinémathèque
05|14:00|Looking for Cézanne|Cineplex Quartier Latin
05|14:45|L'objet du délit|Cineplex Quartier Latin
05|15:00|Du monde de Peyo à la planète Schtroumpfs|Cinémathèque
05|16:45|La maison des femmes|Cineplex Quartier Latin
05|17:30|Classe de maître avec Jean-Pierre Jeunet|Cinémathèque
05|17:45|Mariage au goût d'orange|Cineplex Quartier Latin
05|17:45|Le faux Soir|Monument National
05|18:00|De souche|Cinéma du Musée
05|18:45|L'extravagant voyage du jeune et prodigieux T. S. Spivet (3D)|Cinémathèque
05|20:15|Gentle monster|Cineplex Quartier Latin
05|20:30|Idling|Cinéma du Musée
05|20:30|Un grand raccourci|Cineplex Quartier Latin
05|21:00|Changer l'eau des fleurs (Jean-Pierre Jeunet)|Monument National
06|13:00|Ceux qui comptent|Cineplex Quartier Latin
06|13:15|L'affaire Marie-Claire|Cineplex Quartier Latin
06|15:15|Heysel 85|Cineplex Quartier Latin
06|15:45|La troisième nuit|Cineplex Quartier Latin
06|17:30|Des beaux malaises à Presque normal (discussion)|Cinémathèque
06|17:30|Rouler des mécaniques|Cineplex Quartier Latin
06|18:00|Du fioul dans les artères|Cineplex Quartier Latin
06|18:00|Le fabuleux destin d'Amélie Poulain (version restaurée)|Cinéma Beaubien
06|18:15|La grande soirée du court québécois — partie 1|Monument National
06|18:45|Les yeux verts|Cinéma du Parc
06|19:00|Au nord des hommes|Cinéma du Musée
06|20:00|Dans Gaza|Cineplex Quartier Latin
06|20:15|La grande soirée du court québécois — partie 2|Monument National
06|20:30|Radio Bonheur|Cinémathèque
06|20:30|Les baronnes|Cineplex Quartier Latin
06|21:00|Le triangle d'or|Cinéma du Parc
07|10:00|Courts métrages : ARTOU, Ceci est mon cœur, Gwoka Odyssey, Orchestre en immersion — OPRL|Cinémathèque
07|10:30|New York, Miriam et moi|Cineplex Quartier Latin
07|11:00|Julián|Cinéma Moderne
07|12:30|Le faux Soir|Cineplex Quartier Latin
07|12:45|Un grand raccourci|Cineplex Quartier Latin
07|13:00|Du fioul dans les artères|Cinéma du Parc
07|13:30|Paradis|Cinéma Moderne
07|13:30|Placée|Cinémathèque
07|15:00|Beaux seigneurs|Cineplex Quartier Latin
07|15:00|Vernissage du volet réalité virtuelle|Cinémathèque
07|15:15|Notre salut|Monument National
07|15:45|Heysel 85|Cineplex Quartier Latin
07|15:45|Radio Bonheur|Cinémathèque
07|16:00|Au nord des hommes|Cinéma Moderne
07|17:15|Les baronnes|Cineplex Quartier Latin
07|18:00|Vivre encore|Cinémathèque
07|18:00|Formats courts|Cineplex Quartier Latin
07|20:00|Bête noire|Cineplex Quartier Latin
07|20:30|Rouler des mécaniques|Cinémathèque
07|20:30|Europe : la bataille des sièges (ciné-concert)|Monument National
07|20:30|Le roi du game|Cineplex Quartier Latin
08|11:00|In waves|Cineplex Quartier Latin
08|11:15|Julián|Cineplex Quartier Latin
08|11:30|Milimo|Cinémathèque
08|13:15|Soudain (Ryusuke Hamaguchi)|Cineplex Quartier Latin
08|13:30|LOL 2.0|Cineplex Quartier Latin
08|13:45|L'Arabe|Cinémathèque
08|13:45|Le dernier acte|Cinéma du Musée
08|14:45|Moulin|Monument National
08|16:00|La frappe|Cineplex Quartier Latin
08|16:00|Le corset|Cinémathèque
08|17:00|Les chrysalides|Cinéma du Musée
08|17:15|L'objet du délit|Cineplex Quartier Latin
08|18:00|Les braves (Coward, Lukas Dhont)|Monument National
08|18:00|Shana|Cinémathèque
08|18:30|Barça zou|Cineplex Quartier Latin
08|19:45|15/18|Cinéma du Musée
08|20:00|Ben'imana|Cinémathèque
08|20:15|La gradiva|Cineplex Quartier Latin
08|20:45|La chaleur|Cineplex Quartier Latin
09|10:45|Table ronde : quand la musique raconte l'image|ONF
09|14:00|Champions|ONF
09|15:30|Un détour par Diane|Cineplex Quartier Latin
09|15:45|Étude de cas : les parcours d'immigration à l'écran (Hôtel Beyrouth)|ONF
09|16:00|Les braves (Coward)|Cineplex Quartier Latin
09|18:00|Adieu monde cruel|Cineplex Quartier Latin
09|19:00|Gala de la 32e édition : Villeneuve, l'ascension d'une légende|PDA - Théâtre Maisonneuve
09|19:15|Garance|Cineplex Quartier Latin
09|20:30|L'espèce explosive|Cineplex Quartier Latin
10|10:00|Table ronde : les séries francophones dans le paysage international|Cinémathèque
10|11:30|Table ronde : quand la littérature québécoise prend vie en série|Cinémathèque
10|13:15|Vivre encore|Cineplex Quartier Latin
10|13:45|Jupiter|Cineplex Quartier Latin
10|14:15|Étude de cas : prélude à la série Farador|Cinémathèque
10|15:30|À voix basse|Cineplex Quartier Latin
10|16:00|Villeneuve, l'ascension d'une légende|Cineplex Quartier Latin
10|16:15|On the roc, Monaco fait son cinéma|Cinémathèque
10|18:00|Vieille Corneille|Cinéma du Musée
10|18:00|Le dernier acte|Cinéma Moderne
10|18:15|Cinquième acte|Cineplex Quartier Latin
10|18:15|Barça zou|Cinémathèque
10|18:30|Un gars, une fille (nouveaux épisodes)|Cineplex Quartier Latin
10|18:45|Mystik|Cinéma du Parc
10|19:00|Lumière ! par Thierry Frémaux|Monument National
10|20:00|La vie d'une femme|Cinéma du Musée
10|20:30|Voilà c'est fini|Cinémathèque
10|20:45|Je te tiens|Cineplex Quartier Latin
10|21:00|7h40 ce matin-là|Cineplex Quartier Latin
10|21:00|Sanguine|Cinéma du Parc
11|10:00|Table ronde : ce que racontent nos tournages en Martinique|Cinémathèque
11|11:30|Table ronde : produire en Martinique|Cinémathèque
11|13:00|Camembert|Cineplex Quartier Latin
11|13:15|Récits martiniquais en formats courts|Cinémathèque
11|13:30|Secondes chances|Cineplex Quartier Latin
11|14:00|Table ronde : du Cambodge au Québec, des cinémas en dialogue|Cinémathèque
11|15:15|La vie d'une femme|Cineplex Quartier Latin
11|15:15|Étude de cas : la création des séries Nish et Kadebwe|Cinémathèque
11|16:00|Voilà c'est fini|Cineplex Quartier Latin
11|17:30|La maison des livres|Cinémathèque
11|17:45|Idling|Cinéma Moderne
11|18:00|Quelques mots d'amour|Cineplex Quartier Latin
11|18:30|Marquer le Congo|Cinéma du Musée
11|18:30|Dernière seconde : Requiem de minuit|Cineplex Quartier Latin
11|19:30|Labrador — Autopsie du silence|Monument National
11|20:45|Ben'imana|Cinémathèque
11|20:45|Mystik|Cineplex Quartier Latin
11|21:00|15/18|Cineplex Quartier Latin
12|10:00|Table ronde : festivals et circulation de la Caraïbe francophone|Cinémathèque
12|11:30|Table ronde : préserver le cinéma d'art et d'essai|Cinémathèque
12|12:45|Le triangle d'or|Cineplex Quartier Latin
12|13:00|Peau d'homme|Cineplex Quartier Latin
12|13:30|Dans Gaza|Cinémathèque
12|14:00|Table ronde : les festivals, vecteur du regard des femmes|Cinémathèque
12|15:00|Une femme aujourd'hui|Cineplex Quartier Latin
12|15:30|L'Arabe|Cineplex Quartier Latin
12|17:15|Isabelle Huppert : message personnel|Cinémathèque
12|18:00|Si tu penses bien|Cineplex Quartier Latin
12|18:15|Marquer le Congo|Cinéma Moderne
12|18:15|Murmures|Cineplex Quartier Latin
12|18:30|Gala Crave : Vigilante|Cinéma du Musée
12|18:30|La grande soirée du court international — partie 1|Cinémathèque
12|18:45|Quelques mots d'amour|Cinéma du Parc
12|20:00|Ni vue, ni connue|Monument National
12|20:15|La grande soirée du court international — partie 2|Cinémathèque
12|20:30|Labrador — Autopsie du silence|Cinéma Moderne
12|20:30|Congo Boy|Cineplex Quartier Latin
12|20:45|Sanguine|Cineplex Quartier Latin
12|21:15|Shana|Cinéma du Parc
13|12:30|John Nollet : façonner les icônes|Cinémathèque
13|12:45|7h40 ce matin-là|Cineplex Quartier Latin
13|14:15|Table ronde : créer au Canada, raconter depuis la région NAWA|Cinémathèque
13|15:30|En haut de la pile|Cineplex Quartier Latin
13|15:30|Si tu penses bien|Cineplex Quartier Latin
13|17:15|Nous l'orchestre|Cinémathèque
13|17:30|Gala Air Canada : Les rayons et les ombres (Xavier Giannoli)|Monument National
13|18:00|Marie Madeleine|Cinéma du Musée
13|18:00|Mémoire de fille|Cineplex Quartier Latin
13|18:15|Cinquième acte|Cinéma Moderne
13|18:30|Une femme aujourd'hui|Cineplex Quartier Latin
13|19:15|La baleine et le musicien|Cinémathèque
13|20:30|Ceux qui comptent|Cinéma du Musée
13|20:45|Vigilante|Cinéma du Parc
13|21:00|Moulin|Cineplex Quartier Latin
13|21:30|Beaux seigneurs|Cineplex Quartier Latin
14|11:00|Le corset|Cineplex Quartier Latin
14|11:00|À la recherche de l'oiseau gris aux rayures vertes|Cinémathèque
14|11:30|Camembert|Cineplex Quartier Latin
14|11:45|Ni vue, ni connue|Cinéma du Musée
14|12:45|Focus Guadeloupe|Cinémathèque
14|13:15|En haut de la pile|Cineplex Quartier Latin
14|13:45|Vieille Corneille|Cineplex Quartier Latin
14|14:30|Mémoire de fille|Cinéma du Musée
14|14:45|Au pied du mur|Cinémathèque
14|16:00|Les chrysalides|Cinéma Moderne
14|16:00|La troisième nuit|Cineplex Quartier Latin
14|16:15|Adieu monde cruel|Cineplex Quartier Latin
14|16:45|Les yeux verts|Cinémathèque
14|17:15|La chaleur|Cinéma du Musée
14|18:30|Gala de clôture : De la Comédie-Française|Monument National
14|20:30|Secondes chances|Cinémathèque
14|20:30|Jupiter|Cineplex Quartier Latin
14|21:00|Mariage au goût d'orange|Cineplex Quartier Latin
15|10:30|Carmen, l'oiseau rebelle|Cinémathèque
15|11:00|LOL 2.0|Cineplex Quartier Latin
15|11:00|La gradiva|Cineplex Quartier Latin
15|12:00|Regards croisés : la comédie au cinéma|Cinéma du Musée
15|12:30|Chalvet, la conquête de la dignité|Cinémathèque
15|13:30|Congo Boy|Cineplex Quartier Latin
15|13:30|Les rayons et les ombres|Cinéma du Musée
15|14:00|Garance|Monument National
15|14:00|Marie Madeleine|Cinéma Moderne
15|14:15|Peau d'homme|Cineplex Quartier Latin
15|14:45|Soudain|Cinéma du Parc
15|15:15|À voix basse|Cinémathèque
15|16:00|In waves|Cineplex Quartier Latin
15|16:45|Notre salut|Cineplex Quartier Latin
15|17:00|L'affaire Marie-Claire|Monument National
15|17:45|La frappe|Cinémathèque
15|17:45|Juste la fin du monde (Xavier Dolan)|Cinéma du Musée
15|18:15|Un détour par Diane|Cineplex Quartier Latin
15|20:00|L'espèce explosive|Cinémathèque
"""


def disc_cinemania(t):
    t2 = t.lower()
    if t2.startswith(("table ronde", "étude de cas", "classe de maître")) or "discussion" in t2:
        return "lettres", ["cinema"]
    if "exposition" in t2 or t2.startswith("vernissage"):
        return "expo", ["cinema"]
    if "ciné-concert" in t2:
        return "cinema", ["musique"]
    return "cinema", []


nouveaux = []
for ligne in CINEMANIA.strip().splitlines():
    jj, h, titre, salle = ligne.split("|")
    disc, aussi = disc_cinemania(titre)
    e = {"date": f"2026-11-{jj}", "heure": h, "discipline": disc, "titre": titre, "lieu": SALLES[salle],
         "url": "https://festivalcinemania.com", "complet": "Paradis (Jérémy" in titre, "jeunePublic": False,
         "source": "festival", "festival": "cinemania"}
    if aussi:
        e["aussi"] = aussi
    nouveaux.append(e)

# ---------------- Festival Bach (festivalbachmontreal.com/programmation) ----------------
B = "https://festivalbachmontreal.com/concerts/"
OFF = "Espace Off-Bach (3487, boul. Saint-Laurent)"
BACH = [
    ("2026-11-04", None, "Pré-ouverture, soirée du 20e anniversaire — Schaghajegh Nosrati, piano", "Théâtre Paradoxe", "concert-surprise-20e-anniversaire/", True),
    ("2026-11-08", None, "Intégrale de l'œuvre pour orgue de Bach, récital 1 — Christian Schmitt", "Oratoire Saint-Joseph", "concert-dorgue-christian-schmitt/", False),
    ("2026-11-14", None, "Bach Incognito : les souvenirs de M. Bach (concert familial, 8 à 88 ans)", "Église St-Andrew et St-Paul", "bach-incognito-2026-concert-pour-les-familles/", False),
    ("2026-11-14", None, "12e Nuit des chœurs « 1001 voix » (gratuit)", "Église St-Andrew et St-Paul", "nuit-des-choeurs-2026/", False),
    ("2026-11-15", None, "Intégrale de l'œuvre pour orgue de Bach, récital 2 — Vincent Boucher", "Oratoire Saint-Joseph", "concert-dorgue-vincent-boucher/", False),
    ("2026-11-20", "19:30", "Concert d'ouverture de la 20e édition — Magnificat et Water Music (dir. John Butt)", "Maison symphonique", "concert-ouverture-2026/", False),
    ("2026-11-21", None, "Deux femmes et Bach — Hayoung Choi, violoncelle", "Chapelle Notre-Dame-de-Bon-Secours", "hayoung-choi-violoncelle/", False),
    ("2026-11-22", None, "Rencontre imaginaire : Bach et Vierne (orgue et chœur)", "Oratoire Saint-Joseph", "concert-dorgue-et-choeur/", False),
    ("2026-11-22", None, "Drame sacré — Vox Luminis", "Église Saint-Léon de Westmount", "vox-luminis/", False),
    ("2026-11-23", None, "Baroque dans tous les sens — Daniel Lanthier, hautbois, et Marco Baronchelli, luth", "Église St. John the Evangelist", "daniel-lanthier-marco-baronchelli/", False),
    ("2026-11-24", None, "Le virtuose aux cordes sensibles — Augustin Hadelich, violon", "Église St. George", "augustin-hadelich-violon/", False),
    ("2026-11-25", None, "Génération Jupiter — Ensemble Jupiter, Léa Desandre et Thomas Dunford", "Église St-Andrew et St-Paul", "ensemble-jupiter/", False),
    ("2026-11-26", "16:00", "David Dias da Silva, clarinette et piano · Off-Bach (gratuit)", OFF, "off-concert-david-dias-da-silva-clarinette-et-piano/", False),
    ("2026-11-26", None, "Voyage baroque vers le Grand Nord — Les Boréades à quatre", "Église St. John the Evangelist", "les-boreades/", False),
    ("2026-11-27", None, "Christophe Gauthier, clavecin · Off-Bach (gratuit)", OFF, "off-concert-christophe-gauthier-clavecin-2/", False),
    ("2026-11-28", None, "Gilles Commeau : musique, santé et cerveau (causerie) · Off-Bach (gratuit)", OFF, "off-talk-conference-cafe-croissant-avec-le-dr-gilles-commeau/", False),
    ("2026-11-28", None, "Vincent Boucher : Bach à l'orgue (mini-conférence) · Off-Bach (gratuit)", OFF, "off-mini-conference-vincent-boucher-organiste/", False),
    ("2026-11-28", None, "Dane Ko, piano · Off-Bach (gratuit)", OFF, "off-concert-dane-ko-2-piano/", False),
    ("2026-11-28", None, "Luc Beauséjour : Bach dans quatre villes (mini-conférence) · Off-Bach (gratuit)", OFF, "off-mini-conference-luc-beausejour-26-1/", False),
    ("2026-11-28", None, "Noémie Raymond, violoncelle, et Chloé Dumoulin, piano · Off-Bach (gratuit)", OFF, "off-recital-noemie-raymond-chloe-dumoulin/", False),
    ("2026-11-29", None, "Michael Maul : à la découverte de Bach (causerie) · Off-Bach (gratuit)", OFF, "off-talk-conference-cafe-croissant-avec-michael-maul/", False),
    ("2026-11-29", None, "Luc Beauséjour : les Variations Goldberg (mini-conférence) · Off-Bach (gratuit)", OFF, "off-mini-conference-luc-beausejour-26-2/", False),
    ("2026-11-29", None, "Intégrale de l'œuvre pour orgue de Bach, récital 3 — Bálint Karosi", "Oratoire Saint-Joseph", "concert-dorgue-balint-karosi/", False),
    ("2026-11-29", None, "Loïc Lapatrie, clavecin · Off-Bach (gratuit)", OFF, "off-concert-loic-lapatrie/", False),
    ("2026-11-29", None, "Ariane Racicot, piano jazz · Off-Bach (gratuit)", OFF, "off-concert-ariane-racicot-piano/", False),
    ("2026-11-30", None, "Marie Nadeau-Tremblay, Tristan Best et Kerry Bursey · Off-Bach (gratuit)", OFF, "off-concert-marie-nadeau-tristan-best-kerry-bursey/", False),
    ("2026-11-30", None, "L'absolu Bach — Sir András Schiff, piano", "Maison symphonique", "sir-andras-schiff-piano/", False),
    ("2026-12-01", None, "Étudiants de l'UdeM : l'heure de la découverte · Off-Bach (gratuit)", OFF, "off-lheure-de-la-decouverte-udm/", False),
    ("2026-12-01", None, "Luc Beauséjour : Bach, maître de la fugue (mini-conférence) · Off-Bach (gratuit)", OFF, "off-mini-conference-luc-beausejour-26-3/", False),
    ("2026-12-01", None, "Tristan Longval-Gagné, piano · Off-Bach (gratuit)", OFF, "off-concert-tristan-longval-gagne-piano/", False),
    ("2026-12-01", None, "Trois pupitres pour les Variations Goldberg — Andrew Wan, Victor Fournelle-Blain, Anna Burden", "Chapelle Notre-Dame-de-Bon-Secours", "trio-a-cordes/", False),
    ("2026-12-02", None, "Luc Beauséjour : Bach l'improvisateur (mini-conférence) · Off-Bach (gratuit)", OFF, "off-mini-conference-luc-beausejour-26-4/", False),
    ("2026-12-02", None, "Krystina Marcoux, marimba, et Juan Sebastian Delgado, violoncelle · Off-Bach (gratuit)", OFF, "off-recital-stick-and-bow/", False),
    ("2026-12-02", None, "Étudiants de McGill : l'heure de la découverte · Off-Bach (gratuit)", OFF, "off-lheure-de-la-decouverte-mcgill-2/", False),
    ("2026-12-02", None, "Bach, le feu de la jeunesse — Ensemble Correspondances", "Salle Bourgie", "ensemble-correspondances/", False),
    ("2026-12-03", None, "Luc Beauséjour : Bach, un Européen avant l'heure (mini-conférence) · Off-Bach (gratuit)", OFF, "off-mini-conference-luc-beausejour-26-5/", False),
    ("2026-12-03", None, "Dominique Beauséjour-Ostiguy et Marie Bégin · Off-Bach (gratuit)", OFF, "off-concert-dominique-beausejour-ostiguy-marie-begin/", False),
    ("2026-12-03", None, "Une soirée en solo avec Chris Thile, mandoline", "Salle Bourgie", "chris-thile-mandoline/", False),
    ("2026-12-04", None, "Quatre mains, deux mondes — Pavel Kolesnikov et Samson Tsoy, pianos", "Salle Bourgie", "pavel-kolesnikov-samson-tsoy-duo-piano/", False),
    ("2026-12-05", None, "Clôture en deux temps : 20 ans avec les Bach (1) — Akamus", "Église St. George", "akamus-1-2/", False),
    ("2026-12-06", None, "Clôture en deux temps : suites de danses (2) — Akamus", "Le 9e", "concert-de-cloture-akamus/", False),
    ("2026-12-08", None, "Postlude avec l'OSM : Oratorio de Noël (dir. Kent Nagano)", "Maison symphonique", "oratorio-de-noel-osm/", True),
]
for dt, h, t, lieu, slug, complet in BACH:
    conf = "conférence" in t or "causerie" in t
    e = {"date": dt, "heure": h, "discipline": "lettres" if conf else "musique", "titre": t, "lieu": lieu, "url": B + slug,
         "complet": complet, "jeunePublic": "familial" in t, "source": "festival", "festival": "bach"}
    if conf:
        e["aussi"] = ["musique"]
    if "(gratuit)" in t:
        e["prix"] = "Gratuit"
    if h == "19:30" and "ouverture" in t:
        e["prix"] = "49 à 125 $"
    nouveaux.append(e)

# ---------------- M pour Montréal (jambase) ----------------
MPM = {"2026-11-18": "Béton Armé, Faze, zouz, 2120, Knats, Misc, Julien Fillion, Mario2, Cosmic Dog Fog, Les Louanges, Loviet, 646yf4t",
       "2026-11-19": "Lisa LeBlanc, Les Shirley, dead ex girlfriends, Yoo Doo Right, Population II, Blesse, Emma Beko, Marci, Born At Midnite…",
       "2026-11-20": "Afrotronix, HAWA B, Geoffroy, Lou Val, Cherrykim, Balaclava, TVOD, Skiifall, Papaya Noon, Do Nothing…",
       "2026-11-21": "Suuns, Plants and Animals, We Are Wolves, PERCEVAL, Unessential Oils, EZEZEZ, Moses Belanger, Odeza…"}
for dt, art in MPM.items():
    nouveaux.append({"date": dt, "heure": None, "discipline": "musique", "titre": f"M pour Montréal : {art}",
                     "lieu": "Club Soda", "url": "https://mpourmontreal.com", "complet": False, "jeunePublic": False,
                     "source": "festival", "festival": "mpourmontreal",
                     "resume": "Vitrines du festival dans plusieurs salles du centre-ville ; horaires et salles par artiste sur le site du festival."})

# ---------------- ELEKTRA ----------------
nouveaux.append({"date": "2026-11-07", "heure": None, "discipline": "expo", "titre": "Jeux et énergie solaire avec Lee Wilkins (atelier, Biennale ELEKTRA)",
                 "lieu": "Arsenal art contemporain", "url": "https://www.elektramontreal.ca/activite/jeux-et-energie-solaire-avec-lee-wilkins",
                 "complet": False, "jeunePublic": False, "source": "festival", "festival": "elektra"})

# ---------------- Séries : Salon du livre ----------------
if not any(x.get("festival") == "salonlivre" for x in D["expos"]):
    D["expos"].append({"titre": "Salon du livre de Montréal (49e édition)", "lieu": "Palais des congrès de Montréal", "debut": "2026-11-25",
                       "fin": "2026-11-29", "discipline": "lettres", "url": "https://salondulivredemontreal.com", "festival": "salonlivre"})

# Rejouable : on retire d'abord ce que ce script avait ajouté
D["events"] = [e for e in D["events"] if not (e.get("source") == "festival" and e.get("festival") in ("cinemania", "bach", "mpourmontreal", "elektra"))]
avant = len(D["events"])
D["events"] = dedoublonner(D["events"] + nouveaux)
(R / "docs/data.json").write_text(json.dumps(D, ensure_ascii=False), encoding="utf-8")
(R / "collecteur/lieux.json").write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(nouveaux)} proposés, {len(D['events']) - avant} ajoutés (le reste fusionné avec des doublons)")
