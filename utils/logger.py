import logging
import os
from datetime import datetime
from config import LOGS_DIR

def setup_logger(name='douban_spider'):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建文件处理器
    log_file = os.path.join(LOGS_DIR, f'{name}_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()
