# sqlmap 中文工作台

面向 Windows 的本地 Web 工具：244 个公开参数、17 类功能、84 个内置 Tamper 脚本，支持完整终端输入和常见提示中文旁注。后端执行真实 sqlmap，不依赖远端 API 服务。

## 安装与启动

需要 PowerShell 7、uv、Node.js 20.19+（或 22.12+）、pnpm 10，以及支持 ConPTY 的 Windows 10 / 11。

```powershell
Set-Location E:\ctf\sqlmap
pwsh -NoProfile -File .\setup.ps1
pwsh -NoProfile -File .\start.ps1
```

打开 <http://127.0.0.1:9955>。可通过 `start.ps1 -OpenBrowser` 同时打开默认浏览器。端口固定为 9955，已被占用时会报错；服务只监听 `127.0.0.1`，无需登录。

uv 在项目中创建 `.venv`，按 `uv.lock` 安装 Python 3.12 和 `sqlmap==1.10.10`。前端按 `pnpm-lock.yaml` 安装并构建，之后启动不需要联网或运行 Node 服务。修改前端后请重新运行 `pnpm --dir frontend run build`。

## 使用

1. 在“目标”填写 URL，或粘贴、上传原始 HTTP 请求，也可以指定本机文件绝对路径。
2. 使用左侧分类和全局搜索配置参数。未填写的参数不传入命令，由 sqlmap 决定默认行为；自动回答 `--batch` 默认关闭。
3. 检查底部 PowerShell 命令预览，点击“开始运行”。启动时自动补充独立输出目录和 JSON 报告路径，实际命令记录在 `run.json` 中。
4. 点击终端回答问题、使用方向键和交互 Shell；Enter 提交，Ctrl+C 中断。引擎可能在收到中断后继续提问，可输入回答或使用“强制结束”。
5. “结果文件”下载日志、运行配置、报告和导出数据。“配置”菜单可保存、导入及导出 JSON 配置。

额外参数使用完整名称，例如 `--technique=BEU --timeout=15`。带空格和 Windows 路径的值必须用引号包住，例如 `--proxy-file 'E:\资料\代理 列表.txt'`；此处采用引号分词，不执行 PowerShell。与表单重复的参数会被拒绝。`-H/--header` 可在额外参数中重复，但不能同时在表单设置它；多个请求头也可使用 `--headers` 多行控件。

同一时间只运行一个任务。关闭或刷新网页不会结束后台任务，重新打开可连接当前终端。终端回放最多最近约 1 MB，完整原始输出保存于 `terminal.log`。网页保留原始日志及 ANSI 颜色，中文旁注采用本地规则，不使用在线翻译；未知输出不做翻译。

服务退出时清理其子进程；服务重新启动后将未结束任务标记为中断，不自动继续执行。界面只展示当前或最近一次任务；之前的运行目录仍保留在磁盘中，可手动清理。

## 功能覆盖与依赖

按已安装引擎的真实参数解析器生成目录，覆盖 `sqlmap -hh` 的公开选项。隐藏的内部 API / 自测参数不作为 UI 功能。全部选项有中文名称、说明和原始英文帮助。功能包括目标、请求、优化、注入、检测、技术、指纹、枚举、暴力检查、UDF、文件、系统、注册表、通用、非 SQL 注入及其他工具。

帮助、版本、可选依赖检测、Tamper 列表、交互 Shell、向导、原生 GUI / TUI、更新和数据清理作为独立操作运行，不带当前表单配置。GUI 打开本机 Tkinter 窗口；TUI 取决于平台的 ncurses 支持；本工作台不会将原生窗口嵌入浏览器。

数据库直连、HTTP/2、Tor、Metasploit 等功能可能需要额外驱动或外部程序。“运行环境”显示常见依赖检测结果，使用“检测可选依赖”查看引擎完整检查。检测到功能参数不代表本机已经具备其所有依赖。

引擎自己的 `--update` 可能修改 `.venv`，不会修改 `uv.lock`。推荐通过 `uv add sqlmap==新版本` 明确升级、重启服务并核对新参数的中文映射；缺少映射时目录会报错，避免静默遗漏。`uv sync --frozen` 会恢复锁定版本。

## 本机文件

```text
.data/
  config.json       # 最近保存/运行的配置
  current.json      # 最近一次运行状态
  uploads/          # 上传文件与粘贴的请求
  runs/<运行编号>/   # 运行配置、状态、原始日志、事件流、报告和默认输出目录
```

自定义 `--output-dir` 时，结果页也可列出该输出目录中的文件；下载接口仅允许当前运行目录及该次指定输出目录内的文件。其他自定义日志、导出路径若位于这些目录外，请到对应本机路径查看。

`.venv/`、`.data/`、上传内容、凭据、日志、前端依赖和构建产物已加入 Git 忽略；依赖锁文件、源码及启动脚本保留。运行资料中可能包含敏感请求和结果，请按自己的需要清理。

## 开发与验证

```powershell
uv run --frozen pytest -q
pnpm --dir frontend run build
# 先运行 start.ps1，再执行浏览器测试
pnpm --dir frontend exec playwright install chromium
pnpm --dir frontend run test:e2e
```

后端接口：`GET /api/catalog`、`POST /api/preview`、`GET/PUT /api/config`、`GET/POST /api/run`、`POST /api/run/stop`、`POST /api/upload`、`GET /api/results`、`GET /api/download`。接口类型与字段可在 <http://127.0.0.1:9955/docs> 查看。

终端连接：`WS /api/terminal/{run_id}?after={序号}`。服务端发送 `output`、`annotation`、`status`；客户端发送 `input`、`resize` 和输出渲染完成后的 `ack`。输出确认控制背压，慢客户端不积累无限的浏览器缓冲。接口检查 Host 与同源 Origin。

测试使用本机终端夹具及真实 sqlmap 的版本、帮助和 Shell，不访问外部扫描目标。Windows 是本次支持的平台。

## 参考

- [sqlmap 官方项目与使用说明](https://github.com/sqlmapproject/sqlmap)；引擎保持独立依赖，遵循其 GPLv2 许可。
- [Rootx202/SQLMap-GUI](https://github.com/Rootx202/SQLMap-GUI)：参考功能分类。
- [GitHubNull/sqlmapWebUI](https://github.com/GitHubNull/sqlmapWebUI)：参考中文配置体验。
- [pywinpty](https://github.com/andfoy/pywinpty)、[xterm.js](https://xtermjs.org/)：终端通信和浏览器终端。

本项目独立实现，未复制上述 GUI 项目的源代码。仅在获授权的系统上使用 sqlmap。
