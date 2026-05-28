"""Orchestrator: run all dashboard build scripts."""

import subprocess
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent

for script in sorted(ROOT.rglob("build_*.py")):
    if script.name == "build_all.py":
        continue
    print(f"== {script.relative_to(ROOT)} ==")
    subprocess.run(["python", str(script)], check=True)
