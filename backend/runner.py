import json
import os
import socket
from pathlib import Path
import threading
import time
from uuid import uuid4

import psutil

from .annotations import Annotator
from .commands import Configuration, build
from .paths import DATA, RUNS, prepare


def save_json(path, value):
    temp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


class Runner:
    """Single owner of the PTY. Browser sockets only tail the on-disk event stream."""
    def __init__(self):
        prepare()
        self.data, self.runs = DATA, RUNS
        self.lock = threading.RLock()
        self.process = None
        self.thread = None
        self.current = None
        self.sequence = 0
        self.stopping = False
        pointer = self.data / "current.json"
        if pointer.exists():
            try:
                self.current = json.loads(pointer.read_text(encoding="utf-8"))
                if self.current["status"] in ("starting", "running", "stopping"):
                    self.current.update(status="interrupted", ended=time.time(), message="服务已重启，上次任务已中断")
                    self.persist()
            except (ValueError, KeyError, OSError):
                self.current = None

    def persist(self):
        save_json(self.data / "current.json", self.current)
        save_json(self.runs / self.current["id"] / "run.json", self.current)

    def snapshot(self):
        with self.lock:
            return dict(self.current) if self.current else None

    def publish(self, event_type, **payload):
        with self.lock:
            self.sequence += 1
            event = {"seq": self.sequence, "type": event_type, **payload}
            with (self.runs / self.current["id"] / "events.jsonl").open("ab") as handle:
                handle.write((json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))

    def start(self, config: Configuration, argv_override=None):
        with self.lock:
            if self.current and self.current["status"] in ("starting", "running", "stopping"):
                raise RuntimeError("已有任务正在运行，请先中断或结束当前任务")
            run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]
            directory = self.runs / run_id
            # Validate before changing the current run.
            command = build(config, directory) if argv_override is None else {
                "argv": argv_override, "command": "本地终端测试夹具", "output": None,
            }
            directory.mkdir(parents=True)
            (directory / "events.jsonl").touch()
            (directory / "terminal.log").touch()
            save_json(directory / "config.json", config.model_dump())
            save_json(self.data / "config.json", config.model_dump())
            self.current = {
                "id": run_id, "status": "starting", "started": time.time(),
                "ended": None, "exitCode": None, "command": command["command"],
                "output": command["output"], "message": "正在启动",
            }
            self.sequence = 0
            self.stopping = False
            self.persist()
            try:
                from winpty import PtyProcess
                env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "TERM": "xterm-256color"}
                self.process = PtyProcess.spawn(command["argv"], cwd=str(directory), env=env, dimensions=(28, 120), backend=0)
                self.current.update(status="running", message="运行中", pid=self.process.pid)
                self.persist()
                self.publish("status", run=self.snapshot())
                self.thread = threading.Thread(target=self._read, args=(self.process, directory), daemon=True)
                self.thread.start()
            except Exception as exc:
                self.current.update(status="failed", ended=time.time(), message=f"启动失败：{exc}")
                self.persist()
                self.publish("status", run=self.snapshot())
                raise RuntimeError(self.current["message"]) from exc
            return self.snapshot()

    def _read(self, process, directory):
        annotator = Annotator()
        error = None
        try:
            with (directory / "terminal.log").open("a", encoding="utf-8", newline="") as transcript:
                while True:
                    try:
                        chunk = process.read(8192)
                    except EOFError:
                        break
                    if not chunk:
                        if not process.isalive():
                            break
                        time.sleep(0.02)
                        continue
                    transcript.write(chunk)
                    transcript.flush()
                    self.publish("output", data=chunk)
                    for note in annotator.feed(chunk):
                        self.publish("annotation", **note)
        except Exception as exc:
            error = str(exc)
        finally:
            with self.lock:
                try:
                    code = process.exitstatus
                except Exception:
                    code = None
                status = "interrupted" if self.stopping else ("finished" if code == 0 and not error else "failed")
                self.current.update(status=status, ended=time.time(), exitCode=code,
                                    message=f"终端异常：{error}" if error else ("已中断" if self.stopping else f"运行结束，退出码 {code}"))
                self.persist()
                self.publish("status", run=self.snapshot())
                self.process = None
            try:
                process.close(force=True)
            except Exception:
                pass

    def write(self, data):
        with self.lock:
            if not self.process or not self.process.isalive():
                raise RuntimeError("当前没有运行中的终端")
            self.process.write(data)

    def resize(self, rows, cols):
        with self.lock:
            if self.process:
                self.process.setwinsize(max(5, min(rows, 200)), max(20, min(cols, 400)))

    def stop(self, force=False):
        with self.lock:
            if not self.process:
                return self.snapshot()
            process = self.process
            self.stopping = True
            self.current.update(status="stopping", message="正在强制结束" if force else "已发送 Ctrl+C，等待引擎响应")
            self.persist()
            self.publish("status", run=self.snapshot())
            if not force:
                process.sendcontrol("c")
                return self.snapshot()
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in reversed(children):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                parent.kill()
                parent.wait(timeout=3)
            except psutil.NoSuchProcess:
                pass
            return self.snapshot()

    def shutdown(self):
        self.stop(force=True)
        with self.lock:
            if self.process:
                try:
                    self.process.fileobj.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        if self.thread:
            self.thread.join(timeout=8)
