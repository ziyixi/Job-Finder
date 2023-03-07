echo "Start time: `date`"
scrapy list|xargs -n 1 scrapy crawl -L INFO
echo "End time: `date`"