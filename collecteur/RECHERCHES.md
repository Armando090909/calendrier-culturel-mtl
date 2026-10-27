# Journal des recherches

Ce qui a été trouvé à la main (oct. 2026), pour ne pas refaire le travail. À mettre à jour quand on ajoute ou répare une source.

## Où est rangé quoi
| Fichier | Contenu | Mis à jour par |
|---|---|---|
| `collecteur/sources.yaml` | les 57 agendas et sites de salles lus (adresse, type, jours de lecture) | à la main |
| `collecteur/festivals.yaml` | les 59 festivals : dates, site, page de programmation | à la main + collecte (dates trouvées) |
| `collecteur/lieux.json` | les salles connues, leurs coordonnées et leurs autres noms | collecte (géolocalisation une seule fois par salle) |
| `collecteur/cache/<source>.json` | dernière lecture réussie de chaque source | collecte |
| `collecteur/cache/empreintes.json` | mémoire des pages lues par l'IA : une page inchangée n'est pas relue | collecte |
| `collecteur/cache/heures.json` | heures trouvées sur les pages d'événements | collecte |
| `collecteur/cache/festivals_dates.json` | dates des prochaines éditions trouvées en ligne | collecte |
| `docs/rapport.json` | nombre d'événements et erreurs par source, à chaque collecte | collecte |
| `collecteur/manuels.json` | programmes saisis à la main avant la mise en ligne (festivals, salles, galeries) ; relus à chaque collecte | à la main |
| `outils/ajout_festivals_2026.py` | programmes saisis à la main le 27 oct. 2026 (CINEMANIA, Bach, M pour Montréal…) | ponctuel |

## Rythme de la collecte automatique (GitHub Actions, chaque jour vers 5 h 30)
- Ville de Montréal, calendriers iCal, formulaires : chaque jour (gratuit).
- Agendas et sites de salles : 2 fois par semaine (lundi, jeudi), selon `jours_semaine`.
- **Festivals : chaque lundi pour tous** (veille hebdomadaire) ; **lundi, mercredi, vendredi** de 75 jours avant le début jusqu'à la fin du festival.
- Dates des prochaines éditions : chaque lundi, pour les festivals terminés (IA seulement si le site a changé).
- Une page déjà lue dont le texte n'a pas changé reprend son résultat en mémoire : aucun coût d'IA.

## Liens de découverte (écouter, bande-annonce)
- Ordre : lecteurs intégrés et liens nommés sur la page de l'événement → MusicBrainz (artistes, nom exact, Canada préféré, abstention si homonymes) → TMDb (films, si `TMDB_API_KEY`).
- Mémoire : `collecteur/cache/decouverte.json` (un artiste n'est cherché qu'une fois ; nouvel essai après 30 jours si rien trouvé).
- Songkick n'est jamais utilisé pour ces liens (pages sans liens d'artistes fiables).

## Sources qui marchent bien
- **FestApp** (`festapp.io/festivals/<nom>/<année>`) : horaires complets de plusieurs festivals (CINEMANIA, Coup de cœur). Très utile quand le site officiel est en JavaScript.
- **Place des Arts** (`placedesarts.com/festival/<nom>`) : liste des événements de festivals présentés à la PdA (sans heures sur la liste ; heures sur la page de chaque événement).
- **Festival Bach** : `festivalbachmontreal.com/programmation/` liste tous les concerts ; l'heure est sur la page de chaque concert.
- **La Mèche courte** : liste sur `/programmation`, heures sur `/spectacles/<nom>` (représentations scolaires à ignorer).
- **Jambase** (`jambase.com/festival/<nom>-<année>`) : programmation par soir des festivals de musique.
- **ma.to** : pages de concerts avec l'heure (« Doors… show… »). La liste générale n'a pas d'heures.
- **Tourisme Montréal** (`mtl.org/fr/experience/quoi-faire-<mois>`) : meilleur résumé mensuel des festivals et de leurs dates.

- **AGAC** (`agac.ca/galeries/`) : 34 galeries membres, dont 22 à Montréal (+ Art Mûr déjà suivie). Les fiches AGAC donnent adresse et site, pas les expositions → chaque galerie est une source à part (`cle: galeries`, relue chaque lundi). Pages d'expositions confirmées : Bradley Ertaskiran `/en/exhibitions/`, Blouin Division `/en/exhibitions/`, Eli Kerr `/expositions-fr`, PFOAC `/en/exhibitions/forthcoming/`, Simon Blais `/fr/expos/`. Les autres : page d'accueil (à préciser si le rapport donne 0). Coordonnées des galeries : approximatives, d'après l'adresse.

## Sources à éviter ou limitées
- **Songkick** : aucune heure de concert, même sur la page de l'événement. Gardé pour la couverture ; la version avec l'heure (site de la salle, ma.to) remplace la sienne au dédoublonnage.
- **festivalarabe.com** : programme affiché en JavaScript, illisible sans navigateur → passer par la Place des Arts.
- Sites inaccessibles depuis l'outil de recherche utilisé ici (à vérifier depuis GitHub Actions, qui n'a pas ces restrictions) : festivalcinemania.com, coupdecoeur.ca, ridm.ca, image-nation.org, mpourmontreal.com, elektramontreal.ca (partiel), barleritzpdb.com.

## Programmations encore à venir (au 27 oct. 2026)
- RIDM (19–29 nov.) : 5 films annoncés seulement.
- image+nation (19–29 nov.), Festival du cinéma israélien (15–29 nov.), Mundial (17–21 nov.) : rien de publié trouvé.
- M pour Montréal : salles et heures par artiste pas encore publiées.
- Festithéâtrecréole (28 oct.–8 nov.) : aucun programme en ligne trouvé.

## Adresses à confirmer (déduites, non ouvertes)
Sites de : Mundial, Festival des clowns, Festival de la poésie, Festival du film sud-asiatique, Festival des arts de ruelles, JOAT ; et les salles de musique ajoutées le 26 oct. (Club Soda, Foufounes, Newspeak, Piranha Bar, Café Campus, Théâtre St-Denis, evenko). Le rapport de collecte (`docs/rapport.json`) dira lesquelles donnent 0 événement.


## Tour des « bijoux » (27 oct. 2026)
Objectif : petites salles, quartiers excentrés, lieux multidisciplinaires, art de rue, culture populaire. Exclus : événements corporatifs (C2 Montréal, MTL Connecte, réseautage, salons de l'emploi) — mots ajoutés à `NON_CULTUREL` (normalisation.py).

**Ajoutés aux sources (sources.yaml, bloc « Tour des bijoux »)**
- Boîtes à musique, jazz, monde : Upstairs, Dièse Onze, Club Balattou, Cabaret Jazz L'Entracte, Bistro à Jojo (blues), Hurley's (trad), Le Balcon, Turbo Haüs, Quai des Brumes, Le Ministère, Le Belmont, Ausgang Plaza, Système, Théâtre Rialto, Le National, Le Studio TD, et les pages d'événements de La Toscadura, P'tit Ours et La Sotterenea (Casa del Popolo).
- Électro et raves : Resident Advisor (`ra.co/events/ca/montreal`, l'agenda de référence de la scène), Bar Datcha, SAT. Les raves dans des lieux secrets s'annoncent sur RA, Instagram ou Telegram ; seul RA est lisible.
- Humour amateur et cabaret : Laugh It Off MTL (scènes ouvertes), Cabaret Mado, Wiggle Room, Caf' Conc'.
- Petits théâtres et création : Espace La Risée, InfiniTheatre, MainLine, Repercussion, Théâtre de l'Esquisse, La Comédie de Montréal, Circuit-Est, Studio 303, La Serre, DARE-DARE (art public), Monument-National, Le Livart.
- Littérature et slam : Drawn & Quarterly, La poésie partout, Slamontréal, GSIMtl, La Livrerie.
- Extrémités de l'île : Salle Pauline-Julien (ouest), Pointe-Claire / Stewart Hall (ville liée, absente des données de la Ville), Salle Jean-Grimaldi (LaSalle), programmations de Pierrefonds-Roxboro et de LaSalle (montreal.ca), 150 ans du parc du Mont-Royal.
- Les maisons de la culture, bibliothèques et centres culturels des arrondissements (Anjou, Montréal-Nord, Saint-Léonard, Rivière-des-Prairies–Pointe-aux-Trembles, etc.) sont déjà couverts par les données ouvertes de la Ville.

**Ajoutés aux festivals (festivals.yaml)** : Comiccon (juillet) et son édition des Fêtes (5–6 déc., à confirmer), Under Pressure (graffiti, août), Suoni Per Il Popolo (juin), Escales Improbables (sept.), Festival interculturel du conte (oct.), RU Réappropriation urbaine (juillet), Concerts Campbell (gratuits dans les parcs, juin–août), Shows de ruelle (ruelle Gaboury, été), Tam-tams du Mont-Royal (dimanches), West Island Blues Festival (août), L'OM au pied du Mont-Royal (5 août), Cinéma sous les étoiles (documentaires gratuits en plein air dans ~18 parcs, fin juin–fin août ; grille : `cinemasouslesetoiles.org/programmation/grille-horaire/`, lieux : `/localisations-des-projections/`).

**Repérés mais non ajoutés (pas de page lisible par programme)** : Cabaret Berlin, Bar de Courcelle, Terminal Comédie Club, Le Bordel Comédie Club, The Comedy Nest, 3rd Floor Comedy Club, Club DD's, Bar Le Cocktail, Complexe Sky (Instagram ou Facebook seulement) → passer par le formulaire. Cinémas indépendants (Cinéma Public, du Parc, Moderne, Beaubien) : leurs séances quotidiennes noieraient le calendrier ; à n'ajouter que pour des soirées spéciales. Musée des ondes Emile Berliner, Bâtiment 7, Fonderie Darling : à surveiller.

**Sources utiles pour un prochain tour** : themain.com/guide/best-music-venues-montreal (28 salles), cultmtl.com (guide annuel des salles), mtl.org (jazz, drag, musique live), laughitoffmtl.ca (humour), studio303.ca/en/directory (lieux de danse et performance), ptaff.ca/theatre_montreal (théâtres), estmediamontreal.com (culture dans l'est), ra.co/guide/ca/montreal (clubs).
