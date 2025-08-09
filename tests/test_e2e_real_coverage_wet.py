#!/usr/bin/env python3
import subprocess
import sys


def test_e2e_real_coverage_wet():
    proc = subprocess.run([
        sys.executable,
        "scripts/demo/demo_real_coverage_chat.py",
    ], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert "OK: lint evidence found and completion message includes lint details" in proc.stdout
