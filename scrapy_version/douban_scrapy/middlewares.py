import random
import time
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.http import HtmlResponse
from utils.user_agents import USER_AGENTS
from utils.logger import logger

class RandomUserAgentMiddleware(UserAgentMiddleware):
    def process_request(self, request, spider):
        user_agent = random.choice(USER_AGENTS)
        request.headers['User-Agent'] = user_agent
        # 动态设置 Referer
        if 'Referer' not in request.headers:
            request.headers['Referer'] = 'https://movie.douban.com/'
        return None

class RetryMiddleware:
    def __init__(self, max_retry_times=3, backoff_base=30):
        self.max_retry_times = max_retry_times
        self.backoff_base = backoff_base

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            max_retry_times=crawler.settings.get('MAX_RETRY_TIMES', 3),
            backoff_base=crawler.settings.get('RETRY_BACKOFF_BASE', 30)
        )

    def process_response(self, request, response, spider):
        if response.status in [403, 429, 500, 502, 503, 504]:
            retries = request.meta.get('retry_times', 0) + 1
            if retries <= self.max_retry_times:
                # 指数退避：30s, 60s, 120s...
                wait = self.backoff_base * (2 ** (retries - 1))
                logger.warning(f"触发反爬 ({response.status})，等待 {wait}s 后重试 ({retries}/{self.max_retry_times}): {response.url}")
                time.sleep(wait)
                retry_req = request.copy()
                retry_req.meta['retry_times'] = retries
                retry_req.dont_filter = True
                return retry_req
            else:
                logger.error(f"重试次数耗尽，放弃请求: {response.url}")
        return response

class SessionWarmupMiddleware:
    """在爬虫启动时先访问豆瓣首页建立会话，获取 cookies"""

    def __init__(self):
        self._warmed_up = False

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        if not self._warmed_up:
            logger.info("正在预热会话（访问豆瓣首页获取 cookies）...")
            import requests as req
            try:
                resp = req.get(
                    'https://movie.douban.com/',
                    headers={'User-Agent': random.choice(USER_AGENTS)},
                    timeout=15
                )
                cookies = resp.cookies.get_dict()
                for key, value in cookies.items():
                    request.cookies[key] = value
                logger.info(f"会话预热完成，获取 {len(cookies)} 个 cookies")
            except Exception as e:
                logger.warning(f"会话预热失败: {e}")
            self._warmed_up = True
        return None
