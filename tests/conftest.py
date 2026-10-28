import pytest

import backend.app as web
import backend.runner as engine


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    data = tmp_path / ".data"
    runs, uploads = data / "runs", data / "uploads"
    for path in (data, runs, uploads):
        path.mkdir(parents=True, exist_ok=True)
    for module in (web, engine):
        monkeypatch.setattr(module, "DATA", data)
        monkeypatch.setattr(module, "RUNS", runs)
    monkeypatch.setattr(web, "UPLOADS", uploads)
    return data
