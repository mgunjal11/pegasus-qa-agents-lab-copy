#!/usr/bin/env python3
"""HTML helpers for msc-dev-code-and-qa-test-coverage-validator reports (facade)."""

from __future__ import annotations

import report_helpers.common as _common
import report_helpers.sections as _sections
import report_helpers.ui as _ui
from report_helpers.common import *  # noqa: F403
from report_helpers.sections import *  # noqa: F403
from report_helpers.ui import *  # noqa: F403

# `import *` skips leading-underscore names; tests and scripts import these from here.
for _mod in (_common, _sections, _ui):
    for _name in dir(_mod):
        if _name.startswith("_") and not _name.startswith("__"):
            globals()[_name] = getattr(_mod, _name)
