"""Catalogues Deezer / Apple Music : un lien seulement avec un indice qui confirme, jamais contre un indice contraire."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import decouverte as d  # noqa: E402

d.time.sleep = lambda x: None


def faux_catalogue(label="Bonsound", genre="Rap/Hip Hop", homonyme=False):
    def gj(u):
        if "deezer.com/search" in u:
            data = [{"id": 1, "name": "Emma Beko", "link": "https://www.deezer.com/artist/1", "nb_album": 2}]
            return {"data": data * (2 if homonyme else 1)}
        if "deezer.com/artist" in u:
            return {"data": [{"id": 9, "title": "Lumière", "release_date": "2024-03-01"}]}
        if "deezer.com/album" in u:
            return {"label": label, "genres": {"data": [{"name": genre}]}}
        if "itunes.apple.com/search" in u:
            return {"results": []}
        return {"results": []}
    return gj


class Catalogues(unittest.TestCase):
    ctx = {"texte": "emma beko", "style": None, "date": "2026-11-04", "lancement": False}

    def test_etiquette_quebecoise_confirme(self):
        self.assertEqual(len(d.catalogues("Emma Beko", self.ctx, faux_catalogue())), 1)

    def test_sans_indice_on_s_abstient(self):
        self.assertEqual(d.catalogues("Emma Beko", self.ctx, faux_catalogue(label="Sony Music")), [])

    def test_genre_contraire_refuse(self):
        self.assertEqual(d.catalogues("Emma Beko", dict(self.ctx, style="classique"), faux_catalogue()), [])

    def test_homonymes_on_s_abstient(self):
        self.assertEqual(d.catalogues("Emma Beko", self.ctx, faux_catalogue(homonyme=True)), [])

    def test_nom_trop_court(self):
        self.assertEqual(d.catalogues("Kim", self.ctx, faux_catalogue()), [])

    def test_album_nomme_sur_la_page(self):
        ctx = dict(self.ctx, texte=d.plat("Emma Beko présente Lumière en spectacle"))
        self.assertEqual(len(d.catalogues("Emma Beko", ctx, faux_catalogue(label="Sony Music"))), 1)


if __name__ == "__main__":
    unittest.main()
