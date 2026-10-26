"""Tests for importing local OpenSky aircraft metadata CSV files."""

import tempfile
import unittest
from pathlib import Path

from aircraft_explorer.opensky_import import (
    OPENSKY_SOURCE_URL,
    OpenSkyImportError,
    import_opensky_csv,
    merge_opensky_records,
)


class OpenSkyImportTests(unittest.TestCase):
    def _csv(self, content):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "aircraft.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_collapses_aircraft_rows_to_unique_model_records(self):
        path = self._csv(
            "icao24,registration,manufacturername,model,typecode\n"
            "abc123,N123AB,Cessna,172 Skyhawk,C172\n"
            "def456,N456CD,Cessna,172 Skyhawk,C172\n"
        )
        records, summary = import_opensky_csv(
            path, retrieved_at="2026-10-26T12:00:00+00:00"
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["model"], "172 Skyhawk")
        self.assertEqual(records[0]["manufacturer"], "Cessna")
        self.assertEqual(records[0]["icao_type_designator"], "C172")
        self.assertEqual(records[0]["source_url"], OPENSKY_SOURCE_URL)
        self.assertEqual(records[0]["verification_status"], "imported_unverified")
        self.assertEqual(summary["rows_read"], 2)
        self.assertEqual(summary["unique_records"], 1)

    def test_accepts_model_without_code_and_preserves_unknown_code(self):
        path = self._csv("manufacturer,model,typecode\nPiper,PA-28,\nUnknown,,ZZZZ\n")
        records, summary = import_opensky_csv(path, retrieved_at="2026-10-26T12:00:00Z")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["icao_type_designator"], None)
        self.assertEqual(records[1]["model"], None)
        self.assertEqual(records[1]["icao_type_designator"], "ZZZZ")
        self.assertEqual(summary["conflicting_codes"], 0)

    def test_reports_conflicting_models_for_same_code(self):
        path = self._csv(
            "manufacturer,model,typecode\nCessna,Model A,C172\nPiper,Model B,C172\n"
        )
        records, summary = import_opensky_csv(path)
        self.assertEqual(len(records), 2)
        self.assertEqual(summary["conflicting_codes"], 1)

    def test_rejects_unrecognized_headers(self):
        path = self._csv("registration,owner\nN123AB,Example\n")
        with self.assertRaises(OpenSkyImportError):
            import_opensky_csv(path)

    def test_rejects_empty_csv(self):
        path = self._csv("")
        with self.assertRaises(OpenSkyImportError):
            import_opensky_csv(path)

    def test_merge_adds_new_records_and_tracks_exact_match_provenance(self):
        existing = [{
            "model": "Cessna 172",
            "manufacturer": "Cessna",
            "icao_type_designator": "C172",
            "source": "Curated",
        }]
        imported = [{
            "model": "Cessna 172",
            "manufacturer": "Cessna",
            "icao_type_designator": "C172",
            "source": "OpenSky Aircraft Metadata",
            "source_url": OPENSKY_SOURCE_URL,
            "source_retrieved_at": "2026-10-26T12:00:00Z",
        }, {
            "model": "PA-28",
            "manufacturer": "Piper",
            "icao_type_designator": None,
            "source": "OpenSky Aircraft Metadata",
        }]
        merged, summary = merge_opensky_records(existing, imported)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["source"], "Curated")
        self.assertEqual(merged[0]["source_records"][0]["source"], "OpenSky Aircraft Metadata")
        self.assertEqual(summary, {"added": 1, "enriched": 1})

    def test_does_not_overwrite_conflicting_records(self):
        existing = [{
            "model": "Cessna Model A",
            "manufacturer": "Cessna",
            "icao_type_designator": "C172",
        }]
        imported = [{
            "model": "Piper Model B",
            "manufacturer": "Piper",
            "icao_type_designator": "C172",
        }]
        merged, summary = merge_opensky_records(existing, imported)
        self.assertEqual(len(merged), 2)
        self.assertEqual(summary["added"], 1)


if __name__ == "__main__":
    unittest.main()
