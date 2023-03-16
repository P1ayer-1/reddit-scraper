# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from itemloaders.processors import Compose, Join, MapCompose
from scrapy import Item, Field


def clean_post_content(value):
    return value.strip().replace('\n', ' ')

class RedditItem(Item):
    title = Field()
    link = Field()
    score = Field()
    post_content = Field(
        input_processor=MapCompose(str.strip),
        output_processor=Compose(Join(), clean_post_content)
    )
    is_nsfw = Field()
    comments = Field()