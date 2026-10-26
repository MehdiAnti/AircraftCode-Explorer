"""Tests for local aircraft metadata cross-checking."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from aircraft_explorer.metadata import (
    MetadataError,
    cross_check_candidates,
    load_metadata_csv,
    write_cross_check_report,
)


class MetadataCsvTests(unittest.TestCase):
    def test_reads_common_opensky_style_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.csv"
            path.write_text(
                "icao24,registration,manufacturername,model,typecode\n"
                "abc123,N123AB,Cessna,172 Skyhawk,C172\n",
                encoding="utf-8",
            )
            records = load_metadata_csv(path)
        self.assertEqual(records, [{
            "model": "172 Skyhawk",
            "icao_type_designator": "C172",
        }])

    def test_accepts_type_code_only_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.csv"
            path.write_text("icao_type_designator\nC172\n", encoding="utf-8")
            self.assertEqual(
                load_metadata_csv(path),
                [{"model": None, "icao_type_designator": "C172"}],
            )

    def test_rejects_unrecognized_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.csv"
            path.write_text("registration,owner\nN123AB,Example\n", encoding="utf-8")
            with self.assertRaises(MetadataError):
                load_metadata_csv(path)

    def test_empty_csv_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.csv"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(MetadataError):
                load_metadata_csv(path)


class CrossCheckTests(unittest.TestCase):
    def test_model_and_code_match_is_corroborated_not_verified(self):
        report = cross_check_candidates(
            [{
                "source_id": "Q1",
                "model": "Cessna 172 Skyhawk",
                "icao_type_designator": "C172",
                "candidate_classification": "model_candidate",
            }],
            [{"model": "Cessna-172 Skyhawk", "icao_type_designator": "c172"}],
            metadata_source="sample.csv",
            checked_at="2026-10-26T12:00:00Z",
        )
        result = report["results"][0]
        self.assertEqual(result["status"], "corroborated")
        self.assertEqual(
            result["matched_fields"],
            ["icao_type_designator", "model"],
        )
        self.assertTrue(result["review_required"])
        self.assertNotIn("field_evidence", result)
        self.assertIn("Comparison only", report["note"])

    def test_same_code_with_different_model_is_conflict(self):
        report = cross_check_candidates(
            [{"model": "Cessna 172", "icao_type_designator": "C172"}],
            [{"model": "Cessna 182", "icao_type_designator": "C172"}],
            metadata_source="sample.csv",
        )
        result = report["results"][0]
        self.assertEqual(result["status"], "conflict")
        self.assertIn("model", result["conflicting_fields"])

    def test_no_match_does_not_corroborate(self):
        report = cross_check_candidates(
            [{"model": "Unknown aircraft", "icao_type_designator": "ZZZZ"}],
            [{"model": "Cessna 172", "icao_type_designator": "C172"}],
            metadata_source="sample.csv",
        )
        self.assertEqual(report["results"][0]["status"], "no_match")

    def test_multiple_rows_are_flagged(self):
        report = cross_check_candidates(
            [{"model": "Cessna 172", "icao_type_designator": "C172"}],
            [
                {"model": "Cessna 172", "icao_type_designator": "C172"},
                {"model": "Cessna 172", "icao_type_designator": "C172"},
            ],
            metadata_source="sample.csv",
        )
        self.assertEqual(report["results"][0]["status"], "multiple_matches")

    def test_report_writer_outputs_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            report = cross_check_candidates(
                [], [], metadata_source="sample.csv", checked_at="2026-10-26T12:00:00Z"
            )
            write_cross_check_report(report, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), report)


if __name__ == "__main__":
    unittest.main()
