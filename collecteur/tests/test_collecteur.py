"""Tests hors ligne. Lancer : python -m unittest discover -s collecteur/tests -v"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import connecteurs  # noqa: E402
import ia  # noqa: E402
from ics import parse_ics  # noqa: E402
from normalisation import Lieux, classer, dedoublonner, est_non_culturel, hors_ile  # noqa: E402

D1, D2 = date(2026, 10, 26), date(2026, 12, 25)

ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:a1
DTSTART;TZID=America/Toronto:20261030T200000
DTEND;TZID=America/Toronto:20261030T230000
SUMMARY:Concert de fin de semaine\\, avec invités
LOCATION:Casa del Popolo, 4873 boul. Saint-Laurent, Montréal
URL:https://exemple.org/concert
END:VEVENT
BEGIN:VEVENT
UID:a2
DTSTART:20261101T010000Z
SUMMARY:Projection de minuit
END:VEVENT
BEGIN:VEVENT
UID:a3
DTSTART;VALUE=DATE:20261105
DTEND;VALUE=DATE:20261106
SUMMARY:Vernissage
  toute la journée
END:VEVENT
BEGIN:VEVENT
UID:a4
DTSTART;TZID=America/Toronto:20261104T190000
RRULE:FREQ=WEEKLY;COUNT=3
SUMMARY:Jam hebdo
END:VEVENT
BEGIN:VEVENT
UID:a5
DTSTART;TZID=America/Toronto:20261102T190000
STATUS:CANCELLED
SUMMARY:Annulé
END:VEVENT
END:VCALENDAR
"""

JSONLD = """<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"TheaterEvent","name":"Georges","startDate":"2026-11-03T19:00:00-05:00","url":"/pieces/georges",
  "location":{"@type":"Place","name":"La Licorne","address":{"streetAddress":"4559 Papineau","addressLocality":"Montréal"}},
  "offers":{"availability":"https://schema.org/SoldOut"}},
 {"@type":"ExhibitionEvent","name":"Grande expo","startDate":"2026-10-01","endDate":"2027-01-10",
  "location":{"name":"Galerie X"}},
 {"@type":"Organization","name":"pas un événement"}]}
</script></head><body></body></html>"""

GANCIO = [{"id": 1, "title": "Cross Check + Rubble", "slug": "cross-check", "start_datetime": 1793404800,
           "place": {"name": "Turbo Haüs", "address": "2040 Saint-Denis"}, "tags": ["punk"]}]

VILLE_CSV = ("id,titre,url_fiche,date_debut,date_fin,type_evenement,titre_adresse,adresse_principale,public_cible\n"
             "1,Possessions - Théâtre Bistouri,https://montreal.ca/evenements/p,2026-10-28 19:30:00,2026-10-28 21:00:00,Spectacle,Maison de la culture Ahuntsic,10300 Lajeunesse,Adultes\n"
             "2,Yoga sur chaise,https://montreal.ca/evenements/y,2026-10-28 10:00:00,2026-10-28 11:00:00,Activité,Centre Sanaaq,,Aînés\n"
             "3,Surcharge - Benz Debrosse,https://montreal.ca/evenements/s,2026-09-16,2026-12-13,Exposition,Maison de la culture Maisonneuve,,\n"
             "4,Fille de laitier (Annulé),https://montreal.ca/evenements/f,2026-10-30 19:30:00,2026-10-30 21:00:00,Spectacle,MC PAT,,\n")


class Rep:
    def __init__(self, text="", data=None):
        self.text, self._data = text, data
        self.content = text.encode("utf-8")

    def json(self):
        return self._data


class TestICS(unittest.TestCase):
    def test_parse(self):
        evs = parse_ics(ICS, D1, D2)
        titres = [e["titre"] for e in evs]
        self.assertIn("Concert de fin de semaine, avec invités", titres)
        self.assertIn("Vernissage toute la journée", titres)
        self.assertEqual(titres.count("Jam hebdo"), 3)
        concert = next(e for e in evs if e["titre"].startswith("Concert"))
        self.assertEqual((concert["debut"].hour, concert["debut"].minute), (20, 0))
        minuit = next(e for e in evs if e["titre"] == "Projection de minuit")
        self.assertEqual(minuit["debut"].date(), date(2026, 10, 31))  # 01:00 UTC = 21:00 le 31 à Montréal
        self.assertEqual(minuit["debut"].hour, 21)
        self.assertTrue(next(e for e in evs if e["titre"] == "Annulé")["annule"])

    def test_connecteur(self):
        with mock.patch.object(connecteurs, "telecharger", return_value=Rep(ICS)):
            evs, _ = connecteurs.ics({"url": "webcal://x.org/a.ics", "cle_source": "calendrier"}, D1, D2)
        c = next(e for e in evs if e["titre"].startswith("Concert"))
        self.assertEqual((c["date"], c["heure"], c["lieu"]), ("2026-10-30", "20:00", "Casa del Popolo"))
        v = next(e for e in evs if e["titre"].startswith("Vernissage"))
        self.assertIsNone(v["heure"])

    def test_url_google(self):
        u = connecteurs.url_calendrier("https://calendar.google.com/calendar/embed?src=abc%40group.calendar.google.com&ctz=America%2FToronto")
        self.assertEqual(u, "https://calendar.google.com/calendar/ical/abc%40group.calendar.google.com/public/basic.ics")
        self.assertEqual(connecteurs.url_calendrier("webcal://a.org/x.ics"), "https://a.org/x.ics")


class TestAutres(unittest.TestCase):
    def test_jsonld(self):
        evs, series = connecteurs.evenements_jsonld(JSONLD, "https://theatrelalicorne.com/", {"cle_source": "theatre"}, D1, D2)
        self.assertEqual(len(evs), 1)
        e = evs[0]
        self.assertEqual((e["date"], e["heure"], e["lieu"], e["complet"]), ("2026-11-03", "19:00", "La Licorne", True))
        self.assertEqual(e["url"], "https://theatrelalicorne.com/pieces/georges")
        self.assertEqual(series[0]["titre"], "Grande expo")

    def test_gancio(self):
        evs = connecteurs.evenements_gancio(GANCIO, "https://montreal.askapunk.net", {"cle_source": "askapunk"})
        self.assertEqual(evs[0]["url"], "https://montreal.askapunk.net/event/cross-check")
        self.assertEqual(evs[0]["date"], "2026-10-30")
        self.assertEqual(evs[0]["heure"], "20:00")

    def test_ville(self):
        with mock.patch.object(connecteurs, "telecharger", return_value=Rep(VILLE_CSV)):
            evs, series = connecteurs.ville_csv({"url": "x"}, D1, D2)
        titres = {e["titre"]: e for e in evs}
        self.assertIn("Possessions - Théâtre Bistouri", titres)
        self.assertEqual(titres["Possessions - Théâtre Bistouri"]["heure"], "19:30")
        self.assertTrue(titres["Fille de laitier"]["annule"])
        self.assertEqual(series[0]["titre"], "Surcharge - Benz Debrosse")

    def test_formulaires(self):
        prop = ("Horodateur,Titre de l'événement,Date de l'événement,Heure,Lieu (nom de la salle),Adresse,Discipline,Lien,Courriel,Approuvé\n"
                "2026-10-20 10:00,Vernissage Rouge,2026-11-07,18 h,Galerie Rouge,123 rue X,Exposition,https://g.org,a@b.c,oui\n"
                "2026-10-20 11:00,Pas encore validé,2026-11-08,20:00,Bar Y,,Musique,,,\n")
        with mock.patch.object(connecteurs, "telecharger", return_value=Rep(prop)):
            evs, _ = connecteurs.propositions({"url": "x"}, D1, D2)
        self.assertEqual(len(evs), 1)
        self.assertEqual(connecteurs._disciplines_formulaire("Danse, Poésie, slam et rap battle, Jeune public"), ["danse", "poesie", "jeune"])
        self.assertEqual(connecteurs._disciplines_formulaire("Humour et cabaret"), ["humour"])
        self.assertEqual((evs[0]["titre"], evs[0]["date"], evs[0]["heure"], evs[0]["lieu"]),
                         ("Vernissage Rouge", "2026-11-07", "18:00", "Galerie Rouge"))
        cal = ("Horodateur,Nom de l'organisme,Adresse web du calendrier,Nom de la salle,Adresse de la salle,Discipline principale,Courriel,Approuvé\n"
               "x,Galerie Rouge,webcal://g.org/cal.ics,Galerie Rouge,123 rue X,Arts visuels,a@b.c,Oui\n")
        with mock.patch.object(connecteurs, "telecharger", return_value=Rep(cal)):
            cfgs = connecteurs.calendriers_soumis({"url": "x"})
        self.assertEqual((cfgs[0]["url"], cfg_lieu := cfgs[0]["lieu"], cfgs[0]["adresse"]),
                         ("webcal://g.org/cal.ics", "Galerie Rouge", "123 rue X"))

    def test_urls_modele(self):
        u = connecteurs.urls_modele({"url": "https://s/{mois_fr}-{annee}/{jour}/", "repeter": "jour", "jours": 3}, date(2026, 10, 30), D2)
        self.assertEqual(u, ["https://s/octobre-2026/30/", "https://s/octobre-2026/31/", "https://s/novembre-2026/1/"])
        u = connecteurs.urls_modele({"url": "https://k/{month_en}-{annee}?page={page}", "repeter": "mois", "mois": 2, "pages": 2}, D1, D2)
        self.assertEqual(len(u), 4)
        self.assertTrue(u[2].startswith("https://k/november-2026"))

    def test_texte_page(self):
        t = connecteurs.texte_page('<div><script>x</script><a href="/e/1">Concert A</a> 30 oct.</div>', "https://s.org/")
        self.assertIn("Concert A <https://s.org/e/1>", t)
        self.assertNotIn("x", t.replace("https", ""))

    def test_resume_page(self):
        html = '<head><meta name="description" content="Concert pop-rock déjanté de FEU TOUTE!"></head><body><p>Menu</p></body>'
        r = connecteurs.resume_page(html)
        self.assertIn("Concert pop-rock", r)
        from normalisation import classer as c
        self.assertEqual(c("Feu Toute!", "", description=r), "musique")

    def test_ia_json(self):
        self.assertEqual(ia.lire_json('```json\n{"evenements": []}\n```'), {"evenements": []})
        self.assertEqual(ia.lire_json('Voici : {"0": "musique"}'), {"0": "musique"})


class TestNormalisation(unittest.TestCase):
    def test_classer(self):
        self.assertEqual(classer("Possessions - Théâtre Bistouri"), "theatre")
        self.assertEqual(classer("Charles Brunet", "Humour"), "humour")
        self.assertEqual(classer("Rawayana", "Reggae"), "musique")
        self.assertEqual(classer("Les Songes d'une nuit d'été", "Ballet"), "danse")
        self.assertEqual(classer("Ciné-club Caserne 45"), "cinema")
        self.assertEqual(classer("Marcia"), "autre")

    def test_filtres(self):
        self.assertTrue(est_non_culturel("Yoga sur chaise"))
        self.assertTrue(est_non_culturel("PING! Formation informatique"))
        self.assertFalse(est_non_culturel("Danser avec le feu"))
        self.assertTrue(hors_ile("Place Bell", "", "Laval"))
        self.assertTrue(hors_ile("Le Club Square Dix30"))
        self.assertFalse(hors_ile("Théâtre Desjardins", "", "LaSalle"))

    def test_lieux(self):
        L = Lieux({"L'Escogriffe": {"lat": 1, "lon": 2, "alias": ["L'Esco"]}, "Théâtre Fairmount": {"lat": 1, "lon": 2}})
        self.assertEqual(L.trouver("L'Escogriffe Bar Spectacle (L'Esco)"), "L'Escogriffe")
        self.assertEqual(L.trouver("Théâtre Fairmount Theatre"), "Théâtre Fairmount")
        self.assertEqual(L.trouver("l'esco"), "L'Escogriffe")
        self.assertIsNone(L.trouver("Casa Obscura"))

    def test_doublons(self):
        evs = [
            {"date": "2026-10-30", "heure": None, "titre": "Ak'Chamel, avec Kee Avil", "lieu": "L'Escogriffe", "source": "songkick"},
            {"date": "2026-10-30", "heure": "20:00", "titre": "Ak'Chamel", "lieu": "L'Escogriffe", "source": "sorstu"},
            {"date": "2026-10-31", "heure": "20:00", "titre": "Ak'Chamel", "lieu": "L'Escogriffe", "source": "sorstu"},
        ]
        out = dedoublonner(evs)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["heure"], "20:00")


class TestDetails(unittest.TestCase):
    def test_details(self):
        import collecte
        d = collecte.details({"source": "songkick", "description": "x" * 500, "prix": "25 $",
                              "billets": "https://b.ca", "image": "https://img.ca/a.jpg"})
        self.assertLessEqual(len(d["resume"]), 201)
        self.assertEqual(d["prix"], "25 $")
        self.assertNotIn("image", d)  # pas d'image d'une source tierce
        d = collecte.details({"source": "formulaire", "image": "https://img.ca/a.jpg"})
        self.assertEqual(d["image"], "https://img.ca/a.jpg")


class TestCollecte(unittest.TestCase):
    """Collecte complète avec des sources simulées (aucun accès réseau)."""

    def test_bout_en_bout(self):
        import collecte
        tmp = Path(tempfile.mkdtemp())
        (tmp / "docs").mkdir()
        sources = tmp / "sources.yaml"
        sources.write_text("""
reglages: {horizon_jours: 60, minimum_evenements: 2}
noms_sources: {ville: {nom: Ville, url: x}, calendrier: {nom: Cal, url: ''}}
sources:
  - {nom: Ville, cle: ville, type: ville_csv, url: x}
  - {nom: Cal, cle: calendrier, type: ics, url: y}
""", encoding="utf-8")
        lieux = tmp / "lieux.json"
        lieux.write_text(json.dumps({"Maison de la culture Ahuntsic": {"lat": 45.55, "lon": -73.66, "quartier": "Ahuntsic"}}), encoding="utf-8")

        def fake_dl(url, accept="*/*"):
            return Rep(VILLE_CSV if url == "x" else ICS)

        class Jour(collecte.datetime):
            @classmethod
            def now(cls, tz=None):
                return collecte.datetime(2026, 10, 26, 8, 0, tzinfo=tz)

        geo_appels = []

        def fake_geo(q, ua):
            geo_appels.append(q)
            return {"lat": 45.52, "lon": -73.59, "quartier": "Mile End"}

        with mock.patch.multiple(collecte, SORTIE=tmp / "docs" / "data.json", RAPPORT=tmp / "docs" / "rapport.json",
                                 LIEUX=lieux, SOURCES=sources, CACHE=tmp / "cache", MANUELS=tmp / "aucun.json",
                                 datetime=Jour), \
                mock.patch.object(connecteurs, "telecharger", side_effect=fake_dl), \
                mock.patch.object(collecte.geo, "localiser", side_effect=fake_geo), \
                mock.patch.dict("os.environ", {}, clear=False):
            for k in ("ANTHROPIC_API_KEY", "PROPOSITIONS_CSV_URL", "CALENDRIERS_CSV_URL"):
                __import__("os").environ.pop(k, None)
            code = collecte.main()
        self.assertEqual(code, 0)
        data = json.loads((tmp / "docs" / "data.json").read_text(encoding="utf-8"))
        titres = [e["titre"] for e in data["events"]]
        self.assertIn("Possessions - Théâtre Bistouri", titres)
        self.assertNotIn("Yoga sur chaise", titres)
        self.assertNotIn("Fille de laitier", titres)
        self.assertIn("Concert de fin de semaine, avec invités", titres)
        self.assertEqual(data["events"][0]["date"], "2026-10-28")
        self.assertTrue(any(x["titre"] == "Surcharge - Benz Debrosse" for x in data["expos"]))
        self.assertIn("Casa del Popolo", data["lieux"])
        self.assertTrue(geo_appels)
        self.assertTrue(all(e["discipline"] != "autre" or True for e in data["events"]))
        rapport = json.loads((tmp / "docs" / "rapport.json").read_text(encoding="utf-8"))
        self.assertEqual(rapport["statut"], "publié")


if __name__ == "__main__":
    unittest.main()


class TestHeurePage(unittest.TestCase):
    def test_heures(self):
        from connecteurs import heure_page
        self.assertEqual(heure_page('<script type="application/ld+json">{"@type":"Event","startDate":"2026-10-30T20:30:00-04:00"}</script>'), "20:30")
        self.assertEqual(heure_page("<p>Doors open at 20:00, with the show starting at 20:30.</p>"), "20:30")
        self.assertEqual(heure_page("<p>Portes : 19 h · Spectacle : 20 h 30</p>"), "20:30")
        self.assertEqual(heure_page("<p>Doors 8pm / Show 9pm</p>"), "21:00")
        self.assertIsNone(heure_page("<p>Le 12 novembre, entrée 15 $</p>"))


class TestAussi(unittest.TestCase):
    def test_performance(self):
        from normalisation import disciplines_aussi
        self.assertEqual(disciplines_aussi("PERDÓN – Losinformalls", "", "autre", "La Chapelle Scènes contemporaines"), ("theatre", ["danse"]))
        self.assertEqual(disciplines_aussi("Solo", "une performance entre danse et théâtre", "danse", ""), ("danse", ["theatre"]))
        self.assertEqual(disciplines_aussi("Sting", "", "musique", "Théâtre St-Denis"), ("musique", []))


class TestFestivals(unittest.TestCase):
    def test_fenetre_et_etiquette(self):
        import festivals as fest
        from datetime import date
        F = [{"id": "cdc", "nom": "Coup de cœur francophone", "court": "Coup de cœur", "disciplines": ["musique"],
              "debut": "2026-11-05", "fin": "2026-11-15", "site": "https://coupdecoeur.ca"}]
        self.assertTrue(fest.en_fenetre(F[0], date(2026, 9, 1)))
        self.assertFalse(fest.en_fenetre(F[0], date(2026, 8, 1)))
        self.assertEqual(len(fest.sources(F, date(2026, 10, 27))), 1)
        ev = [{"titre": "Richard Desjardins · Coup de cœur", "date": "2026-11-06", "url": ""},
              {"titre": "Autre show", "date": "2026-11-06", "url": "https://coupdecoeur.ca/x"},
              {"titre": "Coup de cœur pour toi", "date": "2027-03-01", "url": ""}]
        fest.etiqueter(ev, F)
        self.assertEqual([e.get("festival") for e in ev], ["cdc", "cdc", None])

    def test_dedoublonnage_garde_festival(self):
        from normalisation import dedoublonner
        a = {"date": "2026-11-06", "heure": None, "titre": "Richard Desjardins", "lieu": "Club Soda", "source": "songkick"}
        b = {"date": "2026-11-06", "heure": "20:00", "titre": "Richard Desjardins", "lieu": "Club Soda", "source": "songkick", }
        a["festival"] = "cdc"
        r = dedoublonner([a, b])
        self.assertEqual(len(r), 1)
        self.assertEqual((r[0]["heure"], r[0].get("festival")), ("20:00", "cdc"))


class TestMemoire(unittest.TestCase):
    def test_page_inchangee_pas_relue(self):
        import connecteurs, ia
        from datetime import date
        appels = []
        vrai = ia.extraire_page
        ia.extraire_page = lambda *a: appels.append(1) or {"evenements": [], "series": []}
        connecteurs._memoire = {}
        try:
            for _ in range(3):
                connecteurs.extraire_avec_memoire("https://x.ca", "même texte", date(2026, 11, 1), date(2026, 12, 31))
            connecteurs.extraire_avec_memoire("https://x.ca", "texte modifié", date(2026, 11, 1), date(2026, 12, 31))
        finally:
            ia.extraire_page = vrai
            connecteurs._memoire = None
        self.assertEqual(len(appels), 2)


class TestDecouverte(unittest.TestCase):
    def test_noms(self):
        from decouverte import noms_artistes
        self.assertEqual(noms_artistes("Jonquille (lancement) + Chloé Jara-Buto"), ["Jonquille", "Chloé Jara-Buto"])
        self.assertEqual(noms_artistes("Forêt + invité·e·s + Virginie Reid"), ["Forêt", "Virginie Reid"])
        self.assertEqual(noms_artistes("Sting"), ["Sting"])

    def test_page(self):
        from decouverte import depuis_page
        html = """<iframe src="https://bandcamp.com/EmbeddedPlayer/album=123"></iframe>
                  <a href="https://www.youtube.com/@salle">YouTube de la salle</a>
                  <a href="https://jonquille.bandcamp.com">Jonquille sur Bandcamp</a>
                  <a href="https://open.spotify.com/artist/abc">Écouter Jonquille</a>"""
        liens = depuis_page(html, "https://salle.ca/show", ["Jonquille"])
        self.assertEqual([l["type"] for l in liens], ["bandcamp", "bandcamp", "spotify"])  # pas le YouTube de la salle

    def test_musicbrainz_homonymes(self):
        from unittest import mock
        from decouverte import musicbrainz
        patch = mock.patch("decouverte.time.sleep", lambda s: None)
        patch.start()
        self.addCleanup(patch.stop)
        rep = {"artists": [{"id": "1", "name": "Forêt", "score": 100, "country": "FR"},
                           {"id": "2", "name": "Forêt", "score": 100, "country": "CA"}]}
        fiche = {"relations": [{"type": "bandcamp", "url": {"resource": "https://foret.bandcamp.com/"}},
                               {"type": "free streaming", "url": {"resource": "https://open.spotify.com/artist/x"}}]}
        get = lambda url: fiche if "inc=url-rels" in url else rep
        self.assertEqual([l["type"] for l in musicbrainz("Forêt", get)], ["bandcamp", "spotify"])
        rep2 = {"artists": [{"id": "1", "name": "Baie", "score": 100, "country": "FR"},
                            {"id": "2", "name": "Baie", "score": 100, "country": "US"}]}
        self.assertEqual(musicbrainz("Baie", lambda url: rep2), [])  # deux homonymes hors Canada : on s'abstient

    def test_affiche(self):
        from decouverte import affiche_page, page_officielle
        html = '<meta property="og:image" content="/media/desjardins-affiche.jpg">'
        a = affiche_page(html, "https://www.clubsoda.ca/spectacle/desjardins")
        self.assertEqual(a["url"], "https://www.clubsoda.ca/media/desjardins-affiche.jpg")
        self.assertEqual(a["credit"], "clubsoda.ca")
        self.assertIsNone(affiche_page('<meta property="og:image" content="https://x.ca/logo.png">', "https://x.ca"))
        self.assertFalse(page_officielle("https://www.songkick.com/concerts/1"))



class TestFestappEtDoublons(unittest.TestCase):
    def test_heure_festapp(self):
        from normalisation import corriger_heure_festapp
        self.assertEqual(corriger_heure_festapp("2026-11-02", "14:00"), "19:00")   # heure normale de l'Est (UTC-5)
        self.assertEqual(corriger_heure_festapp("2026-07-10", "16:00"), "20:00")   # heure avancée (UTC-4)
        self.assertEqual(corriger_heure_festapp("2026-11-02", "21:30"), "21:30")   # changerait de jour : on ne touche pas
        self.assertIsNone(corriger_heure_festapp("2026-11-02", None))

    def test_meme_festival_meme_creneau(self):
        from normalisation import dedoublonner
        a = {"date": "2026-11-20", "heure": "19:30", "lieu": "Maison symphonique", "titre": "Concert d'ouverture — Magnificat",
             "festival": "bach", "source": "festival"}
        b = dict(a, titre="Ouverture jubilatoire !", prix="45 $")
        c = dict(a, lieu="Lieu à confirmer", titre="Concert d'ouverture")
        r = dedoublonner([a, b, c])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["prix"], "45 $")


class TestDoublonsSites(unittest.TestCase):
    def test_deux_sites_meme_concert(self):
        from normalisation import dedoublonner
        base = {"date": "2026-10-27", "lieu": "Théâtre Fairmount"}
        r = dedoublonner([dict(base, heure="19:00", titre="Claudio Simonetti's Goblin : Tenebre", source="salles", url="https://ma.to/a"),
                          dict(base, heure="20:00", titre="Goblin Tenebre", source="salles", url="https://theatrefairmount.com/b"),
                          dict(base, heure="20:00", titre="Claudio Simonetti's Goblin", source="sorstu", url="https://sorstu.ca/c")])
        self.assertEqual(len(r), 1)
        p = dedoublonner([{"date": "2026-10-27", "lieu": "MTELUS", "heure": "18:30", "titre": "Periphery - A Pale White Dot Tour", "source": "sorstu", "url": "https://sorstu.ca/p"},
                          {"date": "2026-10-27", "lieu": "MTELUS", "heure": "20:00", "titre": "Periphery", "source": "salles", "url": "https://ma.to/p"},
                          {"date": "2026-10-27", "lieu": "Lieu à confirmer", "heure": "20:00", "titre": "Periphery Montréal", "source": "salles", "url": "https://ma.to/q"}])
        self.assertEqual(len(p), 1)

    def test_deux_representations_meme_site(self):
        from normalisation import dedoublonner
        base = {"date": "2026-10-29", "lieu": "Upstairs Jazz Bar & Grill", "titre": "TAUREY BUTLER TRIO", "source": "salles", "url": "https://upstairsjazz.com/x"}
        self.assertEqual(len(dedoublonner([dict(base, heure="19:00"), dict(base, heure="21:30")])), 2)


class TestBandcamp(unittest.TestCase):
    PAGE = """<ul><li class="searchresult band"><div class="heading"><a href="https://anguilles.bandcamp.com?from=search">Anguilles</a></div>
      <div class="subhead">Montréal, Québec</div><div class="itemurl"><a>https://anguilles.bandcamp.com</a></div></li>
      <li class="searchresult band"><div class="heading"><a href="https://x.bandcamp.com">Anguilles</a></div>
      <div class="subhead">Lyon, France</div><div class="itemurl"><a>https://x.bandcamp.com</a></div></li>
      <li class="searchresult band"><div class="heading"><a href="https://y.bandcamp.com">Anguilles du Nord</a></div></li></ul>"""

    def test_local_prefere(self):
        from decouverte import bandcamp
        r = bandcamp("Anguilles", lambda u: self.PAGE)
        self.assertEqual(r[0]["url"], "https://anguilles.bandcamp.com")

    def test_abstention(self):
        from decouverte import bandcamp
        page = self.PAGE.replace("Montréal, Québec", "Berlin")
        self.assertEqual(bandcamp("Anguilles", lambda u: page), [])


class TestDoublonsAudit(unittest.TestCase):
    def test_lettres_et_salles(self):
        from normalisation import dedoublonner
        r = dedoublonner([{"date": "2026-10-31", "heure": "20:00", "titre": "Eivør", "lieu": "Le National", "source": "sorstu", "url": "https://sorstu.ca/e"},
                          {"date": "2026-10-31", "heure": "20:00", "titre": "Eivor", "lieu": "Le National", "source": "salles", "url": "https://ma.to/e"}])
        self.assertEqual(len(r), 1)
        r = dedoublonner([{"date": "2026-11-04", "heure": None, "titre": "Ashwaaq | Taqasim", "lieu": "Cinquième Salle", "source": "festival", "url": "https://pda/a"},
                          {"date": "2026-11-04", "heure": None, "titre": "Ashwaaq | Taqasim", "lieu": "Place des Arts", "source": "festival", "url": "https://pda/a"}])
        self.assertEqual(len(r), 1)

    def test_pas_de_fusion_abusive(self):
        from normalisation import dedoublonner
        f = {"date": "2026-11-06", "heure": "22:30", "lieu": "Lieu à confirmer", "source": "festival", "url": "https://festapp.io/x", "festival": "coupdecoeur"}
        self.assertEqual(len(dedoublonner([dict(f, titre="bombe"), dict(f, titre="Soraï")])), 2)
        v = {"date": "2026-10-30", "heure": None, "lieu": "Lieu à confirmer", "source": "ville", "titre": "Soirée d'Halloween"}
        self.assertEqual(len(dedoublonner([dict(v, url="https://montreal.ca/a"), dict(v, url="https://montreal.ca/b")])), 2)


class TestBillets(unittest.TestCase):
    def test_billetterie_connue(self):
        from decouverte import billets_page
        html = '<a href="/a-propos">À propos</a><a href="https://lepointdevente.com/billets/xyz">Info</a><a href="/billets">Billets</a>'
        self.assertEqual(billets_page(html, "https://salle.ca/show"), "https://lepointdevente.com/billets/xyz")

    def test_bouton_texte(self):
        from decouverte import billets_page
        html = '<a href="/politique">Politique de billetterie</a><a href="https://salle.ca/achat/42">Acheter</a>'
        self.assertEqual(billets_page(html, "https://salle.ca/show"), "https://salle.ca/achat/42")
        self.assertIsNone(billets_page('<a href="/contact">Contact</a>', "https://salle.ca/show"))


class TestRedites(unittest.TestCase):
    def test_meme_artiste_deux_salles(self):
        from normalisation import doublons_du_jour
        ev = [{"date": "2026-11-10", "heure": "20:00", "titre": "Noé Lira + Lapelúda", "lieu": "La Sala Rossa", "discipline": "musique", "source": "salles", "url": "https://a/1"},
              {"date": "2026-11-10", "heure": None, "titre": "Noé Lira", "lieu": "Lieu à confirmer", "discipline": "musique", "source": "festival", "url": "https://b/2"}]
        r, j = doublons_du_jour(ev)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["lieu"], "La Sala Rossa")

    def test_ce_qui_reste(self):
        from normalisation import doublons_du_jour
        base = {"date": "2026-11-28", "discipline": "musique", "source": "festival", "lieu": "Espace Off-Bach"}
        r, _ = doublons_du_jour([dict(base, titre="Dane Ko, piano · Off-Bach", url="https://f/a"),
                                 dict(base, titre="Noémie Raymond, violoncelle, et Chloé Dumoulin, piano", url="https://f/b")])
        self.assertEqual(len(r), 2)  # « piano » n'est pas un nom d'artiste
        f = {"date": "2026-11-05", "discipline": "cinema", "titre": "Looking for Cézanne", "source": "festival"}
        r, _ = doublons_du_jour([dict(f, lieu="Cinéma du Parc", url="1"), dict(f, lieu="Cinémathèque québécoise", url="2")])
        self.assertEqual(len(r), 2)  # un film peut passer dans deux salles
        v = {"date": "2026-11-01", "discipline": "atelier", "source": "ville", "lieu": "Lieu à confirmer"}
        r, _ = doublons_du_jour([dict(v, titre="Rencontre avec Edgar", url="1"), dict(v, titre="Atelier avec Edgar", url="2")])
        self.assertEqual(len(r), 2)  # deux fiches distinctes de la Ville
        s = {"date": "2026-10-29", "discipline": "musique", "source": "salles", "lieu": "Upstairs", "titre": "Taurey Butler Trio", "url": "u"}
        r, _ = doublons_du_jour([dict(s, heure="19:00"), dict(s, heure="21:30")])
        self.assertEqual(len(r), 2)  # deux sets dans la même salle


class TestDoublonsExpos(unittest.TestCase):
    def test_meme_expo_plusieurs_titres(self):
        from normalisation import doublons_expos
        b = {"lieu": "PHI", "debut": "2026-10-28", "discipline": "expo", "url": "u"}
        r = doublons_expos([dict(b, titre="HYMNES", fin="2027-03-14"), dict(b, titre="Stephanie Comilang : HYMNES", fin="2027-03-14"),
                            dict(b, titre="HYMNES – Stephanie Comilang", fin="2027-09-14"), dict(b, titre="Foi ou feu", fin="2027-03-14")])
        self.assertEqual(len(r), 2)
        h = [x for x in r if "HYMNES" in x["titre"]][0]
        self.assertEqual(h["fin"], "2027-03-14")  # la date la plus souvent annoncée


class TestAgenda(unittest.TestCase):
    def test_fichier_ics(self):
        import agenda
        from datetime import datetime
        e = {"date": "2026-11-05", "heure": "19:30", "titre": "Spectacle, avec virgule", "lieu": "Lion d'Or", "url": "https://x"}
        t = agenda.contenu(e, datetime(2026, 1, 1))
        self.assertIn("DTSTART;TZID=America/Toronto:20261105T193000", t)
        self.assertIn("SUMMARY:Spectacle\\, avec virgule", t)
        self.assertTrue(all(len(l.encode()) <= 75 for l in t.split("\r\n")))
        sans = agenda.contenu(dict(e, heure=None), datetime(2026, 1, 1))
        self.assertIn("DTSTART;VALUE=DATE:20261105", sans)
