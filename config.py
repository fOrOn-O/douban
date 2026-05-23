import os
from dotenv import load_dotenv

load_dotenv()

# 数据库配置
try:
    _db_port = int(os.getenv('DB_PORT', 3306))
except ValueError:
    _db_port = 3306

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': _db_port,
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'douban_movies'),
    'charset': 'utf8mb4'
}

# 爬虫配置
BASE_URL = 'https://movie.douban.com/top250'
REQUEST_DELAY_MIN = int(os.getenv('REQUEST_DELAY_MIN', 1))
REQUEST_DELAY_MAX = int(os.getenv('REQUEST_DELAY_MAX', 4))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
TIMEOUT = int(os.getenv('TIMEOUT', 10))
DETAIL_MAX_RETRIES = int(os.getenv('DETAIL_MAX_RETRIES', 3))
COMMENT_MAX_RETRIES = int(os.getenv('COMMENT_MAX_RETRIES', 2))
BLOCK_COOLDOWN_MIN = int(os.getenv('BLOCK_COOLDOWN_MIN', 60))
BLOCK_COOLDOWN_MAX = int(os.getenv('BLOCK_COOLDOWN_MAX', 120))
MIN_MOVIES_TO_OVERWRITE = int(os.getenv('MIN_MOVIES_TO_OVERWRITE', 200))
SCRAPY_MIN_MOVIES_TO_OVERWRITE = int(os.getenv('SCRAPY_MIN_MOVIES_TO_OVERWRITE', 200))

# Selenium配置
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'True').lower() == 'true'

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
POSTERS_DIR = os.path.join(DATA_DIR, 'posters')
CSV_DIR = os.path.join(DATA_DIR, 'csv')
JSON_DIR = os.path.join(DATA_DIR, 'json')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# 创建必要的目录
for dir_path in [DATA_DIR, POSTERS_DIR, CSV_DIR, JSON_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)
