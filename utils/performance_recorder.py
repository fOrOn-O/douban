import csv
import os
from datetime import datetime

from config import BASE_DIR, CSV_DIR
from utils.logger import logger

COMPARISON_DOC_PATH = os.path.join(BASE_DIR, 'docs', 'requests_vs_scrapy_comparison.md')
PERFORMANCE_CSV_PATH = os.path.join(CSV_DIR, 'performance_records.csv')
EXPECTED_MOVIE_COUNT = 250

VERSION_CONFIG = {
    'requests': {
        'display_name': 'requests/Selenium',
        'command': 'python main.py --requests',
        'movies_file': 'movies_requests.csv',
        'comments_file': 'comments_requests.csv',
        'default_success_rate': '高',
        'note': '适合完整采集'
    },
    'scrapy': {
        'display_name': 'Scrapy',
        'command': 'python main.py --scrapy',
        'movies_file': 'movies_scrapy.csv',
        'comments_file': 'comments_scrapy.csv',
        'default_success_rate': '中',
        'note': '适合框架展示'
    },
    'analysis': {
        'display_name': '分析流程',
        'command': 'python main.py --analysis',
        'movies_file': 'movies_cleaned.csv',
        'comments_file': 'comments_cleaned.csv',
        'default_success_rate': '高',
        'note': '情感缓存后更快'
    }
}


def count_csv_rows(file_path):
    if not os.path.exists(file_path):
        return 0

    with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def format_duration(seconds):
    if seconds is None:
        return '未知'
    if seconds < 60:
        return f'{seconds:.2f}秒'
    minutes = int(seconds // 60)
    remain_seconds = seconds % 60
    return f'{minutes}分{remain_seconds:.2f}秒'


def calculate_success_rate(movie_count, success):
    if not success:
        return '失败'
    if EXPECTED_MOVIE_COUNT <= 0:
        return '未知'
    return f'{min(movie_count / EXPECTED_MOVIE_COUNT, 1):.1%}'


def load_performance_records():
    if not os.path.exists(PERFORMANCE_CSV_PATH):
        return {}

    records = {}
    with open(PERFORMANCE_CSV_PATH, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            version = row.get('version')
            if version:
                records[version] = row
    return records


def save_performance_records(records):
    fieldnames = [
        'version', 'display_name', 'command', 'movie_count', 'comment_count',
        'duration', 'success_rate', 'note', 'updated_at'
    ]
    with open(PERFORMANCE_CSV_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key in ['requests', 'scrapy', 'analysis']:
            if key in records:
                writer.writerow(records[key])


def build_markdown_table(records):
    lines = [
        '| 版本 | 运行命令 | 电影数 | 短评数 | 耗时 | 成功率 | 备注 | 更新时间 |',
        '|---|---|---:|---:|---:|---:|---|---|'
    ]

    for key, config in VERSION_CONFIG.items():
        record = records.get(key)
        if record:
            movie_count = record.get('movie_count', '待实测')
            comment_count = record.get('comment_count', '待实测')
            duration = record.get('duration', '待实测')
            success_rate = record.get('success_rate', config['default_success_rate'])
            note = record.get('note', config['note'])
            updated_at = record.get('updated_at', '待实测')
        else:
            movie_count = '待实测'
            comment_count = '待实测'
            duration = '待实测'
            success_rate = '待实测'
            note = config['note']
            updated_at = '待实测'

        lines.append(
            f"| {config['display_name']} | `{config['command']}` | {movie_count} | {comment_count} | {duration} | {success_rate} | {note} | {updated_at} |"
        )

    return '\n'.join(lines)


def update_comparison_doc(records):
    if not os.path.exists(COMPARISON_DOC_PATH):
        logger.warning(f'性能对比文档不存在，跳过更新: {COMPARISON_DOC_PATH}')
        return

    with open(COMPARISON_DOC_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    marker = '## 实测记录（自动更新）'
    marker_index = content.find(marker)
    if marker_index == -1:
        old_marker = '## 实测记录模板'
        marker_index = content.find(old_marker)
    if marker_index == -1:
        logger.warning('性能对比文档未找到实测记录模板标题，跳过更新')
        return

    before = content[:marker_index]
    table = build_markdown_table(records)
    note = '每次运行 `python main.py --requests`、`python main.py --scrapy` 或 `python main.py --analysis` 后，程序会自动统计 CSV 行数和运行耗时，并更新下表。成功率按 Top250 的 250 部电影覆盖率计算。'
    new_content = f'{before}{marker}\n\n{note}\n\n{table}\n'

    with open(COMPARISON_DOC_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)


def record_performance(version, elapsed_seconds, success=True, movie_count=None, comment_count=None):
    config = VERSION_CONFIG.get(version)
    if not config:
        logger.warning(f'未知性能记录版本: {version}')
        return

    movies_path = os.path.join(CSV_DIR, config['movies_file'])
    comments_path = os.path.join(CSV_DIR, config['comments_file'])
    if movie_count is None:
        movie_count = count_csv_rows(movies_path)
    if comment_count is None:
        comment_count = count_csv_rows(comments_path)

    records = load_performance_records()
    records[version] = {
        'version': version,
        'display_name': config['display_name'],
        'command': config['command'],
        'movie_count': str(movie_count),
        'comment_count': str(comment_count),
        'duration': format_duration(elapsed_seconds),
        'success_rate': calculate_success_rate(movie_count, success),
        'note': config['note'] if success else '本次运行异常，请查看日志',
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    save_performance_records(records)
    update_comparison_doc(records)
    logger.info(f"性能记录已更新: {config['display_name']}，电影{movie_count}部，短评{comment_count}条，耗时{format_duration(elapsed_seconds)}")
