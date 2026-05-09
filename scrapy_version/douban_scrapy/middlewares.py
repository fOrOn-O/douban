import random
import time
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from utils.user_agents import USER_AGENTS
from utils.logger import logger

class RandomUserAgentMiddleware(UserAgentMiddleware):
    def process_request(self, request, spider):
        user_agent = random.choice(USER_AGENTS)
        request.headers['User-Agent'] = user_agent
        return None

class RandomDelayMiddleware:
    def __init__(self, delay_min=1, delay_max=4):
        self.delay_min = delay_min
        self.delay_max = delay_max
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            delay_min=crawler.settings.get('DOWNLOAD_DELAY_MIN', 1),
            delay_max=crawler.settings.get('DOWNLOAD_DELAY_MAX', 4)
        )
    
    def process_request(self, request, spider):
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)
        return None

class RetryMiddleware:
    def __init__(self, max_retry_times=3):
        self.max_retry_times = max_retry_times
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            max_retry_times=crawler.settings.get('MAX_RETRY_TIMES', 3)
        )
    
    def process_response(self, request, response, spider):
        if response.status in [403, 429, 500, 502, 503, 504]:
            retries = request.meta.get('retry_times', 0) + 1
            if retries <= self.max_retry_times:
                logger.warning(f"重试请求 ({retries}/{self.max_retry_times}): {response.url}")
                retry_req = request.copy()
                retry_req.meta['retry_times'] = retries
                retry_req.dont_filter = True
                return retry_req
        return response
