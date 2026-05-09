import pymysql
from pymysql.cursors import DictCursor
from config import DB_CONFIG
from utils.logger import logger

class DBConnector:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = pymysql.connect(
                **DB_CONFIG,
                cursorclass=DictCursor,
                autocommit=False
            )
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def close(self):
        if self.connection and self.connection.open:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    def execute_query(self, sql, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            self.connection.rollback()
            raise
    
    def execute_update(self, sql, params=None):
        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                self.connection.commit()
                return affected_rows
        except Exception as e:
            logger.error(f"更新执行失败: {e}")
            self.connection.rollback()
            raise
    
    def insert_movie(self, movie_data):
        sql = """
        INSERT INTO movies (`rank`, title_cn, title_en, rating, rating_count, 
                           director, actors, summary, detail_url, release_year, 
                           duration, genres, imdb_rating, poster_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        rating=VALUES(rating), rating_count=VALUES(rating_count),
        director=VALUES(director), actors=VALUES(actors), summary=VALUES(summary),
        release_year=VALUES(release_year), duration=VALUES(duration),
        genres=VALUES(genres), imdb_rating=VALUES(imdb_rating),
        poster_path=VALUES(poster_path)
        """
        return self.execute_update(sql, (
            movie_data['rank'], movie_data['title_cn'], movie_data['title_en'],
            movie_data['rating'], movie_data['rating_count'], movie_data['director'],
            movie_data['actors'], movie_data['summary'], movie_data['detail_url'],
            movie_data['release_year'], movie_data['duration'], movie_data['genres'],
            movie_data['imdb_rating'], movie_data['poster_path']
        ))
    
    def insert_comment(self, comment_data):
        sql = """
        INSERT INTO comments (movie_id, reviewer, rating, content, comment_time, sentiment)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self.execute_update(sql, (
            comment_data['movie_id'], comment_data['reviewer'],
            comment_data['rating'], comment_data['content'],
            comment_data['comment_time'], comment_data.get('sentiment')
        ))
    
    def get_movie_id_by_url(self, detail_url):
        sql = "SELECT id FROM movies WHERE detail_url = %s"
        result = self.execute_query(sql, (detail_url,))
        return result[0]['id'] if result else None
