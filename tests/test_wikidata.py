"""Tests for Wikidata response parsing and retry behavior."""

import json
import unittest
from unittest.mock import Mock
from urllib.error import URLError

from aircraft_explorer.wikidata import (
    WikidataError,
    _request_json,
    parse_wikidata_response,
)


def binding(value):
    return {"value": value}


def response_payload():
    return {
        "results": {
            "bindings": [
                {
                    "item": binding("http://www.wikidata.org/entity/Q123"),
                    "itemLabel": binding("Cessna 172"),
                    "itemDescription": binding("single-engine aircraft"),
                    "manufacturer": binding("http://www.wikidata.org/entity/Q432"),
                    "manufacturerLabel": binding("Cessna"),
                    "icao": binding("C172"),
                },
                {
                    "item": binding("http://www.wikidata.org/entity/Q123"),
                    "itemLabel": binding("Cessna 172"),
                    "manufacturerLabel": binding("Cessna"),
                    "icao": binding("C172"),
                },
                {
                    "item": binding("http://www.wikidata.org/entity/Q999"),
                    "itemLabel": binding("Unrelated item"),
                    "icao": binding("not-a-wikidata-id"),
                },
            ]
        }
    }


class ParseWikidataResponseTests(unittest.TestCase):
    def test_parses_records_and_preserves_provenance(self):
        records = parse_wikidata_response(
            response_payload(),
            retrieved_at="2026-01-02T03:04:05+00:00",
        )
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["source"], "Wikidata")
        self.assertEqual(record["source_id"], "Q123")
        self.assertEqual(record["source_url"], "https://www.wikidata.org/wiki/Q123")
        self.assertEqual(record["source_retrieved_at"], "2026-01-02T03:04:05+00:00")
        self.assertEqual(record["icao_type_designator"], "C172")
        self.assertEqual(record["model"], "Cessna 172")
        self.assertEqual(record["manufacturer"], "Cessna")
        self.assertEqual(record["description"], "single-engine aircraft")

    def test_missing_bindings_raises_clear_error(self):
        with self.assertRaises(WikidataError):
            parse_wikidata_response({})

    def test_invalid_bindings_are_ignored(self):
        payload = {
            "results": {
                "bindings": [
                    "bad",
                    {},
                    {"item": binding("https://example.com/X")},
                ]
            }
        }
        self.assertEqual(parse_wikidata_response(payload), [])


class RequestJsonTests(unittest.TestCase):
    def test_retries_transient_url_error_then_succeeds(self):
        payload = json.dumps(response_payload()).encode("utf-8")
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = payload
        opener = Mock(side_effect=[URLError("temporary failure"), response])
        sleeper = Mock()

        result = _request_json(
            retries=1,
            retry_delay=0,
            opener=opener,
            sleep=sleeper,
        )

        self.assertIn("results", result)
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(0)

    def test_stops_after_bounded_retries(self):
        opener = Mock(side_effect=URLError("offline"))
        sleeper = Mock()
        with self.assertRaises(WikidataError):
            _request_json(retries=2, retry_delay=0, opener=opener, sleep=sleeper)
        self.assertEqual(opener.call_count, 3)
        self.assertEqual(sleeper.call_count, 2)

    def test_rejects_non_positive_timeout(self):
        with self.assertRaises(ValueError):
            _request_json(timeout=0)

    def test_rejects_negative_retry_count(self):
        with self.assertRaises(ValueError):
            _request_json(retries=-1)


if __name__ == "__main__":
    unittest.main()
