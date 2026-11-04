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
"""
Smoke test: every ``superset`` module imports on the current Python and
dependency versions. It catches removed stdlib modules (e.g. ``distutils``,
``imp``) and removed third-party APIs at import time.
"""

import importlib
from pathlib import Path
from typing import List

import pytest

import superset

# Modules that need optional drivers or run code on import
SKIP_PREFIXES = (
    "superset.migrations",  # alembic env, runs on import
    "superset.extensions.metastore_cache",
)


def _modules() -> List[str]:
    """List the modules from the file tree, without importing them."""
    root = Path(superset.__file__).parent
    names = []
    for path in root.rglob("*.py"):
        parts = list(path.relative_to(root.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        name = ".".join(parts)
        if not name.startswith(SKIP_PREFIXES):
            names.append(name)
    return sorted(names)


@pytest.mark.parametrize("module_name", _modules())
def test_module_imports(app_context: None, module_name: str) -> None:
    importlib.import_module(module_name)
