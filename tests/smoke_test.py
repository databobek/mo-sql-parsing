# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from mo_sql_parsing import parse, normal_op

sql = "select trim(' ' from b+c)"
result = parse(sql, calls=normal_op)
print(result)
print("done")
