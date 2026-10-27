"""Tests for local OpenSky CSV importing and merging."""

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from aircraft_explorer.opensky_import import (
    OPENSKY_SOURCE_URL, OpenSkyImportError, import_opensky_csv, merge_opensky_records, write_opensky_registry_shards,
)


class OpenSkyImportTests(unittest.TestCase):
    def make_csv(self, text):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "aircraft.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_groups_aircraft_rows_into_model_record(self):
        path = self.make_csv(
            "icao24,registration,manufacturername,model,typecode\n"
            "abc123,N123AB,Cessna,172 Skyhawk,C172\n"
            "def456,N456CD,Cessna,172 Skyhawk,C172\n"
        )
        records, summary = import_opensky_csv(path, retrieved_at="2026-10-26T12:00:00Z")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["icao_type_designator"], "C172")
        self.assertEqual(records[0]["source_url"], OPENSKY_SOURCE_URL)
        self.assertEqual(records[0]["verification_status"], "imported_unverified")
        self.assertEqual(summary["rows_read"], 2)

    def test_exports_registration_typecode_and_operator_search_shards(self):
        path = self.make_csv(
            "icao24,registration,manufacturericao,manufacturername,model,typecode,serialnumber,operator,operatoricao,owner\n"
            "abc123,N123AB,CESS,Cessna,172 Skyhawk,C172,12345,Example Air,EXA,Example Owner\n"
            "def456,N123CD,CESS,Cessna,172 Skyhawk,C172,67890,Example Air,EXA,Example Owner\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            summary = write_opensky_registry_shards(path, directory, retrieved_at="2026-10-27T06:00:00Z")
            self.assertEqual(summary["registry_records"], 2)
            full_registry_path = Path(directory) / "aircraft-registry.json.gz"
            self.assertEqual(summary["registry_export"], str(full_registry_path))
            self.assertTrue(full_registry_path.exists())
            with gzip.open(full_registry_path, "rt", encoding="utf-8") as file:
                full_registry = json.load(file)
            self.assertEqual(len(full_registry), 2)
            self.assertEqual(full_registry[0]["icao24"], "abc123")
            self.assertEqual(full_registry[0]["registration"], "N123AB")
            self.assertEqual(full_registry[0]["icao_type_designator"], "C172")
            self.assertEqual(full_registry[0]["operator"], "Example Air")
            self.assertEqual(full_registry[1]["icao24"], "def456")
            self.assertEqual(full_registry[1]["registration"], "N123CD")
            self.assertEqual(full_registry[1]["icao_type_designator"], "C172")
            self.assertEqual(full_registry[1]["operator"], "Example Air")
            self.assertEqual(full_registry[0]["owner"], "Example Owner")
            self.assertTrue((Path(directory) / "icao24" / "ab.json.gz").exists())
            self.assertTrue((Path(directory) / "registration" / "n1.json.gz").exists())
            self.assertTrue((Path(directory) / "typecode" / "c1.json.gz").exists())
            self.assertTrue((Path(directory) / "operator" / "ex.json.gz").exists())
            with gzip.open(Path(directory) / "registration" / "n1.json.gz", "rt", encoding="utf-8") as file:
                records = json.load(file)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["registration"], "N123AB")
            self.assertEqual(records[0]["icao_type_designator"], "C172")
            self.assertEqual(records[0]["operator"], "Example Air")
            self.assertEqual(records[0]["serial_number"], "12345")
            self.assertEqual(records[0]["verification_status"], "imported_unverified")

    def test_imports_complete_2024_snapshot_with_quoted_headers_and_values(self):
        path = self.make_csv(
            "'icao24','timestamp','acars','adsb','built','categoryDescription','country','engines','firstFlightDate','firstSeen','icaoAircraftClass','lineNumber','manufacturerIcao','manufacturerName','model','modes','nextReg','operator','operatorCallsign','operatorIata','operatorIcao','owner','prevReg','regUntil','registered','registration','selCal','serialNumber','status','typecode','vdl'\\n"
            "'abc123','2024-05-01T00:00:00Z','yes','yes','1998','Landplane','United States','1','1998-01-01','2020-01-01','L1P','LN-1','CESS','Cessna','172 Skyhawk','S','N456CD','Example Air','EXA','EA','EXA','Example Owner','N123AB','2030-01-01','1998-02-01','N123AB','ABCD','12345','active','C172','yes'\\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            summary = write_opensky_registry_shards(path, directory, retrieved_at="2026-10-27T06:00:00Z")
            with gzip.open(Path(directory) / "aircraft-registry.json.gz", "rt", encoding="utf-8") as file:
                records = json.load(file)
        self.assertEqual(summary["registry_records"], 1)
        record = records[0]
        self.assertEqual(record["icao24"], "abc123")
        self.assertEqual(record["registration"], "N123AB")
        self.assertEqual(record["manufacturer"], "Cessna")
        self.assertEqual(record["manufacturer_icao"], "CESS")
        self.assertEqual(record["icao_type_designator"], "C172")
        self.assertEqual(record["source_timestamp"], "2024-05-01T00:00:00Z")
        self.assertEqual(record["first_seen"], "2020-01-01")
        self.assertEqual(record["next_registration"], "N456CD")
        self.assertEqual(record["previous_registration"], "N123AB")
        self.assertEqual(record["icao_aircraft_class"], "L1P")
        self.assertEqual(record["selcal"], "ABCD")
        self.assertEqual(record["vdl"], "yes")
        self.assertEqual(record["source_url"], OPENSKY_SOURCE_URL)

    def test_preserves_missing_code_and_model(self):
        path = self.make_csv("manufacturer,model,typecode\nPiper,PA-28,\nUnknown,,ZZZZ\n")
        records, _ = import_opensky_csv(path)
        self.assertEqual(records[0]["icao_type_designator"], None)
        self.assertEqual(records[1]["model"], None)
        self.assertEqual(records[1]["icao_type_designator"], "ZZZZ")

    def test_reports_same_code_with_multiple_models(self):
        path = self.make_csv("manufacturer,model,typecode\nCessna,Model A,C172\nPiper,Model B,C172\n")
        _, summary = import_opensky_csv(path)
        self.assertEqual(summary["conflicting_codes"], 1)

    def test_rejects_bad_or_empty_csv(self):
        with self.assertRaises(OpenSkyImportError):
            import_opensky_csv(self.make_csv(""))
        with self.assertRaises(OpenSkyImportError):
            import_opensky_csv(self.make_csv("registration,owner\nN123AB,Example\n"))

    def test_merges_exact_match_and_adds_new_record(self):
        existing = [{"model":"Cessna 172","manufacturer":"Cessna","icao_type_designator":"C172","source":"Curated"}]
        imported = [
            {"model":"Cessna 172","manufacturer":"Cessna","icao_type_designator":"C172",
             "source":"OpenSky Aircraft Metadata","source_url":OPENSKY_SOURCE_URL,
             "source_retrieved_at":"2026-10-26T12:00:00Z"},
            {"model":"PA-28","manufacturer":"Piper","icao_type_designator":None,
             "source":"OpenSky Aircraft Metadata"},
        ]
        merged, summary = merge_opensky_records(existing, imported)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["source"], "Curated")
        self.assertEqual(merged[0]["source_records"][0]["source"], "OpenSky Aircraft Metadata")
        self.assertEqual(summary, {"added": 1, "enriched": 1})

    def test_repeated_import_does_not_duplicate_record_or_provenance(self):
        existing = [{"model": "Cessna 172", "manufacturer": "Cessna", "icao_type_designator": "C172", "source": "OpenSky Aircraft Metadata", "source_url": OPENSKY_SOURCE_URL, "source_retrieved_at": "2026-10-26T12:00:00Z", "verification_status": "imported_unverified"}]
        imported = [{"model": "Cessna 172", "manufacturer": "Cessna", "icao_type_designator": "C172", "source": "OpenSky Aircraft Metadata", "source_url": OPENSKY_SOURCE_URL, "source_retrieved_at": "2026-10-27T12:00:00Z", "verification_status": "imported_unverified"}]
        merged, summary = merge_opensky_records(existing, imported)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source_retrieved_at"], "2026-10-27T12:00:00Z")
        self.assertNotIn("source_records", merged[0])
        self.assertEqual(summary, {"added": 0, "enriched": 1})

    def test_conflicting_record_is_not_overwritten(self):
        existing = [{"model":"Cessna Model A","manufacturer":"Cessna","icao_type_designator":"C172"}]
        imported = [{"model":"Piper Model B","manufacturer":"Piper","icao_type_designator":"C172"}]
        merged, summary = merge_opensky_records(existing, imported)
        self.assertEqual(len(merged), 2)
        self.assertEqual(summary["added"], 1)


if __name__ == "__main__":
    unittest.main()
