from datasets import load_dataset
from collections import Counter
import re

from src.z_scrap.dataset_updater import REPO_ID

dataset = load_dataset(REPO_ID, split="train", cache_dir="./cache")

filtered = dataset.filter(lambda x: x['lang'] == 'uk')
texts = filtered['full_text']
words = re.findall(r'\b\w{5,}\b', ' '.join(texts).lower())
top_10 = Counter(words).most_common(20)
print(top_10)
