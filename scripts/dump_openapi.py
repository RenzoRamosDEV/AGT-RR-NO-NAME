"""Regenera docs/openapi.json (snapshot del contrato). Uso: just openapi"""

import json
from pathlib import Path

from tests.fakes.api import build_fake_api

target = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
target.write_text(json.dumps(build_fake_api().app.openapi(), indent=2, sort_keys=True) + "\n")
print(f"escrito {target}")
