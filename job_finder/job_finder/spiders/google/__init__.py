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

        for i, each in enumerate(all_job_posts):
            try:
                jobitem = self.parse_job_item(each)
                yield jobitem
            except:
                self.logger.error(
                    f"Error parsing job item {i} in {response.url}")

    def parse_job_item(self, post_item: Selector):
        title = post_item.xpath(
            '//h2[@itemprop="title"]/text()').get().strip()
        city_parsed = post_item.xpath(
            '//span[@itemprop="addressLocality"]/text()')
        if city_parsed:
            city = city_parsed.get().strip()
        else:
            city = ""
        country_parsed = post_item.xpath(
            '//span[@itemprop="addressCountry"]/text()')
        if country_parsed:
            country = country_parsed.get().strip()
        else:
            country = ""

        date = post_item.xpath(
            '//meta[@itemprop="datePosted"]/@content').get().strip()
        description = post_item.xpath(
            '//meta[@itemprop="description"]/@content').get().strip()

        item = JobItem(
            id=f"{title}, {city}{country}",
            title=title,
            company="Google",
            location=city+country,
            description=description,
            url=self.settings.get("GOOGLE_BASE_URL") +
            post_item.xpath('//@href').get(),
            date=parser.parse(date),
        )
        return item
