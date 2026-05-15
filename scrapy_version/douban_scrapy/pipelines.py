import json
import csv
import os
import tempfile
from database.db_connector import DBConnector
from config import CSV_DIR, JSON_DIR
from utils.logger import logger

class MySQLPipeline:
    def open_spider(self, spider):
        self.db = None
        try:
            self.db = DBConnector()
        except Exception as e:
            logger.warning(f"MySQL不可用，跳过数据库存储: {e}")
    
    def close_spider(self, spider):
        if self.db:
            self.db.close()
    
    def process_item(self, item, spider):
        if not self.db:
            return item
        
        if item.__class__.__name__ == 'MovieItem':
            try:
                self.db.insert_movie(dict(item))
                logger.debug(f"电影数据已保存: {item['title_cn']}")
            except Exception as e:
                logger.error(f"保存电影数据失败: {e}")
        
        elif item.__class__.__name__ == 'CommentItem':
            try:
                movie_id = self.db.get_movie_id_by_url(item['movie_url'])
                if movie_id:
                    comment_data = dict(item)
                    comment_data['movie_id'] = movie_id
                    del comment_data['movie_url']
                    self.db.insert_comment(comment_data)
                    logger.debug(f"评论数据已保存: {item['reviewer']}")
            except Exception as e:
                logger.error(f"保存评论数据失败: {e}")
        
        return item

class JsonPipeline:
    def open_spider(self, spider):
        self.movies_path = os.path.join(JSON_DIR, 'movies_scrapy.json')
        self.comments_path = os.path.join(JSON_DIR, 'comments_scrapy.json')
        self.movies_tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', dir=JSON_DIR, delete=False, encoding='utf-8')
        self.comments_tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', dir=JSON_DIR, delete=False, encoding='utf-8')
        self.movies_tmp.write('[\n')
        self.comments_tmp.write('[\n')
        self.first_movie = True
        self.first_comment = True
        self.movie_count = 0
        self.comment_count = 0

    def close_spider(self, spider):
        try:
            self.movies_tmp.write('\n]')
            self.comments_tmp.write('\n]')
        except Exception:
            pass
        finally:
            self.movies_tmp.close()
            self.comments_tmp.close()

        # 有数据才替换原文件，无数据时保留原文件不变
        if self.movie_count > 0:
            os.replace(self.movies_tmp.name, self.movies_path)
            logger.info(f"JSON 电影文件已更新: {self.movie_count} 条")
        else:
            os.remove(self.movies_tmp.name)

        if self.comment_count > 0:
            os.replace(self.comments_tmp.name, self.comments_path)
            logger.info(f"JSON 评论文件已更新: {self.comment_count} 条")
        else:
            os.remove(self.comments_tmp.name)

    def process_item(self, item, spider):
        if item.__class__.__name__ == 'MovieItem':
            if not self.first_movie:
                self.movies_tmp.write(',\n')
            json.dump(dict(item), self.movies_tmp, ensure_ascii=False, indent=2, default=str)
            self.first_movie = False
            self.movie_count += 1

        elif item.__class__.__name__ == 'CommentItem':
            if not self.first_comment:
                self.comments_tmp.write(',\n')
            json.dump(dict(item), self.comments_tmp, ensure_ascii=False, indent=2, default=str)
            self.first_comment = False
            self.comment_count += 1

        return item

class CsvPipeline:
    def open_spider(self, spider):
        self.movies_path = os.path.join(CSV_DIR, 'movies_scrapy.csv')
        self.comments_path = os.path.join(CSV_DIR, 'comments_scrapy.csv')
        self.movies_tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', dir=CSV_DIR, delete=False, newline='', encoding='utf-8-sig')
        self.comments_tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', dir=CSV_DIR, delete=False, newline='', encoding='utf-8-sig')
        self.movies_writer = None
        self.comments_writer = None
        self.movie_count = 0
        self.comment_count = 0

    def close_spider(self, spider):
        try:
            self.movies_tmp.close()
            self.comments_tmp.close()
        except Exception:
            pass

        if self.movie_count > 0:
            os.replace(self.movies_tmp.name, self.movies_path)
            logger.info(f"CSV 电影文件已更新: {self.movie_count} 条")
        else:
            os.remove(self.movies_tmp.name)

        if self.comment_count > 0:
            os.replace(self.comments_tmp.name, self.comments_path)
            logger.info(f"CSV 评论文件已更新: {self.comment_count} 条")
        else:
            os.remove(self.comments_tmp.name)

    def process_item(self, item, spider):
        if item.__class__.__name__ == 'MovieItem':
            if not self.movies_writer:
                self.movies_writer = csv.DictWriter(self.movies_tmp, fieldnames=item.keys())
                self.movies_writer.writeheader()
            self.movies_writer.writerow(dict(item))
            self.movie_count += 1

        elif item.__class__.__name__ == 'CommentItem':
            if not self.comments_writer:
                self.comments_writer = csv.DictWriter(self.comments_tmp, fieldnames=item.keys())
                self.comments_writer.writeheader()
            self.comments_writer.writerow(dict(item))
            self.comment_count += 1

        return item
