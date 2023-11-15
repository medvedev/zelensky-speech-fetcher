from datasets import load_dataset

REPO_ID = 'slava-medvedev/zelensky-speeches'


def update_dataset(new_items):
    if len(new_items) != 0:
        dataset = load_dataset(REPO_ID, split="train")
        for new_speech in new_items:
            dataset = dataset.add_item(new_speech)
        dataset.push_to_hub(REPO_ID)
    else:
        print('No items to add to a dataset. Skipping.')
