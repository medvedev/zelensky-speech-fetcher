import traceback

import re
from selenium.webdriver.common.by import By

from date_parse import parse
from model_updater import update_dataset
from selenium_driver import create_driver

epoch_filename = 'last_speech_timestamp.txt'


def is_after_shaved_timestamp(date):
    speech_epoch = int(date.strftime('%s'))
    with open(epoch_filename) as f:
        saved_epoch = int(f.readline())
    return speech_epoch > saved_epoch


def get_full_text(driver, speech_url):
    driver.get(speech_url)
    article_content = driver.find_element(By.XPATH, '//div[@class="article_content"]').text
    return re.sub('\s+', ' ', article_content).strip()


def extract_data(url):
    driver = create_driver()
    speeches = []
    try:
        driver.get(url)
        topics_list = driver.find_elements(By.XPATH, '//div[@class="cat_list"]/div[@class="item_stat cat_stat"]')

        elements_on_page = []
        for i, element in enumerate(topics_list):
            article_href_element = element.find_element(By.XPATH, "//h3/a")
            date_element = element.find_element(By.CSS_SELECTOR, "p.date")
            elements_on_page.append({'href': article_href_element.get_attribute('href'),
                                     'topic': article_href_element.text,
                                     'date': parse(re.sub('\s+', ' ', date_element.text).strip())})

        print(f"Parsed successfully: {url}")

        for i, element in enumerate(elements_on_page):
            print(f"  speech {i} ... ", end='')
            try:
                if is_after_shaved_timestamp(element.get('date')):
                    full_text = get_full_text(driver, element.get('href'))
                    speeches.append({
                        'date': element.get('date'),
                        'link': element.get('href'),
                        'topic': element.get('topic'),
                        'full_text': full_text})
                    print("Done")
                else:
                    print("\nNo more new speeches")
                    break
            except:
                print(f"\nError reading speeches from URL {url}")
                traceback.print_exc()
                pass

        return elements_on_page[0].get('date'), speeches
    finally:
        if driver is not None:
            driver.quit()


def run():
    print(f"Processing latest page")
    latest_speech_date, new_speeches = extract_data("https://www.president.gov.ua/news/speeches")
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
