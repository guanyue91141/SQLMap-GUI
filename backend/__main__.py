import socket
import sys

import uvicorn


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", 9955))
        except OSError:
            print("端口 9955 已被占用，请关闭已有实例或占用该端口的程序。", file=sys.stderr)
            return 1
    uvicorn.run("backend.app:app", host="127.0.0.1", port=9955, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
