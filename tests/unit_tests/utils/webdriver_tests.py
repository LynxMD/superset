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
from typing import Any

from pytest_mock import MockFixture


def test_create_firefox_sets_profile_on_options(
    mocker: MockFixture, app_context: None
) -> None:
    """
    Selenium 4.10 removed the ``firefox_profile`` argument; the profile must be
    set on the options object instead.
    """
    from superset.utils.webdriver import WebDriverProxy

    driver_class = mocker.patch("superset.utils.webdriver.firefox.webdriver.WebDriver")
    WebDriverProxy("firefox").create()

    kwargs: Any = driver_class.call_args.kwargs
    # selenium>=4.10 only accepts ``options``, ``service`` and ``keep_alive``
    assert set(kwargs) <= {"options", "service", "keep_alive"}
    assert kwargs["options"].profile is not None
    assert getattr(kwargs["service"].log_output, "name", None) == "/dev/null"


def test_create_chrome_passes_options(mocker: MockFixture, app_context: None) -> None:
    from superset.utils.webdriver import WebDriverProxy

    driver_class = mocker.patch("superset.utils.webdriver.chrome.webdriver.WebDriver")
    WebDriverProxy("chrome", window=(1024, 768)).create()

    kwargs: Any = driver_class.call_args.kwargs
    assert set(kwargs) <= {"options", "service", "keep_alive"}
    assert "--window-size=1024,768" in kwargs["options"].arguments
    assert driver_class.call_count == 1
