import datetime
import gzip

from datasets import load_dataset

REPO_ID = 'slava-medvedev/zelensky-speeches'


def _patch_hf_filesystem():
    # huggingface_hub 0.34.x returns gzip-compressed bytes via HfFileSystem without
    # decompressing them, causing UnicodeDecodeError when datasets reads the README.md
    # before push_to_hub commits. Add a gzip fallback so the card read succeeds.
    try:
        from huggingface_hub import HfFileSystem

        def _read_text(self, path, encoding="utf-8", errors="strict", newline=None, **kwargs):
            try:
                with self.open(path, mode="rt", encoding=encoding, errors=errors, newline=newline, **kwargs) as f:
                    return f.read()
            except UnicodeDecodeError:
                with self.open(path, mode="rb") as f:
                    raw = f.read()
                return gzip.decompress(raw).decode(encoding, errors=errors)

        HfFileSystem.read_text = _read_text
    except Exception:
        pass


_patch_hf_filesystem()


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
