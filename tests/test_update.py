"""Tests for the safe catalog update command."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aircraft_explorer.cli import main
from aircraft_explorer.wikidata import WikidataError


SAMPLE_RECORD = {
    "icao_type_designator": "C172",
    "model": "Cessna 172",
    "manufacturer": "Cessna",
    "source": "Wikidata",
    "source_id": "Q123",
    "source_url": "https://www.wikidata.org/wiki/Q123",
    "source_retrieved_at": "2026-01-02T03:04:05+00:00",
}


class UpdateCommandTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "aircraft.json"
        self.original = [{"model": "Existing catalog record", "manufacturer": "Existing"}]
        self.path.write_text(json.dumps(self.original), encoding="utf-8")

    @patch("aircraft_explorer.cli.fetch_wikidata_aircraft")
    def test_successfully_replaces_catalog(self, fetch):
        fetch.return_value = [SAMPLE_RECORD]
        code = main(["--data", str(self.path), "update"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), [SAMPLE_RECORD])

    @patch("aircraft_explorer.cli.fetch_wikidata_aircraft")
    def test_network_failure_preserves_existing_catalog(self, fetch):
        fetch.side_effect = WikidataError("offline")
        before = self.path.read_bytes()
        code = main(["--data", str(self.path), "update"])
        self.assertEqual(code, 2)
        self.assertEqual(self.path.read_bytes(), before)

    @patch("aircraft_explorer.cli.fetch_wikidata_aircraft")
    def test_empty_response_preserves_existing_catalog_by_default(self, fetch):
        fetch.return_value = []
        before = self.path.read_bytes()
        code = main(["--data", str(self.path), "update"])
        self.assertEqual(code, 2)
        self.assertEqual(self.path.read_bytes(), before)

    @patch("aircraft_explorer.cli.fetch_wikidata_aircraft")
    def test_allow_empty_explicitly_replaces_catalog(self, fetch):
        fetch.return_value = []
        code = main(["--data", str(self.path), "update", "--allow-empty"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), [])

    @patch("aircraft_explorer.cli.fetch_wikidata_aircraft")
    def test_update_passes_timeout_and_retries(self, fetch):
        fetch.return_value = [SAMPLE_RECORD]
        code = main(["--data", str(self.path), "update", "--timeout", "7", "--retries", "2"])
        self.assertEqual(code, 0)
        fetch.assert_called_once_with(timeout=7.0, retries=2, diagnostics=[])


if __name__ == "__main__":
    unittest.main()
