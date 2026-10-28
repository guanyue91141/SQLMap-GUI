import ast
from functools import lru_cache
from importlib import metadata, util
import json
from pathlib import Path
import shutil
import subprocess
import sys

from .paths import ROOT
from .zh import DEPENDENCIES, FILE_INPUTS, GROUPS, MULTILINE, TOOLS, TRANSLATIONS


def engine_root():
    spec = util.find_spec("sqlmap")
    if not spec or not spec.origin:
        raise RuntimeError("未安装 sqlmap，请先运行 setup.ps1")
    return Path(spec.origin).parent


@lru_cache(maxsize=1)
def options():
    completed = subprocess.run(
        [sys.executable, "-m", "backend.extract"], cwd=ROOT,
        capture_output=True, encoding="utf-8", check=True, timeout=30,
    )
    items = json.loads(completed.stdout)
    for item in items:
        if item["id"] not in TRANSLATIONS:
            raise RuntimeError(f"参数 {item['flag']} 缺少中文说明，请核对引擎版本")
        item["label"], item["description"] = TRANSLATIONS[item["id"]]
        item["groupLabel"] = GROUPS[item["group"]]
        item["tool"] = item["id"] in TOOLS
        item["file"] = item["id"] in FILE_INPUTS
        item["multiline"] = item["id"] in MULTILINE
        item["dependency"] = DEPENDENCIES.get(item["id"])
        item["repeatable"] = item["id"] == "header"
    return items


@lru_cache(maxsize=1)
def tampers():
    result = []
    for path in sorted((engine_root() / "tamper").glob("*.py")):
        if path.name.startswith("_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        doc = next((ast.get_docstring(n) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "tamper"), "") or ""
        result.append({"name": path.stem, "description": doc.strip().split("\n\n")[0]})
    return result


def environment():
    return {
        "sqlmap": metadata.version("sqlmap"), "expectedVersion": "1.10.10",
        "python": sys.version.split()[0], "pythonPath": sys.executable,
        "terminal": "Windows ConPTY", "platform": sys.platform,
        "optional": {
            "tkinter": util.find_spec("tkinter") is not None,
            "pymysql": util.find_spec("pymysql") is not None,
            "psycopg2": util.find_spec("psycopg2") is not None,
            "metasploit": bool(shutil.which("msfconsole")),
            "tor": bool(shutil.which("tor")),
        },
    }
