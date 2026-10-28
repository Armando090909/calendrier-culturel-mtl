"""Nettoyage commun : classement par discipline, tri des activités non culturelles,
filtre « île de Montréal », noms de salles et doublons."""
from __future__ import annotations

import difflib
import re
from urllib.parse import urlparse
import unicodedata

DISCIPLINES = ["theatre", "musique", "danse", "cirque", "humour", "cinema", "lettres", "jeune", "expo", "autre"]


# Lettres que la décomposition Unicode ne ramène pas à l'ASCII (Eivør → eivor, Œuvre → oeuvre…)
_TRANSLIT = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE", "ß": "ss", "ł": "l", "Ł": "L",
                           "đ": "d", "Đ": "D", "þ": "th", "ð": "d", "ı": "i", "’": "'", "‘": "'"})


def plat(s: str) -> str:
    """Minuscules sans accents ni ponctuation, pour comparer des textes."""
    s = (s or "").translate(_TRANSLIT)
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _has(text: str, mots: list[str]) -> bool:
    t = f" {plat(text)} "
    return any(f" {m} " in t for m in mots)


# Mots qui signalent une activité à écarter (cours, services, vie municipale…)
NON_CULTUREL = [
    "yoga", "pilates", "zumba", "tai chi", "callisthenie", "cardio", "gym", "gym douce", "aide aux devoirs",
    "entraide aux devoirs", "informatique", "ipad", "iphone", "ping", "techno express", "soutien technique",
    "depannage", "conversation", "francisation", "parlons francais", "cours de", "atelier de francais",
    "seance du", "conseil d arrondissement", "comite", "consultation", "audition des opinions", "seance d information",
    "marche fermier", "collecte de sang", "tricot", "couture", "jeux video", "jeu video", "jeux de societe",
    "ludotheque", "lego", "bingo", "scrabble", "echecs", "cerveaux actifs", "aines", "bebe conte", "bebes contes",
    "heure du conte", "contes pour les poupons", "matinee des tout petits", "eveil musical", "sac ados",
    "club de lecture", "club de code", "impression 3d", "robotique", "hydroponie", "cuisine", "investissement",
    "inauguration", "desensibilisation", "linkedin", "photoshop", "illustrator", "word", "logiciel",
    # événements d'affaires / corporatifs (pas de la culture)
    "c2 montreal", "mtl connecte", "reseautage", "networking", "salon de l emploi", "foire de l emploi",
    "conference d affaires", "sommet d affaires", "webinaire", "formation professionnelle", "gala corporatif",
]

REGLES = [
    ("expo", ["vernissage", "finissage", "visite commentee", "visite guidee de l exposition"]),
    ("cirque", ["cirque", "acrobat", "trapeze", "jonglerie", "circassien"]),
    ("humour", ["humour", "humoriste", "stand up", "standup", "comedy", "comedie club", "impro", "improvisation"]),
    ("danse", ["danse", "dance", "ballet", "choregraph", "flamenco", "tangente"]),
    ("theatre", ["theatre", "piece", "marionnette", "comedie musicale", "lecture publique", "mise en scene",
                 "conte pour", "spectacle jeunesse", "opera"]),
    ("cinema", ["cine", "cinema", "film", "projection", "documentaire", "bibliocinema", "court metrage"]),
    ("lettres", ["conference", "lecture", "poesie", "poete", "slam", "auteur", "autrice", "litterature",
                 "cafe philo", "philosophique", "rencontre d auteur", "lancement de livre", "causerie"]),
    ("musique", ["concert", "musique", "jazz", "orchestre", "quatuor", "chorale", "chanson", "rap", "hip hop",
                 "dj", "techno", "rave", "punk", "metal", "rock", "folk", "piano", "symphon", "recital", "album",
                 "spectacle musical", "show", "electro", "house", "r b", "art sonore", "sonore", "sound art", "performance sonore",
                 "musique actuelle", "improvisation libre"]),
]

# Catégories données par les sources (Sors-tu?, la Ville, etc.)
CATEGORIES = {
    "theatre": "theatre", "famille": "theatre", "comedie musicale": "theatre", "marionnettes": "theatre",
    "danse": "danse", "ballet": "danse", "humour": "humour", "cirque": "cirque", "cinema": "cinema",
    "conference": "lettres", "litterature": "lettres", "entrevues": "lettres", "poesie": "lettres",
    "exposition": "expo", "arts visuels": "expo",
    "societe et histoire": "lettres", "art de la parole": "lettres",
}


# Lieux pluridisciplinaires : un spectacle qu'on ne sait pas classer y est souvent théâtre ET danse (performance).
LIEUX_PLURI = ["la chapelle", "usine c", "espace libre", "agora de la danse", "theatre aux ecuries", "monument national",
               "edifice wilder", "studio 303", "centre phi", "fonderie darling"]


def disciplines_aussi(titre: str, description: str, disc: str, lieu: str = "") -> tuple[str, list[str]]:
    """Discipline principale + disciplines secondaires (« aussi »). Un événement peut être dans deux catégories."""
    aussi = []
    texte = f"{titre} {description[:800]}"
    for d, mots in REGLES:
        # titre seulement : une description mentionne souvent le nom de la salle (« au Théâtre Fairmount »)
        if d in ("theatre", "danse", "cirque") and d != disc and disc != "musique" and _has(titre, mots):
            aussi.append(d)
    if _has(texte, ["performance", "pluridisciplinaire", "interdisciplinaire", "theatre physique", "danse theatre"]):
        if disc == "autre":
            disc = "theatre"
        aussi += [d for d in ("theatre", "danse") if d != disc]
    if disc == "autre" and any(l in plat(lieu) for l in LIEUX_PLURI):
        disc, aussi = "theatre", aussi + ["danse"]
    aussi = [d for d in dict.fromkeys(aussi) if d != disc and d in DISCIPLINES]
    return disc, aussi[:2]


# Catégories de la Ville qui ne sont pas des sorties culturelles (services, ateliers pratiques, vie municipale)
CATEGORIES_EXCLUES = ["sport", "loisir sportif", "vie democratique", "consultation", "soutien et echange", "bien etre",
                      "jeux", "science et techno", "informatique", "cuisine", "rencontre avec personne elue",
                      "conseil et comite", "langues", "jardinage", "assemblee publique"]


def est_non_culturel(titre: str, categorie: str = "") -> bool:
    return _has(titre, NON_CULTUREL) or _has(categorie, CATEGORIES_EXCLUES)


def classer(titre: str, categorie: str = "", description: str = "", defaut: str = "") -> str:
    """Discipline d'après la catégorie de la source, puis les mots du titre, puis la description."""
    c = plat(categorie)
    for k, v in CATEGORIES.items():
        if k in c and v != "expo":
            return v
    if c and any(m in c for m in ["pop", "rock", "metal", "jazz", "indie", "punk", "folk", "musique", "rap",
                                   "hip hop", "electro", "house", "reggae", "gospel", "progressif", "francophone",
                                   "alternatif", "lo fi", "noise", "monde"]):
        return "musique"
    for disc, mots in REGLES:
        if _has(titre, mots):
            return disc
    for disc, mots in REGLES:
        if description and _has(description[:1500], mots):
            return disc
    return defaut if defaut in DISCIPLINES else "autre"


# Municipalités de l'île de Montréal (agglomération) ; tout le reste est écarté.
VILLES_ILE = [
    "montreal", "westmount", "mont royal", "cote saint luc", "hampstead", "montreal ouest", "dorval",
    "pointe claire", "kirkland", "beaconsfield", "baie d urfe", "sainte anne de bellevue", "senneville",
    "dollard des ormeaux", "montreal est", "l ile dorval", "lasalle", "lachine", "verdun", "anjou",
    "saint laurent", "saint leonard", "montreal nord", "pierrefonds", "pointe aux trembles", "outremont",
]
HORS_ILE = [
    "laval", "longueuil", "brossard", "boucherville", "saint lambert", "repentigny", "terrebonne",
    "sainte therese", "saint eustache", "chambly", "valleyfield", "salaberry", "saint jerome", "blainville",
    "bois des filion", "mascouche", "chateauguay", "vaudreuil", "la prairie", "candiac", "quebec", "ottawa",
    "gatineau", "sherbrooke", "trois rivieres", "dix30", "place bell", "studio azrieli",
]


def hors_ile(*textes: str) -> bool:
    t = " ".join(plat(x) for x in textes if x)
    return any(f" {m} " in f" {t} " for m in HORS_ILE)


def dans_ile(lat: float | None, lon: float | None) -> bool:
    """Boîte grossière autour de l'île (exclut Laval au nord de la rivière des Prairies, approximativement)."""
    if lat is None or lon is None:
        return True
    if not (45.40 <= lat <= 45.71 and -73.98 <= lon <= -73.47):
        return False
    return True


# ---------- Salles ----------
class Lieux:
    """Table des salles : nom canonique -> {lat, lon, quartier, alias[]}. Enregistrée dans lieux.json."""

    def __init__(self, data: dict):
        self.data = data
        self._index: dict[str, str] = {}
        for nom, info in data.items():
            self._indexer(nom, nom)
            for a in (info or {}).get("alias", []) if isinstance(info, dict) else []:
                self._indexer(a, nom)

    def _indexer(self, alias: str, nom: str) -> None:
        self._index[self._cle(alias)] = nom

    @staticmethod
    def _cle(nom: str) -> str:
        k = plat(nom)
        k = re.sub(r"\b(bar spectacle|bar|salle|the|le|la|les|l|de|du|des|montreal|mtl|theatre|qc)\b", " ", k)
        return re.sub(r"\s+", " ", k).strip() or plat(nom)

    def trouver(self, nom: str) -> str | None:
        if not nom:
            return None
        k = self._cle(nom)
        if k in self._index:
            return self._index[k]
        # Un nom connu contenu dans le nom lu (ex. « L'Escogriffe Bar Spectacle (L'Esco) ») : le plus précis gagne.
        dedans = sorted(((len(cle), canon) for cle, canon in self._index.items()
                         if len(cle) >= 5 and re.search(r"(^| )" + re.escape(cle) + r"( |$)", k)), reverse=True)
        if dedans:
            return dedans[0][1]
        # Nom lu plus court qu'un nom connu (ex. « Chapelle ») : seulement s'il ne désigne qu'une seule salle.
        if len(k) >= 5:
            cands = {canon for cle, canon in self._index.items() if re.search(r"(^| )" + re.escape(k) + r"( |$)", cle)}
            if len(cands) == 1:
                return cands.pop()
        return None

    def ajouter(self, nom: str, info: dict | None, alias: str | None = None) -> str:
        if nom not in self.data:
            self.data[nom] = info
            self._indexer(nom, nom)
        if alias and plat(alias) != plat(nom):
            if isinstance(self.data.get(nom), dict):
                self.data[nom].setdefault("alias", [])
                if alias not in self.data[nom]["alias"]:
                    self.data[nom]["alias"].append(alias)
            self._indexer(alias, nom)
        return nom

    def plus_proche(self, lat: float, lon: float, max_km: float) -> str | None:
        import math
        best, nom_best = max_km, None
        for nom, info in self.data.items():
            if isinstance(info, dict) and info.get("lat") is not None:
                dx = (info["lon"] - lon) * 111.32 * math.cos(math.radians(lat))
                dy = (info["lat"] - lat) * 110.57
                dk = math.hypot(dx, dy)
                if dk < best:
                    best, nom_best = dk, nom
        return nom_best

    def coord(self, nom: str) -> dict | None:
        info = self.data.get(nom)
        if isinstance(info, dict) and info.get("lat") is not None:
            return {"lat": info["lat"], "lon": info["lon"], "quartier": info.get("quartier", "")}
        return None


# ---------- Doublons ----------
PRIORITE = {"formulaire": 0, "calendrier": 1, "festival": 2, "theatre": 2, "ville": 3, "sorstu": 4, "askapunk": 5, "songkick": 6, "ia": 7}


GENERIQUES = {"soiree", "concert", "spectacle", "show", "festival", "les", "the", "une", "des", "atelier", "lancement",
              "exposition", "projection", "party", "nuit", "grand", "grande", "special", "halloween", "fest", "jour"}


MOTS_COURANTS = {"montreal", "lancement", "album", "spectacle", "concert", "soiree", "festival", "edition", "special",
                 "speciale", "invites", "presente", "tournee", "world", "music", "musique", "hommage", "tribute", "night",
                 "party", "anniversaire", "release", "show", "gratuit", "atelier", "theatre", "danse", "cinema", "conference"}


def _mots(titre: str) -> list[str]:
    t = re.sub(r"\b(avec|with|and|et|presente|presents|feat|ft|w)\b", " ", plat(titre))
    return [m for m in t.split() if len(m) > 2]


# Salles d'un même complexe : « Cinquième Salle » et « Place des Arts » désignent le même endroit pour comparer.
COMPLEXES = {
    "place des arts": ["cinquieme salle", "wilfrid pelletier", "theatre maisonneuve", "maison symphonique",
                       "claude leveillee", "studio theatre", "espace danse", "esplanade tranquille"],
    "monument national": ["ludger duvernay", "studio hydro quebec"],
    "gesu": ["amphitheatre du gesu"],
    "usine c": [], "la chapelle": ["chapelle scenes contemporaines"],
    "salle bourgie": ["musee des beaux arts", "bourgie"],
    "sat": ["societe des arts technologiques", "society for arts technology", "society for arts and technology"],
}
_MOTS_LIEU = {"et", "and", "st", "ste", "saint", "sainte", "the", "le", "la", "les", "l", "de", "du", "des", "d", "salle",
              "theatre", "eglise", "church", "montreal", "mtl", "bar", "club", "a", "au"}


def lieu_racine(nom: str) -> str:
    p = plat(nom)
    for racine, membres in COMPLEXES.items():
        if f" {racine} " in f" {p} " or any(m in p for m in membres):
            return racine
    return p


def lieux_proches(a: str, b: str) -> bool:
    """Même salle sous deux graphies (« Église St. Andrew & St. Paul » / « Église St-Andrew et St-Paul »)."""
    ra, rb = lieu_racine(a), lieu_racine(b)
    if ra == rb:
        return True
    ta, tb = set(ra.split()) - _MOTS_LIEU, set(rb.split()) - _MOTS_LIEU
    return bool(ta and tb) and (ta <= tb or tb <= ta)


def _titre_net(t: str) -> str:
    return plat(re.sub(r"\(.*?\)", " ", t)).strip()


def meme_evenement(a: dict, b: dict) -> bool:
    """Même date, même salle (ou salle inconnue d'un côté), et des titres qui désignent le même spectacle."""
    if a["date"] != b["date"]:
        return False
    inconnu = "lieu a confirmer" in (plat(a["lieu"]), plat(b["lieu"]))
    if not inconnu and not lieux_proches(a["lieu"], b["lieu"]):
        return False
    domaine = lambda e: urlparse(e.get("url") or "").netloc.replace("www.", "")  # noqa: E731
    autre_source = a.get("source") != b.get("source") or domaine(a) != domaine(b)
    ta, tb = _titre_net(a["titre"]), _titre_net(b["titre"])
    meme_fest = bool(a.get("festival")) and a.get("festival") == b.get("festival")
    ha = hb = None
    if a.get("heure") and b.get("heure"):
        ha, hb = (int(x[:2]) * 60 + int(x[3:]) for x in (a["heure"], b["heure"]))
        ecart = abs(ha - hb)
        # Deux heures différentes : deux représentations, sauf si deux sites décrivent le même spectacle
        # (ouverture des portes / début : 18 h 30 et 20 h), ou le même titre à moins de 75 min d'écart.
        if ecart and not ((autre_source and ecart <= 120) or (ta == tb and ecart <= 75)):
            return False
    meme_heure = a.get("heure") and a.get("heure") == b.get("heure")
    une_sans_heure = bool(a.get("heure")) != bool(b.get("heure"))  # exactement une des deux sans heure
    contient = min(len(ta), len(tb)) >= 5 and (ta in tb or tb in ta)
    proche = difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.85
    if inconnu:  # salle inconnue d'un côté : prudence (ex. deux ateliers de bibliothèques différentes)
        if plat(a["lieu"]) == plat(b["lieu"]) and not autre_source:  # deux salles inconnues, même site : même page seulement
            return ta == tb and a.get("heure") == b.get("heure") and bool(a.get("url")) and a.get("url") == b.get("url")
        return (ta == tb and (meme_heure or une_sans_heure or not (a.get("heure") or b.get("heure")))) or (meme_fest and (contient or proche) and (meme_heure or une_sans_heure))
    if ta == tb or contient or proche:
        return True
    # Même festival, même jour, même heure, même salle : le même spectacle sous deux titres
    if meme_fest and meme_heure:
        return True
    ma, mb = _mots(a["titre"]), _mots(b["titre"])
    if not ma or not mb:
        return False
    if ma[0] == mb[0] and ma[0] not in GENERIQUES and ma[0] not in MOTS_COURANTS:
        return True
    if " ".join(ma[:3]) == " ".join(mb[:3]):
        return True
    # Deux sites, deux titres (« Claudio Simonetti's Goblin : Tenebre » / « Goblin Tenebre »),
    # ou le même festival dont une version n'a pas d'heure : un mot rare en commun suffit.
    if autre_source or (meme_fest and une_sans_heure):
        rares = lambda m: {w for w in m if len(w) >= 5 and w not in GENERIQUES and w not in MOTS_COURANTS}  # noqa: E731
        return bool(rares(ma) & rares(mb))
    return False


def _meme_titre_strict(a: dict, b: dict) -> bool:
    """Pour rattacher un événement sans salle à un autre du même jour : même début de titre et heures compatibles."""
    if a.get("heure") and b.get("heure"):
        ha, hb = (int(x[:2]) * 60 + int(x[3:]) for x in (a["heure"], b["heure"]))
        if abs(ha - hb) > 120:
            return False
    if a.get("festival") and a.get("festival") == b.get("festival") and a.get("heure") and a.get("heure") == b.get("heure"):
        return True
    ma, mb = _mots(a["titre"]), _mots(b["titre"])
    if not ma or not mb:
        return False
    return (ma[0] == mb[0] and ma[0] not in GENERIQUES and ma[0] not in MOTS_COURANTS and len(ma[0]) >= 4) \
        or " ".join(ma[:3]) == " ".join(mb[:3])


def corriger_heure_festapp(jour: str, heure: str | None) -> str | None:
    """FestApp, lu depuis GitHub Actions, affiche les heures décalées de l'écart avec UTC (19 h → 14 h en novembre) :
    constaté le 27 oct. 2026 sur 212 séances de CINEMANIA et Coup de cœur comparées au site. On remet l'heure de Montréal."""
    if not heure or not re.fullmatch(r"\d{2}:\d{2}", heure):
        return heure
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    d = datetime.fromisoformat(f"{jour}T{heure}")
    ecart = -ZoneInfo("America/Montreal").utcoffset(d)
    return (d + ecart).strftime("%H:%M") if (d + ecart).date() == d.date() else heure


def dedoublonner(events: list[dict]) -> list[dict]:
    seaux: dict[tuple, list[dict]] = {}
    for e in events:
        garde = seaux.setdefault(e["date"], [])
        for i, old in enumerate(garde):
            if meme_evenement(e, old):
                mieux = (bool(e.get("heure")), -PRIORITE.get(e.get("source", ""), 9)) > \
                        (bool(old.get("heure")), -PRIORITE.get(old.get("source", ""), 9))
                if mieux:
                    garde[i], e = e, old
                # On garde ce que l'autre version savait de plus (festival, heure, prix, billets…)
                for k in ("festival", "heure", "prix", "billets", "resume", "image", "aussi"):
                    if not garde[i].get(k) and e.get(k):
                        garde[i][k] = e[k]
                break
        else:
            garde.append(e)
    tous = [e for g in seaux.values() for e in g]
    # Un événement sans salle connue, déjà présent le même jour avec sa salle : on le retire.
    par_jour: dict[str, list[dict]] = {}
    for e in tous:
        if plat(e["lieu"]) != "lieu a confirmer":
            par_jour.setdefault(e["date"], []).append(e)
    garde = []
    for e in tous:
        if plat(e["lieu"]) == "lieu a confirmer" and e.get("source") != "ville":
            autre = next((x for x in par_jour.get(e["date"], []) if _meme_titre_strict(e, x)), None)
            if autre:
                for k in ("prix", "billets", "resume", "image", "aussi"):
                    if not autre.get(k) and e.get(k):
                        autre[k] = e[k]
                continue
        garde.append(e)
    tous = garde
    return sorted(tous, key=lambda e: (e["date"], e.get("heure") or "99", e["titre"]))


# ---- Styles de musique (larges) -------------------------------------------------------------------------------
STYLES = {
    "rock": "Rock et indie", "pop": "Pop et chanson", "hiphop": "Hip-hop et R&B", "electro": "Électro",
    "jazz": "Jazz et blues", "classique": "Classique et opéra", "monde": "Musiques du monde",
    "folk": "Folk, trad et country", "metal": "Métal et punk", "experimental": "Expérimental",
}
# Mots (catégorie de la source, puis titre et résumé) → style. L'ordre compte : le plus précis d'abord.
REGLES_STYLE = [
    ("metal", ["metal", "metalcore", "deathcore", "black metal", "doom", "hardcore", "punk", "grindcore", "thrash", "screamo", "oi"]),
    ("hiphop", ["hip hop", "hiphop", "rap", "r b", "rnb", "soul", "trap", "drill", "funk"]),
    ("electro", ["electro", "electronique", "techno", "house", "dj", "dj set", "drum and bass", "dnb", "rave", "ambient", "edm", "dubstep", "trance", "disco"]),
    ("classique", ["classique", "opera", "orchestre", "symphonique", "symphonie", "quatuor", "quintette", "baroque", "cantate",
                   "concerto", "sonate", "recital", "choeur", "choral", "orgue", "musique de chambre", "philharmonique", "osm", "bach", "mozart", "beethoven"]),
    ("jazz", ["jazz", "blues", "swing", "bebop", "big band", "trio jazz", "manouche", "bossa"]),
    ("monde", ["musiques du monde", "musique du monde", "world", "afro", "afrobeat", "latin", "latino", "salsa", "cumbia", "flamenco", "reggae",
               "klezmer", "arabe", "orientale", "balkan", "tango", "kompa", "zouk", "bollywood", "celtique", "fado", "maloya", "mandingue"]),
    ("folk", ["folk", "trad", "traditionnel", "country", "bluegrass", "americana", "irlandais", "irish", "veillee", "violoneux", "western"]),
    ("experimental", ["experimental", "experimentale", "noise", "improvisation", "improvisee", "musique actuelle", "electroacoustique", "acousmatique", "drone", "avant garde"]),
    ("rock", ["rock", "indie", "alternatif", "alternative", "garage", "shoegaze", "grunge", "post rock", "psych", "psychedelique", "emo", "power pop", "lo fi"]),
    ("pop", ["pop", "chanson", "chansonnier", "auteur compositeur", "variete", "francophone", "hommage", "tribute", "cabaret", "karaoke", "comedie musicale"]),
]
STYLE_LIEU = {  # salles dont la programmation est presque toute d'un même style
    "upstairs": "jazz", "diese onze": "jazz", "entracte": "jazz", "bistro a jojo": "jazz", "maison du jazz": "jazz",
    "balattou": "monde", "hurley": "folk", "maison symphonique": "classique", "salle bourgie": "classique",
    "pollack": "classique", "salle claude champagne": "classique", "turbo haus": "metal", "foufounes": "metal",
    "piranha": "metal", "datcha": "electro", "stereo": "electro", "new city gas": "electro", "sat": "electro",
    "le belmont": "electro", "ausgang": "electro",
}
STYLE_FESTIVAL = {"bach": "classique", "coupdecoeur": "pop", "mpourmontreal": "rock", "akousma": "experimental",
                  "nuitsdafrique": "monde", "jazz": "jazz", "suoni": "experimental", "mutek": "electro",
                  "igloofest": "electro", "piknic": "electro", "francos": "pop", "wiblues": "jazz", "trad": "folk",
                  "fma": "classique", "chambre": "classique", "elektra": "experimental"}


def style_musique(titre: str, categorie: str = "", lieu: str = "", resume: str = "", festival: str | None = None) -> str | None:
    """Style large d'un concert, d'après des indices sûrs. None si rien ne permet de trancher."""
    for texte in (categorie, titre):
        for style, mots in REGLES_STYLE:
            if texte and _has(texte, mots):
                return style
    if festival and festival in STYLE_FESTIVAL:
        return STYLE_FESTIVAL[festival]
    l = plat(lieu)
    for k, v in STYLE_LIEU.items():
        if f" {k} " in f" {l} ":
            return v
    for style, mots in REGLES_STYLE:
        if resume and _has(resume, mots):
            return style
    return None
