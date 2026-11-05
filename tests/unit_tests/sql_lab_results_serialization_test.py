# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# pylint: disable=import-outside-toplevel, unused-argument
import math
from unittest import mock

import msgpack
import pytest


def test_msgpack_results_round_trip(app_context: None) -> None:
    """
    Results stored in the results backend with msgpack + Arrow load back intact.

    pyarrow removed ``serialize``/``deserialize``; the payload now uses the
    Arrow IPC stream format.
    """
    from superset.db_engine_specs.base import BaseEngineSpec
    from superset.result_set import SupersetResultSet
    from superset.sql_lab import _serialize_and_expand_data
    from superset.views.utils import _deserialize_results_payload

    result_set = SupersetResultSet(
        [(1, "a", 1.5), (2, "b", None)],
        [("id",), ("name",), ("value",)],
        BaseEngineSpec,
    )
    data, selected_columns, _, _ = _serialize_and_expand_data(
        result_set, BaseEngineSpec, use_msgpack=True
    )
    assert isinstance(data, bytes)

    payload = msgpack.dumps(
        {"data": data, "selected_columns": selected_columns}, use_bin_type=True
    )
    query = mock.MagicMock()
    query.database.db_engine_spec = BaseEngineSpec

    result = _deserialize_results_payload(payload, query, use_msgpack=True)

    first, second = result["data"]
    assert first == {"id": 1, "name": "a", "value": 1.5}
    assert second["id"] == 2 and second["name"] == "b"
    # a NULL float comes back as NaN, as before the pyarrow upgrade
    assert math.isnan(second["value"])
    assert [col["name"] for col in result["columns"]] == ["id", "name", "value"]


def test_msgpack_results_bad_payload_raises(app_context: None) -> None:
    from superset.exceptions import SerializationError
    from superset.views.utils import _deserialize_results_payload

    payload = msgpack.dumps({"data": b"not arrow", "selected_columns": []})
    with pytest.raises(SerializationError):
        _deserialize_results_payload(payload, mock.MagicMock(), use_msgpack=True)
