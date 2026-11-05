"""Version anglaise des pages fixes du site (docs/en/*.html), produite à partir des pages françaises : mêmes balises,
textes remplacés par leur traduction. Une seule source à entretenir (le français) ; une phrase française modifiée
sans traduction correspondante est signalée (elle resterait en français dans la version anglaise).

Lancé à la publication du site (.github/workflows/collecte.yml), avant les pages d'événements.
"""
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOCS = RACINE / "docs"

# Remplacements communs à toutes les pages (texte exact → anglais). Les noms de salles, de stations et de festivals
# restent tels quels.
COMMUNS = [
    ('<html lang="fr">', '<html lang="en" data-base="../">'),
    ('<meta property="og:locale" content="fr_CA">', '<meta property="og:locale" content="en_CA">'),
    ('<link rel="stylesheet" href="style.css', '<link rel="stylesheet" href="../style.css'),
    ('<link rel="stylesheet" href="v2.css', '<link rel="stylesheet" href="../v2.css'),
    ('<img src="logo-ccmtl.webp" width="1040" height="704" alt="ccmtl : formes colorées, yeux et étoiles autour des lettres ccmtl">',
     '<img src="../logo-ccmtl.webp" width="1040" height="704" alt="ccmtl: colourful shapes, eyes and stars around the letters ccmtl">'),
    ('<a class="v2-marque" href="./">Calendrier culturel<br><span>de Montréal</span></a>',
     '<a class="v2-marque" href="./">Montréal\'s cultural<br><span>calendar</span></a>'),
    ('<meta property="og:site_name" content="Calendrier culturel montréalais">', '<meta property="og:site_name" content="Montreal\'s cultural calendar">'),
    ('aria-label="La ligne culture : un métro imaginaire dont les stations sont des salles de Montréal"',
     'aria-label="The culture line: an imaginary metro whose stations are Montréal venues"'),
    ('>la ligne culture</text>', '>the culture line</text>'),
    ('<a href="index.html">← Retour au calendrier</a>', '<a href="index.html">← Back to the calendar</a>'),
    ('<link rel="stylesheet" href="fonts/', '<link rel="stylesheet" href="../fonts/'),
    ('<script src="app.js', '<script src="../app.js'),
    ('<a class="langue" id="langue" href="en/" hreflang="en" lang="en" title="English version">EN</a>',
     '<a class="langue" id="langue" href="../" hreflang="fr" lang="fr" title="Version française">FR</a>'),
    ('<p class="wordmark">calendrier culturel <b>mtl</b></p>', '<p class="wordmark">montreal\'s cultural <b>calendar</b></p>'),
    ('href="https://creativecommons.org/licenses/by-nc/4.0/deed.fr"', 'href="https://creativecommons.org/licenses/by-nc/4.0/deed.en"'),
    ('<a class="pied-bt" href="sources.html">Nos sources et salles</a>', '<a class="pied-bt" href="sources.html">Our sources & venues</a>'),
    ('<a class="pied-bt" href="archives.html">Archives</a>', '<a class="pied-bt" href="archives.html">Archive</a>'),
    ('Faire un don 2 $ ♥', 'Donate $2 ♥'),
    ('<p><b>Un projet sans but lucratif, gratuit et sans pub.</b> Il a quand même des frais : le nom de domaine et la lecture automatique de près de 200 sites de salles et de festivals chaque jour. Ton don sert seulement à couvrir ces frais.</p>',
     '<p><b>A non-profit project, free and ad-free.</b> It still has costs: the domain name and the automatic reading of some 200 venue and festival websites every day. Your donation only covers those costs.</p>'),
    ('<p class="don-int">Virement Interac, sans frais, à <b id="donCourriel"></b> <button type="button" class="btn ghost petit" id="donCopier">Copier l\'adresse</button></p>',
     '<p class="don-int">Interac e-Transfer, no fees, to <b id="donCourriel"></b> <button type="button" class="btn ghost petit" id="donCopier">Copy address</button></p>'),
]

PAGES = {
    "index.html": [
        ('<title>Calendrier culturel montréalais</title>', "<title>Montreal's cultural calendar</title>"),
        ('<meta name="description" content="Théâtre, musique, danse, expositions et plus : tous les événements culturels de l\'île de Montréal, par discipline, par date et par quartier.">',
         '<meta name="description" content="Theatre, music, dance, exhibitions and more: every cultural event on the island of Montréal, by discipline, date and neighbourhood.">'),
        ('<link rel="canonical" href="https://ccmtl.ca/">', '<link rel="canonical" href="https://ccmtl.ca/en/">'),
        ('<meta property="og:title" content="Calendrier culturel montréalais">', '<meta property="og:title" content="Montreal\'s cultural calendar">'),
        ('<meta property="og:description" content="Théâtre, musique, danse, expositions et plus : tous les événements culturels de l\'île de Montréal, par discipline, par date et par quartier.">',
         '<meta property="og:description" content="Theatre, music, dance, exhibitions and more: every cultural event on the island of Montréal, by discipline, date and neighbourhood.">'),
        ('<meta property="og:url" content="https://ccmtl.ca/">', '<meta property="og:url" content="https://ccmtl.ca/en/">'),
        ('<noscript><p><a href="jour/">Tous les événements, jour par jour</a></p></noscript>', '<noscript><p><a href="day/">All events, day by day</a></p></noscript>'),
        ("<h1 class=\"v1o\">Qu'est-ce qu'on fait <span class=\"hl\">ce soir</span>&nbsp;?</h1>", '<h1 class="v1o">What\'s on <span class="hl">tonight</span>?</h1>'),
        ("<span>Qu'est-ce</span><span>qu'on fait</span><span><i>ce soir</i>&nbsp;?</span>", "<span>What's</span><span>on</span><span><i>tonight</i>?</span>"),
        ('<p class="sub">Théâtre, shows, danse, expos, DJ sets et lectures de poésie, partout sur l\'île. Filtre par discipline et par date, ou cherche un spectacle.</p>',
         '<p class="sub">Theatre, gigs, dance, exhibitions, DJ sets and poetry readings, all over the island. Filter by discipline and date, or search for a show.</p>'),
        ('<label for="q" class="sr">Chercher un spectacle</label>', '<label for="q" class="sr">Search for a show</label>'),
        ('placeholder="Spectacle, artiste, salle, festival…"', 'placeholder="Show, artist, venue, festival…"'),
        ('aria-label="Effacer la recherche"', 'aria-label="Clear search"'),
        ('<p class="label" id="lbl-disc">Ce qui te tente', '<p class="label" id="lbl-disc">What are you into'),
        ('aria-label="Sélection rapide"', 'aria-label="Quick select"'),
        ('title="Cocher toutes les catégories"><i class="poincon"></i>tout</button>', 'title="Select all categories"><i class="poincon"></i>all</button>'),
        ('title="Décocher toutes les catégories"><i class="poincon"></i>aucun</button>', 'title="Clear all categories"><i class="poincon"></i>none</button>'),
        ('aria-label="Proximité"', 'aria-label="Nearby"'),
        ('<label for="pt">Près de</label>', '<label for="pt">Near</label>'),
        ('<label for="rayon" class="sr">Rayon</label>', '<label for="rayon" class="sr">Radius</label>'),
        ('<option value="0">toute l\'île</option>', '<option value="0">whole island</option>'),
        ('placeholder="ex. 5000 rue Saint-Denis"', 'placeholder="e.g. 5000 rue Saint-Denis"'),
        ('id="addrGo">Trouver</button>', 'id="addrGo">Find</button>'),
        ('aria-label="Affichage"', 'aria-label="View"'),
        ('id="v-week" aria-pressed="true">Semaine</button>', 'id="v-week" aria-pressed="true">Week</button>'),
        ('id="v-day" aria-pressed="false">Jour</button>', 'id="v-day" aria-pressed="false">Day</button>'),
        ('id="v-musee" aria-pressed="false" hidden>Expositions</button>', 'id="v-musee" aria-pressed="false" hidden>Exhibitions</button>'),
        ('aria-label="Tri"', 'aria-label="Sort"'),
        ('id="s-time" aria-pressed="true">Par heure</button>', 'id="s-time" aria-pressed="true">By time</button>'),
        ('id="s-dist" aria-pressed="false">Par distance</button>', 'id="s-dist" aria-pressed="false">By distance</button>'),
        ('id="allOn">Tout afficher</button>', 'id="allOn">Show all</button>'),
        ('aria-label="Période précédente"', 'aria-label="Previous period"'),
        ('aria-label="Période suivante"', 'aria-label="Next period"'),
        ('aria-label="Jours de la semaine"', 'aria-label="Days of the week"'),
        ('<div class="loading">Chargement des événements…</div>', '<div class="loading">Loading events…</div>'),
        ('<summary>Expositions et art public <span id="xcount"></span></summary>', '<summary>Exhibitions and public art <span id="xcount"></span></summary>'),
        ("<p>Tu fais de la programmation d'événements ?</p>", '<p>Do you program events?</p>'),
        ('hidden target="_blank" rel="noopener">+ Proposer un événement</a><a href="salles.html">Partager un calendrier</a>',
         'hidden target="_blank" rel="noopener">+ Submit an event</a><a href="salles.html">Share a calendar</a>'),
    ],
}

PAGES["salles.html"] = [
    ('<title>Ajouter tes événements · Calendrier culturel montréalais</title>', "<title>Add your events · Montreal's cultural calendar</title>"),
    ('content="Salles, galeries, compagnies et festivals : comment faire paraître tes événements dans le Calendrier culturel montréalais, gratuitement."',
     'content="Venues, galleries, companies and festivals: how to get your events listed in Montreal\'s cultural calendar, for free."'),
    ('content="Ajouter tes événements · Calendrier culturel montréalais"', 'content="Add your events · Montreal\'s cultural calendar"'),
    ('https://ccmtl.ca/salles.html">', 'https://ccmtl.ca/en/salles.html">'),
    ('<a href="en/salles.html" hreflang="en" lang="en">English</a>', '<a href="../salles.html" hreflang="fr" lang="fr">Français</a>'),
    ('<h1>Ajoute tes <span class="hl">shows</span>.</h1>', '<h1>Add your <span class="hl">shows</span>.</h1>'),
    ("<p class=\"sub\">Salles, bars, galeries, compagnies, collectifs, festivals : si ça se passe sur l'île, ça a sa place ici. C'est gratuit, et chaque événement renvoie vers ta page ou ta billetterie.</p>",
     '<p class="sub">Venues, bars, galleries, companies, collectives, festivals: if it happens on the island, it belongs here. It\'s free, and every event links to your page or box office.</p>'),
    ('<span class="tag">Le plus simple · recommandé</span>', '<span class="tag">Easiest · recommended</span>'),
    ('<h3>1. Donne-nous le lien de ton calendrier</h3>', '<h3>1. Give us your calendar link</h3>'),
    ("<p>Si tes événements sont déjà dans un agenda en ligne, donne-nous son adresse une seule fois. Il sera relu automatiquement chaque jour : ajouts, changements et annulations apparaissent ici sans rien faire de plus.</p>",
     "<p>If your events are already in an online calendar, give us its address once. It will be read automatically every day: additions, changes and cancellations show up here with nothing more to do.</p>"),
    ("<li><b>Google Agenda</b> : Paramètres → ton agenda → coche « Rendre disponible publiquement », puis copie l'« Adresse publique au format iCal ».</li>",
     '<li><b>Google Calendar</b>: Settings → your calendar → check “Make available to public”, then copy the “Public address in iCal format”.</li>'),
    ("<li><b>Autres outils</b> (sites WordPress, Squarespace, Wix, billetteries…) : cherche un lien « iCal », « .ics », « S'abonner » ou « Exporter le calendrier ».</li>",
     '<li><b>Other tools</b> (WordPress, Squarespace, Wix sites, ticketing platforms…): look for an “iCal”, “.ics”, “Subscribe” or “Export calendar” link.</li>'),
    ("<li><b>Pas de lien de ce genre ?</b> Donne simplement l'adresse de ta page « Programmation » : on la lira automatiquement.</li>",
     '<li><b>No such link?</b> Just give us the address of your “Programming” or “Events” page: we\'ll read it automatically.</li>'),
    ('hidden>Ajouter mon calendrier</a>', 'hidden>Add my calendar</a>'),
    ('<span class="tag">Pour un événement ponctuel</span>', '<span class="tag">For a one-off event</span>'),
    ('<h3>2. Propose un événement</h3>', '<h3>2. Submit an event</h3>'),
    ("<p>Un vernissage, un show, une soirée : remplis le formulaire en deux minutes. Ça paraît après une vérification rapide.</p>",
     '<p>An opening, a show, a party: fill in the form in two minutes. It goes up after a quick check.</p>'),
    ('hidden>Proposer un événement</a>', 'hidden>Submit an event</a>'),
    ('<span class="tag">Autrement</span>', '<span class="tag">Otherwise</span>'),
    ('<h3>3. Écris-nous</h3>', '<h3>3. Write to us</h3>'),
    ('<p>Une question, une correction ou un retrait : <b id="courriel"></b></p>', '<p>A question, a correction or a removal: <b id="courriel"></b></p>'),
    ("<h2>Ce qu'on publie</h2>", '<h2>What we publish</h2>'),
    ("<p>Le titre, la date, l'heure, la salle et un lien vers ta page. Le calendrier ne vend pas de billets et ne copie ni tes textes ni tes images. Le premier ajout d'une salle est vérifié par une personne avant d'être publié.</p>",
     '<p>The title, date, time, venue and a link to your page. The calendar doesn\'t sell tickets and doesn\'t copy your texts or images. A venue\'s first addition is checked by a person before it is published.</p>'),
    ('<h2>Une erreur, ou tu veux être retiré ?</h2>', '<h2>A mistake, or want to be removed?</h2>'),
    ("<p>Écris-nous et on corrige vite. Les événements viennent aussi d'agendas publics (Ville de Montréal, agendas culturels) : si une information est fausse, la source d'origine est indiquée sur chaque événement.</p>",
     '<p>Write to us and we\'ll fix it quickly. Events also come from public listings (City of Montréal, cultural calendars): if something is wrong, the original source is shown on each event.</p>'),
    ('<h2>Tes renseignements</h2>', '<h2>Your information</h2>'),
    ("<p>L'adresse courriel demandée dans les formulaires sert seulement à te joindre au sujet de tes événements. Elle n'est jamais publiée ni partagée.</p>",
     '<p>The email address asked for in the forms is only used to reach you about your events. It is never published or shared.</p>'),
    ('fetch("config.json"', 'fetch("../config.json"'),
    ('set("btnCal",c.formulaireCalendrier);set("btnEv",c.formulaireEvenement);',
     'set("btnCal",c.formulaireCalendrierEn||c.formulaireCalendrier);set("btnEv",c.formulaireEvenementEn||c.formulaireEvenement);'),
]

PAGES["sources.html"] = [
    ('<title>Nos sources et salles · Calendrier culturel montréalais</title>', "<title>Our sources & venues · Montreal's cultural calendar</title>"),
    ('content="Toutes les salles, musées, galeries et agendas que le Calendrier culturel montréalais consulte chaque jour."',
     'content="Every venue, museum, gallery and listing that Montreal\'s cultural calendar checks every day."'),
    ('content="Nos sources et salles · Calendrier culturel montréalais"', 'content="Our sources & venues · Montreal\'s cultural calendar"'),
    ('https://ccmtl.ca/sources.html">', 'https://ccmtl.ca/en/sources.html">'),
    ('<a href="salles.html">Ajouter tes événements</a><a href="en/sources.html" hreflang="en" lang="en">English</a>',
     '<a href="salles.html">Add your events</a><a href="../sources.html" hreflang="fr" lang="fr">Français</a>'),
    ('<h1>Nos <span class="hl">sources</span> et nos salles</h1>', '<h1>Our <span class="hl">sources</span> and venues</h1>'),
    ("<p class=\"sub\">Tout ce que le calendrier consulte : les agendas et sites relus automatiquement, puis chaque salle, musée et galerie où il y a quelque chose à l'affiche. Ce ne sont pas des partenariats officiels : ces informations sont publiques, et chaque événement renvoie à sa source. Une salle manque ? <a href=\"salles.html\">Ajoute-la</a>.</p>",
     '<p class="sub">Everything the calendar checks: the listings and websites read automatically, then every venue, museum and gallery with something on. These are not official partnerships: the information is public, and every event links to its source. A venue is missing? <a href="salles.html">Add it</a>.</p>'),
    ('<h2 class="label">Agendas et sites consultés</h2>', '<h2 class="label">Listings and websites checked</h2>'),
    ('<p class="loading">Chargement…</p>', '<p class="loading">Loading…</p>'),
    ('<h2 class="label">Salles, musées et galeries</h2>', '<h2 class="label">Venues, museums and galleries</h2>'),
    ('<label for="q" class="sr">Chercher une salle</label>', '<label for="q" class="sr">Search for a venue</label>'),
    ('placeholder="Chercher une salle, un quartier, une station…"', 'placeholder="Search for a venue, a neighbourhood, a station…"'),
    ('fetch("sources.json"', 'fetch("../sources.json"'),
    ('fetch("data.json"', 'fetch("../data.json"'),
    ('`${L.length} sources relues chaque jour ou chaque semaine.`', '`${L.length} sources read every day or every week.`'),
    ('<span>· ${esc(s.type)}</span>', '<span>· ${esc(({"page lue par l\'IA":"page read by AI","recurrents":"weekly events","données ouvertes":"open data","agenda Gancio":"Gancio calendar"})[s.type]||s.type)}</span>'),
    ("'<p class=\"empty\">Liste indisponible.</p>'", "'<p class=\"empty\">List unavailable.</p>'"),
    ('||"Quartier à préciser"}', '||"Neighbourhood unknown"}'),
    ('`${vis.length} lieu${vis.length>1?"x":""} sur ${lieux.length}`', '`${vis.length} venue${vis.length>1?"s":""} of ${lieux.length}`'),
    ('a.localeCompare(b,"fr")', 'a.localeCompare(b,"en")'),
    ('a.nom.localeCompare(b.nom,"fr")', 'a.nom.localeCompare(b.nom,"en")'),
    ('<span>activité${l.n>1?"s":""} au calendrier</span>', '<span>listing${l.n>1?"s":""} in the calendar</span>'),
    ("'<p class=\"empty\">Aucune salle ne correspond.</p>'", "'<p class=\"empty\">No venue matches.</p>'"),
    ('.qhead{font-family:var(--f-display);font-weight:800;font-size:15px;margin:18px 0 8px;text-transform:lowercase}',
     '.qhead{font-family:var(--f-display);font-weight:800;font-size:15px;margin:18px 0 8px}'),
]

PAGES["archives.html"] = [
    ('<title>Archives · Calendrier culturel montréalais</title>', "<title>Archive · Montreal's cultural calendar</title>"),
    ('content="Les spectacles, concerts et activités culturelles déjà présentés sur l\'île de Montréal, mois par mois."',
     'content="Shows, concerts and cultural activities already presented on the island of Montréal, month by month."'),
    ('content="Archives · Calendrier culturel montréalais"', 'content="Archive · Montreal\'s cultural calendar"'),
    ('https://ccmtl.ca/archives.html">', 'https://ccmtl.ca/en/archives.html">'),
    ('<a href="en/archives.html" hreflang="en" lang="en">English</a>', '<a href="../archives.html" hreflang="fr" lang="fr">Français</a>'),
    ('<h1>Archives</h1>', '<h1>Archive</h1>'),
    ("<p class=\"lead\">Ce qui s'est présenté sur l'île depuis le lancement du calendrier, par jour, semaine ou mois. En mode Mois, clique une journée pour la voir.</p>",
     '<p class="lead">What was on across the island since the calendar launched, by day, week or month. In Month view, click a day to see it.</p>'),
    ('aria-label="Affichage"><button type="button" data-mode="jour">Jour</button><button type="button" data-mode="semaine">Semaine</button><button type="button" data-mode="mois">Mois</button>',
     'aria-label="View"><button type="button" data-mode="jour">Day</button><button type="button" data-mode="semaine">Week</button><button type="button" data-mode="mois">Month</button>'),
    ('aria-label="Précédent"', 'aria-label="Previous"'),
    ('aria-label="Suivant"', 'aria-label="Next"'),
    ('placeholder="Titre, artiste, salle…"', 'placeholder="Title, artist, venue…"'),
    ('<option value="">Toutes les disciplines</option>', '<option value="">All disciplines</option>'),
    ('<main id="liste"><div class="empty">Chargement…</div></main>', '<main id="liste"><div class="empty">Loading…</div></main>'),
    ('const DISC={theatre:"Théâtre",musique:"Musique",danse:"Danse",cirque:"Cirque",humour:"Humour et cabaret",cinema:"Cinéma",\n'
     '  poesie:"Poésie, slam et rap battle",lettres:"Littérature",conference:"Conférences",jeune:"Jeune public",atelier:"Ateliers",\n'
     '  fete:"Fêtes et célébrations",quiz:"Quiz",expo:"Vernissages",autre:"Autre"};',
     'const DISC={theatre:"Theatre",musique:"Music",danse:"Dance",cirque:"Circus",humour:"Comedy & cabaret",cinema:"Film",\n'
     '  poesie:"Poetry, slam & rap battles",lettres:"Literature",conference:"Talks",jeune:"Kids & family",atelier:"Workshops",\n'
     '  fete:"Parties & celebrations",quiz:"Quiz nights",expo:"Openings",autre:"Other"};'),
    ('const MOIS=["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"];',
     'const MOIS=["January","February","March","April","May","June","July","August","September","October","November","December"];'),
    ('toLocaleDateString("fr-CA",{weekday:"long",day:"numeric",month:"long"})', 'toLocaleDateString("en-CA",{weekday:"long",day:"numeric",month:"long"})'),
    ('toLocaleDateString("fr-CA",{day:"numeric",month:"short"})', 'toLocaleDateString("en-CA",{day:"numeric",month:"short"})'),
    ('fetch(`archives/${mois}.json`', 'fetch(`../archives/${mois}.json`'),
    ('.then(d=>{CACHE[mois]=d})', '.then(d=>{(d.events||[]).forEach(e=>{if(e.lieu==="Lieu à confirmer")e.lieu="Venue TBA"});CACHE[mois]=d})'),
    ('fetch("archives/index.json"', 'fetch("../archives/index.json"'),
    ('${e.heure?e.heure.replace(":"," h "):"—"}',
     '${e.heure?(([a,b])=>(a%12||12)+(b?":"+String(b).padStart(2,"0"):"")+(a>=12?" p.m.":" a.m."))(e.heure.split(":").map(Number)):"—"}'),
    ('$("compte").textContent=`${L.length} activité${L.length>1?"s":""}`;', '$("compte").textContent=`${L.length} listing${L.length>1?"s":""}`;'),
    ("'<div class=\"empty\">Rien d\\'archivé pour ce jour.</div>'", "'<div class=\"empty\">Nothing archived for this day.</div>'"),
    ('$("compte").textContent=`${n} activité${n>1?"s":""}`;', '$("compte").textContent=`${n} listing${n>1?"s":""}`;'),
    ('`<span class="n">${L.length} activité${L.length>1?"s":""}</span>', '`<span class="n">${L.length} listing${L.length>1?"s":""}</span>'),
    ('["lun.","mar.","mer.","jeu.","ven.","sam.","dim."]', '["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]'),
    ('`${n} activité${n>1?"s":""} ce mois-ci · clique une journée`', '`${n} listing${n>1?"s":""} this month · click a day`'),
    ("'<div class=\"empty\">Chargement…</div>';Promise", "'<div class=\"empty\">Loading…</div>';Promise"),
    ("'<div class=\"empty\">Pas encore d\\'archives.</div>'", "'<div class=\"empty\">No archive yet.</div>'"),
]

# Noms des sources : les précisions entre parenthèses ou après « – » sont traduites ; le nom propre reste.
PAGES["sources.html"].append((
    'const $=id=>document.getElementById(id);',
    '''const $=id=>document.getElementById(id);
const MOTS=[["événements publics","public events"],[/(\\d+) prochains jours/,"next $1 days"],[/(\\d+) mois/,"$1 months"],[/(\\d+) pages/,"$1 pages"],["2e page","page 2"],
  ["impro et humour","improv and comedy"],["humour, scènes ouvertes","comedy, open mics"],["université populaire","people's university"],["conférences grand public","public lectures"],
  ["recherche-création","research-creation"],["LIM et spectacles","LIM and shows"],["festival jeune public","children's festival"],["sorties en famille","family outings"],
  ["expositions des musées","museum exhibitions"],["expositions automne-hiver","fall–winter exhibitions"],["centres d'artistes, vernissages","artist-run centres, openings"],
  ["expositions à venir","upcoming exhibitions"],["musique live","live music"],["musiques du monde","world music"],["arts vivants","live arts"],["art public","public art"],
  ["centre d'art multidisciplinaire","multidisciplinary art centre"],["lancements, lectures","launches, readings"],["slam de poésie","poetry slam"],["ouest de l'île","West Island"],
  ["Stewart Hall et activités","Stewart Hall and activities"],["programmation culturelle","cultural programming"],["agenda musique","music listings"],["communauté","community"],
  ["billetterie","box office"],["hebdomadaires","weekly"],["événements","events"],["calendrier","calendar"],["activités","activities"],["conférences","talks"],
  ["spectacles","shows"],["saison","season"],["humour","comedy"],["et ","and "]];
const trNom=n=>n.replace(/(\\(([^)]*)\\)| – (.*)$)/g,m=>{let t=m;for(const[a,b]of MOTS)t=t.replace(a,b);return t});'''))
PAGES["sources.html"].append(('>${esc(s.nom)}</a>', '>${esc(trNom(s.nom))}</a>'))


ABSENTS = []


def traduire(nom, html):
    for fr, en in COMMUNS + PAGES.get(nom, []):
        if fr not in html and (fr, en) not in COMMUNS:
            ABSENTS.append(f"{nom} : {fr[:70]}")
        html = html.replace(fr, en)
    html = re.sub(r"<title>([^<]*)</title>", lambda m: m.group(0), html)
    # stations de la carte : « métro X » → « metro X »
    html = re.sub(r"(<title>[^<]*) · métro ", r"\1 · metro ", html)
    return html


def main():
    (DOCS / "en").mkdir(exist_ok=True)
    restes = []
    for nom in PAGES:
        src = DOCS / nom
        if not src.exists():
            continue
        en = re.sub(r'<link rel="alternate" hreflang="[a-z]+" href="[^"]*">\n?', "", src.read_text(encoding="utf-8"))
        en = traduire(nom, en)
        # Sélecteur de langue : la page française pointe vers l'anglaise et inversement (+ hreflang pour Google)
        en = en.replace("</head>", '<link rel="alternate" hreflang="fr" href="https://ccmtl.ca/' + ("" if nom == "index.html" else nom) + '">\n'
                        '<link rel="alternate" hreflang="en" href="https://ccmtl.ca/en/' + ("" if nom == "index.html" else nom) + '">\n</head>', 1)
        (DOCS / "en" / nom).write_text(en, encoding="utf-8")
        # phrases françaises restées (texte visible entre balises, avec accent ou mot français courant)
        visible = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>|<[^>]+>", "\n", en, flags=re.S)
        for ligne in visible.splitlines():
            t = ligne.strip()
            if len(t) > 3 and re.search(r"(?i)\b(le|la|les|des|du|une|pour|avec|sans|tous|toute|ton|ta|tes)\b", t):
                restes.append(f"{nom} : {t[:80]}")
    for r in ABSENTS:
        print("  texte français introuvable (traduction à revoir) :", r)
    for r in restes:
        print("  à traduire :", r)
    print(f"Pages anglaises : {len(PAGES)} ; phrases françaises restantes : {len(restes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
