import json
import sys

from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from backend.app import app
from backend.commands import Configuration
from test_runtime import FIXTURE, done, transcript, wait_for


def test_api_origin_upload_and_download_boundary(isolated):
    with TestClient(app, base_url="http://127.0.0.1:9955") as client:
        assert client.get("/api/catalog").status_code == 200
        assert client.get("/api/run", headers={"host": "evil.example"}).status_code == 400
        assert client.post("/api/run", json={"values": {"showVersion": True}}, headers={"origin": "https://evil.example"}).status_code == 403
        assert client.post("/api/run", json={"values": "broken"}).status_code == 422
        response = client.post("/api/upload", files={"file": ("../中文 请求.txt", b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")})
        assert response.status_code == 200
        assert "uploads" in response.json()["path"]
        config = {"values": {"cookie": "a=1"}, "extra": ""}
        assert client.put("/api/config", json=config).status_code == 200
        assert client.get("/api/config").json() == config
        assert client.post("/api/run", json={"values": {"showVersion": True}}).status_code == 201
        wait_for(lambda: done(app.state.runner))
        files = client.get("/api/results").json()["files"]
        assert any(file["path"] == "terminal.log" for file in files)
        assert client.get("/api/download", params={"root": "run", "path": "terminal.log"}).status_code == 200
        assert client.get("/api/download", params={"root": "run", "path": "../../config.json"}).status_code == 404


def test_websocket_input_ack_replay_and_origin(isolated):
    with TestClient(app, base_url="http://127.0.0.1:9955") as client:
        runner = app.state.runner
        current = runner.start(Configuration(), [sys.executable, "-u", FIXTURE])
        wait_for(lambda: "[Y/n]" in transcript(isolated, runner))
        assert client.post("/api/run", json={"values": {"showVersion": True}}).status_code == 409
        path = f"ws://127.0.0.1:9955/api/terminal/{current['id']}"
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(path, headers={"origin": "https://evil.example"}):
                pass
        with client.websocket_connect(path, headers={"origin": "http://127.0.0.1:9955"}) as ws:
            output = ""
            last = 0
            while "[Y/n]" not in output:
                event = ws.receive_json()
                last = event.get("seq", last)
                if event["type"] == "output":
                    output += event["data"]
                    ws.send_json({"type": "ack", "seq": event["seq"]})
            ws.send_json({"type": "resize", "rows": 30, "cols": 100})
            ws.send_json({"type": "input", "data": "reconnected\r"})
        wait_for(lambda: done(runner))
        with client.websocket_connect(path + f"?after={last}") as ws:
            replay = ""
            while "ANSWER:reconnected" not in replay:
                event = ws.receive_json()
                if event["type"] == "output":
                    assert event["seq"] > last
                    assert event["replay"] is True
                    replay += event["data"]
                    ws.send_json({"type": "ack", "seq": event["seq"]})
        assert "ANSWER:reconnected" in replay
