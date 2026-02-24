"""
Test configuration for TaxMantri backend tests.

sys.path is configured so BOTH import styles resolve:
  - 'from agents...'         (test files, using backend/ as root)
  - 'from backend.agents...' (production files, using project root)

This handles pytest being run from either d:/TaxMantri/ or d:/TaxMantri/backend/.
"""
import sys
from pathlib import Path

_backend_dir = Path(__file__).parent.parent        # .../backend/
_project_root = _backend_dir.parent               # .../TaxMantri/

for _path in (_project_root, _backend_dir):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
