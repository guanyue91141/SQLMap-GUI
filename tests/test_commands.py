import ast
import subprocess
import sys

import pytest

from backend.catalog import engine_root, options, tampers
from backend.commands import Configuration, build, powershell_command


def test_catalog_covers_public_parser_and_help():
    items = options()
    source = ast.parse((engine_root() / "lib/parse/cmdline.py").read_text(encoding="utf-8"))
    public = set()
    for node in ast.walk(source):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
            continue
        help_node = next((k.value for k in node.keywords if k.arg == "help"), None)
        if help_node is None or isinstance(help_node, ast.Name) and help_node.id == "SUPPRESS":
            continue
        public.update(a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("-"))
    expected = (public - {"--hh"}) | {"-hh", "-h", "--help"}
    assert expected == {flag for item in items for flag in item["flags"]}
    assert len({item["id"] for item in items}) == len(items)
    assert all(item["label"] and item["description"] and item["groupLabel"] for item in items)
    assert len({item["group"] for item in items}) == 17
    help_text = subprocess.run([sys.executable, str(engine_root() / "sqlmap.py"), "-hh"], capture_output=True, encoding="utf-8", check=True).stdout
    assert all(group in help_text for group in {item["group"] for item in items} - {"Basic"})
    assert len(tampers()) >= 80


def test_special_values_are_preserved(tmp_path):
    values = {"url": "http://127.0.0.1/x?id=1&name=中文", "cookie": "session=a'b; quoted=\"x\"", "headers": "X-A: 一\nX-B: two", "fileWrite": "E:\\资料\\一个 文件.txt", "verbose": 0, "batch": True}
    result = build(Configuration(values=values), tmp_path)
    assert values["url"] in result["argv"]
    assert values["cookie"] in result["argv"]
    assert values["headers"] in result["argv"]
    assert values["fileWrite"] in result["argv"]
    assert result["argv"][result["argv"].index("-v") + 1] == "0"
    assert "--batch" in result["argv"]
    assert "--output-dir" in result["argv"]
    assert "a''b" in result["command"]


def test_extra_args_paths_headers_and_negative_values():
    result = build(Configuration(values={"url": "http://127.0.0.1"}, extra="--proxy-file 'E:\\资料\\代理 列表.txt' -H 'X-A: 1' -H 'X-B: 2' --delay=0.2"))
    assert "E:\\资料\\代理 列表.txt" in result["argv"]
    assert result["argv"].count("--header") == 2
    assert "--batch" not in result["argv"]


@pytest.mark.parametrize("values,extra", [
    ({"url": "x"}, "-u y"), ({"url": "x"}, "--timeout=1 --timeout=2"),
    ({"url": "x", "header": "X: y"}, "-H 'B: c'"),
    ({"url": "x", "risk": 4}, ""), ({"url": "x"}, "--threads=nan"),
    ({"url": "x"}, "--nonsense"), ({"url": "x"}, "--cookie 'unterminated"),
    ({"url": "x"}, "--cookie --batch"), ({"url": "x", "showVersion": True}, ""),
    ({}, ""), ({"url": "x", "batch": "false"}, ""),
])
def test_invalid_or_conflicting_arguments(values, extra):
    with pytest.raises(ValueError):
        build(Configuration(values=values, extra=extra))


def test_tools_do_not_require_a_target():
    for key in ("showVersion", "help", "advancedHelp", "dependencies", "shell", "listTampers", "gui", "tui", "updateAll", "wizard", "purge"):
        assert build(Configuration(values={key: True}))["argv"]


def test_pwsh_display_does_not_interpolate():
    assert powershell_command(["x", "$(Get-Secret)`abc'\n"]) == "& 'x' '$(Get-Secret)`abc''\n'"
