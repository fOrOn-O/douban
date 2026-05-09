import os
from tqdm import tqdm
from utils.logger import logger

class PosterDownloader:
    def __init__(self, driver):
        self.driver = driver
    
    def download_all_posters(self, movies):
        logger.info("跳过海报下载（为了快速完成项目，可后续单独下载）")
        for movie in movies:
            movie['poster_path'] = None
        return movies