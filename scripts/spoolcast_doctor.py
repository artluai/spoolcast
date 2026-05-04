#!/usr/bin/env python3
"""Backward-compatible wrapper for scripts/spoolcast_audit.py."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from spoolcast_audit import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
