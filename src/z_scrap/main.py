import time
import traceback
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from curl_cffi import requests
from lxml import html

from dataset_updater import update_dataset
from xpath_selectors import ARTICLE_CONTENT
from debug_utils import (
    save_debug_html, log_error, log_warning, log_group_start, log_group_end,
)

IMPERSONATE = "chrome131"

_STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    window.chrome = {runtime: {}};
"""

RSS_URLS = {
    'en': 'https://www.president.gov.ua/en/rss/news/speeches.rss',
    'uk': 'https://www.president.gov.ua/rss/news/speeches.rss',
}


class HttpFetcher:
    """Fetches pages with curl_cffi; on bot-detection block falls back to Playwright."""

    def __init__(self):
        self._session = requests.Session()
        self._pw = None
        self._pw_page = None

    def get_html(self, url):
        """Returns (html_text, status_code)."""
        try:
            resp = self._session.get(url, impersonate=IMPERSONATE, timeout=20)
            if resp.status_code == 200 and "Access Denied" not in resp.text[:500]:
                return resp.text, 200
            print(f"curl_cffi: status={resp.status_code} size={len(resp.text)}b — falling back to Playwright")
            fallback = self._playwright_get(url)
            if fallback and "Access Denied" not in fallback[:500]:
                return fallback, 200
            return fallback or resp.text, resp.status_code
        except Exception as e:
            log_warning(f"curl_cffi error for {url}: {e}")
            fallback = self._playwright_get(url)
            return fallback or "", 0

    def _playwright_get(self, url):
        try:
            if self._pw_page is None:
                self._init_playwright()
            self._pw_page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(4)  # allow Akamai JS challenge to complete
            return self._pw_page.content()
        except Exception as e:
            log_warning(f"Playwright fetch failed for {url}: {e}")
            return None

    def _init_playwright(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        browser = self._pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
        )
        context.add_init_script(_STEALTH_SCRIPT)
        self._pw_page = context.new_page()

    def close(self):
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None
            self._pw_page = None


def epoch_filename(language):
    return f"last_speech_timestamp_{language}.txt"


def is_after_saved_timestamp(speech_epoch, language="uk"):
    with open(epoch_filename(language)) as f:
        saved_epoch = int(f.readline())
    return speech_epoch > saved_epoch


def parse_rss_date(date_str):
    if not date_str:
        return None
    try:
        return int(parsedate_to_datetime(date_str).timestamp())
    except Exception as e:
        log_warning(f"RSS date parse failed for {date_str!r}: {e}")
        return None


def get_full_text(fetcher, speech_url):
    try:
        page_text, _ = fetcher.get_html(speech_url)
        tree = html.fromstring(page_text)
        content = tree.xpath(ARTICLE_CONTENT)
        if content:
            return re.sub(r'\s+', ' ', content[0].text_content()).strip()
    except Exception:
        traceback.print_exc()
        print(f"\nError reading speech from URL {speech_url}")
    return None


def extract_data(rss_url, language="uk", force=False):
    fetcher = HttpFetcher()
    speeches = []
    try:
        log_group_start(f"Processing {language} - {rss_url}")
        print(f"Fetching RSS: {rss_url}")
        rss_text, status = fetcher.get_html(rss_url)

        print(f"Status: {status}, size: {len(rss_text)} bytes")

        if status != 200:
            log_error(f"Failed to fetch RSS {rss_url}: status {status}")
            save_debug_html(rss_text, rss_url, language, f"rss_fetch_failed_{status}")
            log_group_end()
            return None, []

        try:
            root = ET.fromstring(rss_text)
        except ET.ParseError as e:
            log_error(f"RSS parse error for {rss_url}: {e}")
            save_debug_html(rss_text, rss_url, language, "rss_parse_error")
            log_group_end()
            return None, []

        items = root.find('channel').findall('item')
        print(f"RSS items: {len(items)}")

        if not items:
            log_error(f"No items in RSS feed {rss_url}")
            log_group_end()
            return None, []

        latest_timestamp = parse_rss_date(items[0].findtext('pubDate'))
        if latest_timestamp is None:
            log_error(f"Could not parse date from first RSS item: {items[0].findtext('pubDate')!r}")
            log_group_end()
            return None, []

        log_group_end()

        for i, item in enumerate(items):
            speech_date = parse_rss_date(item.findtext('pubDate'))
            speech_href = item.findtext('link')
            speech_topic = item.findtext('title', '').strip()

            if not speech_date or not speech_href:
                log_warning(f"Skipping item {i}: missing date or link")
                continue

            print(f"  speech {i}: {speech_topic[:60]!r}  date={speech_date}")

            if force or is_after_saved_timestamp(speech_date, language=language):
                full_text = get_full_text(fetcher, speech_href)
                speeches.append({
                    'date': speech_date,
                    'link': speech_href,
                    'topic': speech_topic,
                    'full_text': full_text,
                    'lang': language,
                })
                print(f"    → fetched ({len(full_text or '')} chars)")
            else:
                print(f"  No more new speeches (stopped at index {i})")
                break

        print(f"Returning latest_timestamp={latest_timestamp}, speeches={len(speeches)}")
        return latest_timestamp, speeches
    except Exception:
        traceback.print_exc()
        log_group_end()
        return None, []
    finally:
        fetcher.close()


def main():
    import os
    retry_attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
    print(f"=== Starting speech fetcher (retry attempt: {retry_attempt}) ===")

    languages = ['en', 'uk']
    timestamps = {}
    new_speeches = []
    errors_occurred = False

    for language in languages:
        rss_url = RSS_URLS[language]
        print(f"Processing {language}: {rss_url}")

        try:
            timestamps[language], new_speeches_lang = extract_data(rss_url, language=language)

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
        print(f'Got {len(new_speeches)} new speeches. Latest timestamps: {timestamps}')
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
