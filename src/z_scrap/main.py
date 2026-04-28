import traceback
import re

from curl_cffi import requests
from lxml import html

from date_parse import parse
from dataset_updater import update_dataset
from simple_language_checker import looks_like_english_text
from xpath_selectors import SPEECH_ITEMS, SPEECH_DATES, SPEECH_HREFS, ARTICLE_CONTENT
from debug_utils import (
    save_debug_html, log_error, log_warning, log_group_start, log_group_end,
    debug_element_detection, debug_language_filtering, debug_element_processing,
    debug_processing_results, debug_bounds_check,
)

IMPERSONATE = "chrome120"


def epoch_filename(language):
    return f"last_speech_timestamp_{language}.txt"


def is_after_saved_timestamp(speech_epoch, language="uk"):
    with open(epoch_filename(language)) as f:
        saved_epoch = int(f.readline())
    return speech_epoch > saved_epoch


def get_full_text(session, speech_url):
    try:
        resp = session.get(speech_url, impersonate=IMPERSONATE, timeout=20)
        tree = html.fromstring(resp.text)
        content = tree.xpath(ARTICLE_CONTENT)
        if content:
            return re.sub(r'\s+', ' ', content[0].text_content()).strip()
    except Exception:
        traceback.print_exc()
        print(f"\nError reading speech from URL {speech_url}")
    return None


def extract_data(url, language="uk", force=False):
    session = requests.Session()
    speeches = []
    try:
        log_group_start(f"Processing {language} - {url}")
        print(f"Fetching URL: {url}")
        resp = session.get(url, impersonate=IMPERSONATE, timeout=20)

        print(f"Status: {resp.status_code}")
        print(f"Page size: {len(resp.text)} bytes")

        if resp.status_code != 200 or "Access Denied" in resp.text[:500]:
            log_error(f"Access denied or unexpected status {resp.status_code} for {url}")
            save_debug_html(resp.text, url, language, "access_denied")
            log_group_end()
            return None, []

        tree = html.fromstring(resp.text)
        topics_list = tree.xpath(SPEECH_ITEMS)
        dates = tree.xpath(SPEECH_DATES)
        hrefs = tree.xpath(SPEECH_HREFS)

        elements_ok, error_context = debug_element_detection(topics_list, dates, hrefs, url, language)
        if not elements_ok:
            save_debug_html(resp.text, url, language, error_context)
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

                element_text = element.text_content().strip()
                date_text = date_element.text_content().strip()

                debug_element_processing(i, element_text, date_text)

                if language == "uk":
                    is_valid = True
                    reason = "Ukrainian language"
                else:
                    is_valid = looks_like_english_text(element_text)
                    reason = f"English check: {is_valid}"

                if is_valid:
                    clean_date_text = re.sub(r'\s+', ' ', date_text).strip()
                    try:
                        parsed_date = parse(clean_date_text)
                    except Exception as e:
                        log_warning(f"Date parse failed for {clean_date_text!r}: {e}")
                        parsed_date = None
                    print(f"  date_text={clean_date_text!r}  parsed={parsed_date}")
                    elements_on_page.append({
                        'href': href_element.get('href'),
                        'topic': href_element.text_content().strip(),
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
            save_debug_html(resp.text, url, language, "no_valid_elements_after_filtering")
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
                    full_text = get_full_text(session, speech_href)
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
            except Exception:
                traceback.print_exc()
                print(f"\nError reading speeches from URL {url}")

        latest_timestamp = elements_on_page[0].get('date') if elements_on_page else None
        if latest_timestamp is None:
            log_error(f"latest_timestamp is None — elements_on_page[0]={elements_on_page[0] if elements_on_page else 'empty'}")
        print(f"Returning latest timestamp: {latest_timestamp}, speeches count: {len(speeches)}")
        return latest_timestamp, speeches
    except Exception:
        traceback.print_exc()
        log_group_end()
        return None, []


def main():
    import os
    retry_attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
    print(f"=== Starting speech fetcher (retry attempt: {retry_attempt}) ===")

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
                log_error(f"No timestamp returned for language {language}: blocking error")
                exit(1)
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
