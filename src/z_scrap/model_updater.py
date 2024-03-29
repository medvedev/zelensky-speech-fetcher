import datetime

from datasets import load_dataset

REPO_ID = 'slava-medvedev/zelensky-speeches'


def update_dataset(new_items):
    if len(new_items) != 0:
        dataset = load_dataset(REPO_ID, split="train", cache_dir="./cache")
        old_num_rows = dataset.num_rows
        for new_speech in new_items:
            dataset = dataset.add_item(new_speech)
        print(f"Old num_rows: {old_num_rows}, new num_rows: {dataset.num_rows}")
        dataset.push_to_hub(REPO_ID, commit_message=f'Update speeches from {datetime.date.today().isoformat()}')
    else:
        print('No items to add to a dataset. Skipping.')
