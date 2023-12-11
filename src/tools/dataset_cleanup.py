import json
from datetime import datetime
import pandas as pd

from datasets import load_dataset, Dataset


def convert_date(date_str):
    if "T" in date_str:
        date_format = '%Y-%m-%dT%H:%M:%S.%f'
    else:
        date_format = '%Y-%m-%d %H:%M:%S.%f'
    return int(datetime.strptime(date_str, date_format).timestamp())


REPO_ID = 'slava-medvedev/zelensky-speeches'

dataset = load_dataset(REPO_ID, split='train', cache_dir='./.cache')
ds = dataset.to_pandas()
# ds['date'] = ds['date'].apply(convert_date)
# ds_modified = False

new_data = []
with open('speeches_en.jsonl', 'r', encoding='utf-8') as file:
    for line in file:
        new_data.append(json.loads(line))

# Convert the list of dictionaries to a Hugging Face dataset
new_dataset = Dataset.from_list(new_data)
new_ds = new_dataset.to_pandas()
new_ds['lang'] = 'en'

ds = pd.concat([ds, new_ds])
ds_modified = True

# Remove duplicates:
# duplicates = ds[ds.duplicated(subset='date', keep=False)]
# if duplicates.empty:
#     print("No duplicates found in.")
# else:
#     ds.drop_duplicates(subset='date', keep='first', inplace = True)
#     print("Duplicates removed and dataset saved.")
#     ds_modified = True


# Remove row by index:
# rus_speech_url = 'https://www.president.gov.ua/news/prezident-ukrainy-vladimir-zelenskij-obratilsya-k-grazhdanam-73217'
# ds = ds.drop(ds[ds['link'] == rus_speech_url].index)
# ds_modified = True

# Add lang column
# ds['lang'] = 'uk'
# ds_modified = True


if ds_modified:
    # ds = ds.drop(columns=['__index_level_0__'])
    ds = Dataset.from_pandas(ds)
    ds.push_to_hub(REPO_ID)
    print('Pushed successfully')
