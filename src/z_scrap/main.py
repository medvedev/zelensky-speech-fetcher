import traceback

import re
from selenium.webdriver.common.by import By

from date_parse import parse
from model_updater import update_dataset
from selenium_driver import create_driver

from language_checker import is_english


def epoch_filename(language):
    return f"last_speech_timestamp_{language}.txt"


def is_after_saved_timestamp(speech_epoch, language="uk"):
    with open(epoch_filename(language)) as f:
        saved_epoch = int(f.readline())
    return speech_epoch > saved_epoch


def get_full_text(driver, speech_url):
    driver.get(speech_url)
    article_content = driver.find_element(By.XPATH, '//div[@class="article_content"]').text
    return re.sub('\s+', ' ', article_content).strip()


def extract_data(url, language="uk", force=False):
    driver = create_driver()
    speeches = []
    try:
        driver.get(url)
        topics_list = driver.find_elements(By.XPATH, '//div[@class="cat_list"]/*/div[@class="item_stat_headline"]')
        dates = driver.find_elements(By.XPATH, '//div[@class="cat_list"]/*/div[@class="item_stat_headline"]/p')
        hrefs = driver.find_elements(By.XPATH, '//div[@class="cat_list"]/*/div[@class="item_stat_headline"]/h3/a')

        elements_on_page = []
        for i, element in enumerate(topics_list):
            date_element = dates[i]
            if language == "uk" or is_english(element.text):
                href_element = hrefs[i]
                elements_on_page.append({'href': href_element.get_attribute('href'),
                                         'topic': href_element.text,
                                         'date': parse(re.sub('\s+', ' ', date_element.text).strip())})
            else:
                print(f"Element is not in English or Ukrainian")

        print(f"Parsed successfully: {url}")

        for i, element in enumerate(elements_on_page):
            print(f"  speech {i} ... ", end='')
            try:
                speech_date = element.get('date')
                if force or is_after_saved_timestamp(speech_date, language=language):
                    speech_href = element.get('href')
                    full_text = get_full_text(driver, speech_href)
                    speeches.append({
                        'date': speech_date,
                        'link': speech_href,
                        'topic': element.get('topic'),
                        'full_text': full_text,
                        'lang': language})
                    print("Done")
                else:
                    print("\nNo more new speeches")
                    break
            except:
                traceback.print_exc()
                print(f"\nError reading speeches from URL {url}")
                pass

        return elements_on_page[0].get('date'), speeches
    finally:
        if driver is not None:
            driver.quit()


def main():
    languages = ['en', 'uk']
    timestamps = {}
    new_speeches = []
    for language in languages:
        print(f"Processing latest page for language {language}")
        if language == 'uk':
            url_suffix = "/"
        else:
            url_suffix = f"/{language}/"
        timestamps[language], new_speeches_lang = extract_data(
            f"https://www.president.gov.ua{url_suffix}news/speeches",
            language=language)
        new_speeches.extend(new_speeches_lang)
    if len(new_speeches) != 0:
        print(f'Got {len(new_speeches)} new speeches. '
              f'Latest timestamps: {timestamps}')
        update_dataset(new_speeches)
        for language in languages:
            if timestamps[language] is not None:
                with open(epoch_filename(language), 'w') as file:
                    file.write(str(timestamps[language]))
    else:
        print("No new speeches found")


if __name__ == '__main__':
    main()
