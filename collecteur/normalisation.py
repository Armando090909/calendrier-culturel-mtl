"""Nettoyage commun : classement par discipline, tri des activités non culturelles,
filtre « île de Montréal », noms de salles et doublons."""
from __future__ import annotations

import difflib
import re
from collections import Counter
from urllib.parse import urlparse
import unicodedata

DISCIPLINES = ["theatre", "musique", "danse", "cirque", "humour", "cinema", "lettres", "poesie", "conference", "atelier", "fete", "quiz", "jeune", "expo", "autre"]


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
    ("quiz", ["quiz", "trivia", "jeu questionnaire", "pub quiz", "soiree quiz", "quizz"]),
    ("expo", ["vernissage", "finissage", "visite commentee", "visite guidee de l exposition"]),
    ("atelier", ["atelier", "ateliers", "initiation", "fabrication", "creation textile", "tricot", "couture", "broderie",
                 "perlage", "linogravure", "coloriage", "collage", "club d art", "club de laine", "machine a coudre",
                 "art therapie", "bricolage", "bricolo", "medialab", "creer avec", "creation d", "creation de", "fabrique", "zine", "zines"]),
    ("conference", ["conference", "colloque", "causerie", "table ronde", "panel", "seminaire", "cafe philo",
                    "philosophique", "talk", "entretien public", "mini conference", "midi conference", "debat",
                    "rencontre avec", "rencontre informelle", "recits", "temoignages", "discussion", "echange avec"]),
    ("cirque", ["cirque", "acrobat", "trapeze", "jonglerie", "circassien", "magie", "magicien", "magicienne", "illusionniste"]),
    ("humour", ["humour", "humoriste", "stand up", "standup", "comedy", "comedie club", "impro", "improvisation"]),
    ("humour", ["drag", "drag queen", "burlesque", "cabaret drag", "mado", "cabaret", "variete"]),
    ("danse", ["danse", "dance", "ballet", "choregraph", "flamenco", "tangente"]),
    ("theatre", ["theatre", "piece", "marionnette", "comedie musicale", "lecture publique", "mise en scene",
                 "conte pour", "spectacle jeunesse", "opera"]),
    ("cinema", ["cine", "cinema", "film", "projection", "documentaire", "bibliocinema", "court metrage"]),
    ("poesie", ["poesie", "poete", "poetes", "poetique", "slam", "slameur", "slameuse", "spoken word", "rap battle",
                "battle de rap", "battle rap", "joute verbale", "clash de rap", "rap contender", "ligue de rap", "scene ouverte poesie", "micro ouvert poesie"]),
    ("lettres", ["lecture", "auteur", "autrice", "litterature", "litteraire", "roman", "rencontre d auteur",
                 "lancement de livre", "lancement du livre", "lancement litteraire", "conte pour adultes",
                 "soiree de contes", "club de lecture", "salon du livre", "bd", "bande dessinee"]),
    ("musique", ["concert", "musique", "jazz", "orchestre", "quatuor", "chorale", "chanson", "rap", "hip hop",
                 "dj", "techno", "rave", "punk", "metal", "rock", "folk", "piano", "symphon", "recital", "album",
                 "spectacle musical", "show", "electro", "house", "r b", "art sonore", "sonore", "sound art", "performance sonore",
                 "musique actuelle", "improvisation libre", "oratorio", "cantate", "messe", "choeur", "choral", "band",
                 "cover", "trio", "quartet", "ensemble"]),
    ("fete", ["halloween", "noel", "fete", "fetes", "festivites", "celebration", "marche de noel", "marche des fetes",
              "carnaval", "parade", "defile", "commemorati", "jour du souvenir", "village d halloween", "maison hantee",
              "party de quartier", "bal de", "reveillon", "saint jean", "fete nationale", "fete du canada"]),
]

# Catégories données par les sources (Sors-tu?, la Ville, etc.)
CATEGORIES = {
    "theatre": "theatre", "famille": "theatre", "comedie musicale": "theatre", "marionnettes": "theatre",
    "danse": "danse", "ballet": "danse", "humour": "humour", "cirque": "cirque", "cinema": "cinema",
    "conference": "conference", "litterature": "lettres", "entrevues": "conference", "poesie": "poesie", "slam": "poesie",
    "exposition": "expo", "arts visuels": "expo",
    "societe et histoire": "conference", "art de la parole": "poesie", "art et artisanat": "atelier",
    "fete et marche": "fete", "club de lecture": "lettres",
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
    "niagara", "fallsview", "toronto", "gatineau", "sherbrooke", "trois rivieres", "kingston", "granby", "drummondville",
    "saint hyacinthe", "joliette", "rimouski", "saguenay", "mont tremblant", "magog", "st sauveur", "saint sauveur",
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
# Valeurs qui ne sont pas des noms de salle (colonne « emplacement » de la Ville, cases vides…)
PAS_DES_SALLES = {"en salle", "a l exterieur", "en ligne", "nan", "none", "plusieurs salles", "montreal", "divers lieux",
                  "lieu a confirmer", "a confirmer", "virtuel", "online"}


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
        if plat(nom) in PAS_DES_SALLES:
            return "Lieu à confirmer"
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
            if plat(nom) in PAS_DES_SALLES:
                continue
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


def _titres_lies(a: str, b: str) -> bool:
    """Deux titres qui parlent de la même chose : l'un contient l'autre, ils se ressemblent, ou ils partagent un mot rare."""
    ta, tb = _titre_net(a), _titre_net(b)
    if ta == tb or (min(len(ta), len(tb)) >= 5 and (ta in tb or tb in ta)):
        return True
    if difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.6:
        return True
    rares = lambda t: {w for w in _mots(t) if len(w) >= 5 and w not in GENERIQUES and w not in MOTS_COURANTS}  # noqa: E731
    return bool(rares(a) & rares(b))


def _fusion_meme_page(events: list[dict]) -> list[dict]:
    """Deux fiches du même jour qui pointent vers la même page précise (pas une page de programmation commune) :
    le même événement, décrit deux fois. On garde une fiche, complétée par l'autre."""
    par_url = Counter(e.get("url") for e in events if e.get("url"))
    groupes: dict[tuple, list[dict]] = {}
    for e in events:
        u = e.get("url") or ""
        precise = u.startswith("http") and urlparse(u).path.strip("/") != "" and par_url[u] <= 12
        groupes.setdefault((e["date"], u) if precise else (id(e),), []).append(e)
    out = []
    for g in groupes.values():
        if len(g) == 1 or len(g) > 3:
            out += g
            continue
        g.sort(key=lambda e: (plat(e["lieu"]) == "lieu a confirmer", not e.get("heure"), PRIORITE.get(e.get("source", ""), 9)))
        gardes: list[dict] = []
        for e in g:
            # Deux heures différentes sur la même page : deux représentations (matinée et soirée) ; on garde les deux.
            cible = next((x for x in gardes if (not x.get("heure") or not e.get("heure") or x["heure"] == e["heure"])
                          and _titres_lies(x["titre"], e["titre"])), None)
            if cible is None:
                gardes.append(e)
                continue
            for k in ("festival", "heure", "prix", "billets", "resume", "image", "aussi"):
                if not cible.get(k) and e.get(k):
                    cible[k] = e[k]
        out += gardes
    return out


def dedoublonner(events: list[dict]) -> list[dict]:
    events = _fusion_meme_page(events)
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


# ---- Dernier contrôle : pas de redite dans une même journée -------------------------------------------------
# Les spectacles vivants (musique, théâtre, danse, humour…) ne se jouent pas deux fois le même jour dans deux salles.
# Les films et les expositions, eux, peuvent légitimement apparaître plusieurs fois (plusieurs cinémas, plusieurs lieux).
REPRODUCTIBLES = {"cinema", "expo", "quiz"}  # un quiz « Soirée quiz » a lieu dans plusieurs bars le même soir


# Instruments, rôles et mots de programme : ce ne sont pas des noms d'artistes (« Dane Ko, piano »).
ROLES = {"piano", "pianiste", "violon", "violoncelle", "alto", "contrebasse", "orgue", "organiste", "clavecin", "guitare",
         "voix", "chant", "soprano", "mezzo", "tenor", "baryton", "basse", "batterie", "percussions", "flute", "hautbois",
         "clarinette", "saxophone", "trompette", "harpe", "mandoline", "marimba", "accordeon", "trio", "quatuor", "quintette",
         "ensemble", "orchestre", "choeur", "chorale", "direction", "dj set", "live", "band", "duo", "solo", "recital",
         "conference", "mini conference", "lecture", "atelier", "spectacle", "concert", "lancement", "premiere",
         "gratuit", "complet", "off bach", "montreal", "invites", "invitees", "et invites", "and friends", "friends"}


# Noms de festivals et de séries (« M pour Montréal : … ») : ce ne sont pas des artistes. Complété par la collecte.
SERIES_CONNUES: set[str] = {"m pour montreal", "off bach", "coup de coeur francophone", "cinemania"}


def _artistes(titre: str) -> set[str]:
    """Noms d'artistes ou de spectacles dans un titre (« Jonquille + Chloé Jara-Buto @ X » → {jonquille, chloe jara buto})."""
    t = re.sub(r"\(.*?\)", " ", titre)
    t = re.split(r"\s[–—|:@]\s|\s-\s|:\s|\s@\s|\s·\s", t)[0]
    noms = set()
    for m in re.split(r"\s\+\s|\s/\s|,|\savec\s|\swith\s|\sw/\s|\set\s(?=[A-ZÉ])|\s&\s|\sx\s", t):
        p = plat(m)
        if len(p) >= 4 and p not in GENERIQUES and p not in MOTS_COURANTS and p not in ROLES and p not in SERIES_CONNUES \
                and not p.startswith(("invit", "guest")):
            noms.add(p)
    return noms


def meme_spectacle(a: dict, b: dict) -> bool:
    """Même titre, titre qui contient l'autre, titres très proches, ou un même artiste."""
    ta, tb = _titre_net(a["titre"]), _titre_net(b["titre"])
    if not ta or not tb:
        return False
    if ta == tb or (min(len(ta), len(tb)) >= 6 and (ta in tb or tb in ta)):
        return True
    if difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.88:
        return True
    # Mêmes mots dans un autre ordre (« HYMNES de Stephanie Comilang » / « Stephanie Comilang : HYMNES »)
    mots = lambda t: {w for w in t.split() if len(w) >= 4 and w not in GENERIQUES and w not in MOTS_COURANTS and w not in ROLES}  # noqa: E731
    wa, wb = mots(ta), mots(tb)
    if len(wa) >= 2 and len(wb) >= 2 and (wa <= wb or wb <= wa) and max(len(wa), len(wb)) <= 2 * min(len(wa), len(wb)):
        return True
    return bool(_artistes(a["titre"]) & _artistes(b["titre"]))


def doublons_du_jour(events: list[dict]) -> tuple[list[dict], list[str]]:
    """Retire les redites d'une même journée que le dédoublonnage par salle n'a pas vues (salle différente d'une
    source à l'autre, ou inconnue). Renvoie (événements gardés, description des retraits pour le rapport)."""
    par_jour: dict[str, list[dict]] = {}
    for e in events:
        par_jour.setdefault(e["date"], []).append(e)
    retires, journal = set(), []
    inconnu = lambda e: plat(e["lieu"]) == "lieu a confirmer"  # noqa: E731
    for jour, L in par_jour.items():
        vivants = [e for e in L if e.get("discipline") not in REPRODUCTIBLES]
        for i, a in enumerate(vivants):
            if id(a) in retires:
                continue
            for b in vivants[i + 1:]:
                if id(b) in retires or not meme_spectacle(a, b):
                    continue
                meme_salle = not inconnu(a) and not inconnu(b) and lieux_proches(a["lieu"], b["lieu"])
                if meme_salle and a.get("heure") and b.get("heure") and a["heure"] != b["heure"]:
                    continue  # matinée et soirée dans la même salle : deux représentations
                if a.get("source") == "ville" and b.get("source") == "ville" and a.get("url") != b.get("url"):
                    continue  # deux fiches distinctes de la Ville (ex. le même atelier dans deux bibliothèques)
                # On garde la meilleure fiche : salle connue, heure connue, source la plus fiable
                rang = lambda e: (inconnu(e), not e.get("heure"), PRIORITE.get(e.get("source", ""), 9))  # noqa: E731
                garde, enleve = (a, b) if rang(a) <= rang(b) else (b, a)
                for k in ("festival", "heure", "prix", "billets", "resume", "image", "aussi", "affiche", "liens"):
                    if not garde.get(k) and enleve.get(k):
                        garde[k] = enleve[k]
                retires.add(id(enleve))
                journal.append(f"{jour} : « {enleve['titre'][:50]} » ({enleve['lieu']}) = « {garde['titre'][:50]} » ({garde['lieu']})")
                if garde is b:
                    break
    return [e for e in events if id(e) not in retires], journal


_TITRES_EXPO_VAGUES = {"exposition", "expo", "expositions", "exposition permanente", "collection permanente",
                       "exposition temporaire", "vernissage", "oeuvres", "nouvelle exposition"}


def doublons_expos(expos: list[dict]) -> list[dict]:
    """Une même exposition annoncée sous plusieurs titres dans le même lieu (« HYMNES », « Stephanie Comilang : HYMNES »,
    « HYMNES – Stephanie Comilang ») : on garde une seule fiche, la plus complète (titre le plus long), avec la date de
    fin la plus souvent annoncée."""
    gardees: list[list[dict]] = []
    for x in expos:
        tx = _titre_net(re.sub(r"(?i)^\s*exposition\s*[:\-–]\s*", "", x["titre"]))
        groupe = None
        if tx and tx not in _TITRES_EXPO_VAGUES:
            for g in gardees:
                y = g[0]
                if (x.get("discipline") or "expo") == (y.get("discipline") or "expo") and lieux_proches(x["lieu"], y["lieu"]) \
                        and meme_spectacle(dict(x, titre=re.sub(r"(?i)^\s*exposition\s*[:\-–]\s*", "", x["titre"])),
                                           dict(y, titre=re.sub(r"(?i)^\s*exposition\s*[:\-–]\s*", "", y["titre"]))):
                    groupe = g
                    break
        if groupe is None:
            gardees.append([x])
        else:
            groupe.append(x)
    out = []
    for g in gardees:
        if len(g) == 1:
            out.append(g[0])
            continue
        fins = Counter(x["fin"] for x in g)
        fin = sorted(fins.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        meilleure = dict(max(g, key=lambda x: len(x["titre"])))
        meilleure["fin"] = fin
        meilleure["debut"] = min(x["debut"] for x in g)
        for x in g:
            for k in ("festival", "resume", "url", "prix", "billets", "affiche"):
                if not meilleure.get(k) and x.get(k):
                    meilleure[k] = x[k]
        out.append(meilleure)
    return out
