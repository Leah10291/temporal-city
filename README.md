# Temporal City · v21 UI

以 `temporal_city_v15_no_database(1).zip` 为功能与资料底稿。Story 移除了重复的局限性段落；Information 保留最新版的研究问题、数据、方法和参考文献，并新增四位作者的可上传圆形头像。彩色阅读光标沿 Story、Collector、Atlas、Information 的段落外缘移动，轨迹线隐藏，经过处有柔和拖尾。Collector 使用七张独立步骤卡，顶部不再出现悬浮四栏菜单。地图白天使用冷白灰底、夜间使用深蓝底；营业数量和热力使用珊瑚红色系，GFA 使用蓝色系，原有图例文字不变。

AR5958A Group 3 · *Predicting 24-Hour Amenity Availability in Singapore Mixed-Use Planning*

一个程序，四个页面，共用顶部导航：

| 页面 | 地址 | 内容 |
|---|---|---|
| **Story**（首页） | `/` | 拖动时间轴查看三个研究区 POI 随营业时间亮灭；“空间混合 ≠ 时间混合”对比与项目入口。局限、方法和来源在 Information 阅读 |
| **Collector** | `/collector.html` | 采集器：发现 POI → 找营业时间 → AI 结构化 → 验证 → 导出。界面、地图（MapLibre + 同一底图）与 Atlas 统一 |
| **Atlas** | `/atlas.html` | 你们的 2D/3D dashboard。GFA 拆成独立图层（高度 = GFA 强度，颜色可选：仅 GFA / 用地 / 营业比例）。右上角可切换数据源：**Google Places 样本** 或 **Collector 数据库** |
| **Information** | `/information.html` | 四位作者与可上传头像；最新版的研究问题、逻辑图、研究范围与数据来源、指标定义、数据质量、局限、下一步、反馈回应和参考文献。Atlas 导航通过 “METHOD & LIMITS →” 链接到此页 |

**日夜模式：** 顶部导航右侧有 **Auto / ☀ / ☾** 开关，四个页面共用、会记住选择。
- **Auto**：跟随页面上的时间。Story、Atlas 选具体某一天后拖动时间轴，或在 Collector 的 EXPLORE 页拖动时间——17:00 后底图逐渐变暗，过黄昏中点（约 18:30）整页切到夜间；夜里营业的地点在热力图上发金色的光，关门的 POI 变暗。Atlas 选 “Whole week” 时没有具体时刻，保持白天。夜间卡片、结论、统计数字、图表文字及导航统一使用高对比深色主题。
- **☀ / ☾**：四个页面一起锁定为白天或夜间。
- 样式在 `static/theme.css`（夜间部分）和 `static/daynight.js`；改完后运行 `py tools\build_atlas.py` 更新 Atlas。

**用地与 GFA（任何研究范围）：** `data/mp2025_landuse.json.gz` 是 URA Master Plan 2025 用地图层的精简版（约 15 MB，`py tools\build_landuse.py MasterPlan2025LandUseLayer.geojson` 生成）。Atlas 用 Collector 数据时，会把每个研究范围内的地块裁剪到范围圆内，计算用地熵（六类）、数值 GPR 覆盖率和 GFA（裁剪面积 × 数值 GPR），所以 Beauty World 等任何区域都有 GFA 分析。计算定义与三个案例区的 GIS 结果一致（单元测试 `test_landuse_matches_sample_definitions`）。Google 样本页面仍用组里原来的 2019 版结果。用地分类表在 `core/landuse.py` 的 `LU_CLASS`：前 14 类沿用组里的 GIS 分类；Business 1/2、Business Park 归 Commercial，Health & Medical 归 Civic_Edu，Sports & Recreation 归 Open_Space，道路/水体/交通设施排除——需要的话直接改这张表。

**Atlas 的 COMPARE 页按问题组织：** 顶部是问题目录；每一节标题是研究问题，下面金色框是根据当前数据自动算出的结论（Finding），方法和数据说明放在该节底部（Data note）。

**Collector 和 Atlas 是打通的：** 用 `py app.py` 运行后，在 Atlas 右上角选 **COLLECTOR DATABASE**（或在 Collector 点 “VIEW IN ATLAS →”），Atlas 就改用采集器的数据：
- **选哪些区域**：在 Collector 里勾选研究范围，点 VIEW IN ATLAS（或最后一步的 Open in Atlas），Atlas 就只显示勾选的区域；Atlas 顶部提示条里的 “Choose study areas” 也可以改选。没有指定时显示 POI 最多的区域。
- **任何研究范围都可以**：Collector 里每个有 POI 的研究范围都会成为 Atlas 的一个区域（按名字显示，比如 Beauty World MRT），最多同时比较 8 个（按 POI 数量从多到少）。名字含 Bencoolen / Tanjong Pagar / Promenade、或位于这三个站点 400 m 内的 POI，归入对应的案例区。用地构成和 GFA 来自 Master Plan 2025，任何区域都有。只有 `verified / observed / retrieved` 的营业时间算“已知”，其余（missing、conflict、estimated、pending）算 Unknown，不当作关门。
- **随数据重新计算的**：地图、热力、3D、GFA 图层，以及 COMPARE 页的全部图表和表格（24 小时曲线、工作日/周末/全周、相对与绝对可用性、功能多样性、22:00–05:00 夜间指标、GFA 加权对比、各类别覆盖率、地块与建筑匹配数）。计算方法与 Google 样本完全相同，单元测试 `test_atlas_analysis_matches_sample` 用样本验证过结果一致。
- **不变的**：用地构成、GPR/GFA 来自 URA 地块，和 POI 来源无关；项目方法与样本限制在 Information 说明。
- 直接双击打开 `static/atlas.html` 只能看样本；要用采集数据，必须通过 `py app.py` 打开。

---

## 1. 在自己电脑上运行（Windows）

需要 Python 3.10 或以上。

```bat
cd temporal_city
py -m pip install -r requirements.txt
py app.py
```

浏览器会自动打开 **http://127.0.0.1:8765**（端口被占用时自动换下一个，黑色窗口里会显示实际地址）。也可以双击 `start.bat`。数据保存在 `data/temporal_city.db`（第一次运行时自动创建）。

**作者头像：** 在本机运行后打开 Information，点击头像圈内的加号，上传不超过 5 MB 的 JPG、PNG 或 GIF。图片保存在项目的 `static/avatars/` 中；打包或部署时连同该文件夹一起复制。只读公开演示不允许上传。

## 2. 公开链接：GitHub Pages（课程要求）

课程要求提交一个公开的网页链接和 GitHub 仓库链接。`docs/` 文件夹就是网站的静态版本，GitHub Pages 可以直接托管：

- **Story、Atlas、Information**：与本地版相同，Atlas 使用三个案例区的 Google Places 样本，可以完整交互。
- **Collector**：需要 Python 服务器，GitHub Pages 运行不了，所以公开版是一个说明页，用截图介绍七个步骤，并附本地运行方法。
- 每页页脚会自动出现 “Project repository on GitHub →”，链接到你们的仓库。

步骤：

1. 登录 GitHub，新建一个 **Public** 仓库，例如 `temporal-city`。
2. 把整个项目文件夹上传到仓库（网页上 **Add file → Upload files** 拖进去，或用 GitHub Desktop）。`docs/` 文件夹一定要在里面。
3. 仓库页面 → **Settings → Pages** → Source 选 **Deploy from a branch**，Branch 选 **main**，文件夹选 **/docs** → Save。
4. 1–2 分钟后，页面顶部会显示网址：`https://你的用户名.github.io/temporal-city/`。
5. 在 Canvas 提交这个网址和仓库地址 `https://github.com/你的用户名/temporal-city`。

修改了 `static/` 里的页面后，重新生成 `docs/` 再上传：

```bat
py tools\build_pages.py
```

API key 只保存在本机数据库里，不会进入 `docs/`。上传前确认 `data/temporal_city.db` 里没有填写你自己的 key（或不上传这个文件）。

## 2b. 带 Collector 的在线版（Render，可选）

在线版是**只读演示**：同学可以浏览 Story、Atlas、Collector 里已经采集好的数据、证据和验证结果，但不能启动新的采集，也不能改设置。采集请在自己电脑上做，做完再部署。

1. 在自己电脑上用 Collector 采集好数据（数据在 `data/temporal_city.db`）。
2. 把整个 `temporal_city` 文件夹上传到一个 GitHub 仓库（数据库文件也一起上传）。
3. 登录 https://render.com → **New → Blueprint** → 选这个仓库。它会读取 `render.yaml` 和 `Dockerfile` 自动部署。
4. 几分钟后得到 `https://temporal-city-xxxx.onrender.com`，发给同学即可。

说明：Render 免费版闲置一段时间后会休眠，第一次打开要等 30–60 秒。在线版不会保存新数据，重启后恢复成你上传的数据库。

## 3. 更新 Atlas

Atlas 页面由你们的 dashboard 生成。dashboard 改了以后：

```bat
copy 你的新dashboard.html tools\atlas_source.html
py tools\build_atlas.py
```

`build_atlas.py` 会重新加上 GFA 图层、离线底图、导航和数据源切换。如果它报 “expected 1 got 0”，说明 dashboard 里对应的那段代码改了，需要同步修改 `build_atlas.py` 里那一行。

---

## Atlas 里 COLLECTOR DATABASE 显示 0 个 POI？

Atlas 读的是**当前正在运行的 `py app.py` 所在文件夹**里的 `data/temporal_city.db`。黑色窗口启动时会打印数据库路径和每个研究范围的 POI 数；Atlas 显示 0 时，页面顶部也会写出它读的是哪个文件、里面有什么。

- **数据库是空的（0 POIs）**：你采集的数据在另一个项目文件夹里（每个副本有自己的数据库），或者解压新版本时覆盖了数据库。从采集时用的那个文件夹运行 `py app.py`，或者把那里的 `data/temporal_city.db`（如果旁边还有 `-wal` 文件，一起复制）复制过来。**更新包从 v9 起不再附带数据库文件**，解压覆盖不会再动你的数据。
- **有 POI，但不在三个案例区**：POI 所在研究范围的名字要包含 Bencoolen / Tanjong Pagar / Promenade（中文名也可以），或者 POI 位于三个站点 400 m 范围内。
- **在线版（Render）是 0**：在线版用的是你上传到 GitHub 的数据库文件。旧版本的新数据先写在 `temporal_city.db-wal` 里，而这个文件不会上传。现在程序会自动把数据写回 `temporal_city.db`（写入后几秒内、每次采集结束、关闭程序时）。用新版本运行一次 `py app.py` 再关掉，然后重新上传 `temporal_city.db`。

## 采集跑不动 / 一直卡在 Discovering？

1. 先确认打开的是这个版本：Collector 页标题是 **Build the dataset.**，右上角有 STORY / COLLECTOR / ATLAS 切换。如果看到 “Discover places. Extract their hours.” / “Start autonomous discovery”，那是旧平台——关掉它的黑色窗口。
2. 进入 **⚙ Settings → Test connections**，看看哪些服务连得上：
   - 三个 Overpass 全部 ✗ → POI 发现无法运行。如果你在中国大陆，打开 VPN 客户端，把它的本地代理地址填进 **Proxy**（Clash 默认 `http://127.0.0.1:7890`，v2rayN 默认 `http://127.0.0.1:10809`），点 Save，再测一次。
   - DuckDuckGo ✗、Bing ✓ → 把 Search engine 设为 **Bing only**。
   - 地图底图 ✗ → 地图背景是空白的，但不影响采集。
3. 现在每个 Overpass 服务器最多连接 12 秒、等待 75 秒，全部失败会直接报错，不会再无限转圈。Log 里会写清楚是哪一台、什么原因。

---

## 4. Collector 的步骤

页面标题下面有一个流程面板：**00 Setup**（可选：Google Places API key、AI 模型、代理、连接测试）→ 6 个阶段，点任意一步可跳转；下面的信息框说明这一步要做什么、目前完成了多少，右边是大的 Next 按钮。顶部导航同样带编号和 ✓。6 个阶段是：**01 Area · 02 Discover · 03 Hours**（= 下表 03 Retrieve + 04 Google check，页内切换）**· 04 Review**（= 05 Records + 06 Validate）**· 05 Explore · 06 Export**，Settings 在最右。研究范围列表上方有 Select all / Clear selection，勾选会记在这台电脑上。

| 步骤 | 做什么 | 数据来源 |
|---|---|---|
| **01 Area** | 选研究范围：三个案例站点（一键）、任意 MRT/LRT 站 + 半径、地图上点选、上传 GeoJSON 多边形、或全部 190 个站点 | `data/stations.json`（由 LTA 出口数据计算的站点中心） |
| **02 Discover** | 自动发现范围内所有 POI，去掉长椅/停车场/厕所/ATM 等，分成六类 | OpenStreetMap Overpass API（免费、无需 key） |
| **03 Retrieve** | 为每个 POI 找营业时间 | ① OSM `opening_hours` ② Google Places（可选）③ 商户网站 + 网页搜索 |
| **04 Google check** | 自动来源没找到的 POI 排成队列：每个 POI 自动在旁边标签页打开 Google 搜索，你把 Google 商家卡上的营业时间表复制粘贴进来（英文或中文界面都行，如“星期一 上午11:00–晚上10:00”），系统自动解析、预览，Ctrl+Enter 保存并跳到下一个。保存为研究者核实记录（`verified`），Google 链接作为证据 | 你的浏览器 |
| **05 Records** | 查看每个 POI 的所有来源、原文证据、来源链接、爬取日志；可手动录入/更正 | — |
| **06 Validate** | 人工抽样审核、来源间一致性、估算回测 | — |
| **07 Explore** | 24 小时可用性曲线 + 地图随时间变化 | — |
| **08 Export** | CSV / GeoJSON | — |

### 03 Retrieve 的具体流程

对每个 POI：

1. **OSM 标签**：如果有 `opening_hours`，按 OSM 语法解析 → 标为 `observed`。
2. **Google Places（可选）**：用你自己的 API key 做 Text Search，按距离（≤150 m）和名称相似度匹配，读取 `regularOpeningHours`；同时会标出“永久停业”。设置里有每次运行的调用上限，防止超额收费。
3. **网页**：
   - 网址来源：OSM 的 `website` 标签 → DuckDuckGo 搜索 `"店名" 街道 Singapore opening hours` → Wikidata 品牌官网。
   - 遵守 robots.txt，每个域名间隔 1.5 秒，以研究爬虫身份访问。
   - 先找网页里的 **schema.org 结构化数据**（`openingHoursSpecification`，可信度最高）。
   - 没有的话，截取页面中营业时间附近的文字，用**规则解析器**（支持 `Mon–Fri 11am–10pm`、`1000hrs–2200hrs`、`12nn`、`Daily`、`Weekdays`、跨午夜等）和/或 **AI 模型**转成 Mon–Sun 时间表。
   - 页面里没有出现店名的，丢弃（防止拿到别家的时间）；如果页面有多个分店，优先选出现该 POI 地址/邮编的那段。
   - 首页没有时间时，会跟进同站的 Contact / Outlets / Location 页面。
4. 打开 **Cross-check**（默认开）时，即使已经找到一个来源，也会继续找第二个，用于交叉验证。

每一条结果都单独保存（来源、方法、URL、原文证据、可信度），不会互相覆盖。

### AI 模型（可选）

设置里选择：

- **None**：只用结构化数据 + 规则解析，完全不用 AI。
- **Ollama**：本机免费模型（先安装 Ollama 并 `ollama pull qwen2.5:7b`）。
- **OpenAI 兼容接口**：Gemini 免费额度、Groq 免费额度、DeepSeek、OpenAI 等（有预设按钮）。
- **Anthropic Claude API**。

**防幻觉检查**：模型必须原样引用它依据的句子，如果这句话不在网页原文里，结果直接作废。

### 为什么不让程序自动去读 Google 搜索页？

Google 禁止程序自动抓取搜索结果页（robots.txt 和服务条款），自动访问几次就会出现验证码并封 IP，结果不可靠，也不能写进研究方法。合规的两条路：

1. **Google Places API**（全自动，数据和搜索页右侧的商家卡相同）：Settings 里填 API key。
2. **04 Google check**（半自动）：程序负责排队、打开搜索、解析和记录，人只负责复制粘贴。熟练后大约 10–15 秒一个 POI。

### 跑完 Retrieve 还是很多 missing？

看左下角 Log 末尾的 **Summary**，它会统计这次运行每种失败原因的次数（例如 `search: 0 results`、`fetch: HTTP 403`、`page does not mention the place`）。也可以导出 `crawl_attempts.csv` 查看每个 POI 尝试过的每个网址。

---

## 5. 质量标签（回应老师关于验证的意见）

| 标签 | 含义 | 默认是否进入分析 |
|---|---|---|
| `verified` | 两个**独立**来源（不同来源类型或不同网站）在一周 168 小时中 ≥90% 一致；或研究者人工确认/录入 | ✅ |
| `observed` | 只有 OSM 标签 | ✅ |
| `retrieved` | 只有一个网页或 Google 来源，未确认 | ✅ |
| `conflict` | 有多个来源但不一致，需要人工看 | ❌（可勾选） |
| `estimated` | 用同类 POI（同一 OSM 类型）的逐小时多数投票估算 | ❌（可勾选） |
| `missing` | 没有找到 | — |

**估算数据默认不进入分析和导出的可用性曲线**——这直接回应了老师的担心：如果用估算值训练模型，模型可能学到的是估算规则本身，而不是城市里的真实关系。

### 06 Validate 的三项检查

1. **人工审核（分层随机抽样）**：每种来源/方法随机抽 N 条，你对照官网、Google Maps、电话或实地核对，点 correct / incorrect / unsure。系统按方法报告准确率和 95% Wilson 置信区间。判错的记录会从最终值中剔除；如果填了正确时间，会成为 `verified` 的人工记录。
2. **来源间一致性**：所有同时有两个独立来源的 POI，按来源组合统计平均一致率和 ≥90% 的比例（例如 Google vs 网页规则解析）。
3. **估算回测（leave-one-out）**：把已知时间的 POI 逐个藏起来，用同类 POI 估算，再和真实值比较。这给出估算方法的误差，用来论证估算数据是否可以用、能用到什么程度。

---

## 6. 可用性计算

- 一个 POI 在某小时 *h* 算“营业”：只要 [*h*:00, *h*+1:00) 这一小时内有任何时间营业就算（07:00–18:00 → 07 到 17 点营业、18 点不营业；11:30 开门 → 11 点那一格算营业）。Collector、Atlas、Story 三处用同一条规则（`core/hours.py` 的 `to_matrix`），单元测试会检查三者一致。注意：proposal 表 2.3 用的是“整点那一刻是否营业”，写报告时请说明改成了这条规则。跨午夜的时间会正确延伸到第二天。
- **相对可用性** = 营业的 POI ÷ 有可用记录的 POI（proposal §2.3）。
- **绝对可用性** = 营业的 POI 数量（老师建议同时看两者）。
- **工作日 / 周六 / 周日**分开计算（老师建议区分工作日和周末）；工作日为周一至周五的平均值。
- 表格中的 **Coverage** = 有可用记录的 POI ÷ 全部 POI；低于 50% 会标红提醒。

---

## 7. 导出文件

| 文件 | 内容 |
|---|---|
| `pois.csv` / `pois.geojson` | 每个 POI 一行：类别、标签、最终来源、可信度、一致率、Mon–Sun 时间、来源 URL（GeoJSON 可直接拖进 QGIS） |
| `hourly_matrix.csv` | POI × 星期 × 小时，营业 = 1 / 关门 = 0 |
| `availability_profiles.csv` | 区域 × 类别 × 工作日/周六/周日 × 小时：营业数量、相对比例、覆盖率（即目标变量 Y） |
| `evidence_sources.csv` | 所有来源的所有记录和原文证据 |
| `crawl_attempts.csv` | 每个尝试过的 URL 及结果（解释为什么缺数据） |
| `audits.csv` | 人工审核结果 |

---

## 8. 已知限制（写报告时可以直接说明）

- **DuckDuckGo 搜索可能限流或在中国大陆无法访问**。连不上时会自动改用 Bing（Search engine = Auto）；大批量运行建议分批（Max POIs per run）。
- **Google Places 收费**：超出每月免费额度后按次计费，请先查看 Google 当前价格，并在设置中设定调用上限。
- **很多小商户（尤其熟食中心摊位）没有网站**，网页来源对它们帮助有限；这类 POI 更依赖 Google 或人工核对。这是 proposal §4.1 中提到的数据偏差，`crawl_attempts.csv` 可以量化它。
- Facebook / Instagram / Google Maps 页面不抓取（需要登录或禁止爬取）。
- 公共假期规则（PH）不计入；季节性规则会被跳过并记录。
- OSM 数据本身可能过时，所以 `observed` 也建议纳入人工抽样审核。

---

## 9. 文件结构

```
app.py               网站入口：Story / Atlas / Collector / Information + 采集 API + 后台任务
core/atlas_bridge.py 把 Collector 数据转换成 Atlas 的数据格式（含地块关联）
core/discovery.py    Overpass 查询、六类分类规则、面内判断
core/crawler.py      网页搜索、抓取、schema.org 解析、文字片段提取
core/net.py          robots.txt、限速、代理
core/hours.py        OSM / 自由文字（中英文）/ schema.org / Google 时间格式解析、168 小时矩阵、一致率
core/llm.py          可选 AI 抽取 + 原文引用检查
core/google_places.py 可选 Google Places 查询
core/pipeline.py     流程编排、来源整合与质量标签、估算、审核抽样
core/analysis.py     可用性、覆盖率、验证统计、估算回测
core/export.py       导出
static/index.html    Story（landing page）
static/atlas.html    Atlas（由 tools/build_atlas.py 生成，不要直接改）
static/collector.html + app.js + style.css   Collector 界面（沿用 Atlas 的样式）
static/vendor/       MapLibre、Chart.js（本地文件，不依赖外网 CDN）
tools/               Atlas 源文件和生成脚本
Dockerfile, render.yaml  在线部署（只读演示）
tests/test_core.py   单元测试：py tests/test_core.py
```
