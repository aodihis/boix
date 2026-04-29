import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.detect import detect_onix_version


def test_detects_onix3(onix3_path: str) -> None:
    assert detect_onix_version(onix3_path) in ("3.0", "3.1")


def test_detects_onix21(onix21_path: str) -> None:
    assert detect_onix_version(onix21_path) == "2.1"


def test_detects_release_30_explicitly() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write('<?xml version="1.0"?><ONIXMessage release="3.0">')
        path = f.name
    try:
        assert detect_onix_version(path) == "3.0"
    finally:
        os.unlink(path)


def test_detects_release_31_explicitly() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write('<?xml version="1.0"?><ONIXMessage release="3.1">')
        path = f.name
    try:
        assert detect_onix_version(path) == "3.1"
    finally:
        os.unlink(path)


def test_defaults_to_30_when_no_release() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write('<?xml version="1.0"?><ONIXMessage>')
        path = f.name
    try:
        assert detect_onix_version(path) == "3.0"
    finally:
        os.unlink(path)


def test_reads_only_first_512_bytes() -> None:
    # release="2.1" appears only beyond byte 512 — should default to 3.0
    padding = "x" * 600
    content = f'<?xml version="1.0"?><!-- {padding} --><ONIXMessage release="2.1">'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        result = detect_onix_version(path)
        assert result == "3.0"
    finally:
        os.unlink(path)
