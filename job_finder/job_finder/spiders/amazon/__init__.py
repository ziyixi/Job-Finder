import scrapy
from dateutil import parser
from job_finder.items import JobItem
from scrapy.selector.unified import Selector
from scrapy_playwright.page import PageMethod


class AmazonSpider(scrapy.Spider):
    name = "amazon"
    retry_xpath = '//*[@class="job-tile"]'

    def start_requests(self):
        search_url = self.settings.get("AMAZON_SEARCH_URL")
        lookup_pages = self.settings.get("AMAZON_LOOKUP_PAGES")
        urls = [search_url.format(offset_count=page * 10)
                for page in range(lookup_pages)]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse, meta=dict(
                playwright=True,
                playwright_page_methods=[
                    PageMethod(
                        "evaluate", "window.scrollBy(0, document.body.scrollHeight)"),
                    PageMethod("wait_for_timeout", 1000),
                ],
            ))

    def parse(self, response: scrapy.http.Response):
        all_job_posts = response.xpath('//*[@class="job-tile"]')

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

    def parse_job_item(self, post_item: Selector):
        title = post_item.xpath(".//*[@class='job-title']/text()").get()

        location_and_id = post_item.xpath(
            ".//*[@class='location-and-id']/text()").get()
        location = location_and_id.split("|")[0].strip()
        location = ", ".join(location.split(", ")[::-1])

        job_id = location_and_id.split("|")[1].split(":")[1].strip()

        date_text = post_item.xpath(".//*[@class='posting-date']/text()").get()
        date = date_text.split("Posted ")[1]
        date = parser.parse(date).date()

        description_list = post_item.xpath(
            ".//*[@class='qualifications-preview']//li")
        description = "".join(
            f"({index + 1}).{item.xpath('text()').get()} " for index, item in enumerate(description_list))

        key_words = self.settings.get("AMAZON_KEY_WORDS", [])
        if not any(keyword.lower() in title.lower() or keyword.lower() in description.lower() for keyword in key_words):
            return None

        relative_url = post_item.xpath(".//*[@class='job-link']/@href").get()
        url = self.settings.get("AMAZON_BASE_URL") + relative_url

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
