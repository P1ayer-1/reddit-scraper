import scrapy
from scrapy.loader import ItemLoader
from ..items import RedditItem

class OldredditSpider(scrapy.Spider):
    name = 'oldreddit'
    allowed_domains = ['old.reddit.com']
    start_urls = ["https://old.reddit.com/over18?dest=https%3A%2F%2Fold.reddit.com%2Fr%2Fconfessions%2Fnew%2F%3F"]

    def parse(self, response):
        formdata = {
            'over18': 'yes',
        }
        yield scrapy.FormRequest.from_response(response, formdata=formdata, callback=self.after_age_check)

    def after_age_check(self, response):
        if response.url.startswith('https://old.reddit.com/r/confessions/new/'): # check if age check passed
            self.logger.info('Successfully passed the age check.')
            url_template = "https://old.reddit.com/r/confessions/new/?count=25&after={}" # need to change so it doesnt scrape newest ones with no comments
            after = response.css("div.content div#siteTable div.thing::attr(data-fullname)").extract()[-1]
            next_url = url_template.format(after)
            yield scrapy.Request(next_url, callback=self.parse_page)
        else:
            self.logger.error('Failed to pass the age check.')

    def parse_page(self, response):
        for post in response.css("div.thing"):
            item_loader = ItemLoader(item=RedditItem(), selector=post)
            item_loader.add_css("title", "a.title::text")
            item_loader.add_css("link", "a.title::attr(href)")
            item_loader.add_css("score", "div.score.unvoted::text")
            comments_url = response.urljoin(post.css("a.comments::attr(href)").extract_first())
            request = scrapy.Request(comments_url, callback=self.parse_comments)
            request.meta['item_loader'] = item_loader
            yield request

        # get the URL of the next page, if any
        next_page_url = response.css("div.nav-buttons span.next-button a::attr(href)").extract_first()
        if next_page_url:
            yield scrapy.Request(response.urljoin(next_page_url), callback=self.parse_page)


    def parse_comments(self, response):
        item_loader = response.meta['item_loader']
        comments = []
        for comment in response.css("div.comment"):
            score = comment.css("span.score.unvoted::text").get()
            permalink = response.urljoin(comment.css("a[data-event-action='permalink']::attr(href)").extract_first())

            if score is not None:
                score = score.replace(' points', '')
                if 'k' in score:
                    score = score.replace('k', '')
                    score = float(score) * 1000
                    score = int(score)
                else:
                    score = score.replace('point', '')
                    score = int(score)
                comment_item = {"score": score, "permalink": permalink}
                comments.append(comment_item)

        comments = sorted([c for c in comments if c['score'] is not None], key=lambda c: c['score'], reverse=True)[:5]
        item_loader.add_value("comments", comments)
        
        # extract post_content
        post_content = ''.join(response.xpath('/html/body/div[4]/div[1]/div[1]/div[2]/div[2]/form/div/div//text()').extract()).strip()
        item_loader.add_value("post_content", post_content)
        
        yield item_loader.load_item()



