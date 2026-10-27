"""Nettoyage commun : classement par discipline, tri des activités non culturelles,
filtre « île de Montréal », noms de salles et doublons."""
from __future__ import annotations

import re
import unicodedata

DISCIPLINES = ["theatre", "musique", "danse", "cirque", "humour", "cinema", "lettres", "jeune", "expo", "autre"]


def plat(s: str) -> str:
    """Minuscules sans accents ni ponctuation, pour comparer des textes."""
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode()
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


def est_non_culturel(titre: str, categorie: str = "") -> bool:
    return _has(titre, NON_CULTUREL) or _has(categorie, ["sport", "loisir sportif", "vie democratique", "consultation"])


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
        # nom contenu dans un alias connu (ex. « L'Escogriffe Bar Spectacle (L'Esco) »)
        for cle, canon in self._index.items():
            if len(cle) >= 5 and (cle in k or k in cle):
                return canon
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

    def coord(self, nom: str) -> dict | None:
        info = self.data.get(nom)
        if isinstance(info, dict) and info.get("lat") is not None:
            return {"lat": info["lat"], "lon": info["lon"], "quartier": info.get("quartier", "")}
        return None


# ---------- Doublons ----------
PRIORITE = {"formulaire": 0, "calendrier": 1, "festival": 2, "theatre": 2, "ville": 3, "sorstu": 4, "askapunk": 5, "songkick": 6, "ia": 7}


GENERIQUES = {"soiree", "concert", "spectacle", "show", "festival", "les", "the", "une", "des", "atelier", "lancement",
              "exposition", "projection", "party", "nuit", "grand", "grande", "special", "halloween", "fest", "jour"}


def _mots(titre: str) -> list[str]:
    t = re.sub(r"\b(avec|with|and|et|presente|presents|feat|ft|w)\b", " ", plat(titre))
    return [m for m in t.split() if len(m) > 2]


def meme_evenement(a: dict, b: dict) -> bool:
    """Même date, même salle, et même premier mot distinctif (souvent le nom de l'artiste ou de la pièce)."""
    if a["date"] != b["date"] or plat(a["lieu"])[:18] != plat(b["lieu"])[:18]:
        return False
    if a.get("heure") and b.get("heure") and a["heure"] != b["heure"]:
        return False
    # Même festival, même jour, même heure, même salle : le même spectacle sous deux titres
    # (ex. « Concert d'ouverture… » et « Ouverture jubilatoire ! »).
    if a.get("festival") and a.get("festival") == b.get("festival") and a.get("heure") and a.get("heure") == b.get("heure") \
            and plat(a["lieu"]) != "lieu a confirmer":
        return True
    ma, mb = _mots(a["titre"]), _mots(b["titre"])
    if not ma or not mb:
        return plat(a["titre"]) == plat(b["titre"])
    if ma[0] == mb[0] and ma[0] not in GENERIQUES:
        return True
    return " ".join(ma[:3]) == " ".join(mb[:3])


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
        garde = seaux.setdefault((e["date"], plat(e["lieu"])[:18]), [])
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
    # Un événement de festival sans salle connue, déjà présent avec sa salle (même jour, même heure) : on le retire.
    connus = {(e["date"], e.get("heure"), e.get("festival")): e for e in tous
              if e.get("festival") and e.get("heure") and plat(e["lieu"]) != "lieu a confirmer"}
    garde = []
    for e in tous:
        if e.get("festival") and plat(e["lieu"]) == "lieu a confirmer":
            autre = connus.get((e["date"], e.get("heure"), e.get("festival")))
            if autre and meme_evenement(dict(e, lieu=autre["lieu"]), autre):
                for k in ("prix", "billets", "resume", "image", "aussi"):
                    if not autre.get(k) and e.get(k):
                        autre[k] = e[k]
                continue
        garde.append(e)
    tous = garde
    return sorted(tous, key=lambda e: (e["date"], e.get("heure") or "99", e["titre"]))
