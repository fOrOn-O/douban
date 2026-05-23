import os
import time
import random
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import POSTERS_DIR, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX
from utils.logger import logger
from .anti_crawl import AntiCrawlStrategy

class PosterDownloader(AntiCrawlStrategy):
    def __init__(self, driver):
        super().__init__()
        self.driver = driver

    def has_value(self, value):
        return value is not None and str(value).strip() and str(value).strip().lower() != 'nan'

    def get_poster_url(self, detail_url):
        try:
            self.driver.get(detail_url)
            # 等待海报图片元素加载完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'img[rel="v:image"]'))
            )
            time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            poster_img = soup.find('img', rel='v:image')

            if poster_img and 'src' in poster_img.attrs:
                return poster_img['src']
            return None
        except Exception as e:
            logger.error(f"获取海报URL失败: {detail_url}, 错误: {e}")
            return None
    
    def download_poster(self, poster_url, movie_title):
        if not poster_url:
            return None

        file_ext = poster_url.split('.')[-1].split('?')[0]
        safe_title = "".join([c for c in movie_title if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_title:
            import hashlib
            safe_title = hashlib.md5(movie_title.encode('utf-8')).hexdigest()[:12]
        filename = f"{safe_title}.{file_ext}"
        save_path = os.path.join(POSTERS_DIR, filename)
        
        if os.path.exists(save_path):
            logger.debug(f"海报已存在: {filename}")
            return save_path
        
        part_path = f"{save_path}.part"
        downloaded_size = os.path.getsize(part_path) if os.path.exists(part_path) else 0
        headers = {'Range': f'bytes={downloaded_size}-'} if downloaded_size > 0 else None
        
        try:
            response = self.session.get(poster_url, stream=True, timeout=30, headers=headers)
            response.raise_for_status()
            if downloaded_size > 0 and response.status_code != 206:
                downloaded_size = 0
            
            content_length = int(response.headers.get('content-length', 0))
            total_size = downloaded_size + content_length if response.status_code == 206 else content_length
            mode = 'ab' if downloaded_size > 0 and response.status_code == 206 else 'wb'
            
            with open(part_path, mode) as f, tqdm(
                desc=f"下载 {movie_title[:20]}",
                total=total_size,
                initial=downloaded_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                leave=False
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            # 完整性校验：确认实际下载大小与预期一致
            actual_size = os.path.getsize(part_path)
            if total_size > 0 and actual_size != total_size:
                logger.warning(f"海报文件不完整: {filename} (预期 {total_size}B, 实际 {actual_size}B)")
                os.remove(part_path)
                return None

            os.replace(part_path, save_path)
            logger.debug(f"海报下载完成: {filename}")
            return save_path
        
        except Exception as e:
            logger.error(f"海报下载失败: {movie_title}, 错误: {e}")
            return None
    
    def download_all_posters(self, movies, download=True):
        if not download:
            logger.info("跳过海报下载，仅获取海报URL")
            for movie in tqdm(movies, desc="获取海报URL"):
                poster_url = self.get_poster_url(movie['detail_url'])
                if poster_url:
                    movie['poster_path'] = poster_url
                elif not self.has_value(movie.get('poster_path')):
                    movie['poster_path'] = None
            return movies

        logger.info("开始下载电影海报")

        for movie in tqdm(movies, desc="下载海报"):
            poster_url = self.get_poster_url(movie['detail_url'])
            if poster_url:
                movie['poster_path'] = poster_url
                self.download_poster(poster_url, movie['title_cn'])
            else:
                if not self.has_value(movie.get('poster_path')):
                    movie['poster_path'] = None
                logger.warning(f"未找到海报: {movie['title_cn']}")

        logger.info("海报下载完成")
        return movies
