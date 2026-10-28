"""Read the installed engine's parser in an isolated interpreter, without running it."""
import json
import optparse
import sys


class Captured(BaseException):
    def __init__(self, parser):
        self.parser = parser


def extract():
    import sqlmap  # sets up sqlmap's internal import path
    from lib.core.defaults import defaults
    from lib.parse import cmdline

    class Inspector(optparse.OptionParser):
        def format_help(self, *args, **kwargs):
            raise Captured(self)

    cmdline.ArgumentParser = Inspector
    try:
        cmdline.cmdLineParser(["sqlmap"])
    except Captured as capture:
        groups = [("Basic", capture.parser.option_list)]
        groups += [(g.title, g.option_list) for g in capture.parser.option_groups]
        result = []
        for group, options in groups:
            for option in options:
                if option.help == optparse.SUPPRESS_HELP:
                    continue
                flags = option._short_opts + option._long_opts
                result.append({
                    "id": option.dest or "help", "group": group,
                    "flags": flags, "flag": (option._long_opts or option._short_opts)[0],
                    "action": option.action, "type": option.type or "string",
                    "choices": option.choices, "default": defaults.get(option.dest),
                    "help": option.help or "", "metavar": option.metavar,
                })
        return result
    raise RuntimeError("无法提取 sqlmap 参数，解析器接口可能已经改变")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(extract(), ensure_ascii=False))
