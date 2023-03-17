import scrapy
from dateutil import parser
from job_finder.items import JobItem
from scrapy.selector.unified import Selector
from scrapy_playwright.page import PageMethod


class GoogleSpider(scrapy.Spider):
    name = "google"
    retry_xpath = '//*[@id="search-results"]/li/div/a'

    def start_requests(self):
        search_url = self.settings.get("GOOGLE_SEARCH_URL")
        key_words = self.settings.get("GOOGLE_KEY_WORDS")
        urls = [f"{search_url}{key_word}" for key_word in key_words]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse, meta=dict(
                playwright=True,
                playwright_page_methods=[
                    PageMethod(
                        "evaluate", "window.scrollBy(0, document.body.scrollHeight)"),
                    PageMethod("wait_for_timeout", 1000),
                ],
            ))

    def parse(self, response):
        all_job_posts = response.xpath('//*[@id="search-results"]/li/div/a')

        if not all_job_posts:
            self.logger.info(f"No job posts found for {response.url}")
            return

        count = 0
        for index, post in enumerate(all_job_posts):
            try:
                jobitem = self.parse_job_item(post)
                if jobitem:
                    yield jobitem
                    count += 1
            except:
                self.logger.error(
                    f"Error parsing job item {index} in {response.url}")

        self.logger.info(f"Handled {count} job posts in {response.url}")

        next_page = response.xpath(
            '//a[@data-gtm-ref="search-results-next-click"]/@href').get()
        next_page_visible = response.xpath(
            '//a[@data-gtm-ref="search-results-next-click"]/@style').get() != "display: none;"

        if next_page and next_page_visible:
            yield response.follow(next_page, callback=self.parse, meta=dict(
                playwright=True,
                playwright_page_methods=[
                    PageMethod(
                        "evaluate", "window.scrollBy(0, document.body.scrollHeight)"),
                    PageMethod("wait_for_timeout", 1000),
                ],
            ))

    def parse_job_item(self, post_item: Selector):
        title = post_item.xpath(
            './/h2[@itemprop="title"]/text()').get().strip()
        exclude_keywords = self.settings.get("GOOGLE_EXCLUDE_KEY_WORDS")

        if any(exclude.lower() in title.lower() for exclude in exclude_keywords):
            return None

        city = post_item.xpath('.//span[@itemprop="addressLocality"]/text()').get().strip(
        ) if post_item.xpath('.//span[@itemprop="addressLocality"]/text()') else ""
        country = post_item.xpath('.//span[@itemprop="addressCountry"]/text()').get(
        ).strip() if post_item.xpath('.//span[@itemprop="addressCountry"]/text()') else ""

        date = post_item.xpath(
            './/meta[@itemprop="datePosted"]/@content').get().strip()
        description = post_item.xpath(
            './/meta[@itemprop="description"]/@content').get().strip()
        relative_url = post_item.xpath('.//@href').get()

        unique_id = post_item.xpath('.//@href').re_first(r'(\d+)-')

        key_words = self.settings.get("GOOGLE_KEY_WORDS", [])

        if not any(keyword.lower() in title.lower() or keyword.lower() in description.lower() for keyword in key_words):
            return None

        item = JobItem(
            id=unique_id,
            title=title,
            company=self.name,
            location=f"{city}{country}",
            description=description,
            url=self.settings.get("GOOGLE_BASE_URL") + relative_url,
            date=parser.parse(date),
        )
        return item
