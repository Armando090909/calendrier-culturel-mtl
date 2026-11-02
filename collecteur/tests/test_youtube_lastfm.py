"""Bandes-annonces YouTube et témoin Last.fm : ce qui est accepté, ce qui est refusé (réponses d'API simulées)."""
import os
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import decouverte as d  # noqa: E402


def api(videos, durees):
    def get_json(url):
        if "/search?" in url:
            return {"items": [{"id": {"videoId": f"v{i}"}, "snippet": {"title": t, "channelTitle": c, "publishedAt": p}}
                              for i, (t, c, p) in enumerate(videos)]}
        return {"items": [{"id": f"v{i}", "contentDetails": {"duration": du}} for i, du in enumerate(durees)]}
    return get_json


class YouTube(unittest.TestCase):
    def setUp(self):
        os.environ["YOUTUBE_API_KEY"] = "x"

    def trouve(self, titre, videos, durees):
        return d.bande_annonce_youtube(titre, 2026, api(videos, durees), {}, date(2026, 11, 2))

    def test_distributeur(self):
        r = self.trouve("Mille secrets, mille dangers",
                        [("MILLE SECRETS MILLE DANGERS - Bande-annonce officielle", "Maison 4:3", "2024-08-01T00:00:00Z")], ["PT2M10S"])
        self.assertEqual(r[0]["url"], "https://www.youtube.com/watch?v=v0")

    def test_critique_refusee(self):
        self.assertEqual(self.trouve("Mille secrets, mille dangers",
                                     [("Mille secrets mille dangers trailer REACTION", "Un cinéphile", "2024-08-01T00:00:00Z")],
                                     ["PT3M"]), [])

    def test_trop_long(self):  # un film complet ou une entrevue de 20 minutes n'est pas une bande-annonce
        self.assertEqual(self.trouve("Au nord des hommes", [("Au nord des hommes - bande-annonce", "x", "2026-01-01T00:00:00Z")],
                                     ["PT20M"]), [])

    def test_titre_court_chaine_inconnue(self):  # « Paradis » : trop ambigu sans chaîne de confiance
        self.assertEqual(self.trouve("Paradis", [("PARADIS bande-annonce", "Chaîne quelconque", "2025-05-01T00:00:00Z")], ["PT2M"]), [])

    def test_plusieurs_inconnues(self):  # deux vidéos possibles sur des chaînes inconnues : on s'abstient
        self.assertEqual(self.trouve("Les yeux verts", [("Les yeux verts trailer", "a", "2025-01-01T00:00:00Z"),
                                                        ("Les yeux verts bande-annonce", "b", "2025-01-01T00:00:00Z")],
                                     ["PT2M", "PT2M"]), [])

    def test_quota_quotidien(self):
        memo = {"_youtube": {"jour": "2026-11-02", "n": d.YT_PAR_JOUR}}
        self.assertEqual(d.bande_annonce_youtube("Mille secrets", 2026, api([], []), memo, date(2026, 11, 2)), [])


class LastFm(unittest.TestCase):
    def test_artiste_ici(self):
        os.environ["LASTFM_API_KEY"] = "x"
        f = d.fiche_lastfm("Rabaska", lambda u: {"artist": {"name": "Rabaska", "tags": {"tag": [{"name": "folk"}]},
                                                            "bio": {"content": "Groupe folk de Montréal."}}})
        self.assertTrue(f["ici"])
        self.assertIsNone(d.fiche_lastfm("Rabaska", lambda u: {"artist": {"name": "Autre nom"}}))


if __name__ == "__main__":
    unittest.main()
