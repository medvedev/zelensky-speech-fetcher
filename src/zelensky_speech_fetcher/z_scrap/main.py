import time
import traceback
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from curl_cffi import requests
from lxml import html

from .dataset_updater import update_dataset
from .date_parse import parse as parse_listing_date
from .xpath_selectors import ARTICLE_CONTENT, SPEECH_HREFS, SPEECH_DATES
from .debug_utils import (
    save_debug_html, log_error, log_warning, log_group_start, log_group_end,
)

IMPERSONATE = "chrome131"


class SpeechExtractionError(Exception):
    pass

_STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    window.chrome = {runtime: {}};
"""

RSS_URLS = {
    'en': 'https://www.president.gov.ua/en/rss/news/speeches.rss',
    'uk': 'https://www.president.gov.ua/uk/rss/news/speeches.rss',
}

HTML_LISTING_URLS = {
    'en': 'https://president.gov.ua/en/news/speeches',
    'uk': 'https://president.gov.ua/news/speeches',
}


class HttpFetcher:
    """Fetches pages with Playwright first; falls back to curl_cffi on bot-block or failure."""

    def __init__(self):
        self._session = requests.Session()
        self._pw = None
        self._pw_page = None

    @staticmethod
    def _is_bot_challenge(text):
        return "Access Denied" in text[:500] or "sec-if-cpt-container" in text

    def get_html(self, url):
        """Returns (html_text, status_code)."""
        pw_html = self._playwright_get(url)
        if pw_html and not self._is_bot_challenge(pw_html):
            return pw_html, 200

        reason = "bot challenge detected" if pw_html else "fetch failed"
        print(f"Playwright {reason} for {url} — falling back to curl_cffi")
        try:
            resp = self._session.get(url, impersonate=IMPERSONATE, timeout=20)
            if resp.status_code == 200 and not self._is_bot_challenge(resp.text):
                return resp.text, 200
            log_warning(f"curl_cffi: status={resp.status_code} size={len(resp.text)}b — both methods failed")
            return resp.text, resp.status_code
        except Exception as e:
            log_warning(f"curl_cffi error for {url}: {e}")
            return pw_html or "", 0

    def _playwright_get(self, url):
        try:
            if self._pw_page is None:
                self._init_playwright()
            self._pw_page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(7)  # allow Akamai JS challenge to execute and trigger reload
            # Akamai challenge calls location.reload(); wait for that navigation to land
            try:
                self._pw_page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass
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
        page_text, status = fetcher.get_html(speech_url)
        tree = html.fromstring(page_text)
        content = tree.xpath(ARTICLE_CONTENT)
        if content:
            return re.sub(r'\s+', ' ', content[0].text_content()).strip()
        save_debug_html(page_text, speech_url, "speech", "no_article_content")
        raise SpeechExtractionError(
            f"article_content XPath matched 0 elements for {speech_url} (status={status}, size={len(page_text)})"
        )
    except SpeechExtractionError:
        raise
    except Exception as e:
        raise SpeechExtractionError(f"Error reading speech from {speech_url}: {e}") from e


def to_listing_url(url, language):
    if '/rss/' in url or url.endswith('.rss'):
        return HTML_LISTING_URLS[language]
    return url


def add_page_param(url, page):
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query['page'] = str(page)
    return urlunparse(parsed._replace(query=urlencode(query)))


def normalize_href(href, base_url):
    parsed = urlparse(base_url)
    if href.startswith('http://') or href.startswith('https://'):
        href_parsed = urlparse(href)
        if href_parsed.netloc.endswith('president.gov.ua'):
            return urlunparse(href_parsed._replace(scheme=parsed.scheme, netloc=parsed.netloc))
        return href
    return f'{parsed.scheme}://{parsed.netloc}{href}'


def parse_listing_items(listing_text, language, listing_url):
    tree = html.fromstring(listing_text)
    hrefs = tree.xpath(SPEECH_HREFS)
    dates = tree.xpath(SPEECH_DATES)

    if not hrefs:
        return []

    items = []
    for href_node, date_node in zip(hrefs, dates):
        href = href_node.get('href')
        date_text = date_node.text_content().strip()
        title = re.sub(r'\s+', ' ', href_node.text_content()).strip()

        if not href or not date_text or not title:
            continue

        try:
            speech_date = parse_listing_date(date_text)
        except Exception as e:
            log_warning(f"HTML listing date parse failed for {date_text!r}: {e}")
            continue

        items.append({
            'date': speech_date,
            'link': normalize_href(href, listing_url),
            'title': title,
        })

    return items


def extract_from_html_listing(fetcher, listing_url, language="uk", force=False):
    speeches = []
    latest_timestamp = None
    page = 1

    while True:
        page_url = listing_url if page == 1 else add_page_param(listing_url, page)
        print(f"Fetching HTML listing: {page_url}")
        listing_text, status = fetcher.get_html(page_url)
        print(f"Status: {status}, size: {len(listing_text)} bytes")

        if status != 200:
            log_error(f"Failed to fetch HTML listing {page_url}: status {status}")
            save_debug_html(listing_text, page_url, language, f"html_listing_fetch_failed_{status}")
            break

        items = parse_listing_items(listing_text, language, page_url)
        print(f"HTML items on page {page}: {len(items)}")

        if not items:
            if page == 1:
                log_error(f"No items in HTML listing {listing_url}")
                save_debug_html(listing_text, page_url, language, "html_listing_no_items")
            break

        if latest_timestamp is None:
            latest_timestamp = items[0]['date']

        should_continue = False
        for i, item in enumerate(items):
            speech_date = item['date']
            speech_href = item['link']
            speech_topic = item['title']

            print(f"  speech p{page}.{i}: {speech_topic[:60]!r}  date={speech_date}")

            if force or is_after_saved_timestamp(speech_date, language=language):
                try:
                    full_text = get_full_text(fetcher, speech_href)
                except SpeechExtractionError as e:
                    log_warning(str(e))
                    continue
                speeches.append({
                    'date': speech_date,
                    'link': speech_href,
                    'topic': speech_topic,
                    'full_text': full_text,
                    'lang': language,
                })
                should_continue = True
                print(f"    → fetched ({len(full_text)} chars)")
            else:
                print(f"  No more new speeches (stopped at page {page}, index {i})")
                return latest_timestamp, speeches

        if not should_continue:
            break

        page += 1

    return latest_timestamp, speeches


def extract_data(rss_url, language="uk", force=False):
    fetcher = HttpFetcher()
    try:
        log_group_start(f"Processing {language} - {rss_url}")
        print(f"Fetching RSS: {rss_url}")
        rss_text, status = fetcher.get_html(rss_url)

        print(f"Status: {status}, size: {len(rss_text)} bytes")

        if status != 200:
            log_error(f"Failed to fetch RSS {rss_url}: status {status}")
            save_debug_html(rss_text, rss_url, language, f"rss_fetch_failed_{status}")
            log_group_end()
            listing_url = to_listing_url(rss_url, language)
            print(f"Falling back to HTML listing: {listing_url}")
            return extract_from_html_listing(fetcher, listing_url, language=language, force=force)

        try:
            root = ET.fromstring(rss_text)
        except ET.ParseError as e:
            log_error(f"RSS parse error for {rss_url}: {e}")
            save_debug_html(rss_text, rss_url, language, "rss_parse_error")
            log_group_end()
            listing_url = to_listing_url(rss_url, language)
            print(f"Falling back to HTML listing: {listing_url}")
            return extract_from_html_listing(fetcher, listing_url, language=language, force=force)

        items = root.find('channel').findall('item')
        print(f"RSS items: {len(items)}")

        if not items:
            log_error(f"No items in RSS feed {rss_url}")
            log_group_end()
            listing_url = to_listing_url(rss_url, language)
            print(f"Falling back to HTML listing: {listing_url}")
            return extract_from_html_listing(fetcher, listing_url, language=language, force=force)

        latest_timestamp = parse_rss_date(items[0].findtext('pubDate'))
        if latest_timestamp is None:
            log_error(f"Could not parse date from first RSS item: {items[0].findtext('pubDate')!r}")
            log_group_end()
            listing_url = to_listing_url(rss_url, language)
            print(f"Falling back to HTML listing: {listing_url}")
            return extract_from_html_listing(fetcher, listing_url, language=language, force=force)

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
                try:
                    full_text = get_full_text(fetcher, speech_href)
                except SpeechExtractionError as e:
                    log_warning(str(e))
                    continue
                speeches.append({
                    'date': speech_date,
                    'link': speech_href,
                    'topic': speech_topic,
                    'full_text': full_text,
                    'lang': language,
                })
                print(f"    → fetched ({len(full_text)} chars)")
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
                log_error(f"No timestamp returned for language {language}: skipping this language")
                errors_occurred = True
            else:
                new_speeches.extend(new_speeches_lang)
                print(f"Successfully processed {len(new_speeches_lang)} speeches for {language}")

        except Exception as e:
            log_error(f"Failed to process language {language}: {e}")
            traceback.print_exc()
            timestamps[language] = None
            errors_occurred = True

    successful_languages = [lang for lang in languages if timestamps.get(lang) is not None]
    if not successful_languages:
        log_error("All languages failed to process — aborting")
        exit(1)

    if len(new_speeches) != 0:
        print(f'Got {len(new_speeches)} new speeches. Latest timestamps: {timestamps}')
        update_dataset(new_speeches)
        for language in successful_languages:
            with open(epoch_filename(language), 'w') as file:
                file.write(str(timestamps[language]))
            print(f"Updated timestamp file for {language}")
    else:
        print("No new speeches found")

    if errors_occurred:
        log_warning("Some languages had errors during processing, check logs above")


if __name__ == '__main__':
    main()
