import traceback

import requests
import re
from lxml import html

from date_parse import parse
from model_updater import update_dataset

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Accept': 'application/json, text/html'
}

epoch_filename = 'last_speech_timestamp.txt'


def is_after_shaved_timestamp(date):
    speech_epoch = int(date.strftime('%s'))
    with open(epoch_filename) as f:
        saved_epoch = int(f.readline())
    return speech_epoch > saved_epoch


def get_full_text(speech_url):
    response = requests.get(speech_url, headers=headers)
    if response.status_code == 200:
        parsed_html = html.fromstring(response.text)
        article_content = parsed_html.xpath('//div[@class="article_content"]')[0].text_content()
        return re.sub('\s+', ' ', article_content).strip()
    else:
        print(f"Error reading speech: {speech_url}")
        traceback.print_exc()
        return None


def extract_data(url):
    response = requests.get(url, headers=headers)
    speeches = []
    speech_date = None
    prev_speech_date = None
    if response.status_code == 200:
        parsed_html = html.fromstring(response.text)

        topics_list = parsed_html.xpath('//div[@class="cat_list"]/div[@class="item_stat cat_stat"]')

        for i, element in enumerate(topics_list):
            print(f"  speech {i} ... ", end='')
            link = element.xpath('.//h3/a/@href')[0]
            topic = element.xpath('.//h3/a/text()')[0]
            try:
                date_text = element.cssselect("p.date")[0].text_content()
                speech_date = parse(re.sub('\s+', ' ', date_text).strip())
                if is_after_shaved_timestamp(speech_date):
                    full_text = get_full_text(link)
                    speeches.append({
                        'date': speech_date,
                        'link': link,
                        'topic': topic,
                        'full_text': full_text})
                    prev_speech_date = speech_date
                    print("Done")
                else:
                    print("\nNo more new speeches")
                    return prev_speech_date, speeches
            except:
                print(f"\nError reading speeches page {i} from URL {url}")
                traceback.print_exc()
                pass
    else:
        print(f"Failed to fetch the URL: {url}. Status code: {response.status_code}")
    return speech_date, speeches


def run():
    print(f"Processing latest page")
    latest_speech_date, new_speeches = extract_data(f"https://www.president.gov.ua/news/speeches")
    if len(new_speeches) != 0:
        latest_timestamp_epoch = latest_speech_date.strftime('%s')
        print(f'Got {len(new_speeches)} new speeches.'
              f'Latest timestamp: {latest_speech_date} ({latest_timestamp_epoch})')
        update_dataset(new_speeches)
        if latest_speech_date is not None:
            with open(epoch_filename, 'w') as file:
                file.write(latest_timestamp_epoch)
    else:
        print('No new speeches found')


if __name__ == '__main__':
    run()
