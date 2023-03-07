import scrapy
from dateutil import parser
from job_finder.items import JobItem
from scrapy.selector.unified import Selector


class GoogleSpider(scrapy.Spider):
    name = "google"
    retry_xpath = '//*[@id="search-results"]/li/div/a'

    def start_requests(self):
        search_url = self.settings.get("GOOGLE_SEARCH_URL")
        key_words = self.settings.get("GOOGLE_KEY_WORDS")
        urls = [f"{search_url}{key_word}" for key_word in key_words]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse, meta={"playwright": True})

    def parse(self, response):
        all_job_posts = response.xpath(
            '//*[@id="search-results"]/li/div/a')
        if len(all_job_posts) == 0:
            self.logger.info(f"No job posts found for {response.url}")
            return

        count = 0
        for i, each in enumerate(all_job_posts):
            try:
                jobitem = self.parse_job_item(each)
                if jobitem.id != None:
                    yield jobitem
                    count += 1
                else:
                    self.logger.error(
                        f"Error parsing job item {i} in {response.url}")
            except:
                self.logger.error(
                    f"Error parsing job item {i} in {response.url}")
        self.logger.info(f"Handled {count} job posts in {response.url}")

        next_page = response.xpath(
            '//a[@data-gtm-ref="search-results-next-click"]/@href').get()
        next_page_visiable = response.xpath(
            '//a[@data-gtm-ref="search-results-next-click"]/@style').get() != "display: none;"

        if (next_page is not None) and next_page_visiable:
            yield response.follow(next_page, callback=self.parse, meta={"playwright": True})

    def parse_job_item(self, post_item: Selector):
        title = post_item.xpath(
            './/h2[@itemprop="title"]/text()').get().strip()
        city_parsed = post_item.xpath(
            './/span[@itemprop="addressLocality"]/text()')
        if city_parsed:
            city = city_parsed.get().strip()
        else:
            city = ""
        country_parsed = post_item.xpath(
            './/span[@itemprop="addressCountry"]/text()')
        if country_parsed:
            country = country_parsed.get().strip()
        else:
            country = ""

        date = post_item.xpath(
            './/meta[@itemprop="datePosted"]/@content').get().strip()
        description = post_item.xpath(
            './/meta[@itemprop="description"]/@content').get().strip()
        relative_url = post_item.xpath('.//@href').get()
        # relative_url: https://careers.google.com/jobs/results/113538880541467334-student-researcher-phd-2023/?distance=50&q=phd
        # unique_id: 113538880541467334
        unique_id = post_item.xpath('.//@href').re_first(r'(\d+)-')

        item = JobItem(
            id=unique_id,
            title=title,
            company=self.name,
            location=city+country,
            description=description,
            url=self.settings.get("GOOGLE_BASE_URL") + relative_url,
            date=parser.parse(date),
        )
        return item
