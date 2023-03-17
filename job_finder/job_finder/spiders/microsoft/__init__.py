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
            ],))

    def parse(self, response):
        all_job_posts = response.xpath(
            '//*[@class="jobs-list-item"]//div[@class="information"]')
        if len(all_job_posts) == 0:
            self.logger.info(f"No job posts found for {response.url}")
            return

        count = 0
        for i, each in enumerate(all_job_posts):
            try:
                jobitem = self.parse_job_item(each)
                if jobitem is not None:
                    yield jobitem
                    count += 1
                else:
                    continue
            except:
                self.logger.error(
                    f"Error parsing job item {i} in {response.url}")
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
                ],))

    def parse_job_item(self, post_item: Selector):
        title = post_item.xpath('.//*[@class="job-title"]/text()').get()
        # if title contains any keyword from MICROSOFT_EXCLUDE_KEY_WORDS, skip it
        if any(keyword in title for keyword in self.settings.get("MICROSOFT_EXCLUDE_KEY_WORDS")):
            return None

        location = post_item.xpath(
            './/*[@class="job-location"]/text()').get().strip()
        # if location doesn't contain any country in setting's MICROSOFT_COUNTRYS, skip it
        if not any(country in location for country in self.settings.get("MICROSOFT_COUNTRYS")):
            return None

        url = post_item.xpath(
            './/*[@class="job-title"]/parent::a/@href').get()

        # example url: https://careers.microsoft.com/students/us/en/job/1516287/Microsoft-Discovery-Program-High-School-Opportunities
        # parse job_id from url, eg: 1516287, using regrex, regrex should consider /1516287/
        job_id = re.search(r'\/(\d+)\/', url).group(1)

        date = post_item.xpath(
            './/*[contains(@class, "job-date")]/text()').get()
        date = parser.parse(date).date()

        description = post_item.xpath(
            './/*[contains(@class, "description")]/text()').get().replace("\u202F", "")

        # either title or description should contain al leat one keyword from MICROSOFT_KEY_WORDS
        # use cleaner code without any()
        for keyword in self.settings.get("MICROSOFT_KEY_WORDS"):
            keyword = keyword.lower()
            if keyword in title.lower() or keyword in description.lower():
                break
        else:
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
        print(item)
        return item
