# 豆瓣电影Top250 爬虫与智能分析平台

Python 网络爬虫期末大作业 | 个人独立完成项目

## 项目概述

本项目围绕豆瓣电影 Top250 完成数据采集、存储、清洗、统计分析、情感分析与可视化展示，由本人独立完成。项目同时提供 `requests + BeautifulSoup/lxml` 基础爬虫、`Selenium` 动态详情页爬虫和 `Scrapy` 框架重构版本。

当前项目的主流程是：先用 `requests + BeautifulSoup` 抓取 Top250 列表页基础信息，再用 `Selenium` 进入详情页和短评页补充片长、类型、IMDb、评论等数据，随后保存到 CSV，并尝试同步写入 MySQL。分析模块会优先读取 MySQL；如果数据库不可用或电影表为空，才会回退读取 CSV。

需要注意：字段缺失不一定是程序异常。部分字段本身依赖详情页解析或海报下载，例如 `duration`、`imdb_rating`、`poster_path`。如果详情页加载失败、遇到反爬验证、页面结构变化，或者未开启海报下载，这些字段可能为空。

## 功能对应课程要求

### 1. 基础爬取模块

- 使用 `requests + BeautifulSoup/lxml` 爬取 Top250 全量列表页，共 10 页。
- 提取字段：
  - 排名
  - 中文标题
  - 英文标题
  - 评分
  - 评价人数
  - 导演
  - 主演
  - 简介
  - 详情链接
- 反爬与健壮性：
  - 随机 User-Agent 池
  - 随机请求延时
  - 超时、403、429、5xx 重试
  - 可选免费代理池轮换
  - robots.txt 检查日志

核心文件：

```text
requests_version/basic_spider.py
requests_version/anti_crawl.py
utils/user_agents.py
```

### 2. 进阶详情与动态爬取模块

- 使用 Selenium 无头浏览器进入详情页。
- 额外提取：
  - 上映年份
  - 片长
  - 类型
  - IMDb 评分
  - 至少前 15 条短评
- 短评字段：
  - 评论者
  - 评分
  - 内容
  - 时间
- 支持短评“加载更多”动态内容处理。
- 支持电影海报下载，并使用 `.part` 临时文件和 `Range` 请求实现断点续传。
- 默认运行 `python main.py --requests` 时不会下载海报，因此 `poster_path` 通常为空；需要加 `--download-posters` 或单独运行 `--posters` 才会写入海报路径。
- 短评时间保存到 `comments.comment_time`，不是 `movies` 表字段。
- 详情页会检测豆瓣访问限制页、验证码页和无效页面；如果详情页无效，会保留列表页基础数据，不再用空的详情字段覆盖已有字段。
- 详情页字段采用“解析到再更新”的策略，例如只有成功解析到 `duration`、`genres`、`imdb_rating` 时才写入对应字段。

核心文件：

```text
requests_version/selenium_driver.py
requests_version/detail_spider.py
requests_version/image_downloader.py
```

### 3. 数据存储与 Scrapy 框架重构

- MySQL 存储：
  - `movies` 主表（含 `created_at` / `updated_at` 自动时间戳）
  - `comments` 短评表（含 `updated_at`，`movie_id + reviewer` 唯一索引防重复）
  - 使用外键关联
  - `insert_movie` 使用 `IFNULL(NULLIF(...))` 防止空值覆盖已有有效数据
  - `insert_comment` 使用 `ON DUPLICATE KEY UPDATE` 实现幂等插入，重复爬取不产生冗余记录
  - `DBConnector` 支持连接断开自动重连（`ping` + 自动 `reconnect`）
  - `created_at` 表示首次插入时间，重复爬取不会改变；判断记录是否被更新应查看 `updated_at`
  - 已有电影记录重复时，当前主要更新 `rating`、`rating_count`、`director`、`actors`、`summary`、`release_year`、`duration`、`genres`、`imdb_rating`、`poster_path`
  - `title_cn`、`title_en`、`detail_url`、`created_at` 不会在重复写入时主动覆盖更新
  - 如果本次爬到的是空字符串或 `NULL`，数据库会尽量保留旧值，避免把已有有效数据覆盖为空
- 数据库迁移：
  - `database/migrate.py` 幂等迁移脚本，可安全重复执行
  - 自动添加 `updated_at` 字段、清理重复评论、建立唯一索引
- CSV 备份：
  - `data/csv/movies_requests.csv`
  - `data/csv/comments_requests.csv`
  - `data/csv/movies_cleaned.csv`
  - `data/csv/comments_cleaned.csv`
- JSON 备份：
  - Scrapy Pipeline 输出到 `data/json`
- Scrapy 重构内容：
  - Item / Spider / Pipeline / Downloader Middleware
  - 随机 UA 中间件
  - 下载延时 5 秒 + 随机浮动
  - 启用 AutoThrottle 自适应限速
  - 重试中间件处理 403、429、5xx 等异常响应
  - 会话预热中间件（启动时访问豆瓣首页获取 cookies）
  - 并发控制（并发数 1）

核心文件：

```text
database/schema.sql
database/db_connector.py
database/migrate.py
scrapy_version/douban_scrapy/items.py
scrapy_version/douban_scrapy/spiders/movie_spider.py
scrapy_version/douban_scrapy/pipelines.py
scrapy_version/douban_scrapy/middlewares.py
scrapy_version/douban_scrapy/settings.py
```

### 4. 数据分析与可视化模块

- 使用 pandas 完成：
  - 缺失值处理
  - 类型转换
  - 去重
  - CSV/数据库兜底加载
- 分析维度：
  - 高分电影 Top10
  - 导演分布
  - 类型分布
  - 评分与评价人数相关性
  - 上映年份趋势
  - 短评情感倾向
- 可视化图表：
  - 评分分布直方图
  - 类型分布饼图
  - 评分与评价人数散点图
  - 上映年份趋势线图
  - 情感分布饼图
  - 短评词云
- 情感分析：
  - `jieba` 分词
  - `SnowNLP` 情感分数
  - 正面/中性/负面比例统计
  - 分析结果自动回写数据库（不仅存 CSV）
- 可视化容错：
  - 每张图表独立生成，单张失败不影响其余图表输出

核心文件：

```text
analysis/data_cleaner.py
analysis/analyzer.py
analysis/sentiment_analysis.py
analysis/visualizer.py
```

### 5. 工程实践与优化

- 日志：
  - 文件日志（按日期滚动）
  - 控制台日志
- 进度条：
  - `tqdm`
- 异常处理：
  - 爬虫请求异常
  - 页面解析异常
  - 数据库不可用自动回退 CSV
  - 数据库连接断开自动重连
  - 可视化图表单张失败不影响其余
- 海报下载：
  - `.part` 临时文件 + `Range` 请求实现断点续传
  - 下载完成后完整性校验（文件大小 vs Content-Length）
  - 纯中文标题自动使用 MD5 哈希作为文件名，避免文件名冲突
- Scrapy 性能控制：
  - 并发数 1
  - 下载延时 5 秒 + 随机浮动
  - AutoThrottle 自适应限速，最大延迟 60 秒
  - 触发反爬或异常状态码后进行重试
  - 会话预热（启动时访问首页获取 cookies）
- 代理池：
  - 复制 `proxies.example.txt` 为 `proxies.txt`
  - 每行填写一个代理

## 项目结构

```text
douban_movie_analyzer/
├── analysis/                  # 数据清洗、统计分析、情感分析、可视化
├── data/                      # CSV、JSON、图表、海报输出
├── database/                  # MySQL连接、建表SQL、迁移脚本
│   ├── schema.sql             # 建表语句（含 updated_at 字段和评论唯一索引）
│   ├── db_connector.py        # 数据库操作（防覆盖、幂等插入、自动重连）
│   └── migrate.py             # 数据库迁移脚本（幂等执行）
├── docs/                      # 说明文档与版本对比
├── requests_version/          # requests基础爬虫 + Selenium详情爬虫
├── scrapy_version/            # Scrapy框架重构版本
├── utils/                     # 日志、User-Agent池、停用词、性能记录
│   ├── logger.py              # 双输出日志（文件+控制台）
│   ├── user_agents.py         # 随机User-Agent池
│   ├── performance_recorder.py # 运行性能自动记录与文档更新
│   └── stopwords.txt          # 中文停用词表
├── config.py                  # 全局配置（从 .env 加载）
├── main.py                    # 项目入口（CLI参数 / 交互菜单）
├── proxies.example.txt        # 代理池配置示例
└── requirements.txt           # Python依赖列表
```

## 环境准备

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

如果使用 MySQL，请先执行建表：

```bash
mysql -u root -p < database/schema.sql
```

已有数据库需执行迁移（添加 `updated_at` 字段和评论唯一索引）：

```bash
python database/migrate.py
```

如不配置 MySQL，项目会自动使用 CSV 数据进行分析。

## 运行方式

### 交互式菜单

```bash
python main.py
```

### 运行 requests + Selenium 采集

```bash
python main.py --requests
```

### 运行 requests + Selenium 并下载海报

```bash
python main.py --requests --download-posters
```

### 仅下载海报

从已有 CSV 数据中读取电影详情页链接并下载海报：

```bash
python main.py --posters
```

该命令会优先读取 `data/csv/movies_cleaned.csv`；如果不存在，则读取 `data/csv/movies_requests.csv`。

### 运行 Scrapy 爬虫

```bash
python main.py --scrapy
```

### 运行数据分析与可视化

```bash
python main.py --analysis
```

### 运行采集与分析

```bash
python main.py --all
```

`--all` 当前执行的是 requests/Selenium 爬虫加数据分析流程，默认不下载海报。如果需要在完整流程中下载海报：

```bash
python main.py --all --download-posters
```

## 代理池配置

复制示例文件：

```bash
copy proxies.example.txt proxies.txt
```

在 `proxies.txt` 中按行填写代理：

```text
http://127.0.0.1:7890
http://username:password@proxy.example.com:8080
```

没有 `proxies.txt` 时，程序自动使用直连模式。

## requests 与 Scrapy 对比

详细对比见：

```text
docs/requests_vs_scrapy_comparison.md
```

简要结论：

- `requests + BeautifulSoup` 适合快速抓取静态列表页。
- `Selenium` 适合处理详情页和短评动态加载。
- `Scrapy` 适合框架化、管道化、可扩展的大规模抓取。

## 输出结果

CSV：

```text
data/csv/
```

JSON：

```text
data/json/
```

图表：

```text
data/charts/
```

海报：

```text
data/posters/
```

## 实际字段与同步说明

### 字段来源

`movies_requests.csv` 当前字段包括：

```text
rank,title_cn,title_en,rating,rating_count,director,actors,summary,detail_url,release_year,duration,genres,imdb_rating,poster_path
```

`comments_requests.csv` 当前字段包括：

```text
movie_url,reviewer,rating,content,comment_time,sentiment
```

字段来源说明：

- `rank`、`title_cn`、`title_en`、`rating`、`rating_count`、`director`、`actors`、`summary`、`detail_url` 主要来自 Top250 列表页。
- `release_year`、`genres` 既可能来自列表页，也可能在详情页成功解析后被更完整的结果更新。
- `duration`、`imdb_rating` 主要来自详情页，详情页解析失败时可能为空。
- `poster_path` 只有下载海报后才会有值。
- `comment_time` 属于短评数据，保存在评论 CSV 和数据库 `comments` 表中。

### CSV 与数据库不一致时如何判断

- 如果 CSV 里字段为空，通常说明本次爬虫没有成功解析到该字段。
- 如果 CSV 里有值但数据库没有变化，通常需要检查数据库的重复更新策略。
- `movies.created_at` 是首次创建时间，不代表最新爬取时间；应查看 `movies.updated_at`。
- `comments.comment_time` 是评论发布时间，不会出现在 `movies` 表。
- 分析流程优先读取 MySQL。如果数据库有旧数据且不为空，即使 CSV 更新了，`python main.py --analysis` 也会优先使用数据库数据。

### 常见缺失字段解释

- `summary` 为空：部分电影列表页本身没有简介短句。
- `duration` 为空：详情页没有解析成功，或豆瓣页面结构/访问状态导致字段缺失。
- `imdb_rating` 为空：详情页未提供 IMDb 评分，或当前解析规则未匹配到评分文本。
- `poster_path` 为空：未开启海报下载，或海报元素未解析成功。
- `genres` 分隔不统一：列表页可能出现空格分隔，详情页成功解析后通常是 `/` 分隔；如果详情页无效，会保留列表页已有类型信息。

## 个人完成说明

- 本项目为个人独立完成项目，不涉及小组成员分工。
- 本人完成 `requests + BeautifulSoup` 列表页爬虫、Selenium 详情页与短评爬取、海报下载、反爬策略、代理池、MySQL/CSV/JSON 存储。
- 本人完成 Scrapy 框架重构、数据清洗、统计分析、SnowNLP 情感分析、可视化图表生成和项目文档整理。
