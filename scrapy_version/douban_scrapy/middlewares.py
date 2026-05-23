import random
from urllib.parse import parse_qs, urlparse
from twisted.internet import reactor, task
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.exceptions import IgnoreRequest
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

class DetailDelayMiddleware:
    def __init__(self, detail_delay_min=15, detail_delay_max=30, comment_delay_min=8, comment_delay_max=15):
        self.detail_delay_min = detail_delay_min
        self.detail_delay_max = detail_delay_max
        self.comment_delay_min = comment_delay_min
        self.comment_delay_max = comment_delay_max

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            detail_delay_min=crawler.settings.getfloat('DETAIL_REQUEST_DELAY_MIN', 15),
            detail_delay_max=crawler.settings.getfloat('DETAIL_REQUEST_DELAY_MAX', 30),
            comment_delay_min=crawler.settings.getfloat('COMMENT_REQUEST_DELAY_MIN', 8),
            comment_delay_max=crawler.settings.getfloat('COMMENT_REQUEST_DELAY_MAX', 15),
        )

    def process_request(self, request, spider):
        if request.meta.get('is_detail_request'):
            delay = random.uniform(self.detail_delay_min, self.detail_delay_max)
            logger.debug(f"详情页请求延迟 {delay:.1f}s: {request.url}")
            return task.deferLater(reactor, delay, lambda: None)

        if request.meta.get('is_comment_request'):
            delay = random.uniform(self.comment_delay_min, self.comment_delay_max)
            logger.debug(f"评论页请求延迟 {delay:.1f}s: {request.url}")
            return task.deferLater(reactor, delay, lambda: None)

        return None

class RetryMiddleware:
    def __init__(self, max_retry_times=3, challenge_max_retry_times=1, backoff_base=60):
        self.max_retry_times = max_retry_times
        self.challenge_max_retry_times = challenge_max_retry_times
        self.backoff_base = backoff_base

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            max_retry_times=crawler.settings.get('MAX_RETRY_TIMES', 3),
            challenge_max_retry_times=crawler.settings.get('CHALLENGE_MAX_RETRY_TIMES', 1),
            backoff_base=crawler.settings.get('RETRY_BACKOFF_BASE', 60)
        )

    def process_response(self, request, response, spider):
        # 拦截豆瓣安全挑战/访问限制页。不要重试拦截页本身，只对原始 URL 做有限冷却重试。
        block_url = self._get_block_url(response)
        if block_url:
            original_url = self._get_original_url(request, response, block_url)
            retries = request.meta.get('challenge_retry_times', 0) + 1

            if retries <= self.challenge_max_retry_times:
                wait = self.backoff_base * retries + random.uniform(10, 30)
                logger.warning(
                    f"触发豆瓣访问限制，冷却 {wait:.0f}s 后重试原始页面 "
                    f"({retries}/{self.challenge_max_retry_times}): {original_url}"
                )
                retry_req = request.replace(url=original_url)
                retry_req.meta['challenge_retry_times'] = retries
                retry_req.meta.pop('redirect_urls', None)
                retry_req.meta.pop('redirect_reasons', None)
                retry_req.dont_filter = True
                dfd = task.deferLater(reactor, wait, lambda: retry_req)
                return dfd

            logger.error(f"豆瓣访问限制重试耗尽，放弃原始请求: {original_url}")
            if request.meta.get('return_block_response'):
                return response
            raise IgnoreRequest(f"豆瓣访问限制重试耗尽: {original_url}")

        if response.status in [403, 429, 500, 502, 503, 504]:
            retries = request.meta.get('retry_times', 0) + 1
            if retries <= self.max_retry_times:
                wait = 10 * retries + random.uniform(0, 5)
                logger.warning(f"触发反爬 ({response.status})，{wait:.0f}s 后重试 ({retries}/{self.max_retry_times}): {response.url}")
                retry_req = request.copy()
                retry_req.meta['retry_times'] = retries
                retry_req.dont_filter = True
                # 非阻塞延时后重新入队
                dfd = task.deferLater(reactor, wait, lambda: retry_req)
                return dfd
            else:
                logger.error(f"重试次数耗尽，放弃请求: {response.url}")
        return response

    def _get_block_url(self, response):
        if self._is_block_url(response.url):
            return response.url

        location = response.headers.get('Location')
        if not location:
            return None

        location_url = location.decode('utf-8', errors='ignore')
        return location_url if self._is_block_url(location_url) else None

    def _is_block_url(self, url):
        return 'sec.douban.com' in url or 'douban.com/misc/sorry' in url

    def _get_original_url(self, request, response, block_url):
        redirect_urls = request.meta.get('redirect_urls') or []
        if redirect_urls:
            return redirect_urls[0]

        parsed = urlparse(block_url)
        query = parse_qs(parsed.query)
        target = query.get('r', [None])[0] or query.get('original-url', [None])[0]
        if target:
            return target

        return request.url

class SessionWarmupMiddleware:
    """在爬虫启动时先访问豆瓣首页建立会话，获取 cookies"""

    def __init__(self):
        self._warmed_up = False
        self._cookies = {}

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
                for header in resp.headers.get_all('Set-Cookie') or []:
                    parts = header.split(';')[0].split('=', 1)
                    if len(parts) == 2:
                        self._cookies[parts[0].strip()] = parts[1].strip()
                logger.info(f"会话预热完成，获取 {len(self._cookies)} 个 cookies")
            except Exception as e:
                logger.warning(f"会话预热失败: {e}")
            self._warmed_up = True
        if isinstance(request.cookies, dict):
            for key, value in self._cookies.items():
                request.cookies.setdefault(key, value)
        return None
