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
        # 检测是否被重定向到豆瓣安全挑战页面（sec.douban.com）
        if 'sec.douban.com' in response.url:
            retries = request.meta.get('retry_times', 0) + 1
            if retries <= self.max_retry_times:
                wait = self.backoff_base * (2 ** (retries - 1))
                logger.warning(f"触发安全挑战 (sec.douban.com)，等待 {wait}s 后重试 ({retries}/{self.max_retry_times}): {request.url}")
                time.sleep(wait)
                # 用原始 URL 重新发起请求，不跟随重定向
                retry_req = request.copy()
                retry_req.meta['retry_times'] = retries
                retry_req.dont_filter = True
                retry_req.cookies = {}  # 清除旧 cookies，重新获取
                return retry_req
            else:
                logger.error(f"安全挑战重试耗尽，放弃请求: {request.url}")
                return response

        if response.status in [403, 429, 500, 502, 503, 504]:
            retries = request.meta.get('retry_times', 0) + 1
            if retries <= self.max_retry_times:
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
            import urllib.request
            try:
                req = urllib.request.Request(
                    'https://movie.douban.com/',
                    headers={'User-Agent': random.choice(USER_AGENTS)}
                )
                resp = urllib.request.urlopen(req, timeout=15)
                # 从响应头中提取 cookies
                cookies = {}
                for header in resp.headers.get_all('Set-Cookie') or []:
                    parts = header.split(';')[0].split('=', 1)
                    if len(parts) == 2:
                        cookies[parts[0].strip()] = parts[1].strip()
                for key, value in cookies.items():
                    request.cookies[key] = value
                logger.info(f"会话预热完成，获取 {len(cookies)} 个 cookies")
            except Exception as e:
                logger.warning(f"会话预热失败: {e}")
            self._warmed_up = True
        return None
