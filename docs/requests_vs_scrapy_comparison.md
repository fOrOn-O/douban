# requests/Selenium 与 Scrapy 版本对比

## 实现范围

| 维度 | requests/Selenium版本 | Scrapy版本 |
|---|---|---|
| 列表页 | requests + BeautifulSoup/lxml | Scrapy Spider + BeautifulSoup/lxml |
| 详情页 | Selenium无头浏览器 | Scrapy请求详情页 |
| 短评 | Selenium处理动态加载 | Scrapy抓取短评页面前15条 |
| 存储 | MySQL + CSV | MySQL + CSV + JSON Pipeline |
| 反爬 | 随机UA、随机延时、重试、代理池、robots检查日志 | 随机UA、随机延时、重试、Cookie、并发控制 |
| 可维护性 | 流程直观，适合动态页面 | 模块清晰，适合扩展管道和中间件 |

## 性能特点

| 指标 | requests/Selenium版本 | Scrapy版本 |
|---|---|---|
| 启动成本 | Selenium启动浏览器，较高 | 无浏览器，较低 |
| 列表页速度 | requests列表页较快 | 异步框架，理论更快 |
| 详情页/短评 | Selenium加载真实页面，较慢但稳定 | HTTP请求快，但动态内容适配能力弱 |
| 反爬压力 | 更像真实浏览器，但资源消耗大 | 可控并发，需严格限速 |
| 适用场景 | 页面结构复杂、动态加载明显 | 批量爬取、结构化管道存储 |

## 当前项目建议使用方式

1. 首次采集建议运行 `python main.py --requests`，保证详情页与短评稳定抓取。
2. 需要海报时运行 `python main.py --requests --download-posters`。
3. 需要验证Scrapy框架能力时运行 `python main.py --scrapy`。
4. 数据分析和图表生成运行 `python main.py --analysis`。

## 实测记录模板

| 版本 | 运行命令 | 电影数 | 短评数 | 耗时 | 成功率 | 备注 |
|---|---|---:|---:|---:|---:|---|
| requests/Selenium | `python main.py --requests` | 250 | 3700+ | 视网络而定 | 高 | 适合完整采集 |
| Scrapy | `python main.py --scrapy` | 待实测 | 待实测 | 视网络而定 | 中 | 适合框架展示 |
| 分析流程 | `python main.py --analysis` | 250 | 3700+ | 约10-80秒 | 高 | 情感缓存后更快 |
