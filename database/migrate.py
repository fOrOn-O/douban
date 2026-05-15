"""数据库迁移脚本 - 幂等执行，可安全重复运行"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_connector import DBConnector
from utils.logger import logger


def column_exists(cursor, table, column):
    cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
    return cursor.fetchone() is not None


def index_exists(cursor, table, index_name):
    cursor.execute(f"SHOW INDEX FROM `{table}` WHERE Key_name = %s", (index_name,))
    return cursor.fetchone() is not None


def migrate():
    db = DBConnector()
    try:
        with db.connection.cursor() as cursor:
            # 1. movies 表添加 updated_at
            if not column_exists(cursor, 'movies', 'updated_at'):
                cursor.execute(
                    "ALTER TABLE movies ADD COLUMN updated_at TIMESTAMP "
                    "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at"
                )
                logger.info("movies 表已添加 updated_at 字段")
            else:
                logger.info("movies.updated_at 已存在，跳过")

            # 2. comments 表添加 updated_at
            if not column_exists(cursor, 'comments', 'updated_at'):
                cursor.execute(
                    "ALTER TABLE comments ADD COLUMN updated_at TIMESTAMP "
                    "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at"
                )
                logger.info("comments 表已添加 updated_at 字段")
            else:
                logger.info("comments.updated_at 已存在，跳过")

            # 3. 清理 comments 表中已有的重复评论（保留 id 最大的一条）
            if not index_exists(cursor, 'comments', 'idx_movie_reviewer'):
                cursor.execute("""
                    DELETE t1 FROM comments t1
                    INNER JOIN comments t2
                    ON t1.movie_id = t2.movie_id AND t1.reviewer = t2.reviewer AND t1.id < t2.id
                """)
                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"已清理 {deleted} 条重复评论")

                # 4. 添加唯一索引
                cursor.execute(
                    "ALTER TABLE comments ADD UNIQUE INDEX idx_movie_reviewer (movie_id, reviewer)"
                )
                logger.info("comments 表已添加唯一索引 idx_movie_reviewer")
            else:
                logger.info("idx_movie_reviewer 已存在，跳过")

        db.connection.commit()
        logger.info("数据库迁移完成")
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        db.connection.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    migrate()
