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
        urls = [search_url.format(offset_count=ipage*10)
                for ipage in range(self.settings.get("AMAZON_LOOKUP_PAGES"))]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse, meta=dict(
                playwright=True,
                playwright_page_methods=[
                    PageMethod(
                        "evaluate", "window.scrollBy(0, document.body.scrollHeight)"),
                    PageMethod("wait_for_timeout", 1000),
                ],))

    def parse(self, response: scrapy.http.Response):
        all_job_posts = response.xpath(
            '//*[@class="job-tile"]')

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

    def parse_job_item(self, post_item: Selector):
        title = post_item.xpath(".//*[@class='job-title']/text()").get()

        # example result: "USA, TX, Austin | Job ID: 2341183", we want to parse location and id separately
        # also reverse the order of location, to be Austin, TX, USA
        location_and_id = post_item.xpath(
            ".//*[@class='location-and-id']/text()").get()
        location = location_and_id.split("|")[0].strip()
        location = ", ".join(location.split(", ")[::-1])

        job_id = location_and_id.split("|")[1].split(":")[1].strip()

        # example output: Posted March 16, 2023
        # the return value should be in type datetime.date
        date = post_item.xpath(".//*[@class='posting-date']/text()").get()
        date = date.split("Posted ")[1]
        date = parser.parse(date).date()

        description_list = post_item.xpath(
            ".//*[@class='qualifications-preview']//li")
        description = ""
        for i, each in enumerate(description_list):
            description += f"({i+1}).{each.xpath('text()').get()} "

        # if either title or description contain keywords, we will return the item
        # otherwise, return None
        key_words = self.settings.get("AMAZON_KEY_WORDS", [])
        flag_should_return_None = True
        for key_word in key_words:
            if key_word.lower() in title.lower() or key_word.lower() in description.lower():
                flag_should_return_None = False
                break
        if flag_should_return_None:
            return None

        relative_url = post_item.xpath(".//*[@class='job-link']/@href").get()
        url = self.settings.get("AMAZON_BASE_URL")+relative_url

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
