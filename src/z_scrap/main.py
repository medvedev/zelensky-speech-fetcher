import traceback
import re

from selenium.common import WebDriverException
from selenium.webdriver.common.by import By

from date_parse import parse
from dataset_updater import update_dataset
from selenium_driver import create_driver
from simple_language_checker import looks_like_english_text
from debug_utils import (
    save_debug_html, log_error, log_warning, log_group_start, log_group_end,
    debug_element_detection, debug_language_filtering, debug_element_processing,
    debug_processing_results, debug_bounds_check
)


def epoch_filename(language):
    return f"last_speech_timestamp_{language}.txt"


def is_after_saved_timestamp(speech_epoch, language="uk"):
    with open(epoch_filename(language)) as f:
        saved_epoch = int(f.readline())
    return speech_epoch > saved_epoch


def get_full_text(driver, speech_url):
    driver.get(speech_url)
    try:
        article_content = driver.find_element(By.XPATH, '//div[@class="article_content"]').text
        return re.sub('\s+', ' ', article_content).strip()
    except  WebDriverException:
        traceback.print_exc()
        print(f"\nError reading speech from URL {speech_url}")
        pass


def extract_data(url, language="uk", force=False):
    driver = create_driver()
    speeches = []
    try:
        log_group_start(f"Processing {language} - {url}")
        print(f"Fetching URL: {url}")
        driver.get(url)
        
        print(f"Page loaded. Title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Find elements with detailed logging
        print("Searching for speech elements...")
        topics_list = driver.find_elements(By.XPATH, '//div[@class="cat_list"]/*/div[@class="item_stat_headline"]')
        dates = driver.find_elements(By.XPATH, '//div[@class="cat_list"]/*/div[@class="item_stat_headline"]/p')
        hrefs = driver.find_elements(By.XPATH, '//div[@class="cat_list"]/*/div[@class="item_stat_headline"]/h3/a')

        # Debug element detection with helper function
        elements_ok, error_context = debug_element_detection(topics_list, dates, hrefs, url, language)
        if not elements_ok:
            save_debug_html(driver, url, language, error_context)
            log_group_end()
            return None, []

        elements_on_page = []
        filtered_out = 0
        for i, element in enumerate(topics_list):
            try:
                if not debug_bounds_check(i, len(dates), len(hrefs)):
                    continue
                    
                date_element = dates[i]
                href_element = hrefs[i]
                
                element_text = element.text.strip() if element.text else ""
                date_text = date_element.text.strip() if date_element.text else ""
                
                debug_element_processing(i, element_text, date_text)
                
                # Language filtering with detailed logging
                if language == "uk":
                    is_valid = True
                    reason = "Ukrainian language"
                else:
                    is_valid = looks_like_english_text(element_text)
                    reason = f"English check: {is_valid}"
                
                if is_valid:
                    parsed_date = parse(re.sub('\s+', ' ', date_text).strip())
                    elements_on_page.append({
                        'href': href_element.get_attribute('href'),
                        'topic': href_element.text,
                        'date': parsed_date
                    })
                    debug_language_filtering(element_text, language, True, reason)
                else:
                    filtered_out += 1
                    debug_language_filtering(element_text, language, False, reason)
            except Exception as e:
                log_warning(f"Error processing element {i}: {e}")
                continue

        debug_processing_results(len(elements_on_page), filtered_out)
        
        if len(elements_on_page) == 0:
            log_error(f"No valid elements after filtering on {url}")
            save_debug_html(driver, url, language, "no_valid_elements_after_filtering")
            log_group_end()
            return None, []

        print(f"Parsed successfully: {url}")
        log_group_end()

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

        # Return the most recent speech date (first element) if available
        latest_timestamp = elements_on_page[0].get('date') if elements_on_page else None
        print(f"Returning latest timestamp: {latest_timestamp}, speeches count: {len(speeches)}")
        return latest_timestamp, speeches
    finally:
        if driver is not None:
            driver.quit()


def main():
    languages = ['en', 'uk']
    timestamps = {}
    new_speeches = []
    errors_occurred = False
    
    for language in languages:
        print(f"Processing latest page for language {language}")
        if language == 'uk':
            url_suffix = "/"
        else:
            url_suffix = f"/{language}/"
        
        try:
            timestamps[language], new_speeches_lang = extract_data(
                f"https://www.president.gov.ua{url_suffix}news/speeches",
                language=language)
            
            if timestamps[language] is None:
                log_warning(f"No timestamp returned for language {language}")
                errors_occurred = True
            else:
                new_speeches.extend(new_speeches_lang)
                print(f"Successfully processed {len(new_speeches_lang)} speeches for {language}")
                
        except Exception as e:
            log_error(f"Failed to process language {language}: {e}")
            traceback.print_exc()
            timestamps[language] = None
            errors_occurred = True
    
    if len(new_speeches) != 0:
        print(f'Got {len(new_speeches)} new speeches. '
              f'Latest timestamps: {timestamps}')
        update_dataset(new_speeches)
        for language in languages:
            if timestamps[language] is not None:
                with open(epoch_filename(language), 'w') as file:
                    file.write(str(timestamps[language]))
                print(f"Updated timestamp file for {language}")
            else:
                log_warning(f"Skipping timestamp update for {language} due to processing error")
    else:
        if errors_occurred:
            log_error("No new speeches found, and errors occurred during processing")
            exit(1)
        else:
            print("No new speeches found")
    
    if errors_occurred:
        log_warning("Some errors occurred during processing, check logs above")


if __name__ == '__main__':
    main()
