# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Build and install dependencies:**
```bash
poetry install --no-root
```

**Run main speech fetcher:**
```bash
python ./src/z_scrap/main.py
```

**Run tests:**
```bash
python -m pytest tests/
```

**Run individual test:**
```bash
python tests/date_parse_test.py
```

**Activate poetry environment:**
```bash
source $(poetry env info --path)/bin/activate
```

## Architecture

This is a web scraper that fetches speeches from president.gov.ua and maintains a HuggingFace dataset at `slava-medvedev/zelensky-speeches`.

**Core Components:**

- `src/z_scrap/main.py` - Main entry point that orchestrates the scraping process
- `src/z_scrap/selenium_driver.py` - Creates Chrome driver with random user agents
- `src/z_scrap/dataset_updater.py` - Handles HuggingFace dataset updates
- `src/z_scrap/simple_language_checker.py` - Language detection for filtering content
- `src/z_scrap/date_parse.py` - Parses Ukrainian date strings to datetime objects

**Data Flow:**
1. Script fetches both Ukrainian (`/`) and English (`/en/`) speech pages
2. Uses Selenium to parse speech metadata and full text
3. Language filtering ensures appropriate content for each language
4. New speeches are compared against timestamp files (`last_speech_timestamp_*.txt`)
5. Dataset is updated and pushed to HuggingFace hub
6. Timestamp files are updated for incremental processing

**Tools Directory:**
- `src/tools/` - Analysis and cleanup utilities for the dataset
- `src/tools/dataset_cleanup.py` - Removes duplicates and cleans dataset

**Automation:**
- GitHub Actions runs daily at 23:20 UTC
- Auto-commits updated timestamp files
- Uses retry mechanism for robustness