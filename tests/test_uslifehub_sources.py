"""Offline checks for the institutions behind US Life Hub event sources."""

import json
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlparse


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "nyc_community_event_sources.json"


class CommunitySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["sources"]
        cls.by_id = {source["id"]: source for source in cls.sources}

    def test_source_ids_are_unique(self):
        self.assertEqual(len(self.sources), len(self.by_id))

    def test_flushing_uses_one_queens_public_library_source(self):
        flushing = [
            source for source in self.sources
            if "flushing" in source["id"].lower()
            and source["parse_module"] in {"parsers.queens_library", "parsers.nypl", "parsers.bpl"}
        ]
        self.assertEqual(["qpl_flushing"], [source["id"] for source in flushing])
        source = flushing[0]
        self.assertEqual("Queens Public Library - Flushing Branch", source["name_en"])
        self.assertEqual("皇后区公共图书馆法拉盛分馆", source["name_zh"])
        self.assertEqual("Queens", source["borough_scope"])
        self.assertEqual("parsers.queens_library", source["parse_module"])
        for url in source["urls"]:
            with self.subTest(url=url):
                self.assertEqual("https", urlparse(url).scheme)
                self.assertEqual("www.queenslibrary.org", urlparse(url).hostname)

    def test_flushing_uses_verified_branch_and_location_filtered_calendar(self):
        # Verified through QPL's official locations directory on 2026-10-09.
        # https://www.queenslibrary.org/about-us/locations
        source = self.by_id["qpl_flushing"]
        self.assertIn("https://www.queenslibrary.org/about-us/locations/flushing", source["urls"])
        self.assertIn(
            "https://www.queenslibrary.org/programs-activities/adult-learners/adult-learning-centers/flushing",
            source["urls"],
        )
        calendars = [url for url in source["urls"] if urlparse(url).path == "/calendar"]
        self.assertEqual(1, len(calendars))
        self.assertEqual(
            ["sm_pSsnVirtua:91400000"],
            parse_qs(urlparse(calendars[0]).query)["searchFilter"],
        )
        self.assertIn("seat availability must be checked", source["notes"])

    def test_false_nypl_flushing_claim_is_absent(self):
        self.assertNotIn("nypl_flushing", self.by_id)
        for source in self.sources:
            with self.subTest(source=source["id"]):
                for url in source["urls"]:
                    if urlparse(url).hostname in {"nypl.org", "www.nypl.org"}:
                        self.assertNotIn("flushing", url.lower())
                description = " ".join(source.get(key, "") for key in ("name_en", "name_zh", "notes"))
                self.assertNotIn("NYPL Flushing", description)
                self.assertNotIn("纽约公共图书馆法拉盛", description)

    def test_other_library_sources_are_preserved(self):
        self.assertEqual("parsers.queens_library", self.by_id["qpl_elmhurst"]["parse_module"])
        self.assertEqual("parsers.bpl", self.by_id["bpl_sunset_park"]["parse_module"])
        self.assertEqual("parsers.rss", self.by_id["bpl_rss"]["parse_module"])
        chatham = self.by_id["nypl_chatham_square"]
        self.assertEqual("parsers.nypl", chatham["parse_module"])
        self.assertIn("https://www.nypl.org/locations/chatham-square", chatham["urls"])


if __name__ == "__main__":
    unittest.main()
