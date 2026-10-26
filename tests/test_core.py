"""Unit tests for the aircraft catalog core."""

import json
import tempfile
import unittest
from pathlib import Path

from aircraft_explorer.core import catalog_stats, load_aircraft, search_aircraft


class LoadAircraftTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
