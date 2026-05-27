from datasets import load_dataset
from zelensky_speech_fetcher.z_scrap.dataset_updater import REPO_ID

OUTPUT_FILE = "missing_full_text_urls.txt"

dataset = load_dataset(REPO_ID, split='train', cache_dir='./.cache')
missing = [row['link'] for row in dataset if not row['full_text']]
print(f"Found {len(missing)} speeches with missing full_text")

with open(OUTPUT_FILE, 'w') as f:
    f.write('\n'.join(missing))

print(f"Written to {OUTPUT_FILE}")
