import unittest
import json
import os
import tests.mocked_responses as mocks

from pathlib import Path
from tests import TestConnection, TestCursor
from etl_manager.extract_metadata import (
    get_table_names,
    create_json_for_database,
    create_json_for_tables,
    get_table_meta,
    get_primary_key_fields,
    get_partitions,
    get_subpartitions,
)

test_path = Path("./tests/data/test_metadata")


class TestMetadata(unittest.TestCase):
    def test_get_table_names(self):
        """Checks that table names are pulled out of
        their tuples and listed with original capitalisation
        """
        result = get_table_names("TEST_DB", TestConnection([mocks.table_names]))
        self.assertEqual(result, ["TEST_TABLE1", "TEST_TABLE2", "SYS_TABLE"])

    def test_create_json_for_database(self):
        """Tests json file is created with correct content
        """
        try:
            create_json_for_database(
                "This is a database",
                "test_database",
                "bucket-name",
                "hmpps/delius/DELIUS_APP_SCHEMA",
                test_path,
            )
            with open(test_path / "database.json", "r") as f:
                output = json.load(f)
        finally:
            os.remove(test_path / "database.json")

        with open(test_path / "database_expected.json", "r") as f:
            expected = json.load(f)

        self.assertEqual(output, expected)

    def test_create_json_for_tables(self):
        """Tests that the correct json is created for multiple tables
        """
        # List of query responses; empty dicts are for primary key & partition queries
        responses = [mocks.first_table, {}, {}, mocks.second_table, {}, {}]
        try:
            create_json_for_tables(
                tables=["TEST_TABLE1", "TEST_TABLE2"],
                database="TEST_DB",
                location=test_path,
                include_op_column=True,
                include_derived_columns=False,
                include_objects=False,
                connection=TestConnection(responses),
            )
            with open(test_path / "test_table1.json", "r") as f:
                output1 = json.load(f)
            with open(test_path / "test_table2.json", "r") as f:
                output2 = json.load(f)

        finally:
            os.remove(test_path / "test_table1.json")
            os.remove(test_path / "test_table2.json")

        with open(test_path / "table1_expected.json", "r") as f:
            expected1 = json.load(f)
        with open(test_path / "table2_expected.json", "r") as f:
            expected2 = json.load(f)

        self.assertEqual(output1, expected1)
        self.assertEqual(output2, expected2)

    def test_get_table_meta(self):
        """Tests option flags, document_history tables and data type conversion
        Partitions and primary key fields tested separately

        This function receives a cursor that's already had .execute run
        This means it should already have a description and data if needed

        That's why TestCursors used here are initialised with the description parameter
        """
        # All flag parameters set to False
        output_no_flags = get_table_meta(
            TestCursor(description=mocks.first_table["desc"]),
            table="TEST_TABLE1",
            include_op_column=False,
            include_derived_columns=False,
            include_objects=False,
        )
        columns_no_flags = [
            {
                "name": "test_number",
                "type": "decimal(38,0)",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_id",
                "type": "decimal(0,-127)",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_date",
                "type": "datetime",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_varchar",
                "type": "character",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_flag",
                "type": "character",
                "description": "",
                "nullable": True,
            },
        ]
        expected_no_flags = {
            "$schema": (
                "https://moj-analytical-services.github.io/metadata_schema/table/"
                "v1.1.0.json"
            ),
            "name": "test_table1",
            "description": "",
            "data_format": "parquet",
            "columns": columns_no_flags,
            "location": "TEST_TABLE1/",
            "partitions": None,
            "primary_key_fields": None,
        }

        # All parameter flags set to True
        output_all_flags = get_table_meta(
            TestCursor(description=mocks.first_table["desc"]),
            table="TEST_TABLE1",
            include_op_column=True,
            include_derived_columns=True,
            include_objects=True,
        )
        columns_all_flags = [
            {
                "name": "op",
                "type": "character",
                "description": "Type of change, for rows added by ongoing replication.",
                "nullable": True,
                "enum": ["I", "U", "D"],
            },
            {
                "name": "test_number",
                "type": "decimal(38,0)",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_id",
                "type": "decimal(0,-127)",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_date",
                "type": "datetime",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_varchar",
                "type": "character",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_flag",
                "type": "character",
                "description": "",
                "nullable": True,
            },
            {
                "name": "test_object_skip",
                "type": "array<character>",
                "description": "",
                "nullable": True,
            },
            {
                "name": "mojap_extraction_datetime",
                "type": "datetime",
                "description": "",
                "nullable": False,
            },
            {
                "name": "mojap_start_datetime",
                "type": "datetime",
                "description": "",
                "nullable": False,
            },
            {
                "name": "mojap_end_datetime",
                "type": "datetime",
                "description": "",
                "nullable": False,
            },
            {
                "name": "mojap_latest_record",
                "type": "boolean",
                "description": "",
                "nullable": False,
            },
            {
                "name": "mojap_image_tag",
                "type": "character",
                "description": "",
                "nullable": False,
            },
        ]
        expected_all_flags = {
            "$schema": (
                "https://moj-analytical-services.github.io/metadata_schema/table/"
                "v1.1.0.json"
            ),
            "name": "test_table1",
            "description": "",
            "data_format": "parquet",
            "columns": columns_all_flags,
            "location": "TEST_TABLE1/",
            "partitions": None,
            "primary_key_fields": None,
        }

        # DOCUMENT_HISTORY table
        output_doc_history = get_table_meta(
            TestCursor(description=mocks.doc_history["desc"]),
            table="DOCUMENT_HISTORY",
            include_op_column=False,
            include_derived_columns=False,
            include_objects=False,
        )
        columns_doc_history = [
            {
                "name": "test_id",
                "type": "decimal(0,-127)",
                "description": "",
                "nullable": True,
            },
            {
                "name": "mojap_document_path",
                "type": "character",
                "description": "The path to the document",
                "nullable": True,
            },
        ]
        expected_doc_history = {
            "$schema": (
                "https://moj-analytical-services.github.io/metadata_schema/table/"
                "v1.1.0.json"
            ),
            "name": "document_history",
            "description": "",
            "data_format": "parquet",
            "columns": columns_doc_history,
            "location": "DOCUMENT_HISTORY/",
            "partitions": None,
            "primary_key_fields": None,
        }

        self.assertEqual(output_no_flags, expected_no_flags)
        self.assertEqual(output_all_flags, expected_all_flags)
        self.assertEqual(output_doc_history, expected_doc_history)

    def test_get_primary_key_fields(self):
        """Tests that primary key output is formatted correctly
        Doesn't check that the SQL results are right
        """
        output_key = get_primary_key_fields(
            "TEST_TABLE_KEY", TestCursor([mocks.primary_key])
        )
        output_keys = get_primary_key_fields(
            "TEST_TABLE_KEYS", TestCursor([mocks.primary_keys])
        )
        output_no_keys = get_primary_key_fields("TEST_TABLE_NO_KEYS", TestCursor())

        expected_key = ("long_postcode_id",)
        expected_keys = ("long_postcode_id", "team_id")
        expected_no_keys = None

        self.assertEqual(output_key, expected_key)
        self.assertEqual(output_keys, expected_keys)
        self.assertEqual(output_no_keys, expected_no_keys)

    def test_get_partitions(self):
        """Tests that partitions are returned correctly.
        Subpartitions are tested separately.
        """
        output_partition = get_partitions(
            "PARTITION_TEST", TestCursor([mocks.partition])
        )
        output_partitions = get_partitions(
            "PARTITIONS_TEST", TestCursor([mocks.partitions])
        )
        output_no_partitions = get_partitions("NO_PARTITIONS_TEST", TestCursor())

        expected_partition = [
            {"name": "P_ADDITIONAL_IDENTIFIER", "subpartitions": None}
        ]
        expected_partitions = [
            {"name": "P_ADDITIONAL_IDENTIFIER", "subpartitions": None},
            {"name": "P_ADDITIONAL_OFFENCE", "subpartitions": None},
            {"name": "P_ADDITIONAL_SENTENCE", "subpartitions": None},
            {"name": "P_ADDRESS", "subpartitions": None},
            {"name": "P_ADDRESS_ASSESSMENT", "subpartitions": None},
            {"name": "P_ALIAS", "subpartitions": None},
            {"name": "P_APPROVED_PREMISES_REFERRAL", "subpartitions": None},
        ]
        expected_no_partitions = None

        self.assertEqual(output_partition, expected_partition)
        self.assertEqual(output_partitions, expected_partitions)
        self.assertEqual(output_no_partitions, expected_no_partitions)

    def test_get_subpartitions(self):
        output_subpartition = get_subpartitions(
            table="SUBPARTITION_TABLE",
            partition="SUBPARTITION",
            cursor=TestCursor([mocks.subpartition]),
        )
        output_subpartitions = get_subpartitions(
            table="SUBPARTITIONS_TABLE",
            partition="SUBPARTITIONS",
            cursor=TestCursor([mocks.subpartitions]),
        )
        output_no_subpartitions = get_subpartitions(
            table="NO_SUBPARTITIONS_TABLE",
            partition="NO_SUBPARTITIONS",
            cursor=TestCursor(),
        )

        expected_subpartition = ["SUBPARTITION_A"]
        expected_subpartitions = [
            "SUBPARTITION_A",
            "SUBPARTITION_B",
            "SUBPARTITION_C",
            "SUBPARTITION_D",
        ]
        expected_no_subpartitions = []

        self.assertEqual(output_subpartition, expected_subpartition)
        self.assertEqual(output_subpartitions, expected_subpartitions)
        self.assertEqual(output_no_subpartitions, expected_no_subpartitions)
