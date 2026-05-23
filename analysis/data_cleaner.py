import pandas as pd
import numpy as np
import os
from database.db_connector import DBConnector
from config import CSV_DIR
from utils.logger import logger

class DataCleaner:
    def __init__(self, data_source='auto'):
        self.db = None
        self.data_source = data_source
    
    def load_data_from_db(self):
        logger.info("从数据库加载数据")
        self.db = DBConnector()
        
        movies_df = pd.DataFrame(self.db.execute_query("SELECT * FROM movies"))
        comments_df = pd.DataFrame(self.db.execute_query("SELECT * FROM comments"))
        
        logger.info(f"加载了{len(movies_df)}部电影和{len(comments_df)}条评论")
        return movies_df, comments_df
    
    def load_data_from_csv(self):
        logger.info("从CSV文件加载数据")
        
        movie_candidates = [
            os.path.join(CSV_DIR, 'movies_requests.csv'),
            os.path.join(CSV_DIR, 'movies_scrapy.csv'),
            os.path.join(CSV_DIR, 'movies_cleaned.csv')
        ]
        comment_candidates = [
            os.path.join(CSV_DIR, 'comments_requests.csv'),
            os.path.join(CSV_DIR, 'comments_scrapy.csv'),
            os.path.join(CSV_DIR, 'comments_cleaned.csv')
        ]
        
        def select_latest_existing_file(candidates):
            existing_files = [path for path in candidates if os.path.exists(path) and os.path.getsize(path) > 0]
            return max(existing_files, key=os.path.getmtime) if existing_files else None
        
        movies_path = select_latest_existing_file(movie_candidates)
        comments_path = select_latest_existing_file(comment_candidates)
        
        if not movies_path:
            raise FileNotFoundError("未找到可用的电影CSV数据文件")
        
        movies_df = pd.read_csv(movies_path, encoding='utf-8-sig')
        if comments_path:
            comments_df = pd.read_csv(comments_path, encoding='utf-8-sig')
        else:
            comments_df = pd.DataFrame(columns=['id', 'movie_id', 'reviewer', 'rating', 'content', 'comment_time', 'sentiment', 'created_at'])
        
        logger.info(f"从CSV加载了{len(movies_df)}部电影和{len(comments_df)}条评论")
        return movies_df, comments_df
    
    def load_data(self):
        if self.data_source == 'csv':
            logger.info("已指定数据分析来源: CSV")
            return self.load_data_from_csv()
        if self.data_source == 'db':
            logger.info("已指定数据分析来源: MySQL")
            movies_df, comments_df = self.load_data_from_db()
            if len(movies_df) == 0:
                raise ValueError("数据库电影数据为空")
            return movies_df, comments_df
        try:
            movies_df, comments_df = self.load_data_from_db()
            if len(movies_df) > 0:
                logger.info("自动选择数据分析来源: MySQL")
                return movies_df, comments_df
            logger.warning("数据库电影数据为空，改用CSV文件")
        except Exception as e:
            logger.warning(f"数据库加载失败，改用CSV文件: {e}")
        
        return self.load_data_from_csv()
    
    def clean_movies_data(self, df):
        logger.info("开始清洗电影数据")
        
        if df.empty:
            raise ValueError("电影数据为空，无法进行分析")
        
        defaults = {
            'title_en': '',
            'director': '未知',
            'actors': '未知',
            'summary': '暂无简介',
            'duration': '未知',
            'genres': '未知',
            'release_year': 0,
            'rating_count': 0,
            'rating': 0,
            'detail_url': '',
            'rank': 0
        }
        
        for column, default_value in defaults.items():
            if column not in df.columns:
                df[column] = default_value
        
        # 处理缺失值
        df['title_en'] = df['title_en'].fillna('')
        df['director'] = df['director'].fillna('未知')
        df['actors'] = df['actors'].fillna('未知')
        df['summary'] = df['summary'].fillna('暂无简介')
        df['duration'] = df['duration'].fillna('未知')
        df['genres'] = df['genres'].fillna('未知')
        
        # 类型转换
        df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce').fillna(0).astype(int)
        df['rating_count'] = pd.to_numeric(df['rating_count'], errors='coerce').fillna(0).astype(int)
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0)
        df['rank'] = pd.to_numeric(df['rank'], errors='coerce').fillna(0).astype(int)
        
        # 去重
        df = df.drop_duplicates(subset=['detail_url'])
        
        # 处理类型字段，拆分为列表
        df['genres_list'] = df['genres'].str.split('/')
        
        logger.info("电影数据清洗完成")
        return df
    
    def clean_comments_data(self, df):
        logger.info("开始清洗评论数据")
        
        required_columns = {
            'id': None,
            'movie_id': None,
            'reviewer': '',
            'rating': 0,
            'content': '',
            'comment_time': None,
            'sentiment': None,
            'created_at': None
        }
        
        for column, default_value in required_columns.items():
            if column not in df.columns:
                df[column] = default_value
        
        # 处理缺失值
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0)
        df['content'] = df['content'].fillna('').astype(str)
        df['comment_time'] = pd.to_datetime(df['comment_time'], errors='coerce')
        df['sentiment'] = pd.to_numeric(df['sentiment'], errors='coerce')
        
        # 去除空评论
        df = df[df['content'].str.strip() != '']
        
        # 去重
        df = df.drop_duplicates(subset=['movie_id', 'reviewer', 'content'])
        
        logger.info("评论数据清洗完成")
        return df
    
    def save_cleaned_data(self, movies_df, comments_df):
        movies_path = os.path.join(CSV_DIR, 'movies_cleaned.csv')
        comments_path = os.path.join(CSV_DIR, 'comments_cleaned.csv')
        
        movies_df.to_csv(movies_path, index=False, encoding='utf-8-sig')
        comments_df.to_csv(comments_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"清洗后的数据已保存到: {movies_path} 和 {comments_path}")
    
    def run(self):
        try:
            movies_df, comments_df = self.load_data()
            movies_cleaned = self.clean_movies_data(movies_df)
            comments_cleaned = self.clean_comments_data(comments_df)
            self.save_cleaned_data(movies_cleaned, comments_cleaned)
            return movies_cleaned, comments_cleaned
        finally:
            if self.db:
                self.db.close()
