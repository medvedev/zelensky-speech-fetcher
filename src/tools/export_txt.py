import json
from datetime import datetime

from datasets import load_dataset
from collections import Counter
import re

from src.z_scrap.dataset_updater import REPO_ID

dataset = load_dataset(REPO_ID, split="train", cache_dir="./cache")

filtered = dataset.filter(lambda x: x['lang'] == 'en').remove_columns(['lang', 'link'])

with open('export_en.txt', 'w', encoding='utf-8') as f:
    for entry in filtered:
        f.write('date: ' + datetime.fromtimestamp(entry['date']).strftime('%Y-%m-%d') + '\n')
        f.write('topic: ' + entry['topic'] + '\n')
        f.write('text: ' + entry['full_text'] + '\n\n')
