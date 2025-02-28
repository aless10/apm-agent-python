#  BSD 3-Clause License
#
#  Copyright (c) 2019, Elasticsearch BV
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  * Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#  FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#  DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import pytest

from elasticapm.instrumentation.packages.dbapi2 import (
    Literal,
    extract_action_from_signature,
    extract_signature,
    scan,
    tokenize,
)


def test_scan_simple():
    sql = "Hello 'Peter Pan' at Disney World"
    tokens = tokenize(sql)
    actual = [t[1] for t in scan(tokens)]
    expected = ["Hello", Literal("'", "Peter Pan"), "at", "Disney", "World"]
    assert actual == expected


def test_scan_with_escape_single_quote():
    sql = "Hello 'Peter\\' Pan' at Disney World"
    tokens = tokenize(sql)
    actual = [t[1] for t in scan(tokens)]
    expected = ["Hello", Literal("'", "Peter' Pan"), "at", "Disney", "World"]
    assert actual == expected


def test_scan_with_escape_slash():
    sql = "Hello 'Peter Pan\\\\' at Disney World"
    tokens = tokenize(sql)
    actual = [t[1] for t in scan(tokens)]
    expected = ["Hello", Literal("'", "Peter Pan\\"), "at", "Disney", "World"]
    assert actual == expected


def test_scan_double_quotes():
    sql = """Hello 'Peter'' Pan''' at Disney World"""
    tokens = tokenize(sql)
    actual = [t[1] for t in scan(tokens)]
    expected = ["Hello", Literal("'", "Peter' Pan'"), "at", "Disney", "World"]
    assert actual == expected


def test_scan_double_quotes_at_end():
    sql = """Hello Peter Pan at Disney 'World'"""
    tokens = tokenize(sql)
    actual = [t[1] for t in scan(tokens)]
    expected = ["Hello", "Peter", "Pan", "at", "Disney", Literal("'", "World")]
    assert actual == expected


@pytest.mark.parametrize("quote", ["$$", "$q$"])
@pytest.mark.parametrize(
    "content",
    [
        "",
        "q",
        "Peter q Pan",
        "Peter $ Pan",
        "Peter $q Pan",
        "Peter q$ Pan",
        "Peter $q q$ $q q$ Pan Peter $q q$ $q q$ Pan",
        "Peter $qq$ Pan",
    ],
)
def test_scan_dollar_quote(quote, content):
    sql = f"Hello {quote}{content}{quote} at Disney World"
    tokens = tokenize(sql)
    actual = [t[1] for t in scan(tokens)]
    expected = ["Hello", Literal(quote, content), "at", "Disney", "World"]
    assert actual == expected


def test_dollar_quote_containing_double_dollar():
    sql = "Hello $q$Peter $$ Pan$q$ at Disney World"
    tokens = tokenize(sql)
    actual = [t[1] for t in scan(tokens)]
    expected = ["Hello", Literal("$q$", "Peter $$ Pan"), "at", "Disney", "World"]
    assert actual == expected


def test_extract_signature_string():
    sql = "Hello 'Peter Pan' at Disney World"
    actual = extract_signature(sql)
    expected = "HELLO"
    assert actual == expected


def test_extract_signature_bytes():
    sql = b"Hello 'Peter Pan' at Disney World"
    actual = extract_signature(sql)
    expected = "HELLO"
    assert actual == expected


@pytest.mark.parametrize(
    ["sql", "expected"],
    [
        (
            "EXEC AdventureWorks2022.dbo.uspGetEmployeeManagers 50;",
            "EXECUTE AdventureWorks2022.dbo.uspGetEmployeeManagers",
        ),
        ("EXECUTE sp_who2", "EXECUTE sp_who2"),
        ("EXEC sp_updatestats @@all_schemas = 'true'", "EXECUTE sp_updatestats"),
        ("CALL get_car_stats_by_year(2017, @number, @min, @avg, @max);", "CALL get_car_stats_by_year()"),
        ("CALL get_car_stats_by_year", "CALL get_car_stats_by_year()"),
        ("CALL get_car_stats_by_year;", "CALL get_car_stats_by_year()"),
        ("CALL get_car_stats_by_year();", "CALL get_car_stats_by_year()"),
    ],
)
def test_extract_signature_for_procedure_call(sql, expected):
    actual = extract_signature(sql)
    assert actual == expected


@pytest.mark.parametrize(
    ["sql", "expected"],
    [
        ("SELECT FROM table", "query"),
        ("EXEC sp_who", "exec"),
        ("EXECUTE sp_updatestats", "exec"),
        ("CALL me_maybe", "exec"),
    ],
)
def test_extract_action_from_signature(sql, expected):
    actual = extract_action_from_signature(sql, "query")
    assert actual == expected
