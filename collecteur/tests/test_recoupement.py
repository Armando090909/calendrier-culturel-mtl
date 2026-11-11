import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import normalisation as N  # noqa: E402


def ev(titre, lieu, heure, url, source="salles", date="2026-11-12"):
    return {"titre": titre, "lieu": lieu, "heure": heure, "url": url, "source": source, "date": date}


class Recoupement(unittest.TestCase):
    def test_salle_dans_un_batiment(self):
        a = ev("Violence du corps de l'autre", "Cinémathèque québécoise", "19:00", "https://cinematheque.qc.ca/a")
        b = ev("Violence du corps de l'autre", "Salle Fernand-Seguin", "19:00", "https://festival.ca/b", "festival")
        out = N.dedoublonner([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["confirmations"], 2)

    def test_titre_francais_et_anglais(self):
        a = ev("Les mille et une notes de Shéhérazade (programme condensé)", "Maison symphonique", "19:30",
               "https://www.placedesarts.com/evenement/mille-notes")
        b = ev("The Thousand and One Notes of Sheherazade (programme condensé)", "Maison symphonique", "19:30",
               "https://www.placedesarts.com/en/event/thousand-notes")
        self.assertEqual(len(N.dedoublonner([a, b])), 1)

    def test_heure_par_defaut(self):
        a = ev("Coco Belliveau : Cocologie au Gesù, Montréal", "Gesù", "12:00", "https://spectaculos.ca/x")
        b = ev("Coco Belliveau", "Gesù", "20:00", "https://sorstu.ca/artiste/coco", "sorstu")
        out = N.dedoublonner([a, b])
        self.assertEqual([e["heure"] for e in out], ["20:00"])

    def test_deux_representations_restent(self):
        a = ev("Les 7 Doigts : Le Grenier", "Théâtre St-Denis", "15:00", "https://theatrestdenis.com/a")
        b = ev("Les 7 Doigts : Le Grenier", "Théâtre St-Denis", "20:00", "https://theatrestdenis.com/a")
        self.assertEqual(len(N.dedoublonner([a, b])), 2)

    def test_deux_films_meme_heure_restent(self):
        a = ev("CINEMANIA : Un film", "Cinéma du Parc", "19:00", "https://cinemania.ca/a", "festival")
        b = ev("CINEMANIA : Autre chose", "Cinéma du Parc", "19:00", "https://cinemania.ca/b", "festival")
        self.assertEqual(len(N.dedoublonner([a, b])), 2)


if __name__ == "__main__":
    unittest.main()
