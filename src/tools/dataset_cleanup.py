from datetime import datetime

from datasets import load_dataset, Dataset


def convert_date(date_str):
    if "T" in date_str:
        date_format = '%Y-%m-%dT%H:%M:%S.%f'
    else:
        date_format = '%Y-%m-%d %H:%M:%S.%f'
    return int(datetime.strptime(date_str, date_format).timestamp())


REPO_ID = 'slava-medvedev/zelensky-speeches'

dataset = load_dataset(REPO_ID, split='train')
ds = dataset.to_pandas()
# ds['date'] = ds['date'].apply(convert_date)
ds_modified = False

# Remove duplicates:
# duplicates = ds[ds.duplicated(subset='date', keep=False)]
# if not duplicates.empty:
#     ds.drop_duplicates(subset='date', keep='first', inplace = True)
#     print("Duplicates removed and dataset saved.")
#     ds_modified = True
# else:
#     print("No duplicates found in.")

# Remove row by index:
rus_speech_url = 'https://www.president.gov.ua/news/prezident-ukrainy-vladimir-zelenskij-obratilsya-k-grazhdanam-73217'
ds = ds.drop(ds[ds['link'] == rus_speech_url].index)
ds_modified = True


if ds_modified:
    ds = ds.drop(columns=['__index_level_0__'])
    ds = Dataset.from_pandas(ds)
    ds.push_to_hub(REPO_ID)
    print('Pushed successfully')