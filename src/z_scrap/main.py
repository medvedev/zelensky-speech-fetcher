import traceback

import re
from selenium.webdriver.common.by import By

from date_parse import parse
from model_updater import update_dataset
from selenium_driver import create_driver


def epoch_filename(language):
    return f"last_speech_timestamp_{language}.txt"


def is_after_saved_timestamp(speech_epoch, language):
    with open(epoch_filename(language)) as f:
        saved_epoch = int(f.readline())
    return speech_epoch > saved_epoch


def get_full_text(driver, speech_url):
    driver.get(speech_url)
    article_content = driver.find_element(By.XPATH, '//div[@class="article_content"]').text
    return re.sub('\s+', ' ', article_content).strip()


def extract_data(url, language="ua"):
    driver = create_driver()
    speeches = []
    try:
        driver.get(url)
        topics_list = driver.find_elements(By.XPATH, '//div[@class="cat_list"]/div[@class="item_stat cat_stat"]//h3/a')

        elements_on_page = []
        for i, element in enumerate(topics_list):
            date_element = element.find_element(By.XPATH, "../../p")
            elements_on_page.append({'href': element.get_attribute('href'),
                                     'topic': element.text,
                                     'date': parse(re.sub('\s+', ' ', date_element.text).strip()),
                                     'lang': language})

        print(f"Parsed successfully: {url}")

        for i, element in enumerate(elements_on_page):
            print(f"  speech {i} ... ", end='')
            try:
                speech_date = element.get('date')
                if is_after_saved_timestamp(speech_date):
                    speech_href = element.get('href')
                    full_text = get_full_text(driver, speech_href)
                    speeches.append({
                        'date': speech_date,
                        'link': speech_href,
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
    latest_timestamp_epoch, new_speeches = extract_data("https://www.president.gov.ua/news/speeches")
    if len(new_speeches) != 0:
        print(f'Got {len(new_speeches)} new speeches.'
              f'Latest timestamp: {latest_timestamp_epoch} ({latest_timestamp_epoch})')
        update_dataset(new_speeches)
        if latest_timestamp_epoch is not None:
            with open(epoch_filename('ua'), 'w') as file:
                file.write(str(latest_timestamp_epoch))
    else:
        print('No new speeches found')


if __name__ == '__main__':
    run()
