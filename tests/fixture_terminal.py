"""Local deterministic child used by PTY integration tests. Never contacts targets."""
import json
import signal
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
if mode == "args":
    print(json.dumps(sys.argv[2:], ensure_ascii=False), flush=True)
elif mode == "burst":
    print("测试输出" * 100000, flush=True)
    print("BURST-END", flush=True)
elif mode == "fail":
    print("LOCAL-FAIL", flush=True)
    raise SystemExit(7)
else:
    if mode == "interrupt":
        def handler(signum, frame):
            print("CTRL-C-RECEIVED", flush=True)
            raise SystemExit(0)
        signal.signal(signal.SIGINT, handler)
    print("等待输入（无换行） [Y/n] ", end="", flush=True)
    line = input()
    print("ANSWER:" + line, flush=True)
    if mode == "wait":
        time.sleep(120)
