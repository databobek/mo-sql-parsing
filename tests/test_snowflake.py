# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

from unittest import TestCase

from mo_parsing.debug import Debugger

from mo_sql_parsing import parse, normal_op


class TestSnowflake(TestCase):
    def test_issue_101_create_temp_table(self):
        sql = """CREATE TEMP TABLE foo(a varchar(10))"""
        result = parse(sql)
        expected = {"create table": {
            "columns": {"name": "a", "type": {"varchar": 10}},
            "name": "foo",
            "temporary": True,
        }}
        self.assertEqual(result, expected)

    def test_issue_101_create_transient_table(self):
        sql = """CREATE TRANSIENT TABLE foo(a varchar(10))"""
        result = parse(sql)
        expected = {"create table": {
            "columns": {"name": "a", "type": {"varchar": 10}},
            "name": "foo",
            "transient": True,
        }}
        self.assertEqual(result, expected)

    def test_issue_102_table_functions1(self):
        sql = """
        SELECT seq4()
        FROM TABLE(generator(rowcount => 10))
        """
        result = parse(sql)
        expected = {
            "from": {"table": {"generator": {}, "rowcount": 10}},
            "select": {"value": {"seq4": {}}},
        }
        self.assertEqual(result, expected)

    def test_issue_102_table_functions2(self):
        sql = """
        SELECT uniform(1, 10, random())
        FROM TABLE(generator(rowcount => 5));
        """
        result = parse(sql)
        expected = {
            "from": {"table": {"generator": {}, "rowcount": 5}},
            "select": {"value": {"uniform": [1, 10, {"random": {}}]}},
        }
        self.assertEqual(result, expected)

    def test_issue_102_table_functions3(self):
        sql = """
        SELECT seq4()
        FROM TABLE(generator(rowcount => 10))
        """
        result = parse(sql, calls=normal_op)
        expected = {
            "from": {
                "op": "table",
                "args": [{"op": "generator", "kwargs": {"rowcount": 10},}],
            },
            "select": {"value": {"op": "seq4"}},
        }
        self.assertEqual(result, expected)

    def test_issue_102_table_functions4(self):
        sql = """
        SELECT uniform(1, 10, random())
        FROM TABLE(generator(rowcount => 5));
        """
        result = parse(sql, calls=normal_op)
        expected = {
            "from": {
                "op": "table",
                "args": [{"op": "generator", "kwargs": {"rowcount": 5},}],
            },
            "select": {"value": {"op": "uniform", "args": [1, 10, {"op": "random"}]}},
        }

        self.assertEqual(result, expected)

    def test_issue_102_table_functions5(self):
        sql = """
        SELECT t.index, t.value
        FROM TABLE(split_to_table('a.b.z.d', '.')) as t
        ORDER BY t.value;
        """
        result = parse(sql)
        expected = {
            "from": {
                "name": "t",
                "value": {"table": {"split_to_table": [
                    {"literal": "a.b.z.d"},
                    {"literal": "."},
                ]}},
            },
            "orderby": {"value": "t.value"},
            "select": [{"value": "t.index"}, {"value": "t.value"}],
        }
        self.assertEqual(result, expected)

    def test_issue_102_within_group(self):
        sql = """
        SELECT listagg(name, ', ' ) WITHIN GROUP (ORDER BY name) AS names
        FROM names_table
        """
        result = parse(sql)
        expected = {
            "from": "names_table",
            "select": {
                "name": "names",
                "value": {"listagg": ["name", {"literal": ", "}]},
                "within": {"orderby": {"value": "name"}},
            },
        }
        self.assertEqual(result, expected)

    def test_issue_105_multiline_strings(self):
        sql = """SELECT 'one
            two
            three'
            FROM my_table"""
        result = parse(sql)
        expected = {
            "from": "my_table",
            "select": {"value": {"literal": "one\n            two\n            three"}},
        }
        self.assertEqual(result, expected)

    def test_issue_104_character_varying1(self):
        sql = """CREATE TABLE foo(a CHARACTER(5))"""
        result = parse(sql)
        expected = {"create table": {
            "columns": {"name": "a", "type": {"character": 5}},
            "name": "foo",
        }}
        self.assertEqual(result, expected)

    def test_issue_104_character_varying2(self):
        sql = """CREATE TABLE foo(a CHARACTER VARYING(5))"""
        result = parse(sql)
        expected = {"create table": {
            "columns": {"name": "a", "type": {"character_varying": 5}},
            "name": "foo",
        }}
        self.assertEqual(result, expected)

    def test_issue_106_index_column_name1(self):
        sql = """SELECT index FROM my_table;"""
        result = parse(sql)
        expected = {"from": "my_table", "select": {"value": "index"}}
        self.assertEqual(result, expected)

    def test_issue_106_index_column_name2(self):
        sql = """CREATE TABLE my_table(index INTEGER);"""
        result = parse(sql)
        expected = {"create table": {
            "columns": {"name": "index", "type": {"integer": {}}},
            "name": "my_table",
        }}
        self.assertEqual(result, expected)

    def test_issue_107_lateral_function(self):
        sql = """SELECT emp.employee_id, emp.last_name, value AS project_name
        FROM employees AS emp, LATERAL flatten(input => emp.project_names) AS proj_names
        ORDER BY employee_id;"""
        result = parse(sql)
        expected = {
            "from": [
                {"name": "emp", "value": "employees"},
                {"lateral": {
                    "name": "proj_names",
                    "value": {"flatten": {}, "input": "emp.project_names"},
                }},
            ],
            "orderby": {"value": "employee_id"},
            "select": [
                {"value": "emp.employee_id"},
                {"value": "emp.last_name"},
                {"name": "project_name", "value": "value"},
            ],
        }
        self.assertEqual(result, expected)

    def test_issue_108_colon1(self):
        sql = """SELECT src:dealership FROM car_sales"""
        result = parse(sql)
        expected = {
            "from": "car_sales",
            "select": {"value": {"get": ["src", {"literal": "dealership"}]}},
        }
        self.assertEqual(result, expected)

    def test_issue_108_colon2(self):
        sql = """SELECT src:salesperson.name FROM car_sales"""
        result = parse(sql)
        expected = {
            "from": "car_sales",
            "select": {"value": {"get": [
                "src",
                {"literal": "salesperson"},
                {"literal": "name"},
            ]}},
        }
        self.assertEqual(result, expected)

    def test_issue_108_colon3(self):
        sql = """SELECT src:['salesperson']['name'] FROM car_sales"""
        result = parse(sql)
        expected = {
            "from": "car_sales",
            "select": {"value": {"get": [
                "src",
                {"literal": "salesperson"},
                {"literal": "name"},
            ]}},
        }
        self.assertEqual(result, expected)

    def test_issue_110_double_quote(self):
        sql = """SELECT REPLACE(foo, '"', '') AS bar FROM my_table"""
        result = parse(sql)
        expected = {
            "from": "my_table",
            "select": {
                "name": "bar",
                "value": {"replace": ["foo", {"literal": '"'}, {"literal": ""}]},
            },
        }
        self.assertEqual(result, expected)

    def test_issue_109_qualify1(self):
        sql = """SELECT id, row_number() OVER (PARTITION BY id ORDER BY id) AS row_num
        FROM my_table
        QUALIFY row_num = 1"""
        result = parse(sql)
        expected = {
            "from": "my_table",
            "qualify": {"eq": ["row_num", 1]},
            "select": [
                {"value": "id"},
                {
                    "name": "row_num",
                    "over": {"orderby": {"value": "id"}, "partitionby": "id"},
                    "value": {"row_number": {}},
                },
            ],
        }

        self.assertEqual(result, expected)

    def test_issue_109_qualify2(self):
        sql = """SELECT id, names
        FROM my_table
        QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY id) = 1"""
        result = parse(sql)
        expected = {
            "from": "my_table",
            "qualify": {"eq": [
                {
                    "over": {"orderby": {"value": "id"}, "partitionby": "id"},
                    "value": {"row_number": {}},
                },
                1,
            ]},
            "select": [{"value": "id"}, {"value": "names"}],
        }
        self.assertEqual(result, expected)

    def test_issue_112_qualify(self):
        sql = """SELECT 
            a
        FROM 
            a
        QUALIFY
            ROW_NUMBER() OVER
            (PARTITION BY ssmu.cak, ssmu.rsd  ORDER BY created_at DESC) = 1"""
        result = parse(sql)
        expected = {
            "from": "a",
            "qualify": {"eq": [
                {
                    "over": {
                        "orderby": {"sort": "desc", "value": "created_at"},
                        "partitionby": ["ssmu.cak", "ssmu.rsd"],
                    },
                    "value": {"row_number": {}},
                },
                1,
            ]},
            "select": {"value": "a"},
        }
        self.assertEqual(result, expected)

    def test_issue_101_ilike(self):
        sql = """SELECT * 
        FROM my_table 
        WHERE subject ILIKE '%j%do%'"""
        result = parse(sql)
        expected = {
            "from": "my_table",
            "select": "*",
            "where": {"ilike": ["subject", {"literal": "%j%do%"}]},
        }
        self.assertEqual(result, expected)

    def test_issue_113_dash_in_identifier(self):
        sql = """SELECT SUM(a-b) AS diff
        FROM my_table"""
        result = parse(sql)
        expected = {
            "from": "my_table",
            "select": {"name": "diff", "value": {"sum": {"sub": ["a", "b"]}}},
        }
        self.assertEqual(result, expected)

    def test_issue_114_pivot(self):
        sql = """SELECT *
          FROM (SELECT * FROM monthly_sales_table) monthly_sales
            PIVOT(SUM(amount) FOR month IN ('JAN', 'FEB', 'MAR', 'APR')) AS p
        """
        result = parse(sql)
        expected = {
            "from": [
                {
                    "name": "monthly_sales",
                    "value": {"select": "*", "from": "monthly_sales_table"},
                },
                {
                    "pivot": {
                        "name": "p",
                        "aggregate": {"sum": "amount"},
                        "for": "month",
                        "in": {"literal": ["JAN", "FEB", "MAR", "APR"]},
                    },
                },
            ],
            "select": "*",
        }

        self.assertEqual(result, expected)

    def test_unpivot(self):
        sql = """SELECT * FROM monthly_sales
        UNPIVOT(sales FOR month IN (jan, feb, mar, april))
        ORDER BY empid;
        """
        result = parse(sql)
        expected = {
            "from": [
                "monthly_sales",
                {"unpivot": {
                    "value": "sales",
                    "for": "month",
                    "in": {"value": ["jan", "feb", "mar", "april"]},
                }},
            ],
            "orderby": {"value": "empid"},
            "select": "*",
        }

        self.assertEqual(result, expected)

    def test_issue_116_select_w_quotes1(self):
        sql = """SELECT src:"sales-person".name
        FROM car_sales"""
        result = parse(sql)
        expected = {
            "from": "car_sales",
            "select": {"value": {"get": [
                "src",
                {"literal": "sales-person"},
                {"literal": "name"},
            ]}},
        }
        self.assertEqual(result, expected)

    def test_issue_116_select_w_quotes2(self):
        sql = """SELECT src:".".name
        FROM car_sales"""
        result = parse(sql)
        expected = {
            "from": "car_sales",
            "select": {"value": {"get": [
                "src",
                {"literal": "."},
                {"literal": "name"},
            ]}},
        }
        self.assertEqual(result, expected)

    def test_issue_118_set1(self):
        sql = """ALTER SESSION SET TIMESTAMP_TYPE_MAPPING = TIMESTAMP_NTZ"""
        result = parse(sql)
        expected = {"set": {"TIMESTAMP_TYPE_MAPPING": "TIMESTAMP_NTZ"}}
        self.assertEqual(result, expected)

    def test_issue_118_set2(self):
        sql = """ALTER SESSION SET LOCK_TIMEOUT = 3600*2"""
        result = parse(sql)
        expected = {"set": {"LOCK_TIMEOUT": {"mul": [3600, 2]}}}
        self.assertEqual(result, expected)

    def test_issue_118_unset(self):
        sql = """ALTER SESSION UNSET LOCK_TIMEOUT"""
        result = parse(sql)
        expected = {"unset": "LOCK_TIMEOUT"}
        self.assertEqual(result, expected)

    def test_issue_121_many_concat(self):
        sql = "SELECT a" + (" || a" * 300)
        result = parse(sql)
        expected = {"select": {"value": {"concat": ["a"] * 301}}}
        self.assertEqual(result, expected)

    def test_issue_119_copy1(self):
        sql = """COPY INTO mytable FROM @my_int_stage"""
        result = parse(sql)
        expected = {"copy": {"from": "@my_int_stage", "into": "mytable"}}
        self.assertEqual(result, expected)

    def test_issue_119_copy2(self):
        sql = """COPY INTO mytable FILE_FORMAT = (TYPE = CSV)"""
        result = parse(sql)
        expected = {"copy": {"file_format": {"type": "CSV"}, "into": "mytable"}}
        self.assertEqual(result, expected)

    def test_issue_119_copy3(self):
        sql = (
            """COPY INTO mytable from @~/staged FILE_FORMAT = (FORMAT_NAME = 'mycsv')"""
        )
        result = parse(sql)
        expected = {"copy": {
            "file_format": {"format_name": {"literal": "mycsv"}},
            "from": "@~/staged",
            "into": "mytable",
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copy4(self):
        sql = """COPY INTO mycsvtable FROM @my_ext_stage/tutorials/dataloading/contacts1.csv;"""
        result = parse(sql)
        expected = {"copy": {
            "from": "@my_ext_stage/tutorials/dataloading/contacts1.csv",
            "into": "mycsvtable",
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copy5(self):
        sql = """COPY INTO mytable
            FROM s3://mybucket/data/files
            STORAGE_INTEGRATION = myint
            ENCRYPTION=(MASTER_KEY = 'eSxX0jzYfIamtnBKOEOwq80Au6NbSgPH5r4BDDwOaO8=')
            FILE_FORMAT = (FORMAT_NAME = my_csv_format);"""
        result = parse(sql)
        expected = {"copy": {
            "encryption": {"master_key": {
                "literal": "eSxX0jzYfIamtnBKOEOwq80Au6NbSgPH5r4BDDwOaO8="
            }},
            "file_format": {"format_name": "my_csv_format"},
            "from": "s3://mybucket/data/files",
            "into": "mytable",
            "storage_integration": "myint",
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copy6(self):
        sql = """COPY INTO mytable
            FROM s3://mybucket/data/files
            CREDENTIALS=(AWS_KEY_ID='$AWS_ACCESS_KEY_ID' AWS_SECRET_KEY='$AWS_SECRET_ACCESS_KEY')
            ENCRYPTION=(MASTER_KEY = 'eSxX0jzYfIamtnBKOEOwq80Au6NbSgPH5r4BDDwOaO8=')
            FILE_FORMAT = (FORMAT_NAME = my_csv_format);"""
        result = parse(sql)
        expected = {"copy": {
            "credentials": {
                "aws_key_id": {"literal": "$AWS_ACCESS_KEY_ID"},
                "aws_secret_key": {"literal": "$AWS_SECRET_ACCESS_KEY"},
            },
            "encryption": {"master_key": {
                "literal": "eSxX0jzYfIamtnBKOEOwq80Au6NbSgPH5r4BDDwOaO8="
            }},
            "file_format": {"format_name": "my_csv_format"},
            "from": "s3://mybucket/data/files",
            "into": "mytable",
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copy7(self):
        sql = """COPY INTO mytable
            FROM 'gcs://mybucket/data/files'
            STORAGE_INTEGRATION = myint
            FILE_FORMAT = (FORMAT_NAME = my_csv_format);"""
        result = parse(sql)
        expected = {"copy": {
            "file_format": {"format_name": "my_csv_format"},
            "from": {"literal": "gcs://mybucket/data/files"},
            "into": "mytable",
            "storage_integration": "myint",
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copy8(self):
        sql = """COPY INTO mytable
            FROM 'azure://myaccount.blob.core.windows.net/data/files'
            STORAGE_INTEGRATION = myint
            ENCRYPTION=(TYPE='AZURE_CSE' MASTER_KEY = 'kPxX0jzYfIamtnJEUTHwq80Au6NbSgPH5r4BDDwOaO8=')
            FILE_FORMAT = (FORMAT_NAME = my_csv_format);"""
        result = parse(sql)
        expected = {"copy": {
            "encryption": {
                "master_key": {
                    "literal": "kPxX0jzYfIamtnJEUTHwq80Au6NbSgPH5r4BDDwOaO8="
                },
                "type": {"literal": "AZURE_CSE"},
            },
            "file_format": {"format_name": "my_csv_format"},
            "from": {"literal": "azure://myaccount.blob.core.windows.net/data/files"},
            "into": "mytable",
            "storage_integration": "myint",
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copy9(self):
        sql = """COPY INTO mytable
            FROM 'azure://myaccount.blob.core.windows.net/mycontainer/data/files'
            CREDENTIALS=(AZURE_SAS_TOKEN='?sv=2016-05-31&ss=b&srt=sco&sp=rwdl&se=2018-06-27T10:05:50Z&st=2017-06-27T02:05:50Z&spr=https,http&sig=bgqQwoXwxzuD2GJfagRg7VOS8hzNr3QLT7rhS8OFRLQ%3D')
            ENCRYPTION=(TYPE='AZURE_CSE' MASTER_KEY = 'kPxX0jzYfIamtnJEUTHwq80Au6NbSgPH5r4BDDwOaO8=')
            FILE_FORMAT = (FORMAT_NAME = my_csv_format);"""
        result = parse(sql)
        expected = {"copy": {
            "credentials": {"azure_sas_token": {
                "literal": "?sv=2016-05-31&ss=b&srt=sco&sp=rwdl&se=2018-06-27T10:05:50Z&st=2017-06-27T02:05:50Z&spr=https,http&sig=bgqQwoXwxzuD2GJfagRg7VOS8hzNr3QLT7rhS8OFRLQ%3D"
            }},
            "encryption": {
                "master_key": {
                    "literal": "kPxX0jzYfIamtnJEUTHwq80Au6NbSgPH5r4BDDwOaO8="
                },
                "type": {"literal": "AZURE_CSE"},
            },
            "file_format": {"format_name": "my_csv_format"},
            "from": {
                "literal": (
                    "azure://myaccount.blob.core.windows.net/mycontainer/data/files"
                )
            },
            "into": "mytable",
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copyA(self):
        sql = """COPY INTO mytable
            FILE_FORMAT = (TYPE = 'CSV')
            PATTERN='.*/.*/.*[.]csv[.]gz';"""
        result = parse(sql)
        expected = {"copy": {
            "file_format": {"type": {"literal": "CSV"}},
            "into": "mytable",
            "pattern": {"literal": ".*/.*/.*[.]csv[.]gz"},
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copyB(self):
        sql = """COPY INTO mytable
            FILE_FORMAT = (FORMAT_NAME = myformat)
            PATTERN='.*sales.*[.]csv';"""
        result = parse(sql)
        expected = {"copy": {
            "file_format": {"format_name": "myformat"},
            "into": "mytable",
            "pattern": {"literal": ".*sales.*[.]csv"},
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copyC(self):
        sql = """COPY INTO load1 FROM @%load1/data1/
            FILES=('test1.csv', 'test2.csv');"""

        result = parse(sql)
        expected = {"copy": {
            "from": "@%load1/data1/",
            "into": "load1",
            "files": {"literal": ["test1.csv", "test2.csv"]},
        }}
        self.assertEqual(result, expected)

    def test_issue_119_copyD(self):
        sql = """COPY INTO load1 FROM @%load1/data1/
            FILES=('test1.csv', 'test2.csv')
            FORCE=TRUE;"""
        result = parse(sql)
        expected = {"copy": {
            "files": {"literal": ["test1.csv", "test2.csv"]},
            "force": True,
            "from": "@%load1/data1/",
            "into": "load1",
        }}
        self.assertEqual(result, expected)
