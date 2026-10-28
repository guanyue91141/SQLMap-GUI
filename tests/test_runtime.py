import json
from pathlib import Path
import sys
import time

import pytest

from backend.commands import Configuration
from backend.runner import Runner

FIXTURE = str(Path(__file__).with_name("fixture_terminal.py"))


def wait_for(predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("本地终端在超时内未达到预期状态")


def transcript(data, runner):
    return (data / "runs" / runner.snapshot()["id"] / "terminal.log").read_text(encoding="utf-8")


def done(runner):
    return runner.snapshot()["status"] not in ("starting", "running", "stopping")


def test_no_newline_prompt_input_resize_single_owner(isolated):
    runner = Runner()
    try:
        runner.start(Configuration(), [sys.executable, "-u", FIXTURE])
        wait_for(lambda: "[Y/n]" in transcript(isolated, runner))
        with pytest.raises(RuntimeError, match="已有任务"):
            runner.start(Configuration(values={"showVersion": True}))
        runner.resize(35, 100)
        runner.write("中文回答\r")
        wait_for(lambda: done(runner))
        assert "ANSWER:中文回答" in transcript(isolated, runner)
        assert runner.snapshot()["exitCode"] == 0
        events = [json.loads(line) for line in (isolated / "runs" / runner.snapshot()["id"] / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        assert any(event["type"] == "annotation" and event["title"] == "等待回答" for event in events)
    finally:
        runner.shutdown()


@pytest.mark.parametrize("tool,expected", [("showVersion", "1.10.10"), ("advancedHelp", "Target"), ("shell", "sqlmap >")])
def test_real_engine_tools(isolated, tool, expected):
    runner = Runner()
    try:
        runner.start(Configuration(values={tool: True}))
        wait_for(lambda: expected in transcript(isolated, runner))
        if tool == "shell":
            runner.write("help\r")
            wait_for(lambda: "valid example" in transcript(isolated, runner))
            runner.write("exit\r")
        wait_for(lambda: done(runner))
        assert runner.snapshot()["exitCode"] == 0
    finally:
        runner.shutdown()


def test_chinese_arguments_and_large_output(isolated):
    runner = Runner()
    try:
        values = ["E:\\中文 目录\\请求.txt", "引号\"'", "a&b=1", "X-A: 中文\nX-B: 2"]
        runner.start(Configuration(), [sys.executable, "-u", FIXTURE, "args", *values])
        wait_for(lambda: done(runner))
        output = transcript(isolated, runner)
        for value in values:
            assert json.dumps(value, ensure_ascii=False)[1:-1] in output
        runner.start(Configuration(), [sys.executable, "-u", FIXTURE, "burst"])
        wait_for(lambda: done(runner), timeout=30)
        assert "BURST-END" in transcript(isolated, runner)
    finally:
        runner.shutdown()


def test_ctrl_c_force_and_abnormal_exit(isolated):
    runner = Runner()
    try:
        runner.start(Configuration(), [sys.executable, "-u", FIXTURE, "interrupt"])
        wait_for(lambda: "[Y/n]" in transcript(isolated, runner))
        runner.stop()
        wait_for(lambda: done(runner))
        assert runner.snapshot()["status"] == "interrupted"
        assert "CTRL-C-RECEIVED" in transcript(isolated, runner)
        runner.start(Configuration(), [sys.executable, "-u", FIXTURE, "wait"])
        wait_for(lambda: "[Y/n]" in transcript(isolated, runner))
        runner.stop(force=True)
        wait_for(lambda: done(runner))
        assert runner.snapshot()["status"] == "interrupted"
        runner.start(Configuration(), [sys.executable, "-u", FIXTURE, "fail"])
        wait_for(lambda: done(runner))
        assert runner.snapshot()["status"] == "failed"
        assert runner.snapshot()["exitCode"] == 7
    finally:
        runner.shutdown()


def test_restart_marks_previous_run_interrupted(isolated):
    directory = isolated / "runs" / "previous"
    directory.mkdir()
    (isolated / "current.json").write_text(json.dumps({"id": "previous", "status": "running"}), encoding="utf-8")
    assert Runner().snapshot()["status"] == "interrupted"
