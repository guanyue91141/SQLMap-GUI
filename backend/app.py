import asyncio
from contextlib import asynccontextmanager, suppress
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .catalog import environment, options, tampers
from .commands import Configuration, build
from .paths import DATA, FRONTEND, RUNS, UPLOADS, prepare
from .runner import Runner, save_json

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


def origin_allowed(origin, host):
    if not origin:
        return True
    try:
        parsed = urlsplit(origin)
        return parsed.scheme == "http" and parsed.hostname in ALLOWED_HOSTS and parsed.netloc.lower() == host.lower()
    except ValueError:
        return False


@asynccontextmanager
async def lifespan(app):
    app.state.runner = Runner()
    yield
    await asyncio.to_thread(app.state.runner.shutdown)


app = FastAPI(title="sqlmap 中文工作台", lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(ALLOWED_HOSTS))


@app.middleware("http")
async def local_requests(request: Request, call_next):
    if request.url.path.startswith("/api/") and not origin_allowed(request.headers.get("origin"), request.headers.get("host", "")):
        return JSONResponse({"detail": "不允许跨站访问本机接口"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse({"detail": "提交的数据格式不正确，请检查参数内容", "errors": [str(e["loc"]) for e in exc.errors()]}, status_code=422)


@app.get("/api/catalog")
def catalog():
    return {"options": options(), "tampers": tampers(), "environment": environment()}


@app.post("/api/preview")
def preview(config: Configuration):
    try:
        command = build(config)
        return {"command": command["command"], "argv": command["argv"]}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/config")
def get_config():
    path = DATA / "config.json"
    try:
        return Configuration.model_validate_json(path.read_text(encoding="utf-8")).model_dump() if path.exists() else Configuration().model_dump()
    except (ValueError, OSError):
        return Configuration().model_dump()


@app.put("/api/config")
def set_config(config: Configuration):
    prepare()
    save_json(DATA / "config.json", config.model_dump())
    return {"message": "配置已保存到本机"}


@app.get("/api/run")
def current_run():
    return app.state.runner.snapshot()


@app.post("/api/run", status_code=201)
def start_run(config: Configuration):
    try:
        return app.state.runner.start(config)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


class StopRequest(BaseModel):
    force: bool = False


@app.post("/api/run/stop")
def stop_run(body: StopRequest):
    return app.state.runner.stop(body.force)


@app.post("/api/upload")
async def upload(file: UploadFile):
    prepare()
    safe_name = Path((file.filename or "request.txt").replace("\\", "/")).name
    path = UPLOADS / f"{uuid4().hex[:12]}-{safe_name}"
    size = 0
    try:
        with path.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 32 * 1024 * 1024:
                    raise HTTPException(413, "上传文件不能超过 32 MB，大文件请直接填写本机路径")
                handle.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {"path": str(path), "name": safe_name, "size": size}


def run_roots():
    current = app.state.runner.snapshot()
    if not current:
        raise HTTPException(404, "尚无运行结果")
    roots = {"run": RUNS / current["id"]}
    if current.get("output"):
        roots["output"] = Path(current["output"])
    return current, roots


@app.get("/api/results")
def results():
    if not app.state.runner.snapshot():
        return {"files": [], "truncated": False}
    _, roots = run_roots()
    files = []
    seen = set()
    truncated = False
    for key, root in roots.items():
        root = root.resolve()
        if not root.is_dir():
            continue
        for directory, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not Path(directory, d).is_symlink() and not Path(directory, d).is_junction()]
            for name in names:
                path = Path(directory, name)
                try:
                    resolved = path.resolve()
                    if not resolved.is_relative_to(root) or resolved in seen or not resolved.is_file():
                        continue
                    seen.add(resolved)
                    if name == "events.jsonl":
                        continue
                    stat = resolved.stat()
                    files.append({"root": key, "path": str(path.relative_to(root)).replace("\\", "/"), "size": stat.st_size, "modified": stat.st_mtime})
                except OSError:
                    continue
                if len(files) >= 1000:
                    truncated = True
                    break
            if truncated:
                break
        if truncated:
            break
    return {"files": files, "truncated": truncated}


@app.get("/api/download")
def download(root: str, path: str):
    _, roots = run_roots()
    if root not in roots:
        raise HTTPException(404, "结果目录不存在")
    base = roots[root].resolve()
    target = (base / path).resolve()
    if not target.is_relative_to(base) or not target.is_file() or target.name == "events.jsonl":
        raise HTTPException(404, "文件不存在或不在本次运行的结果目录内")
    return FileResponse(target, filename=target.name, media_type="application/octet-stream")


@app.websocket("/api/terminal/{run_id}")
async def terminal(socket: WebSocket, run_id: str):
    if socket.headers.get("host", "").split(":")[0] not in ALLOWED_HOSTS or not origin_allowed(socket.headers.get("origin"), socket.headers.get("host", "")):
        await socket.close(code=1008)
        return
    runner = app.state.runner
    current = runner.snapshot()
    if not current or current["id"] != run_id:
        await socket.close(code=1008)
        return
    await socket.accept()
    ack = asyncio.Event()
    ack_sequence = -1
    try:
        after = max(0, int(socket.query_params.get("after", "0")))
    except ValueError:
        await socket.close(code=1008)
        return

    async def receive():
        nonlocal ack_sequence
        while True:
            message = await socket.receive_json()
            kind = message.get("type")
            if kind == "ack":
                ack_sequence = int(message.get("seq", -1))
                ack.set()
            elif kind == "input":
                data = message.get("data", "")
                if not isinstance(data, str) or len(data) > 65536:
                    await socket.close(code=1009)
                    return
                try:
                    await asyncio.to_thread(runner.write, data)
                except RuntimeError as exc:
                    await socket.send_json({"type": "error", "message": str(exc)})
            elif kind == "resize":
                await asyncio.to_thread(runner.resize, int(message.get("rows", 28)), int(message.get("cols", 120)))

    receiver = asyncio.create_task(receive())
    try:
        path = RUNS / run_id / "events.jsonl"
        with path.open("rb") as handle:
            replay_boundary = path.stat().st_size
            replay_finished = False
            if after == 0 and path.stat().st_size > 1024 * 1024:
                handle.seek(-1024 * 1024, 2)
                handle.readline()
                await socket.send_json({"type": "notice", "message": "终端仅回放最近约 1 MB 输出；完整内容可下载终端日志。"})
            await socket.send_json({"type": "status", "run": current})
            while True:
                if not replay_finished and handle.tell() >= replay_boundary:
                    await socket.send_json({"type": "replay_end"})
                    replay_finished = True
                if receiver.done():
                    receiver.result()
                    break
                position = handle.tell()
                line = handle.readline()
                if not line or not line.endswith(b"\n"):
                    handle.seek(position)
                    latest = runner.snapshot()
                    if latest and latest["id"] != run_id:
                        await socket.close(code=1000)
                        break
                    await asyncio.sleep(0.08)
                    continue
                event = json.loads(line)
                if event["seq"] <= after:
                    continue
                event["replay"] = not replay_finished
                await socket.send_json(event)
                if event["type"] == "output":
                    # Wait for xterm's write callback; slow clients never build unbounded buffers.
                    while ack_sequence < event["seq"]:
                        ack.clear()
                        await asyncio.wait_for(ack.wait(), timeout=30)
    except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError, ValueError, OSError):
        pass
    finally:
        receiver.cancel()
        with suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError, ValueError):
            await receiver


if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
else:
    @app.get("/")
    def missing_frontend():
        return JSONResponse({"detail": "前端尚未构建，请运行 setup.ps1"}, status_code=503)
