import unittest
from unittest.mock import Mock
import pytest
from pynonymizer.fake import FakeDataType
from pynonymizer.database.exceptions import UnsupportedColumnStrategyError
from pynonymizer.strategy.table import UpdateColumnsTableStrategy
from pynonymizer.strategy.update_column import (
    FakeUpdateColumnStrategy,
    EmptyUpdateColumnStrategy,
    UniqueLoginUpdateColumnStrategy,
    UniqueEmailUpdateColumnStrategy,
    LiteralUpdateColumnStrategy,
)
import pynonymizer.database.postgres.query_factory as query_factory

"""
These tests are brittle and based on the actual SQL generatedColumnStrategyTypes.
The sentiment is to test the 'meaning' of the SQL, rather than the actual formatting, so it may be prudent to replace
these tests with some form of parsing or pattern matching.

The general idea, however, is that by keeping the queryfactory separate from the provider, it will not change often,
and the sql returned should be very stable.
"""


def test_get_truncate_table(simple_strategy_trunc):
    assert (
        query_factory.get_truncate_table(simple_strategy_trunc)
        == 'TRUNCATE TABLE "truncate_table" CASCADE;'
    )


# deletes are identical to truncates because postgres has cascading truncs
def test_get_delete_table(simple_strategy_delete):
    assert (
        query_factory.get_delete_table(simple_strategy_delete)
        == 'TRUNCATE TABLE "delete_table" CASCADE;'
    )


def test_get_schema_truncate_table(simple_strategy_schema_trunc):
    assert (
        query_factory.get_truncate_table(simple_strategy_schema_trunc)
        == 'TRUNCATE TABLE "schema"."truncate_schema_table" CASCADE;'
    )


def test_get_drop_seed_table():
    assert (
        query_factory.get_drop_seed_table("seed_table")
        == "DROP TABLE IF EXISTS seed_table;"
    )


def test_get_create_database():
    assert (
        query_factory.get_create_database("test_database")
        == "CREATE DATABASE test_database;"
    )


def test_get_drop_database():
    assert query_factory.get_drop_database("test_database") == [
        "SELECT pid, pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'test_database' AND pid != pg_backend_pid();",
        "DROP DATABASE IF EXISTS test_database;",
    ]


def test_get_dumpsize_estimate():
    assert query_factory.get_dumpsize_estimate("test") == "SELECT 1;"


@pytest.fixture
def str_fake_column_generator():
    return Mock(
        get_data_type=Mock(return_value=FakeDataType.STRING),
        get_value=Mock(return_value="test_value"),
    )


@pytest.fixture
def int_fake_column_generator():
    return Mock(
        get_data_type=Mock(return_value=FakeDataType.INT),
        get_value=Mock(return_value=645),
    )


@pytest.fixture
def uuid_fake_column_generator():
    return Mock(
        get_data_type=Mock(return_value=FakeDataType.STRING),
        get_value=Mock(return_value="d4b7d972-99c9-4c0f-83c0-4cf2c63fd6ed"),
    )


@pytest.fixture
def fake_update_column_str_first_name(str_fake_column_generator):
    return FakeUpdateColumnStrategy(
        "test_column1", str_fake_column_generator, "first_name"
    )


@pytest.fixture
def fake_update_column_int_last_name(int_fake_column_generator):
    return FakeUpdateColumnStrategy(
        "test_column2", int_fake_column_generator, "last_name"
    )


@pytest.fixture
def fake_update_column_uuid_user_id(uuid_fake_column_generator):
    return FakeUpdateColumnStrategy(
        "test_column7", uuid_fake_column_generator, "user_id", sql_type="UUID"
    )


@pytest.fixture
def empty_strategy():
    return EmptyUpdateColumnStrategy("test_column3")


@pytest.fixture
def ulogin_strategy():
    return UniqueLoginUpdateColumnStrategy("test_column4")


@pytest.fixture
def uemail_strategy():
    return UniqueEmailUpdateColumnStrategy("test_column5")


@pytest.fixture
def literal_strategy():
    return LiteralUpdateColumnStrategy("test_column6", value="RANDOM()")


@pytest.fixture
def database_strategy():
    pass


@pytest.fixture
def qualifier_column_map(
    fake_update_column_str_first_name,
    fake_update_column_int_last_name,
    empty_strategy,
    ulogin_strategy,
    uemail_strategy,
    literal_strategy,
):
    return {
        "first_name": fake_update_column_str_first_name,
        "last_name": fake_update_column_int_last_name,
        "first_name_test_arg_5": fake_update_column_str_first_name,
    }


@pytest.fixture
def column_strategy_list(
    fake_update_column_str_first_name,
    fake_update_column_int_last_name,
    fake_update_column_uuid_user_id,
    empty_strategy,
    ulogin_strategy,
    uemail_strategy,
    literal_strategy,
):
    return [
        fake_update_column_str_first_name,
        fake_update_column_int_last_name,
        fake_update_column_uuid_user_id,
        empty_strategy,
        ulogin_strategy,
        uemail_strategy,
        literal_strategy,
    ]


@pytest.fixture
def update_table_strategy(column_strategy_list):
    return UpdateColumnsTableStrategy("table_name", column_strategy_list)


@pytest.fixture
def update_table_strategy_unknown(unsupported_column_strategy):
    return UpdateColumnsTableStrategy("invalid_table", [unsupported_column_strategy])


@pytest.fixture
def unsupported_column_strategy():
    column = UniqueLoginUpdateColumnStrategy("column_name")
    column.strategy_type = "NOT_SUPPORTED"

    return column


def test_get_insert_seed_row(qualifier_column_map):
    insert_seed_row = query_factory.get_insert_seed_row(
        "seed_table", qualifier_column_map
    )

    assert (
        insert_seed_row
        == 'INSERT INTO "seed_table" (first_name,last_name,first_name_test_arg_5) '
        "VALUES ('test_value',645,'test_value');"
    )


def test_get_create_seed_table(qualifier_column_map):
    assert (
        query_factory.get_create_seed_table("seed_table", qualifier_column_map)
        == 'CREATE TABLE "seed_table" (_id SERIAL NOT NULL PRIMARY KEY,first_name VARCHAR(65535),last_name INT,first_name_test_arg_5 VARCHAR(65535));'
    )


def test_get_create_seed_table_no_columns():
    """
    get_create_seed_table should error when presented with no columns
    """
    with pytest.raises(ValueError) as e_info:
        query_factory.get_create_seed_table("seed_table", {})


def test_get_update_table_unsupported_column_type(update_table_strategy_unknown):
    """
    get_update_table should raise UnsupportedColumnStrategyError if presented with an unsupported column type
    """
    with pytest.raises(UnsupportedColumnStrategyError):
        query_factory.get_update_table("seed_table", update_table_strategy_unknown)


def test_get_update_table_fake_column(column_strategy_list):
    update_table_all = query_factory.get_update_table(
        "seed_table", UpdateColumnsTableStrategy("anon_table", column_strategy_list)
    )

    assert update_table_all == [
        'UPDATE "anon_table" AS "updatetarget" SET '
        '"test_column1" = ( SELECT "first_name" FROM "seed_table" WHERE "_id"=MOD(ABS((\'x\' || MD5(updatetarget::text))::bit(32)::int), (SELECT MAX("_id") FROM "seed_table")) + 1),'
        '"test_column2" = ( SELECT "last_name" FROM "seed_table" WHERE "_id"=MOD(ABS((\'x\' || MD5(updatetarget::text))::bit(32)::int), (SELECT MAX("_id") FROM "seed_table")) + 1),'
        '"test_column7" = ( SELECT "user_id"::UUID FROM "seed_table" WHERE "_id"=MOD(ABS((\'x\' || MD5(updatetarget::text))::bit(32)::int), (SELECT MAX("_id") FROM "seed_table")) + 1),'
        "\"test_column3\" = (''),"
        '"test_column4" = ( SELECT md5(random()::text) ORDER BY MD5("updatetarget"::text) LIMIT 1),'
        "\"test_column5\" = ( SELECT CONCAT(md5(random()::text), '@', md5(random()::text), '.com') ORDER BY MD5(\"updatetarget\"::text) LIMIT 1),"
        '"test_column6" = RANDOM();'
    ]


def test_get_update_table_literal(literal_strategy):

    result_queries = query_factory.get_update_table(
        "seed_table",
        UpdateColumnsTableStrategy(
            "anon_table", [LiteralUpdateColumnStrategy("literal_column", "RANDOM()")]
        ),
    )

    assert result_queries == [
        'UPDATE "anon_table" AS "updatetarget" SET "literal_column" = RANDOM();'
    ]
