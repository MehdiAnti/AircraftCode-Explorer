"""Tests for CSV export and selectable search sorting."""

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aircraft_explorer.cli import main
from aircraft_explorer.csv_export import write_csv
from aircraft_explorer.core import search_aircraft


class CsvExportTests(unittest.TestCase):
    def test_csv_includes_extra_fields_and_preserves_missing_values(self):
        records = [
            {
                "icao_type_designator": "C172",
                "model": "Cessna, 172",
                "manufacturer": "Cessna",
                "description": None,
                "extra_source_field": {"verified": True},
            },
            {"model": 'Model with "quotes"', "manufacturer": "Piper"},
        ]
        output = io.StringIO(newline="")
        write_csv(records, output)
        output.seek(0)
        rows = list(csv.DictReader(output))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["model"], "Cessna, 172")
        self.assertEqual(rows[1]["model"], 'Model with "quotes"')
        self.assertEqual(rows[0]["description"], "")
        self.assertEqual(json.loads(rows[0]["extra_source_field"]), {"verified": True})
        self.assertEqual(rows[1]["icao_type_designator"], "")

    def test_empty_catalog_still_writes_headers(self):
        output = io.StringIO(newline="")
        write_csv([], output)
        self.assertIn("icao_type_designator", output.getvalue().splitlines()[0])

    def test_cli_exports_to_file(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "aircraft.json"
            output_path = Path(directory) / "aircraft.csv"
            data_path.write_text(
                json.dumps([{"model": "Test aircraft", "manufacturer": "Maker"}]),
                encoding="utf-8",
            )
            result = main(["--data", str(data_path), "export", "--output", str(output_path)])
            self.assertEqual(result, 0)
            with output_path.open(encoding="utf-8", newline="") as output:
                rows = list(csv.DictReader(output))
            self.assertEqual(rows[0]["model"], "Test aircraft")

    def test_cli_exports_to_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "aircraft.json"
            data_path.write_text("[]", encoding="utf-8")
            output = io.StringIO()
            with patch("sys.stdout", output):
                result = main(["--data", str(data_path), "export"])
            self.assertEqual(result, 0)
            self.assertIn("icao_type_designator", output.getvalue())


class SortingTests(unittest.TestCase):
    def setUp(self):
        self.aircraft = [
            {"model": "Zulu", "manufacturer": "Maker B", "icao_type_designator": "Z001"},
            {"model": "Alpha", "manufacturer": "Maker A", "icao_type_designator": "A001"},
            {"model": "No code", "manufacturer": "Maker C"},
        ]

    def test_sort_by_model(self):
        results = search_aircraft(self.aircraft, sort_by="model")
        self.assertEqual([item["model"] for item in results], ["Alpha", "No code", "Zulu"])

    def test_descending_sort_keeps_missing_values_last(self):
        results = search_aircraft(self.aircraft, sort_by="icao", descending=True)
        self.assertEqual(
            [item.get("icao_type_designator") for item in results], ["Z001", "A001", None]
        )

    def test_invalid_sort_field_raises_value_error(self):
        with self.assertRaises(ValueError):
            search_aircraft(self.aircraft, sort_by="unknown")

    def test_cli_sort_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "aircraft.json"
            data_path.write_text(json.dumps(self.aircraft), encoding="utf-8")
            output = io.StringIO()
            with patch("sys.stdout", output):
                result = main([
                    "--data", str(data_path), "search", "--sort-by", "model", "--json"
                ])
            self.assertEqual(result, 0)
            items = json.loads(output.getvalue())
            self.assertEqual([item["model"] for item in items], ["Alpha", "No code", "Zulu"])


if __name__ == "__main__":
    unittest.main()
