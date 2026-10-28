import re

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")
RULES = [
    (r"legal disclaimer", "使用说明", "引擎提示：请仅对已授权的目标进行测试。"),
    (r"testing connection to the target", "连接目标", "正在检查目标是否能够正常连接。"),
    (r"checking if the target is protected", "防护识别", "正在识别目标是否存在 WAF 或 IPS。"),
    (r"testing if .* is dynamic", "参数检查", "正在判断参数变化是否会影响页面内容。"),
    (r"testing .*injection", "注入测试", "正在执行注入检测，具体技术请参照原始日志。"),
    (r"appears to be .*injectable|is vulnerable|identified the following injection", "发现注入线索", "引擎发现注入结果，请结合原始输出与复测确认。"),
    (r"does not seem to be injectable|do not appear to be injectable", "未发现注入", "当前参数或测试组合没有发现可用注入。"),
    (r"back-end DBMS", "数据库信息", "引擎正在报告或确认后端数据库类型。"),
    (r"fetching|retrieving", "提取信息", "正在获取数据库信息或查询结果。"),
    (r"unable to connect|connection timed out|can't establish|connection refused", "连接异常", "连接失败或超时，请检查目标、代理与超时设置。"),
    (r"resuming|resumed", "恢复缓存", "正在复用之前保存的会话信息。"),
    (r"stored under|dumped to|saved to", "结果已保存", "结果已写入文件，可在“结果文件”中查看。"),
    (r"\[CRITICAL\]", "引擎错误", "引擎遇到关键错误，请查看同一行原文。"),
    (r"\[WARNING\]", "引擎提醒", "引擎报告需要留意的情况，详细内容保留在原始日志。"),
    (r"\[[YyNnQq/]+\]|\[Y/n\]|\[y/N\]", "等待回答", "引擎正在等待输入；大写字母通常代表默认选项，直接回车使用默认值。"),
    (r"sqlmap\s*>\s*$", "sqlmap Shell", "在终端输入 sqlmap 参数；输入 help 查看提示，exit 退出。"),
    (r"sql-shell>\s*$", "SQL Shell", "在终端输入 SQL 语句，输入退出命令结束会话。"),
    (r"os-shell>\s*$", "系统 Shell", "当前输入交给 sqlmap 的远端系统会话处理。"),
    (r"ending @", "运行结束", "引擎已结束本次运行。"),
]
COMPILED = [(re.compile(pattern, re.I), title, text) for pattern, title, text in RULES]


class Annotator:
    def __init__(self):
        self.tail = ""
        self.seen = set()

    def feed(self, chunk):
        self.tail = (self.tail + ANSI.sub("", chunk))[-4096:]
        found = []
        for pattern, title, text in COMPILED:
            matches = list(pattern.finditer(self.tail))
            if matches and title not in self.seen:
                found.append({"title": title, "text": text})
                self.seen.add(title)
        return found
