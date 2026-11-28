import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lien_officiel as lo  # noqa: E402


class Rep:
    def __init__(self, text):
        self.text = text


PAGES = {
    "https://sorstu.ca/artiste/suzanne-va-sortir/":
        '<a href="https://www.facebook.com/x">fb</a><a href="https://theatrelalicorne.com/">La Licorne</a>'
        '<a href="https://theatrelalicorne.com/spectacle/suzanne-va-sortir/">Suzanne va sortir</a>'
        '<a href="https://lepointdevente.com/billets/suzanne">Billets</a>',
    "https://sorstu.ca/artiste/autre/": '<a href="https://petitesalle.ca/">Petite Salle</a>',
    "https://www.songkick.com/concerts/1-bach": '<a href="https://bach.example.com/">Bach</a>',
}


def telecharger(u, accept=""):
    if u not in PAGES:
        raise OSError("hors ligne")
    return Rep(PAGES[u])


class TestLienVersLaSalle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        lo.MEMOIRE = Path(self.tmp.name) / "memo.json"
        lo.CONTACTS = Path(self.tmp.name) / "absent.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_page_de_l_evenement_chez_la_salle(self):
        evs = [{"titre": "Suzanne va sortir", "lieu": "La Licorne", "date": "2026-12-01",
                "url": "https://sorstu.ca/artiste/suzanne-va-sortir/"},
               {"titre": "Autre pièce", "lieu": "La Licorne", "date": "2026-12-02",
                "url": "https://theatrelalicorne.com/spectacle/autre-piece/"}]
        lo.officialiser(evs, [], telecharger, date(2026, 11, 28))
        self.assertEqual(evs[0]["url"], "https://theatrelalicorne.com/spectacle/suzanne-va-sortir/")

    def test_accueil_de_la_salle_sinon_et_billetterie_gardee(self):
        e = {"titre": "Spectacle X", "lieu": "Salle Y", "date": "2026-12-01", "url": "https://lepointdevente.com/billets/x"}
        lo.officialiser([e], [{"lieu": "Salle Y", "url": "https://salley.ca/programmation/"}], telecharger, date(2026, 11, 28))
        self.assertEqual(e["url"], "https://salley.ca/")
        self.assertEqual(e["billets"], "https://lepointdevente.com/billets/x")

    def test_salle_trouvee_par_le_lien_qui_porte_son_nom(self):
        e = {"titre": "Concert", "lieu": "Petite Salle", "date": "2026-12-01", "url": "https://sorstu.ca/artiste/autre/"}
        lo.officialiser([e], [], telecharger, date(2026, 11, 28))
        self.assertEqual(e["url"], "https://petitesalle.ca/")

    def test_salle_introuvable_agregateur_garde(self):
        e = {"titre": "Bach", "lieu": "Salle Z", "date": "2026-12-01", "url": "https://www.songkick.com/concerts/1-bach"}
        lo.officialiser([e], [], telecharger, date(2026, 11, 28))
        self.assertEqual(e["url"], "https://www.songkick.com/concerts/1-bach")

    def test_pages_de_la_ville_intouchees(self):
        e = {"titre": "Conte", "lieu": "Maison de la culture", "date": "2026-12-01",
             "url": "https://montreal.ca/evenements/conte-1"}
        lo.officialiser([e], [], telecharger, date(2026, 11, 28))
        self.assertEqual(e["url"], "https://montreal.ca/evenements/conte-1")


if __name__ == "__main__":
    unittest.main()
