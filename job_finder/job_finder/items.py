# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobItem:
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    date: datetime
