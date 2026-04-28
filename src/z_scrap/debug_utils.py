"""
Debug utilities for the speech scraper
Provides comprehensive debugging functionality for GitHub Actions and local development
"""

import os
import datetime


def save_debug_html(driver, url, language, error_context=""):
    """Save HTML page source for debugging purposes"""
    try:
        os.makedirs("debug_output", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"debug_output/debug_{language}_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"<!-- Debug info -->\n")
            f.write(f"<!-- URL: {url} -->\n")
            f.write(f"<!-- Language: {language} -->\n")
            f.write(f"<!-- Error context: {error_context} -->\n")
            f.write(f"<!-- Timestamp: {timestamp} -->\n")
            f.write(f"<!-- Page title: {driver.title} -->\n")
            f.write(f"<!-- Current URL: {driver.current_url} -->\n")
            f.write("\n")
            f.write(driver.page_source)
        
        log_error(f"Debug HTML saved to {filename}")
        print(f"Debug HTML saved to {filename}")
        return filename
    except Exception as e:
        log_warning(f"Failed to save debug HTML: {e}")
        return None


def log_error(message):
    """Log error message with GitHub Actions formatting"""
    print(f"::error::{message}")


def log_warning(message):
    """Log warning message with GitHub Actions formatting"""
    print(f"::warning::{message}")


def log_group_start(message):
    """Start a collapsible group in GitHub Actions logs"""
    print(f"::group::{message}")


def log_group_end():
    """End a collapsible group in GitHub Actions logs"""
    print("::endgroup::")


def debug_probe_selectors(driver):
    """Probe the page with progressively broader selectors to diagnose what's there."""
    from selenium.webdriver.common.by import By

    probes = [
        ('//div[@class="cat_list"]',                             'cat_list'),
        ('//div[contains(@class,"item_stat")]',                  'item_stat (any)'),
        ('//div[@class="item_stat_headline"]',                   'item_stat_headline (exact)'),
        ('//div[contains(@class,"item_stat_headline")]',         'item_stat_headline (contains)'),
        ('//p[@class="date"]',                                   'p.date (exact)'),
        ('//p[contains(@class,"date")]',                         'p[date] (contains)'),
        ('//div[@class="cat_list"]//p',                          'any <p> inside cat_list'),
        ('//div[@class="cat_list"]//h3//a',                      'h3>a inside cat_list'),
    ]

    print("=== Selector diagnostics ===")
    for xpath, label in probes:
        try:
            els = driver.find_elements(By.XPATH, xpath)
            print(f"  [{len(els):3d}] {label}")
            for el in els[:2]:
                try:
                    cls = el.get_attribute('class') or ''
                    txt = (el.text or '')[:80].replace('\n', ' ')
                    print(f"         class={cls!r}  text={txt!r}")
                except Exception:
                    pass
        except Exception as e:
            print(f"  [ERR] {label}: {e}")

    try:
        src = driver.page_source or ''
        print(f"=== Page source: {len(src)} bytes ===")
        idx = src.find('cat_list')
        if idx >= 0:
            print(f"  'cat_list' found at byte {idx}, context:")
            print(src[max(0, idx - 100):idx + 600])
        else:
            print("  'cat_list' NOT found in page source — first 2000 bytes:")
            print(src[:2000])
    except Exception as e:
        print(f"  Failed to inspect page source: {e}")


def debug_element_detection(topics_list, dates, hrefs, url, language):
    """Log detailed information about element detection"""
    print(f"Found elements: topics={len(topics_list)}, dates={len(dates)}, hrefs={len(hrefs)}")
    
    if len(topics_list) == 0:
        log_error(f"No topic elements found on {url}")
        return False, "no_topics_found"
    
    if len(dates) != len(topics_list) or len(hrefs) != len(topics_list):
        log_warning(f"Element count mismatch: topics={len(topics_list)}, dates={len(dates)}, hrefs={len(hrefs)}")
        return False, "element_count_mismatch"
    
    return True, "elements_found"


def debug_language_filtering(element_text, language, is_valid, reason):
    """Log language filtering decisions"""
    print(f"  {'✓' if is_valid else '✗'} {'Added' if is_valid else 'Filtered out'} ({reason})")


def debug_element_processing(i, element_text, date_text, max_length=50):
    """Log individual element processing"""
    truncated_text = element_text[:max_length] + "..." if len(element_text) > max_length else element_text
    print(f"Element {i}: '{truncated_text}' Date: '{date_text}'")


def debug_processing_results(valid_count, filtered_count):
    """Log final processing results"""
    print(f"Results: {valid_count} valid speeches, {filtered_count} filtered out")


def debug_bounds_check(index, max_dates, max_hrefs):
    """Check and log array bounds issues"""
    if index >= max_dates or index >= max_hrefs:
        log_warning(f"Index {index} exceeds available elements, skipping")
        return False
    return True