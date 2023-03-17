import re

import scrapy
from dateutil import parser
from scrapy.selector.unified import Selector
from scrapy_playwright.page import PageMethod

from job_finder.items import JobItem


class MicrosoftSpider(scrapy.Spider):
    name = "microsoft"
    retry_xpath = '//*[@class="jobs-list-item"]//div[@class="information"]'

    def start_requests(self):
        search_url = self.settings.get("MICROSOFT_SEARCH_URL")
        yield scrapy.Request(url=search_url, callback=self.parse, meta=dict(
            playwright=True,
            playwright_page_methods=[
                PageMethod(
                    "evaluate", "window.scrollBy(0, document.body.scrollHeight)"),
                PageMethod("wait_for_timeout", 1000),
            ],
        ))

    def parse(self, response):
        all_job_posts = response.xpath(
            '//*[@class="jobs-list-item"]//div[@class="information"]')
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
            '//a[@data-ph-at-id="pagination-next-link"]/@href').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse, meta=dict(
                playwright=True,
                playwright_page_methods=[
                    PageMethod(
                        "evaluate", "window.scrollBy(0, document.body.scrollHeight)"),
                    PageMethod("wait_for_timeout", 1000),
                ],
            ))

    def parse_job_item(self, post_item: Selector):
        title = post_item.xpath('.//*[@class="job-title"]/text()').get()
        exclude_keywords = self.settings.get("MICROSOFT_EXCLUDE_KEY_WORDS")
        if any(keyword in title for keyword in exclude_keywords):
            return None

        location = post_item.xpath(
            './/*[@class="job-location"]/text()').get().strip()
        allowed_countries = self.settings.get("MICROSOFT_COUNTRYS")
        if not any(country in location for country in allowed_countries):
            return None

        url = post_item.xpath('.//*[@class="job-title"]/parent::a/@href').get()
        job_id = re.search(r'\/(\d+)\/', url).group(1)

        date = post_item.xpath(
            './/*[contains(@class, "job-date")]/text()').get()
        date = parser.parse(date).date()

        description = post_item.xpath(
            './/*[contains(@class, "description")]/text()').get().replace("\u202F", "")
        key_words = self.settings.get("MICROSOFT_KEY_WORDS")
        if not any(keyword.lower() in title.lower() or keyword.lower() in description.lower() for keyword in key_words):
            return None

        item = JobItem(
            id=job_id,
            title=title,
            company=self.name,
            location=location,
            description=description,
            url=url,
            date=date,
        )

        return item
