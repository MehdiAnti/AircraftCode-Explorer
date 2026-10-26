"""Tests for independent aircraft record verification."""

import unittest

from aircraft_explorer.ingestion import verification_issues, verified_records


class VerificationTests(unittest.TestCase):
    def evidence(self, source="FAA", url="https://www.faa.gov/example"):
        return {
            "source_name": source,
            "source_url": url,
            "retrieved_at": "2026-10-26T12:00:00Z",
        }

    def test_opensky_only_evidence_is_not_enough(self):
        record = {
            "verification_status": "verified",
            "model": "Example model",
            "field_evidence": {
                "model": [self.evidence("OpenSky Aircraft Metadata", "https://opensky-network.org/data/aircraft")]
            },
        }
        self.assertTrue(any("independent evidence" in issue for issue in verification_issues(record)))

    def test_missing_designator_is_allowed_when_other_fields_are_verified(self):
        record = {
            "source": "OpenSky Aircraft Metadata",
            "source_id": None,
            "verification_status": "verified",
            "model": "Example model",
            "manufacturer": "Example maker",
            "field_evidence": {
                "model": [self.evidence()],
                "manufacturer": [self.evidence(url="https://manufacturer.example/models")],
            },
        }
        self.assertEqual(verification_issues(record), [])
        accepted, rejected = verified_records([record])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, [])
        self.assertNotIn("icao_type_designator", accepted[0])

    def test_unverified_designator_blocks_verification(self):
        record = {
            "verification_status": "verified",
            "model": "Example model",
            "icao_type_designator": "EXMP",
            "field_evidence": {
                "model": [self.evidence()],
                "icao_type_designator": [self.evidence("OpenSky Aircraft Metadata", "https://opensky-network.org/data/aircraft")],
            },
        }
        self.assertTrue(any("icao_type_designator needs independent" in issue for issue in verification_issues(record)))

    def test_invalid_url_or_timestamp_is_rejected(self):
        record = {
            "verification_status": "verified",
            "model": "Example model",
            "field_evidence": {
                "model": [{
                    "source_name": "FAA",
                    "source_url": "http://www.faa.gov/example",
                    "retrieved_at": "not-a-date",
                }]
            },
        }
        self.assertTrue(verification_issues(record))

    def test_rejects_missing_verification_status(self):
        accepted, rejected = verified_records([{"model": "Example model"}])
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), 1)


if __name__ == "__main__":
    unittest.main()
