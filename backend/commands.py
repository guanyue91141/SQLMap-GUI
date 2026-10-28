import math
from pathlib import Path
import shlex
import sys

from pydantic import BaseModel, ConfigDict, Field

from .catalog import engine_root, options


class Configuration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: dict[str, str | bool | int | float | list[str]] = Field(default_factory=dict)
    extra: str = ""


def powershell_command(argv):
    return "& " + " ".join("'" + str(value).replace("'", "''") + "'" for value in argv)


def build(config: Configuration, run_dir: Path | None = None):
    items = options()
    by_id = {item["id"]: item for item in items}
    by_flag = {flag: item for item in items for flag in item["flags"]}
    result = []
    used = set()
    counts = {}

    def add(item, value=None):
        key = item["id"]
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > 1 and not item["repeatable"]:
            raise ValueError(f"参数重复：{item['label']}（{item['flag']}），请只在一处设置")
        used.add(key)
        result.append(item["flag"])
        if item["action"] not in ("store_true", "store_false", "help", "version"):
            text = str(value)
            if "\x00" in text:
                raise ValueError("参数不能包含空字符")
            if item["type"] in ("int", "float"):
                try:
                    numeric = int(text) if item["type"] == "int" else float(text)
                    if not math.isfinite(numeric):
                        raise ValueError()
                except ValueError:
                    raise ValueError(f"{item['label']} 需要有效数值") from None
            bounds = {"verbose": (0, 6), "level": (1, 5), "risk": (1, 3), "threads": (1, 10)}
            if key in bounds and not bounds[key][0] <= float(text) <= bounds[key][1]:
                raise ValueError(f"{item['label']} 的范围为 {bounds[key][0]}–{bounds[key][1]}")
            result.append(text)

    for key, value in config.values.items():
        if key not in by_id:
            raise ValueError(f"未知参数：{key}")
        if value is False or value == "" or value == []:
            continue
        item = by_id[key]
        if item["action"] in ("store_true", "store_false", "help", "version"):
            if value is not True:
                raise ValueError(f"{item['label']} 必须是开关值")
            add(item)
        else:
            if isinstance(value, bool):
                raise ValueError(f"{item['label']} 需要填写内容")
            if isinstance(value, list):
                if not item["repeatable"]:
                    raise ValueError(f"{item['label']} 不接受重复值")
                for part in value:
                    add(item, part)
            else:
                add(item, value)
    try:
        extra = shlex.split(config.extra, posix=True)
    except ValueError as exc:
        raise ValueError("额外参数引号未闭合，请检查输入") from exc
    index = 0
    while index < len(extra):
        token = extra[index]
        flag, sep, value = token.partition("=")
        item = by_flag.get(flag)
        if not item:
            raise ValueError(f"未知额外参数：{flag}。每个参数请使用完整名称，并用引号包住路径和空格")
        needs_value = item["action"] not in ("store_true", "store_false", "help", "version")
        if needs_value and not sep:
            index += 1
            if index >= len(extra) or extra[index].partition("=")[0] in by_flag:
                raise ValueError(f"{flag} 缺少参数值")
            value = extra[index]
        elif sep and not needs_value:
            raise ValueError(f"开关 {flag} 不接受等号赋值")
        # Form + extra conflicts must never merge silently, including repeatable headers.
        if item["id"] in config.values and config.values[item["id"]] not in (False, "", []):
            raise ValueError(f"参数冲突：{flag} 已在表单中设置")
        add(item, value)
        index += 1

    tools = [item for item in items if item["tool"] and item["id"] in used]
    if tools and (len(tools) != 1 or len(used - {"verbose", "disableColoring", "noTruncate"}) > 1):
        raise ValueError("独立工具操作不能与目标或其他功能组合，请重置表单后单独运行")
    targets = {"url", "direct", "logFile", "bulkFile", "requestFile", "googleDork", "configFile", "openApiFile"}
    if not tools and not (used & targets):
        raise ValueError("请填写目标 URL、导入请求，或选择一种独立工具操作")
    output = None
    if run_dir and not tools:
        if "outputDir" not in used:
            output = run_dir / "output"
            result.extend(["--output-dir", str(output)])
        else:
            output = Path(result[result.index("--output-dir") + 1]).expanduser()
            if not output.is_absolute():
                output = run_dir / output
            output = output.resolve()
            result[result.index("--output-dir") + 1] = str(output)
        if "reportJson" not in used:
            result.extend(["--report-json", str(run_dir / "report.json")])
    # On Windows optparse's early exit otherwise triggers sqlmap's double-click pause.
    # Do not add this to scans or Shell: it also changes ordinary question handling.
    if used & {"help", "advancedHelp", "showVersion"}:
        result.append("--non-interactive")
    argv = [sys.executable, "-u", str(engine_root() / "sqlmap.py"), *result]
    return {"argv": argv, "command": powershell_command(argv), "output": str(output) if output else None}
