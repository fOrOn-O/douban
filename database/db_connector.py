try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    pymysql = None
    DictCursor = None
from config import DB_CONFIG
from utils.logger import logger

class DBConnector:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            if pymysql is None:
                raise RuntimeError("缺少pymysql依赖，请先执行 pip install -r requirements.txt")
            self.connection = pymysql.connect(
                **DB_CONFIG,
                cursorclass=DictCursor,
                autocommit=False
            )
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        if self.connection and self.connection.open:
            self.connection.close()
            logger.info("数据库连接已关闭")

    def _ensure_connection(self):
        try:
            self.connection.ping(reconnect=False)
        except Exception:
            logger.warning("数据库连接已断开，尝试重连...")
            self.connect()

    def execute_query(self, sql, params=None):
        try:
            self._ensure_connection()
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise

    def execute_update(self, sql, params=None):
        try:
            self._ensure_connection()
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
        rating = IFNULL(NULLIF(VALUES(rating), 0), rating),
        rating_count = IFNULL(NULLIF(VALUES(rating_count), 0), rating_count),
        director = IFNULL(NULLIF(VALUES(director), ''), director),
        actors = IFNULL(NULLIF(VALUES(actors), ''), actors),
        summary = IFNULL(NULLIF(VALUES(summary), ''), summary),
        release_year = IFNULL(VALUES(release_year), release_year),
        duration = IFNULL(NULLIF(VALUES(duration), ''), duration),
        genres = IFNULL(NULLIF(VALUES(genres), ''), genres),
        imdb_rating = IFNULL(VALUES(imdb_rating), imdb_rating),
        poster_path = IFNULL(NULLIF(VALUES(poster_path), ''), poster_path)
        """
        return self.execute_update(sql, (
            movie_data.get('rank', 0), movie_data.get('title_cn', ''), movie_data.get('title_en', ''),
            movie_data.get('rating', 0), movie_data.get('rating_count', 0), movie_data.get('director', ''),
            movie_data.get('actors', ''), movie_data.get('summary', ''), movie_data.get('detail_url', ''),
            movie_data.get('release_year'), movie_data.get('duration', ''), movie_data.get('genres', ''),
            movie_data.get('imdb_rating'), movie_data.get('poster_path')
        ))
    
    def insert_comment(self, comment_data):
        sql = """
        INSERT INTO comments (movie_id, reviewer, rating, content, comment_time, sentiment)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        rating = IFNULL(VALUES(rating), rating),
        content = IFNULL(NULLIF(VALUES(content), ''), content),
        comment_time = IFNULL(VALUES(comment_time), comment_time)
        """
        return self.execute_update(sql, (
            comment_data.get('movie_id'), comment_data.get('reviewer', ''),
            comment_data.get('rating'), comment_data.get('content', ''),
            comment_data.get('comment_time'), comment_data.get('sentiment')
        ))

    def update_comment_sentiment(self, comment_id, sentiment):
        sql = "UPDATE comments SET sentiment = %s WHERE id = %s"
        return self.execute_update(sql, (sentiment, comment_id))

    def get_movie_id_by_url(self, detail_url):
        sql = "SELECT id FROM movies WHERE detail_url = %s"
        result = self.execute_query(sql, (detail_url,))
        return result[0]['id'] if result else None
