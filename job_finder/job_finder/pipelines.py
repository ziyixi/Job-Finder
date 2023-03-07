# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import sqlite3


class UpdateDbPipeline:
    collection_name = 'job_items'

    def __init__(self, db_path, table_name, new_table_name):
        self.table_name = table_name
        self.db_path = db_path
        self.new_table_name = new_table_name

    def open_spider(self, spider):
        self.con = sqlite3.connect(self.db_path)
        self.cur = self.con.cursor()
        # create table_name
        self.cur.execute(f"""
        --beginsql
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            url TEXT,
            date DATE,
            lastaccess BOOLEAN,
            PRIMARY KEY(id,company)
        )
        --endsql
        """)
        # create new_table_name
        self.cur.execute(f"""
        --beginsql
        CREATE TABLE IF NOT EXISTS {self.new_table_name} (
            id TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            url TEXT,
            date DATE,
            PRIMARY KEY(id,company)
        )
        --endsql
        """)
        # delete all items from new_table_name where company = spider.name
        self.cur.execute(f"""
        --beginsql
        DELETE FROM {self.new_table_name} WHERE company = ?
        --endsql
        """, (spider.name,))
        # update lastaccess to 0 for all items from this company
        self.cur.execute(f"""
        --beginsql
        UPDATE {self.table_name} SET lastaccess = 0 WHERE company = ?
        --endsql
        """, (spider.name,))

    def close_spider(self, spider):
        self.con.commit()
        self.con.close()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            db_path=crawler.settings.get('SQLITE_DB_PATH'),
            table_name=crawler.settings.get('SQLITE_TABLE_NAME'),
            new_table_name=crawler.settings.get('SQLITE_NEW_TABLE_NAME'))

    def process_item(self, item, spider):
        self.cur.execute(
            f"""
            --beginsql
            select * from {self.table_name} where id = ? AND company = ?
            --endsql
            """, (item.id, item.company))
        result = self.cur.fetchone()

        if not result:
            # add to database
            self.cur.execute(f"""
            --beginsql
                INSERT INTO {self.table_name} (id,title,company,location,description,url,date,lastaccess) VALUES (?,?,?,?,?,?,?,?)
            --endsql
            """, (item.id, item.title, item.company, item.location, item.description, item.url, str(item.date), 1))
            # add to new_table_name
            self.cur.execute(f"""
            --beginsql
                INSERT INTO {self.new_table_name} (id,title,company,location,description,url,date) VALUES (?,?,?,?,?,?,?)
            --endsql
            """, (item.id, item.title, item.company, item.location, item.description, item.url, str(item.date)))
        else:
            # update lastaccess to 1
            self.cur.execute(f"""
            --beginsql
            UPDATE {self.table_name} SET lastaccess = 1 WHERE id = ? AND company = ?
            --endsql
            """, (item.id, item.company))

        return item
