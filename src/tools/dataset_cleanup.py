import json
from datetime import datetime
import pandas as pd

from datasets import load_dataset, Dataset
from transformers import pipeline


def convert_date(date_str):
    if "T" in date_str:
        date_format = '%Y-%m-%dT%H:%M:%S.%f'
    else:
        date_format = '%Y-%m-%d %H:%M:%S.%f'
    return int(datetime.strptime(date_str, date_format).timestamp())


REPO_ID = 'slava-medvedev/zelensky-speeches'

dataset = load_dataset(REPO_ID, split='train', cache_dir='./.cache')
ds = dataset.to_pandas()

# pipe = pipeline("text-classification",
#                 model="papluca/xlm-roberta-base-language-detection")
# for row in ds[ds["lang"] == "en"].iterrows():
#     label_ = pipe(row[1]["full_text"], top_k=1, truncation=True)[0]["label"]
#     if label_ != "en":
#         link_ = row[1]["link"]
#         print(f"{link_} : {label_}")

# ds['date'] = ds['date'].apply(convert_date)
# ds_modified = False
#

# for language in ['en', 'uk']:
#     new_data = []
#     with open(f'speeches_{language}.jsonl', 'r', encoding='utf-8') as file:
#         for line in file:
#             new_data.append(json.loads(line))
#
#     # Convert the list of dictionaries to a Hugging Face dataset
#     new_dataset = Dataset.from_list(new_data)
#     new_ds = new_dataset.to_pandas()
#     new_ds['lang'] = language
#
#     ds = pd.concat([ds, new_ds])
#
# ds_modified = True

# Remove duplicates:
duplicates = ds[ds.duplicated(subset='date', keep=False)]
if duplicates.empty:
    print("No duplicates found in.")
else:
    ds.drop_duplicates(subset=['date', 'lang'], keep='first', inplace = True)
    print("Duplicates removed and dataset saved.")
    ds_modified = True


# Remove row by index:
# speeches_to_remove = [
#     'https://www.president.gov.ua/en/news/ukrayina-ta-polsha-mozhut-buti-vilnimi-tilki-razom-i-ce-fund-88489',
#     'https://www.president.gov.ua/en/news/la-paz-tiene-que-ser-una-opcion-sin-alternativas-por-eso-el-82409',
#     'https://www.president.gov.ua/en/news/europa-und-andere-teile-der-welt-sollten-kein-ort-sein-dem-d-82909',
#     'https://www.president.gov.ua/en/news/address-president-ukraine-arab-league-summit-83101',
#     'https://www.president.gov.ua/en/news/spilne-zvernennya-prezidenta-ukrayini-volodimira-zelenskogo-83549', ]
# for speech_url in speeches_to_remove:
#     ds = ds.drop(ds[ds['link'] == speech_url].index)

ds_modified = True

if ds_modified:
    # ds = ds.drop(columns=['__index_level_0__'])
    ds = Dataset.from_pandas(ds, preserve_index=False)
    ds.push_to_hub(REPO_ID)
    print('Pushed successfully')
