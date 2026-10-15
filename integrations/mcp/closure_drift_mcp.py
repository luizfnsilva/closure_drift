#!/usr/bin/env python3
"""Launcher kept for configurations written for 1.1.1. The server is closure_drift_mcp.py at the
root of the repository, installed as `closure-drift-mcp`."""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "closure_drift_mcp.py"),
               run_name="__main__")
