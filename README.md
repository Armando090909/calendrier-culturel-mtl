# Calendrier culturel montréalais

Site public et gratuit qui rassemble les événements culturels de l'île de Montréal (théâtre, musique, danse, expositions, etc.), avec filtres par discipline et par date (mois, semaine, jour).

Tout fonctionne sur **GitHub**, gratuitement :
- **le site** est hébergé par GitHub Pages (dossier `docs/`) ;
- **la collecte** tourne chaque jour toute seule grâce à GitHub Actions (dossier `collecteur/`), puis met le site à jour.

---

## Comment ça marche

```
Sources ──► programme de collecte (chaque jour, 5 h 30) ──► docs/data.json ──► site web
  │
  ├─ Ville de Montréal (fichier de données ouvertes) ........ code, gratuit
  ├─ Ask A Punk (agenda DIY / punk) ........................... code, gratuit
  ├─ Calendriers iCal des salles (Google Agenda, etc.) ........ code, gratuit
  ├─ Pages avec données « Event » (schema.org) ................ code, gratuit
  ├─ Pages ordinaires (théâtres, Sors-tu?, Songkick…) ......... lues par l'IA (Claude), quelques $ par mois
  └─ Formulaires du public et des salles (Google Forms) ....... code, gratuit
```

Le programme écarte les cours et activités non culturelles, les événements annulés et tout ce qui est hors de l'île. Il fusionne les doublons et place chaque salle sur la carte (OpenStreetMap). Si une collecte donne un résultat anormalement maigre, **l'ancien calendrier reste en ligne** et GitHub vous envoie un courriel.

---

## Mise en ligne, pas à pas (environ 45 minutes la première fois)

### 1. Créer le dépôt sur GitHub
1. Créez un compte gratuit sur <https://github.com>.
2. En haut à droite : **+** → **New repository**. Nom : `calendrier-culturel-mtl`. Cochez **Public** (obligatoire pour l'hébergement gratuit). Cliquez **Create repository**.
3. Sur la page du dépôt vide : **uploading an existing file**. Glissez-déposez **le contenu** du dossier `calendrier-culturel-mtl` (pas le dossier lui-même), puis **Commit changes**.

> **Attention, dossier caché.** Le dossier `.github` commence par un point : sur Mac et Windows, il est souvent invisible et ne sera pas envoyé. Pour vérifier : le dépôt doit contenir `.github/workflows/collecte.yml`. S'il manque : **Add file → Create new file**, tapez exactement `.github/workflows/collecte.yml` comme nom, collez le contenu du fichier, puis **Commit changes**.
> Autre option plus confortable : l'application gratuite **GitHub Desktop**.

### 2. Activer le site
1. Dans le dépôt : **Settings** → **Pages**.
2. *Source* : choisissez **GitHub Actions**. (Il n'y a rien d'autre à régler sur cette page.)
3. Le site sera publié au premier lancement (étape 6), à l'adresse `https://VOTRE-NOM.github.io/calendrier-culturel-mtl/`.

4. **Adresse ccmtl.ca** : dans *Custom domain*, tapez `ccmtl.ca` → **Save**, puis cochez **Enforce HTTPS** quand la case devient disponible (jusqu'à 24 h). Chez Namecheap (*Advanced DNS*), il faut 4 lignes `A` pour `@` (185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153) et une ligne `CNAME` `www` → `armando090909.github.io.`

Si une première exécution a échoué dans l'onglet **Actions** juste après l'envoi des fichiers, c'est normal : elle a eu lieu avant ce réglage.

### 3. Autoriser la collecte à mettre le site à jour
**Settings** → **Actions** → **General** → *Workflow permissions* : **Read and write permissions** → **Save**.

### 4. Votre courriel de contact
**Settings** → **Secrets and variables** → **Actions** → onglet **Variables** → **New repository variable** :
- Nom : `CONTACT`, valeur : votre courriel. Il est envoyé à OpenStreetMap avec les recherches d'adresse, comme leurs règles le demandent. Il n'est pas publié sur le site.

### 5. La clé IA (facultatif, recommandé)
Sans clé, seules les sources « code » sont lues (Ville, Ask A Punk, calendriers iCal, formulaires). Avec la clé, les pages des théâtres, de Sors-tu? et de Songkick sont lues aussi.
1. Créez un compte sur <https://platform.claude.com>, ajoutez un moyen de paiement et **fixez une limite de dépense mensuelle** (ex. 10 $).
2. Créez une clé API (<https://platform.claude.com/settings/keys> → **Create key**). **Choisissez un espace de travail** (*workspace*, ex. « Default ») pour la clé, puis copiez-la (elle n'est affichée qu'une fois). Si la clé n'est liée à aucun espace de travail, ajoutez la variable `ANTHROPIC_WORKSPACE_ID` (identifiant `wrkspc_…`) comme à l'étape 4.
3. Dans GitHub : **Settings** → **Secrets and variables** → **Actions** → onglet **Secrets** → **New repository secret**. Nom : `ANTHROPIC_API_KEY`, valeur : la clé.

Coût estimé avec les sources fournies : **environ 2 à 5 $ par mois**. Le modèle utilisé est Claude Haiku 5.5, le moins cher ; le calcul est une estimation, pas un devis. Pour réduire le coût, utilisez `jours_semaine` dans `collecteur/sources.yaml` : la source n'est relue que ces jours-là.

### 5 bis. Bandes-annonces de films (facultatif, gratuit)
Pour que les films aient un lien « Bande-annonce » vérifié : créez un compte gratuit sur <https://www.themoviedb.org>, demandez une clé d'API (**Paramètres** → **API**), puis ajoutez-la dans GitHub comme secret `TMDB_API_KEY` (même méthode qu'à l'étape 5). Sans cette clé, les bandes-annonces viennent seulement des pages des cinémas et festivals qui en intègrent une.

Les liens « Écouter » des concerts ne demandent rien : ils viennent de la page de l'événement et de MusicBrainz, une base musicale ouverte et gratuite. Seuls des liens vérifiés sont affichés ; sinon le site propose une simple recherche YouTube, présentée comme telle.

### 6. Premier lancement
**Actions** → si GitHub le demande, **I understand my workflows, go ahead and enable them** → **Collecte des événements** → **Run workflow**. Comptez 5 à 20 minutes.

Ensuite :
- ✅ vert : le site est en ligne et à jour (l'adresse s'affiche dans le résumé de l'exécution). Le fichier `docs/rapport.json` indique combien d'événements chaque source a donnés.
- ❌ rouge : cliquez sur la ligne pour lire l'erreur. La première fois, regardez surtout la ligne `colonnes :` de la Ville. Si le fichier de la Ville a changé de format, il faudra ajuster `ville_csv` dans `collecteur/connecteurs.py`.

**Ce même bouton « Run workflow » est votre bouton « Mettre à jour maintenant ».** Sinon, la collecte se fait seule chaque jour vers 5 h 30.

### 7. Les formulaires (Google Forms) — créés par un script
Le fichier `outils/formulaires.gs` crée les deux formulaires (« Proposer un événement » et « Ajouter mon calendrier »), leurs feuilles de réponses, la colonne **Approuvé** et un onglet **publique** sans les courriels.

1. Connecté au compte Google du projet, ouvrez <https://script.google.com> → **Nouveau projet**.
2. Effacez tout, collez le contenu de `outils/formulaires.gs`, cliquez sur **Enregistrer**.
3. Choisissez la fonction `creerFormulaires` → **Exécuter**. Autorisez le script (Google affiche un avertissement pour tout script personnel : **Paramètres avancés** → **Accéder à…** → **Autoriser**).
4. Le **Journal d'exécution** affiche les liens. Puis, pour chacune des 2 feuilles :
   - **Fichier** → **Partager** → **Publier sur le Web** → onglet **publique** (pas l'onglet des réponses) → format **CSV** → **Publier** → copiez le lien ;
   - dans GitHub (comme à l'étape 4), ajoutez la variable `PROPOSITIONS_CSV_URL` (feuille A) ou `CALENDRIERS_CSV_URL` (feuille B).
5. Collez les 2 liens publics des formulaires dans `docs/config.json` (icône crayon sur GitHub) : `formulaireEvenement` et `formulaireCalendrier`. Le site se republie seul ; les boutons apparaissent.

**Modération** : rien n'est publié tant que vous n'écrivez pas `oui` dans la colonne **Approuvé** de l'onglet des réponses.

Les intitulés des questions sont lus par le programme : si vous les modifiez, gardez les mots clés (Titre, Date, Heure, Lieu, Adresse, Discipline, Lien, Jeune public, Description, Prix, billetterie, Image, Courriel ; et pour B : organisme, calendrier, Nom de la salle, Adresse de la salle).

### 8. Votre propre adresse (facultatif)
Achetez un nom de domaine (ex. `sortiramontreal.ca`, environ 20 $ par an), puis **Settings** → **Pages** → **Custom domain**. GitHub explique les réglages à faire chez le vendeur du domaine.

---

## Les festivals
La liste est dans `collecteur/festivals.yaml` (59 festivals : nom, disciplines, dates de la dernière édition connue, site, page de programmation). L'onglet **Festivals** du site les montre : en cours, dans les 3 prochains mois, puis le reste de l'année.

- **Programmations** : la page de programmation de chaque festival est relue **chaque lundi** (veille hebdomadaire), et aussi mercredi et vendredi de 75 jours avant le début jusqu'à la fin du festival. Ses spectacles entrent au calendrier avec l'étiquette du festival. Quand la liste ne donne pas les heures, la page de chaque spectacle est lue. Ajoutez l'adresse exacte de la page « Programmation » dans `programmation:` dès qu'elle est connue (sinon, la page d'accueil est lue).
- **Prochaines éditions** : chaque lundi, le site de chaque festival terminé est relu pour trouver les dates de l'édition suivante (IA, seulement si la page a changé). Les dates trouvées sont marquées « à confirmer ».
- **Mémoire** : une page déjà lue dont le texte n'a pas changé n'est pas renvoyée à l'IA (`collecteur/cache/empreintes.json`) ; la veille hebdomadaire coûte donc presque rien.
- **Journal des recherches** : `collecteur/RECHERCHES.md` résume les sources qui marchent, celles à éviter et ce qui reste à trouver.
- **Ajouter un festival** : copiez une ligne de `festivals.yaml` et adaptez-la.

## La carte du métro
La carte en haut du site est une évocation (un métro imaginaire) : chaque station porte le nom d'une salle. Pour changer les salles, modifiez la liste STATIONS de `outils/carte_metro.py`, puis lancez `python outils/carte_metro.py`.

## Ajouter ou modifier une source
Tout est dans `collecteur/sources.yaml`. Ouvrez-le sur GitHub, cliquez le crayon, modifiez, puis **Commit changes**.
- Une salle vous donne un lien iCal : copiez l'exemple « Galerie Exemple » et remplacez les valeurs. Ou ajoutez-la simplement par le formulaire B.
- Une page de théâtre donne 0 événement dans le rapport : remplacez son adresse par celle de sa page « Programmation » ou « Calendrier ».
- Désactiver une source : `actif: false`.

## Avant d'annoncer le site au public
- **Autorisations** : Sors-tu? et Songkick sont des agendas privés. Lisez leurs conditions d'utilisation et demandez une autorisation écrite. Un projet bénévole sans but lucratif qui renvoie vers leurs pages a de bonnes chances d'obtenir un oui. En attendant, vous pouvez les mettre en `actif: false`. Je ne suis pas juriste.
- **Loi 25 (Québec)** : comme vous recueillez des courriels, désignez une personne responsable des renseignements personnels et publiez une courte politique de confidentialité. Voir la Commission d'accès à l'information : <https://www.cai.gouv.qc.ca>. Ceci n'est pas un avis juridique.

## Entretien (environ 15 minutes par semaine)
- Approuvez les nouvelles lignes dans les deux feuilles Google (colonne **Approuvé**).
- Jetez un œil à `docs/rapport.json` : une source à 0 ou en erreur plusieurs jours de suite a probablement changé son site.
- Les salles nouvellement détectées sont ajoutées à `collecteur/lieux.json`. Une salle mal placée sur la carte se corrige là (lat/lon). On peut y ajouter des `alias`, c'est-à-dire d'autres noms de la même salle.

## Limites connues
- Le classement par discipline se fait par mots-clés, puis par l'IA pour les cas douteux : il reste des erreurs.
- Les positions des salles sont approximatives (OpenStreetMap ou estimation).
- Les raves et une partie de la scène DIY s'annoncent sur Instagram ou Telegram, qu'aucun programme ne peut lire. Le formulaire est la voie pour ces événements.
- **Photos** : par prudence (droit d'auteur), le site n'affiche que les images fournies par les salles elles-mêmes (formulaire ou calendrier soumis). Les résumés des pages lues par l'IA sont réécrits dans ses mots.
- Les pages construites entièrement en JavaScript (ex. Resident Advisor) ne sont pas lisibles par la collecte.

## Pour les curieux : structure du dépôt
```
docs/                     le site (GitHub Pages)
  index.html, app.js, style.css   le calendrier
  salles.html             la page « Ajouter vos événements »
  config.json             liens des formulaires et courriel
  data.json               événements (réécrit chaque jour)
  rapport.json            résultat de la dernière collecte
collecteur/               le programme de collecte (Python)
  collecte.py             chef d'orchestre
  connecteurs.py          un lecteur par type de source
  ics.py                  lecteur de calendriers iCal
  normalisation.py        disciplines, doublons, filtre de l'île, noms de salles
  geo.py                  position des salles (OpenStreetMap)
  ia.py                   lecture des pages ordinaires par Claude
  sources.yaml            LA LISTE DES SOURCES (à modifier)
  lieux.json              salles connues et leurs positions
  tests/                  tests automatiques (lancés avant chaque collecte)
.github/workflows/collecte.yml    l'horaire de la collecte
```
Tester sur votre ordinateur (facultatif) : `pip install -r collecteur/requirements.txt`, puis `python -m unittest discover -s collecteur/tests` et `python collecteur/collecte.py`.

## Dons volontaires (facultatif)

Un encadré de dons s'affiche au bas du calendrier dès qu'un des deux champs est rempli dans `docs/config.json` :

```json
"donInterac": "dons@votre-courriel.ca",
"don": "https://ko-fi.com/votre-nom",
"donTexte": "Donner 1 $ ♥"
```

- **Virement Interac** (`donInterac`) : aucuns frais pour vous ; activez le **dépôt automatique** dans votre banque pour cette adresse. Le courriel est affiché publiquement : utilisez une adresse dédiée.
- **Ko-fi** (`don`) : pour les dons par carte. Pas de commission Ko-fi, mais Stripe ou PayPal prennent environ 2,9 % + 0,30 $ par don (il reste environ 0,67 $ sur 1 $).
- **Plus tard** : si le projet devient un OBNL enregistré, **Zeffy** permet de recevoir des dons par carte sans frais pour l'organisme.
- Laissez les champs vides (`""`) pour cacher l'encadré. Sans organisme de bienfaisance enregistré, aucun reçu fiscal ne peut être remis.

## Entretien et transmission

Le guide complet (architecture, comptes, automatismes, courriels d'alerte, tâches périodiques, déménagement,
passation) est tenu par le propriétaire du projet dans un document « ccmtl.ca · Guide d'entretien et de transmission ».
En bref :
- la collecte tourne chaque nuit (lancée par cron-job.org à 1 h 30) ; le bilan de santé ouvre un avis (onglet Issues)
  seulement pour un problème qui dure ;
- les sources muettes sont réparées automatiquement (`collecteur/autoentretien.py`, `cache/reparations.json`) et de
  nouvelles salles sont découvertes chaque dimanche (`cache/sources_auto.json`) ;
- un ordinateur à Montréal (`docs/mac/`) lit ce que GitHub ne peut pas lire (Ville de Montréal, salles qui bloquent) ;
- secrets nécessaires : `ANTHROPIC_API_KEY`, `TMDB_API_KEY` ; variables : `PROPOSITIONS_CSV_URL`,
  `CALENDRIERS_CSV_URL`, `CONTACT`.

