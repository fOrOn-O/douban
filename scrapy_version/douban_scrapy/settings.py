# 【新增】自动添加项目根目录到模块搜索路径
import sys
import os

# 获取 settings.py 的路径
settings_path = os.path.abspath(__file__)
# 向上找 3 层：settings.py → douban_scrapy → scrapy_version → 项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(settings_path)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

BOT_NAME = "douban_scrapy"

SPIDER_MODULES = ["douban_scrapy.spiders"]
NEWSPIDER_MODULE = "douban_scrapy.spiders"

# ✅ 1. 已关闭 robots.txt 遵守
ROBOTSTXT_OBEY = False

# ✅ 2. 大幅减少并发请求（避免被封）
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
CONCURRENT_REQUESTS_PER_IP = 1

# ✅ 3. 增加下载延时（从2秒改成5-8秒）
DOWNLOAD_DELAY = 5
RANDOMIZE_DOWNLOAD_DELAY = True  # 开启随机延时

# Disable cookies (enabled by default)
COOKIES_ENABLED = True

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# ✅ 4. 【关键】补充完整的默认请求头（模拟真实Chrome浏览器）
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
    "Referer": "https://www.douban.com/",
}

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    "douban_scrapy.middlewares.RandomUserAgentMiddleware": 543,
    "douban_scrapy.middlewares.RandomDelayMiddleware": 544,
}

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    "douban_scrapy.middlewares.RetryMiddleware": 550,
}

# Enable or disable extensions
EXTENSIONS = {
    "scrapy.extensions.telnet.TelnetConsole": None,
}

# Configure item pipelines
ITEM_PIPELINES = {
    "douban_scrapy.pipelines.MySQLPipeline": 300,
    "douban_scrapy.pipelines.JsonPipeline": 301,
    "douban_scrapy.pipelines.CsvPipeline": 302,
}

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# 重试设置
MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [403, 429, 500, 502, 503, 504]