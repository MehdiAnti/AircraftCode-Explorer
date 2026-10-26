"""Tests for catalog review reports."""

import json
import tempfile
import unittest
from pathlib import Path

from aircraft_explorer.review import catalog_review, write_review_report


class CatalogReviewTests(unittest.TestCase):
    def test_counts_states_and_reports_conflicting_codes(self):
        report = catalog_review([
            {"model": "Model A", "manufacturer": "Maker A", "icao_type_designator": "ABCD", "verification_status": "imported_unverified", "source": "OpenSky Aircraft Metadata"},
            {"model": "Model B", "manufacturer": "Maker B", "icao_type_designator": "abcd", "verification_status": "verified", "source": "FAA"},
            {"model": "Model C", "manufacturer": "Maker C", "icao_type_designator": "EFGH", "source": "Other"},
        ])
        self.assertEqual(report["records"], 3)
        self.assertEqual(report["verification_statuses"], {"imported_unverified": 1, "unknown": 1, "verified": 1})
        self.assertEqual(report["conflicting_icao_type_codes"], 1)
        self.assertEqual(report["conflicts"][0]["icao_type_designator"], "ABCD")
        self.assertTrue(report["conflicts"][0]["review_required"])

    def test_normalized_identical_identity_is_not_a_conflict(self):
        report = catalog_review([
            {"model": " Model A ", "manufacturer": "Maker", "icao_type_designator": "ABCD"},
            {"model": "model a", "manufacturer": " maker ", "icao_type_designator": "abcd"},
        ])
        self.assertEqual(report["conflicts"], [])

    def test_writes_json_report(self):
        report = catalog_review([])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reports" / "review.json"
            write_review_report(report, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), report)


if __name__ == "__main__":
    unittest.main()
