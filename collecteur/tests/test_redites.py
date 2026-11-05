"""Cas réels corrigés : chaque collecte les revérifie avant de publier (une régression bloque la publication)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from normalisation import PAS_DES_SALLES, doublons_du_jour, hors_ile, plat  # noqa: E402


def E(titre, lieu, heure=None):
    return {"date": "2026-11-12", "titre": titre, "lieu": lieu, "heure": heure, "discipline": "musique",
            "source": "salles", "url": titre}


def fusionnes(a, b):
    return bool(doublons_du_jour([a, b])[1])


class Redites(unittest.TestCase):
    def test_titre_court_dans_une_autre_salle(self):  # 2 nov. 2026
        self.assertFalse(fusionnes(E("Résistance aujourd'hui en Palestine, et solidarité", "La Librairie"),
                                   E("Aujourd'hui", "L’esco")))

    def test_rodage_puis_spectacle(self):  # 2 nov. 2026
        self.assertFalse(fusionnes(E("Guillaume Pineault - Rodage", "Le Terminal", "19:00"),
                                   E("Guillaume Pineault", "Cabaret Lion d'Or", "21:30")))

    def test_meme_salle_deux_graphies(self):  # L'Esco = L'Escogriffe
        self.assertTrue(fusionnes(E("Catherine Leduc + Perma", "L'Escogriffe"), E("Perma", "L’esco")))
        self.assertTrue(fusionnes(E("Aujourd'hui + DONALDA", "L'Escogriffe"), E("Aujourd'hui", "L’esco")))

    def test_vrai_doublon_entre_salles(self):
        self.assertTrue(fusionnes(E("Nina Kraviz @ Le Studio TD", "Le Studio TD"), E("Nina Kraviz", "L'Olympia")))
        self.assertTrue(fusionnes(E("P'tit Belliveau @ Montreal", "Lieu à confirmer"), E("P'tit Belliveau", "Espace transmission")))


class Salles(unittest.TestCase):
    def test_page_erreur_pas_une_salle(self):  # 2 nov. 2026 : « Error 403 »
        self.assertIn(plat("Error 403"), PAS_DES_SALLES)

    def test_minotaure_gatineau(self):  # 2 nov. 2026
        self.assertTrue(hors_ile("Le Minotaure"))


if __name__ == "__main__":
    unittest.main()


class TestSallesHomonymes(unittest.TestCase):
    """5 nov. 2026 : les spectacles du Théâtre Plaza étaient rangés à l'Ausgang Plaza (même mot « Plaza »)."""

    def test_theatre_plaza_distinct_d_ausgang(self):
        import json
        from pathlib import Path
        from normalisation import Lieux
        lieux = Lieux(json.loads((Path(__file__).parent.parent / "lieux.json").read_text(encoding="utf-8")))
        self.assertEqual(lieux.trouver("Théâtre Plaza"), "Théâtre Plaza")
        self.assertEqual(lieux.trouver("Ausgang Plaza"), "Ausgang Plaza")

    def test_noms_generiques_n_avalent_pas_d_autres_salles(self):
        """Audit du 5 nov. 2026 : « La Librairie », « Maison Théâtre », « Le National », « Théâtre Maisonneuve »,
        « La Chapelle »… avalaient des salles différentes qui contenaient le même mot."""
        import json
        from pathlib import Path
        from normalisation import Lieux
        lieux = Lieux(json.loads((Path(__file__).parent.parent / "lieux.json").read_text(encoding="utf-8")))
        for nom, faux in [("Librairie Zone Libre", "La Librairie"), ("Maison de la culture Francis-Brisson", "Maison Théâtre"),
                          ("Office National du Film - Salle Alanis-Obomsawin", "Le National"),
                          ("Collège de Maisonneuve", "Théâtre Maisonneuve"), ("La Chapelle Saint-Louis", "La Chapelle Scènes contemporaines"),
                          ("Le Saint-Jean Comédie Club", "Théâtre La Comédie de Montréal"), ("Basement of St Denis Church", "Théâtre St-Denis")]:
            self.assertNotEqual(lieux.trouver(nom), faux, nom)
        # les vraies variantes restent reconnues
        self.assertEqual(lieux.trouver("PDA - Théâtre Maisonneuve - Montreal"), "Théâtre Maisonneuve")
        self.assertEqual(lieux.trouver("Cinémathèque québécoise - Salle Principale"), "Cinémathèque québécoise")
        self.assertEqual(lieux.trouver("La Chapelle spectacles"), "La Chapelle Scènes contemporaines")
