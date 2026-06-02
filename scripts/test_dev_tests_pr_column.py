#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from coverage_report_helpers import (
    dev_tests_by_number_from_caches,
    format_dev_tests_summary,
    render_pr_rows_from_prefetch,
)


def test_format_dev_tests_summary_prioritizes_pytest_modules():
    paths = [
        "conftest.py",
        "tests/samples/foo.json",
        "tests/unit/utils/test_passport_manager.py",
        "tests/unit/qualified_manifest_evaluate_handler/controller/test_incrementals.py",
    ]
    summary = format_dev_tests_summary(paths)
    assert "test_passport_manager.py" in summary
    assert "test_incrementals.py" in summary
    assert summary.index("test_passport_manager") < summary.index("conftest")


def test_dev_tests_by_number_from_prefetch_diff_names():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cache_dir = root / "reports" / ".cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "MSC-X-prefetch.json").write_text(
            json.dumps(
                {
                    "prs": [
                        {
                            "number": 161,
                            "org": "wbd-msc",
                            "repo": "pegasus-pick-genie",
                            "diffNames": [
                                "src/foo.py",
                                "tests/unit/utils/test_passport_manager.py",
                            ],
                            "view": {"state": "MERGED", "title": "Fix"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        by_num = dev_tests_by_number_from_caches("MSC-X", root)
        assert by_num[161] == "test_passport_manager.py"


def test_render_pr_rows_from_prefetch_fills_dev_tests_column():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cache_dir = root / "reports" / ".cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "MSC-Y-prefetch.json").write_text(
            json.dumps(
                {
                    "prs": [
                        {
                            "number": 1,
                            "url": "https://github.com/o/r/pull/1",
                            "org": "o",
                            "repo": "r",
                            "diffNames": ["tests/test_foo.py"],
                            "view": {"state": "open", "title": "T"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        html = render_pr_rows_from_prefetch("MSC-Y", root)
        assert "test_foo.py" in html
        assert "<td>—</td>" not in html or html.count("—") < 2
