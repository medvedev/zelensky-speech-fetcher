from datasets import load_dataset, Dataset

REPO_ID = 'slava-medvedev/zelensky-speeches'

ds = load_dataset(REPO_ID, split="train").to_pandas()
duplicates = ds[ds.duplicated(subset='date', keep=False)]

if not duplicates.empty:
    ds.drop_duplicates(subset='date', keep='first', inplace = True)
    ds = Dataset.from_pandas(ds)
    ds.push_to_hub(REPO_ID)
    print("Duplicates removed and dataset saved.")
else:
    print("No duplicates found in.")
