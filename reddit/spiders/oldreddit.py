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
        if response.url.startswith('https://old.reddit.com/'): # check if age check passed
            self.logger.info('Successfully passed the age check.')
            # Read the list of permalinks from a text file
            with open('/home/noah/OpenAssistant/reddit/redditV2/permalinks.txt', 'r') as file:
                permalinks = file.readlines()

            # Send a request for each permalink to the handle_permalinks method
            for permalink in permalinks:
                yield scrapy.Request(url=permalink.strip(), callback=self.parse_post)
        else:
            self.logger.error('Failed to pass the age check.')

    def parse_post(self, response):
        item_loader = ItemLoader(item=RedditItem())
        comments = []

        # extract comment_count
        comment_count = response.xpath('/html/body/div[4]/div[1]/div[1]/@data-comments-count').get()

        if comment_count is not None and int(comment_count) < 5: # skip post if comment count is less than 5
            self.logger.info(f'Skipping post with {comment_count} comments.')
            return
        
        # extract over_18
        over_18 = response.xpath('/html/body/div[4]/div[1]/div[1]/@data-nsfw').get()
        item_loader.add_value("over_18", over_18)

        for comment in response.css("div.comment"):
            score = comment.css("span.score.unvoted::text").get()
            # use .usertext.warn-on-unload input::attr(value) to get the comment id
            comment_id = comment.css(".usertext.warn-on-unload input::attr(value)").extract_first()

            if score is not None:
                score = score.replace(' points', '')
                if 'k' in score:
                    score = score.replace('k', '')
                    score = float(score) * 1000
                    score = int(score)
                else:
                    score = score.replace('point', '')
                    score = int(score)
                comment_item = {"score": score, "comment_id": comment_id}
                comments.append(comment_item)

        comments = sorted([c for c in comments if c['score'] is not None], key=lambda c: c['score'], reverse=True)[:5]
        
        for comment in comments:
            comment_id = comment['comment_id']
            comment_text = response.css(f'form[id^="form-{comment_id}"] p::text').getall()
            comment['comment_text'] = comment_text
        
        post_content = ''.join(response.xpath('/html/body/div[4]/div[1]/div[1]/div[2]/div[2]/form/div/div//text()').extract()).strip()
        item_loader.add_value("post_content", post_content)

        title = response.xpath('/html/body/div[4]/div[1]/div[1]/div[2]/div[1]/p[1]/a//text()').extract_first()
        item_loader.add_value("title", title)

        post_karma = response.xpath('/html/body/div[3]/div[2]/div/div[2]//text()').extract()
        post_score = post_karma[0]
        item_loader.add_value("post_score", post_score)

        upvote_percentage = post_karma[-1].strip().replace('%', '').replace('(', '').replace(')', '').replace('upvoted', '')
        upvote_percentage = float(upvote_percentage) / 100
        item_loader.add_value("upvote_percentage", upvote_percentage)

        item_loader.add_value("comments", comments)

        yield item_loader.load_item()



