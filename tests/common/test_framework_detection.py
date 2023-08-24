# Copyright (c) 2023 Intel Corporation
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import importlib
import logging
import re
import unittest
from importlib.machinery import ModuleSpec
from typing import List
from unittest.mock import MagicMock

import pytest

import nncf

SUPPORTED_FRAMEWORKS = nncf._SUPPORTED_FRAMEWORKS  # pylint:disable=protected-access
_REAL_FIND_SPEC = importlib._bootstrap._find_spec  # pylint:disable=protected-access


class FailForModules:
    def __init__(self, mocked_modules: List[str], hidden_modules: List[str]):
        self._mocked_modules = mocked_modules
        self._hidden_modules = hidden_modules

    def __call__(self, fullname, path=None, target=None):
        if fullname in self._hidden_modules:
            return None
        if fullname in self._mocked_modules:
            return ModuleSpec(fullname, loader=MagicMock(), origin="foo/bar")
        return _REAL_FIND_SPEC(fullname, path, target)


@pytest.mark.parametrize("ref_available_frameworks", [["torch"], ["torch", "tensorflow"], ["onnx", "openvino"], []])
def test_frameworks_detected(ref_available_frameworks: List[str], nncf_caplog, mocker):
    unavailable_frameworks = [fw for fw in SUPPORTED_FRAMEWORKS if fw not in ref_available_frameworks]
    failer = FailForModules(ref_available_frameworks, unavailable_frameworks)
    with unittest.mock.patch("importlib.util.find_spec", wraps=failer):
        with nncf_caplog.at_level(logging.INFO):
            importlib.reload(nncf)
            matches = re.search(r"Supported frameworks detected: (.*)", nncf_caplog.text)
            if ref_available_frameworks:
                assert matches is not None
                match_text = matches[0]
                for fw in ref_available_frameworks:
                    assert fw in match_text
                for fw in unavailable_frameworks:
                    assert fw not in match_text
            else:
                assert matches is None
