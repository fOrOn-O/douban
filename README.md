# 豆瓣电影Top250 爬虫与智能分析平台
Python网络爬虫期末大作业 | 三人组队项目

## 项目功能
1. 基础爬虫：requests+BeautifulSoup爬取Top250列表
2. 动态爬虫：Selenium爬取详情页+短评+海报下载
3. 框架重构：Scrapy完整重构，支持MySQL/CSV/JSON存储
4. 数据分析：pandas清洗+多维度统计
5. 可视化：5+图表+词云+情感分析

## 团队分工
- 成员A：requests爬虫+Selenium+图片下载+反爬
- 成员B：Scrapy重构+MySQL+数据清洗+日志
- 成员C：数据分析+可视化+情感分析+报告+Git

## 运行步骤
1. 创建虚拟环境：python -m venv venv
2. 激活环境：venv\Scripts\activate
3. 安装依赖：pip install -r requirements.txt
4. 执行数据库脚本：database/schema.sql
5. 运行：python main.py
