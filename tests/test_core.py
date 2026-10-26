"""Unit tests for the aircraft catalog core."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aircraft_explorer.core import (
    catalog_stats,
    catalog_status,
    deduplicate_records,
    load_aircraft,
    normalize_record,
    save_aircraft,
    search_aircraft,
)


class LoadAircraftTests(unittest.TestCase):
    def test_normalizes_fields_and_preserves_unknown_fields(self):
        record = normalize_record({
            "icao_type_designator": "  c172  ",
            "model": " Cessna   172 ",
            "description": "   ",
            "custom_source_field": {"id": 12},
        })
        self.assertEqual(record["icao_type_designator"], "C172")
        self.assertEqual(record["model"], "Cessna 172")
        self.assertIsNone(record["description"])
        self.assertEqual(record["custom_source_field"], {"id": 12})

    def test_deduplicates_by_source_id_and_merges_missing_values(self):
        records = deduplicate_records([
            {"source": "OpenSky Aircraft Metadata", "source_id": " Q123 ", "model": "Cessna 172"},
            {"source": "opensky aircraft metadata", "source_id": "q123", "manufacturer": "Cessna"},
        ])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_id"], "Q123")
        self.assertEqual(records[0]["model"], "Cessna 172")
        self.assertEqual(records[0]["manufacturer"], "Cessna")

    def test_fallback_deduplication_requires_complete_identity_fields(self):
        records = deduplicate_records([
            {"icao_type_designator": " c172 ", "model": " 172 Skyhawk ", "manufacturer": "Cessna"},
            {"icao_type_designator": "C172", "model": "172 Skyhawk", "manufacturer": " Cessna "},
            {"model": "Cherokee", "manufacturer": "Piper"},
            {"model": "Cherokee", "manufacturer": "Piper"},
        ])
        self.assertEqual(len(records), 3)

    def test_save_normalizes_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aircraft.json"
            save_aircraft([
                {"icao_type_designator": " c172 ", "model": "Cessna 172", "manufacturer": "Cessna"},
                {"icao_type_designator": "C172", "model": " Cessna   172 ", "manufacturer": " Cessna "},
            ], path)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["icao_type_designator"], "C172")


    def test_loads_json_list(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aircraft.json"
            path.write_text(
                json.dumps([{"model": "Cessna 172", "manufacturer": "Cessna"}]),
                encoding="utf-8",
            )
            self.assertEqual(load_aircraft(path)[0]["model"], "Cessna 172")

    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_aircraft(Path(directory) / "missing.json"), [])

    def test_non_list_top_level_raises_value_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aircraft.json"
            path.write_text('{"model": "Cessna 172"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_aircraft(path)

    def test_non_object_record_raises_value_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aircraft.json"
            path.write_text('["not an object"]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_aircraft(path)

    def test_invalid_field_type_raises_value_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aircraft.json"
            path.write_text('[{"model": 172}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_aircraft(path)


class SearchAircraftTests(unittest.TestCase):
    def setUp(self):
        self.aircraft = [
            {
                "icao_type_designator": "C172",
                "model": "172 Skyhawk",
                "manufacturer": "Cessna",
                "description": "Single-engine piston aircraft",
            },
            {
                "icao_type_designator": "PA28",
                "model": "Cherokee",
                "manufacturer": "Piper",
            },
            {"model": "DA40", "manufacturer": "Diamond Aircraft"},
        ]

    def test_general_search_is_case_insensitive(self):
        results = search_aircraft(self.aircraft, "SKYHAWK")
        self.assertEqual([item["icao_type_designator"] for item in results], ["C172"])

    def test_search_matches_description(self):
        self.assertEqual(len(search_aircraft(self.aircraft, "piston")), 1)

    def test_manufacturer_filter(self):
        results = search_aircraft(self.aircraft, manufacturer="cess")
        self.assertEqual([item["manufacturer"] for item in results], ["Cessna"])

    def test_designator_filter(self):
        results = search_aircraft(self.aircraft, icao_type_designator="pa")
        self.assertEqual([item["model"] for item in results], ["Cherokee"])

    def test_model_filter(self):
        results = search_aircraft(self.aircraft, model="da")
        self.assertEqual([item["model"] for item in results], ["DA40"])

    def test_filters_can_be_combined(self):
        results = search_aircraft(
            self.aircraft,
            "aircraft",
            manufacturer="diamond",
            model="da",
        )
        self.assertEqual([item["manufacturer"] for item in results], ["Diamond Aircraft"])

    def test_records_without_designators_remain_searchable(self):
        results = search_aircraft(self.aircraft, manufacturer="diamond", model="da")
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0].get("icao_type_designator"))

    def test_no_matches_returns_empty_list(self):
        self.assertEqual(search_aircraft(self.aircraft, "not present"), [])


class CatalogStatsTests(unittest.TestCase):
    def test_catalog_statistics(self):
        aircraft = [
            {"icao_type_designator": "C172", "manufacturer": "Cessna"},
            {"icao_type_designator": None, "manufacturer": "Cessna"},
            {"model": "Cherokee", "manufacturer": "Piper"},
            {"model": "Unknown maker"},
        ]
        self.assertEqual(
            catalog_stats(aircraft),
            {
                "aircraft": 4,
                "with_icao_type_designator": 1,
                "manufacturers": 2,
            },
        )

    def test_empty_catalog_statistics(self):
        self.assertEqual(
            catalog_stats([]),
            {
                "aircraft": 0,
                "with_icao_type_designator": 0,
                "manufacturers": 0,
            },
        )


class CatalogStatusTests(unittest.TestCase):
    def test_status_counts_sources_missing_codes_and_timestamps(self):
        aircraft = [
            {
                "icao_type_designator": "C172",
                "manufacturer": "Cessna",
                "source": "OpenSky Aircraft Metadata",
                "source_retrieved_at": "2026-10-25T12:00:00Z",
            },
            {
                "manufacturer": "Cessna",
                "source": "opensky aircraft metadata",
                "source_retrieved_at": "2026-10-26T00:00:00+00:00",
            },
            {"model": "Unknown source and timestamp"},
            {"source": "Other", "source_retrieved_at": "not-a-date"},
        ]
        status = catalog_status(
            aircraft,
            now=datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(status["aircraft"], 4)
        self.assertEqual(status["with_icao_type_designator"], 1)
        self.assertEqual(status["missing_icao_type_designator"], 3)
        self.assertEqual(status["manufacturers"], 1)
        self.assertEqual(status["sources"], {"Other": 1, "Unknown": 1, "OpenSky Aircraft Metadata": 2})
        self.assertEqual(status["with_retrieval_timestamp"], 2)
        self.assertEqual(status["missing_retrieval_timestamp"], 1)
        self.assertEqual(status["invalid_retrieval_timestamp"], 1)
        self.assertEqual(status["oldest_retrieved_at"], "2026-10-25T12:00:00Z")
        self.assertEqual(status["latest_retrieved_at"], "2026-10-26T00:00:00Z")
        self.assertEqual(status["latest_retrieval_age_days"], 0.5)

    def test_status_unknown_freshness_when_no_valid_timestamps(self):
        status = catalog_status([{"model": "No timestamp"}])
        self.assertIsNone(status["latest_retrieved_at"])
        self.assertIsNone(status["latest_retrieval_age_days"])
        self.assertEqual(status["missing_retrieval_timestamp"], 1)

    def test_empty_status(self):
        status = catalog_status([])
        self.assertEqual(status["aircraft"], 0)
        self.assertEqual(status["sources"], {})
        self.assertIsNone(status["latest_retrieved_at"])


if __name__ == "__main__":
    unittest.main()
