import json

from datasets import load_dataset
import pandas as pd

REPO_ID = 'slava-medvedev/zelensky-speeches'

dataset = load_dataset(REPO_ID, split="train", cache_dir="./cache")

labels_and_search_strings = {
    'незламно' : 'незламн',
    'потужно' : 'потужн',
    'дякую' : 'дякую',
    'перемога' : r'перемо[гзж]',
    'партнер' : 'партнер',
    'корупція' : 'корупці'
}

df = dataset.to_pandas()
df = df[df['lang'] == 'uk']
df['місяць'] = pd.to_datetime(df['date'], unit='s').dt.strftime('%y-%m')
texts_str = df['full_text'].str
for label, pattern in labels_and_search_strings.items():
    df[label] = texts_str.count(pattern)
result = df.groupby('місяць')[list(labels_and_search_strings.keys())].sum().reset_index()
result = result[:-1]
result.to_csv('output.csv', index=False)

data = {
    "місяць": result['місяць'].tolist(),
}

for label in labels_and_search_strings.keys():
    data[label] = result[label].tolist()

with open('output.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

