echo "Start time: `date`"
scrapy list|xargs -n 1 scrapy crawl -L INFO > log.txt 2>&1
python update_notion.py >> log.txt 2>&1
python verify_crawler_status.py >> log.txt 2>&1
echo "End time: `date`"