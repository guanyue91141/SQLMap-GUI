GROUPS = {
    "Basic": "基础选项", "Target": "目标", "Request": "请求与连接",
    "Optimization": "性能优化", "Injection": "注入配置", "Detection": "检测策略",
    "Techniques": "注入技术", "Fingerprint": "数据库指纹", "Enumeration": "数据枚举",
    "Brute force": "暴力检查", "User-defined function injection": "自定义函数 UDF",
    "File system access": "文件系统", "Operating system access": "操作系统",
    "Windows registry access": "Windows 注册表", "General": "通用设置",
    "Non-SQL injection": "非 SQL 注入", "Miscellaneous": "其他与工具",
}

_ROWS = """
help|基础帮助|显示基础命令帮助后退出。
advancedHelp|完整帮助|显示全部公开选项的帮助后退出。
showVersion|引擎版本|显示 sqlmap 版本后退出。
verbose|日志详细度|输出级别为 0–6；级别越高，显示的请求和调试信息越多。
url|目标 URL|待测试地址，可包含查询参数，例如 http://127.0.0.1/item?id=1。
direct|数据库直连|数据库连接串，例如 sqlite:///本机数据库路径；其他数据库可能需要对应驱动。
logFile|代理日志|从 Burp 或 WebScarab 日志文件中提取请求目标。
bulkFile|批量目标文件|文本文件中每行填写一个目标地址。
requestFile|原始 HTTP 请求|读取保存的完整 HTTP 请求文件，也可以使用页面上的报文粘贴功能。
googleDork|搜索语句|通过 Google 搜索语句获取目标 URL。
configFile|INI 配置文件|从 sqlmap 格式的 INI 文件加载参数。
openApiFile|OpenAPI 文档|从本地文件或 URL 的 OpenAPI / Swagger 定义中生成目标。
openApiBase|OpenAPI 基础地址|为缺少服务器地址的 API 定义指定基础 URL。
openApiTags|OpenAPI 标签|仅测试这些标签对应的接口，多个标签用逗号分隔。
agent|用户代理|自定义 HTTP User-Agent 请求头。
header|附加请求头|设置单个 HTTP 请求头，例如 X-Test: value；多条可使用“多个请求头”。
method|HTTP 方法|强制请求方法，例如 GET、POST、PUT。
data|请求体|POST 等请求的数据，例如 id=1；也支持 JSON 等原始内容。
paramDel|参数分隔符|指定参数值之间的分隔字符，通常为 &。
cookie|Cookie|设置 HTTP Cookie 字符串，例如 session=abc。
cookieDel|Cookie 分隔符|Cookie 字段的分隔字符，通常为分号。
liveCookies|实时 Cookie 文件|每次请求从文件重新加载最新的 Cookie。
loadCookies|导入 Cookie 文件|读取 Netscape / wget 格式的 Cookie 文件。
dropSetCookie|忽略响应 Cookie|忽略服务器返回的 Set-Cookie 响应头。
http10|HTTP/1.0|使用旧版 HTTP/1.0 协议。
http2|HTTP/2|使用实验性的 HTTP/2 支持，可能需要可选依赖。
mobile|模拟手机|使用移动设备的 User-Agent。
randomAgent|随机用户代理|从内置列表随机选择 User-Agent。
host|Host 请求头|覆盖 HTTP Host 请求头。
referer|来源地址|设置 HTTP Referer 请求头。
headers|多个请求头|每行一个 Header: value，换行会作为参数内容传入引擎。
authType|认证类型|HTTP 认证方式，例如 Basic、Digest、Bearer。
authCred|认证凭据|HTTP 认证的用户名:密码，或认证方式要求的令牌。
authFile|认证证书|用于 HTTP 认证的 PEM 证书或私钥文件。
abortCode|遇到状态码终止|服务器返回指定状态码时终止，多个值用逗号分隔。
ignoreCode|忽略状态码|继续处理指定 HTTP 错误状态码。
ignoreProxy|忽略系统代理|不使用操作系统默认代理设置。
ignoreRedirects|忽略重定向|不跟随服务器返回的跳转。
ignoreTimeouts|忽略连接超时|忽略连接超时并继续。
proxy|代理地址|通过指定代理发送请求，例如 http://127.0.0.1:8080。
proxyCred|代理凭据|代理认证的用户名:密码。
proxyFile|代理列表文件|从文件读取代理列表。
proxyFreq|代理切换频率|使用代理列表时，每发送多少次请求更换代理。
tor|使用 Tor|通过本机 Tor 代理连接，需要先启动 Tor。
torPort|Tor 端口|指定 Tor 代理端口。
torType|Tor 代理类型|可选 HTTP、SOCKS4、SOCKS5。
checkTor|检查 Tor|检查请求是否确实经过 Tor。
delay|请求间隔|两次 HTTP 请求之间等待的秒数。
timeout|连接超时|每次连接最多等待的秒数。
retries|超时重试次数|连接超时后的重试次数。
retryOn|内容匹配重试|响应内容匹配正则表达式时重试请求。
rParam|随机化参数|每次请求随机改变指定参数的值。
safeUrl|安全访问地址|测试过程中定期访问的正常页面。
safePost|安全请求数据|访问安全地址时发送的 POST 数据。
safeReqFile|安全请求文件|从文件加载定期发送的正常 HTTP 请求。
safeFreq|安全访问频率|每经过多少次测试请求发送一次安全请求。
skipUrlEncode|跳过 URL 编码|不对载荷数据进行 URL 编码。
skipXmlEncode|跳过 XML 编码|SOAP / XML 请求中的载荷不进行安全 XML 编码。
csrfToken|CSRF 参数名|指定保存防 CSRF 令牌的参数名称。
csrfUrl|CSRF 提取地址|从该页面获取新的防 CSRF 令牌。
csrfMethod|CSRF 请求方法|获取令牌页面时使用的 HTTP 方法。
csrfData|CSRF 请求体|获取令牌时发送的 POST 数据。
csrfRetries|CSRF 提取重试|获取防 CSRF 令牌的重试次数。
forceSSL|强制 HTTPS|强制通过 SSL / HTTPS 连接。
chunked|分块传输|使用 HTTP 分块传输编码发送 POST 请求。
hpp|参数污染|使用 HTTP 参数污染方式组织请求。
evalCode|请求前 Python 代码|在每次请求前执行指定 Python 代码，可用于计算动态参数。
optimize|启用全部优化|开启引擎提供的一组性能优化开关。
noKeepAlive|禁用连接复用|禁用 HTTP 持久连接 Keep-Alive。
nullConnection|仅获取页面长度|不获取完整响应体，尝试仅获取页面长度。
threads|并发请求数|最多同时发送的 HTTP 请求数量。
testParameter|待测参数|指定要检测的参数名称，多个参数用逗号分隔。
skip|跳过参数|不检测指定参数，多个参数用逗号分隔。
skipStatic|跳过静态参数|跳过看起来不会影响页面内容的参数。
paramExclude|排除参数正则|参数名匹配该正则表达式时不检测。
paramFilter|参数位置过滤|按参数来源筛选，例如 GET、POST、COOKIE。
dbms|指定数据库|强制使用指定 DBMS，例如 MySQL、PostgreSQL、SQLite。
dbmsCred|数据库凭据|数据库认证的用户名:密码。
esperanto|通用枚举引擎|使用不依赖特定 DBMS 的枚举方式。
os|指定服务端系统|指定数据库所在操作系统，例如 Windows 或 Linux。
invalidBignum|大数无效化|用大数构造无效参数值。
invalidLogical|逻辑式无效化|用逻辑表达式构造无效参数值。
invalidString|随机串无效化|用随机字符串构造无效参数值。
noCast|禁用类型转换|关闭载荷中的类型转换机制。
noEscape|禁用字符串转义|关闭注入载荷的字符串转义机制。
prefix|载荷前缀|放在注入载荷之前的字符串。
suffix|载荷后缀|放在注入载荷之后的字符串。
tamper|Tamper 脚本链|依次应用脚本变换注入数据；可搜索、添加和调整顺序，也可填写自定义脚本路径。
proof|验证可利用性|对已检测到的注入点进行利用证明。
level|检测级别|1–5，级别越高，检测范围和测试数量越大。
risk|测试风险|1–3，较高数值启用影响更大的测试载荷。
string|真条件匹配文本|条件为真时，响应中应出现的字符串。
notString|假条件匹配文本|条件为假时，响应中应出现的字符串。
regexp|真条件匹配正则|条件为真时，响应应匹配的正则表达式。
code|真条件状态码|条件为真时应返回的 HTTP 状态码。
lengths|仅比较长度|只根据响应内容长度比较页面。
smart|智能检测|启发式结果为正时才进行深入测试。
textOnly|只比较文本|比较页面时排除非文本内容。
titles|只比较标题|只比较 HTML 页面标题。
technique|注入技术|B 布尔盲注、E 报错、U 联合查询、S 堆叠、T 时间盲注、Q 内联查询。
timeSec|时间盲注延迟|等待数据库响应的延迟秒数。
disableStats|禁用延迟统计|不使用统计模型判断时间延迟。
timeless|HTTP/2 无延迟计时|通过 HTTP/2 时序进行实验性检测，需要 HTTP/2 支持。
multiBit|多位读取|通过渲染结果在单次请求中读取多个比特。
uCols|UNION 列数范围|联合查询测试的列数范围，例如 1-10。
uChar|UNION 测试字符|用于探测联合查询列数的字符或值。
uFrom|UNION 来源表|联合查询 FROM 子句使用的表。
uValues|UNION 列值|指定联合查询使用的各列值。
dnsDomain|DNS 带外域名|用于带外通信的域名，或引擎支持的 interactsh。
secondUrl|二次响应地址|在该页面中寻找二次注入的执行结果。
secondReq|二次请求文件|从文件加载用于获取二次响应的 HTTP 请求。
extensiveFp|详细数据库指纹|执行更全面的数据库版本识别。
getAll|枚举全部信息|获取引擎能够枚举的全部数据库信息。
getBanner|数据库版本横幅|获取数据库版本横幅信息。
getCurrentUser|当前数据库用户|查询当前数据库会话用户。
getCurrentDb|当前数据库|查询当前使用的数据库名称。
getHostname|服务器主机名|获取数据库服务器主机名。
isDba|检查 DBA 权限|检查当前数据库用户是否拥有管理员权限。
getUsers|枚举用户|列出数据库用户。
getPasswordHashes|枚举密码哈希|获取数据库用户的密码哈希。
getPrivileges|枚举权限|列出数据库用户权限。
getRoles|枚举角色|列出数据库用户角色。
getDbs|枚举数据库|列出可见的数据库。
getTables|枚举数据表|列出所选数据库中的表。
getColumns|枚举字段|列出所选表的字段。
getSchema|枚举数据库结构|获取数据库结构信息。
getCount|统计记录数|获取数据表的记录数量。
dumpTable|导出表数据|导出指定数据库、表和字段的数据。
dumpAll|导出全部表|导出全部可访问数据表的记录。
search|搜索数据库对象|搜索数据库、表或字段名称，配合 -D、-T、-C 使用。
getComments|获取对象注释|枚举时读取数据库、表和字段注释。
getStatements|获取运行中 SQL|查询数据库当前正在执行的 SQL 语句。
getProcs|存储过程与函数|获取存储过程、函数及可访问的源代码。
db|数据库名称|指定要枚举的数据库名称。
tbl|数据表名称|指定要枚举的数据表，多个名称用逗号分隔。
col|字段名称|指定要枚举的字段，多个名称用逗号分隔。
exclude|排除数据库对象|不枚举指定的数据库对象标识符。
user|数据库用户名|指定要枚举的数据库用户。
excludeSysDbs|排除系统数据库|枚举表时跳过系统数据库。
pivotColumn|枢轴字段|用于逐行提取数据的枢轴字段名称。
dumpWhere|导出 WHERE 条件|只导出符合该 WHERE 条件的记录。
limitStart|起始记录|导出表数据时的起始记录位置。
limitStop|结束记录|导出表数据时的结束记录位置。
firstChar|起始字符|提取查询结果时的起始字符位置。
lastChar|结束字符|提取查询结果时的结束字符位置。
sqlQuery|执行 SQL|执行自定义 SQL 语句。
sqlShell|交互 SQL Shell|在下方终端进入交互式 SQL 会话。
sqlFile|SQL 文件|执行一个或多个本地文件中的 SQL 语句。
commonTables|常见表名检查|通过常见名称检查数据表是否存在。
commonColumns|常见字段检查|通过常见名称检查字段是否存在。
commonFiles|常见文件检查|通过常见路径检查文件是否存在。
udfInject|注入自定义函数|在数据库中创建自定义函数，需要数据库支持及相应权限。
shLib|共享库路径|用于自定义函数注入的本地共享库文件。
fileRead|读取远端文件|读取数据库服务器文件系统中的指定文件。
fileWrite|写入本地文件|将该本地文件写入数据库服务器文件系统。
fileDest|远端目标路径|写入文件在数据库服务器上的绝对路径。
osCmd|执行系统命令|通过数据库能力执行服务端操作系统命令。
osShell|交互系统 Shell|在终端进入 sqlmap 提供的操作系统交互会话。
osPwn|带外会话|由引擎尝试建立带外 Shell、Meterpreter 或 VNC，需要外部工具。
osSmb|SMB 中继会话|通过引擎的 SMB 中继流程建立带外会话，需要外部工具和环境。
osBof|存储过程溢出|调用引擎的存储过程缓冲区溢出功能。
privEsc|数据库进程提权|尝试提升数据库进程用户权限。
msfPath|Metasploit 路径|本机 Metasploit Framework 的安装目录，本应用不附带该工具。
tmpPath|远端临时目录|数据库服务器上用于临时文件的绝对路径。
regRead|读取注册表|读取数据库服务器 Windows 注册表键值。
regAdd|写入注册表|添加或修改 Windows 注册表键值。
regDel|删除注册表值|删除指定的 Windows 注册表键值。
regKey|注册表键|完整的 Windows 注册表键路径。
regVal|注册表值名称|要读取、写入或删除的注册表值名称。
regData|注册表值数据|要写入的注册表值内容。
regType|注册表值类型|例如 REG_SZ 或 REG_DWORD。
sessionFile|会话文件|读取之前保存的 sqlmap SQLite 会话文件。
trafficFile|HTTP 流量日志|将全部 HTTP 通信记录到指定文本文件。
abortOnEmpty|空结果时中止|数据查询结果为空时停止提取。
answers|预设问答|按提示关键词预设回答，例如 quit=N,follow=N。
base64Parameter|Base64 参数|指定包含 Base64 编码数据的参数名称。
base64Safe|安全 Base64 字母表|使用兼容 URL 和文件名的 Base64 编码。
batch|自动回答|不等待交互输入，全部问题使用引擎默认回答；默认关闭。
binaryFields|二进制字段|指定结果中包含二进制内容的字段。
checkInternet|检查联网|测试目标前检查互联网连接。
cleanup|清理引擎对象|删除数据库中由 sqlmap 创建的 UDF 和临时表。
crawlDepth|网页爬取深度|从目标地址开始爬取页面的最大深度。
crawlExclude|爬取排除规则|URL 匹配该正则表达式的页面不爬取。
csvDel|CSV 分隔符|导出 CSV 文件使用的字段分隔字符。
charset|盲注字符集|限制盲注提取字符集，例如 0123456789abcdef。
dumpFile|自定义导出文件|将提取的数据写入指定文件。
dumpFormat|数据导出格式|可选 CSV、HTML、SQLITE、JSONL。
encoding|结果字符编码|读取数据库内容时使用的字符编码，例如 GBK。
eta|显示预计耗时|提取结果时显示预计剩余时间。
flushSession|清除目标会话|删除当前目标之前保存的引擎会话信息。
forms|检测网页表单|解析并测试目标页面的表单。
mineParams|挖掘隐藏参数|搜索页面未链接的 GET 参数并检测。
freshQueries|忽略查询缓存|不使用会话中保存的查询结果。
googlePage|搜索结果页码|Google 搜索目标时使用的页码。
harFile|HAR 流量文件|将 HTTP 通信记录到指定 HAR 文件。
hexConvert|十六进制转换|数据提取时使用十六进制转换。
outputDir|结果输出目录|自定义本次 sqlmap 结果目录；留空时使用独立运行目录。
parseErrors|解析数据库错误|解析并展示响应中的 DBMS 错误信息。
preprocess|请求预处理脚本|发送请求前执行的 Python 脚本路径。
postprocess|响应后处理脚本|接收响应后执行的 Python 脚本路径。
repair|修复未知字符|重新提取包含未知字符标记的记录。
reportJson|JSON 结果报告|将运行结果保存到指定 JSON 文件。
saveConfig|保存 INI 配置|让 sqlmap 将当前选项保存到指定 INI 文件。
scope|目标范围正则|只处理符合正则表达式的目标。
skipHeuristics|跳过启发式|不进行启发式注入检测。
skipWaf|跳过 WAF 检测|不执行启发式 WAF / IPS 识别。
tablePrefix|临时表前缀|sqlmap 创建临时表时使用的名称前缀。
testFilter|测试包含条件|只执行载荷或标题匹配指定条件的测试。
testSkip|测试排除条件|跳过载荷或标题匹配指定条件的测试。
timeLimit|运行时间上限|限制引擎运行秒数，例如 3600。
unsafeNaming|禁用标识符转义|不转义数据库、表、字段等对象名称。
webRoot|站点根目录|指定数据库服务器上网站文档根目录的绝对路径。
graphql|GraphQL 注入|检测 GraphQL 注入。
ldap|LDAP 注入|检测 LDAP 注入。
nosql|NoSQL 注入|检测 NoSQL 注入。
xpath|XPath 注入|检测 XPath 注入。
ssti|模板注入|检测服务端模板注入 SSTI。
xslt|XSLT 注入|检测 XSLT 注入。
xxe|XML 外部实体|检测 XML 外部实体 XXE 注入。
hql|HQL / JPQL 注入|检测 Hibernate ORM 查询语言注入。
sparql|SPARQL 注入|检测 SPARQL 查询注入。
odata|OData 注入|检测 OData 的 $filter 表达式注入。
jwt|JWT 审计|检测 JSON Web Token 中的弱点。
oobServer|带外服务器|盲 XXE 测试使用的带外服务器地址。
oobToken|带外认证令牌|自托管带外服务器所需的认证令牌。
mnemonics|参数缩写|使用引擎缩写语法，例如 flu,bat,ban,tec=EU。
alert|命中后本机命令|发现 SQL 注入时，在本机执行指定操作系统命令。
beep|提示音|出现交互问题或发现漏洞时发出提示音。
dependencies|检测可选依赖|列出 sqlmap 缺失的可选依赖，不自动安装。
disableColoring|禁用彩色输出|关闭终端输出的颜色。
disableHashing|禁用哈希分析|导出数据时不进行哈希识别分析。
gui|原生图形界面|在本机打开 sqlmap 的 Tkinter 窗口，需要 tkinter；窗口操作不在浏览器内完成。
listTampers|列出 Tamper|在终端列出引擎内置的 Tamper 脚本。
noLogging|禁用引擎日志|关闭 sqlmap 自身的文件日志；工作台仍保存终端记录。
noTruncate|不截断终端内容|完整显示较长字段等终端输出。
offline|离线会话|只读取已有会话数据，不访问目标。
purge|清除引擎数据|由引擎清空其数据目录中的全部内容。
resultsFile|批量结果 CSV|多目标模式下写入结果 CSV 的文件路径。
shell|交互 sqlmap Shell|进入 sqlmap 命令交互环境，在终端输入参数或 help、exit。
tmpDir|本机临时目录|sqlmap 存放本机临时文件的目录。
tui|原生文本界面|启动引擎的 ncurses 文本界面，需要对应平台与终端依赖。
unstable|不稳定连接模式|调整引擎参数以适应不稳定网络。
updateAll|更新 sqlmap|执行引擎自身的更新流程，会修改当前环境；更新后需重新锁定依赖并核对参数目录。
wizard|交互向导|启动 sqlmap 内置的入门交互向导，在下方终端回答问题。
"""
TRANSLATIONS = {row.split("|", 2)[0]: row.split("|", 2)[1:] for row in _ROWS.strip().splitlines()}

# These actions operate without a target and should be launched independently.
TOOLS = {"help", "advancedHelp", "showVersion", "dependencies", "listTampers", "gui", "tui", "shell", "wizard", "updateAll", "purge"}
FILE_INPUTS = {"logFile", "bulkFile", "requestFile", "configFile", "liveCookies", "loadCookies", "authFile", "proxyFile", "safeReqFile", "secondReq", "sqlFile", "shLib", "fileWrite", "sessionFile", "preprocess", "postprocess"}
MULTILINE = {"data", "headers", "cookie", "evalCode", "sqlQuery", "safePost", "csrfData"}
DEPENDENCIES = {
    "direct": "直连驱动按 DBMS 选装；SQLite 使用 Python 内置驱动。",
    "http2": "需要引擎支持的 HTTP/2 可选依赖，可运行“检测可选依赖”。",
    "timeless": "需要 HTTP/2 支持。", "tor": "需本机已运行 Tor 代理。",
    "osPwn": "需另行安装 Metasploit 等外部工具。", "osSmb": "需外部中继工具及对应网络环境。",
    "gui": "需要 Python tkinter 与本机桌面。", "tui": "需要 ncurses；Windows 原生环境可能不支持。",
}
