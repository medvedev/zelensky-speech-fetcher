# XPath selectors for president.gov.ua
# Update these when the site DOM structure changes.
#
# Reference DOM path (as of 2026-04):
#   html body div.all div.cat_section div.container div.catalog_container
#   div.row div.col-xs-8.home_left div.left_part
#   div.cat_list div.item_stat.cat_stat div.item_stat_headline p.date

# Speech list page
SPEECH_ITEMS = '//div[@class="cat_list"]//div[@class="item_stat_headline"]'
SPEECH_DATES = '//div[@class="cat_list"]//div[@class="item_stat_headline"]//p[contains(@class,"date")]'
SPEECH_HREFS = '//div[@class="cat_list"]//div[@class="item_stat_headline"]//h3//a'

# Speech detail page
ARTICLE_CONTENT = '//div[@class="article_content"]'
