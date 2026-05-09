import os
import hashlib
from tqdm import tqdm
from bs4 import BeautifulSoup
from config import POSTERS_DIR
from utils.logger import logger
from .anti_crawl import AntiCrawlStrategy

class PosterDownloader(AntiCrawlStrategy):
    def __init__(self):
        super().__init__()
    
    def get_poster_url(self, detail_url):
        response = self.get_with_retry(detail_url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'lxml')
        poster_img = soup.find('img', rel='v:image')
        
        if poster_img and 'src' in poster_img.attrs:
            return poster_img['src']
        return None
    
    def download_poster(self, poster_url, movie_title):
        if not poster_url:
            return None
        
        # 生成文件名
        file_ext = poster_url.split('.')[-1].split('?')[0]
        safe_title = "".join([c for c in movie_title if c.isalnum() or c in (' ', '-', '_')]).strip()
        filename = f"{safe_title}.{file_ext}"
        save_path = os.path.join(POSTERS_DIR, filename)
        
        # 检查是否已下载
        if os.path.exists(save_path):
            logger.debug(f"海报已存在: {filename}")
            return save_path
        
        try:
            response = self.session.get(poster_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(save_path, 'wb') as f, tqdm(
                desc=f"下载 {movie_title[:20]}",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                leave=False
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            logger.debug(f"海报下载完成: {filename}")
            return save_path
        
        except Exception as e:
            logger.error(f"海报下载失败: {movie_title}, 错误: {e}")
            if os.path.exists(save_path):
                os.remove(save_path)
            return None
    
    def download_all_posters(self, movies):
        logger.info("开始下载电影海报")
        
        for movie in tqdm(movies, desc="下载海报"):
            poster_url = self.get_poster_url(movie['detail_url'])
            if poster_url:
                save_path = self.download_poster(poster_url, movie['title_cn'])
                movie['poster_path'] = save_path
            else:
                movie['poster_path'] = None
                logger.warning(f"未找到海报: {movie['title_cn']}")
        
        logger.info("海报下载完成")
        return movies
