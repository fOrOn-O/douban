import pandas as pd
import numpy as np
from database.db_connector import DBConnector
from config import CSV_DIR
from utils.logger import logger

class DataCleaner:
    def __init__(self):
        self.db = DBConnector()
    
    def load_data_from_db(self):
        logger.info("从数据库加载数据")
        
        movies_df = pd.DataFrame(self.db.execute_query("SELECT * FROM movies"))
        comments_df = pd.DataFrame(self.db.execute_query("SELECT * FROM comments"))
        
        logger.info(f"加载了{len(movies_df)}部电影和{len(comments_df)}条评论")
        return movies_df, comments_df
    
    def clean_movies_data(self, df):
        logger.info("开始清洗电影数据")
        
        # 处理缺失值
        df['title_en'] = df['title_en'].fillna('')
        df['director'] = df['director'].fillna('未知')
        df['actors'] = df['actors'].fillna('未知')
        df['summary'] = df['summary'].fillna('暂无简介')
        df['duration'] = df['duration'].fillna('未知')
        df['genres'] = df['genres'].fillna('未知')
        
        # 类型转换
        df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce').fillna(0).astype(int)
        df['rating_count'] = df['rating_count'].astype(int)
        
        # 去重
        df = df.drop_duplicates(subset=['detail_url'])
        
        # 处理类型字段，拆分为列表
        df['genres_list'] = df['genres'].str.split('/')
        
        logger.info("电影数据清洗完成")
        return df
    
    def clean_comments_data(self, df):
        logger.info("开始清洗评论数据")
        
        # 处理缺失值
        df['rating'] = df['rating'].fillna(0)
        df['comment_time'] = pd.to_datetime(df['comment_time'], errors='coerce')
        
        # 去除空评论
        df = df[df['content'].str.strip() != '']
        
        # 去重
        df = df.drop_duplicates(subset=['movie_id', 'reviewer', 'content'])
        
        logger.info("评论数据清洗完成")
        return df
    
    def save_cleaned_data(self, movies_df, comments_df):
        movies_path = f"{CSV_DIR}/movies_cleaned.csv"
        comments_path = f"{CSV_DIR}/comments_cleaned.csv"
        
        movies_df.to_csv(movies_path, index=False, encoding='utf-8-sig')
        comments_df.to_csv(comments_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"清洗后的数据已保存到: {movies_path} 和 {comments_path}")
    
    def run(self):
        movies_df, comments_df = self.load_data_from_db()
        movies_cleaned = self.clean_movies_data(movies_df)
        comments_cleaned = self.clean_comments_data(comments_df)
        self.save_cleaned_data(movies_cleaned, comments_cleaned)
        self.db.close()
        
        return movies_cleaned, comments_cleaned
