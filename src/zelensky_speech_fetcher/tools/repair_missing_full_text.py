import datetime
import os
import shutil
import time

from datasets import load_dataset, load_from_disk, Dataset
from zelensky_speech_fetcher.z_scrap.dataset_updater import REPO_ID
from zelensky_speech_fetcher.z_scrap.main import HttpFetcher, SpeechExtractionError, get_full_text

CHECKPOINT_DIR = "./.repair_checkpoint"
CACHE_DIR = "./.cache"
REPAIR_DELAY_SECONDS = 5


def load_working_dataset():
    if os.path.exists(CHECKPOINT_DIR):
        print(f"Resuming from checkpoint: {CHECKPOINT_DIR}")
        return load_from_disk(CHECKPOINT_DIR)
    return load_dataset(REPO_ID, split="train", cache_dir=CACHE_DIR)


def save_checkpoint(df):
    shutil.rmtree(CHECKPOINT_DIR, ignore_errors=True)
    Dataset.from_pandas(df, preserve_index=False).save_to_disk(CHECKPOINT_DIR)


def push_dataset(df, fixed_count):
    print(f"Pushing dataset with {fixed_count} repaired full_text values...")
    Dataset.from_pandas(df, preserve_index=False).push_to_hub(
        REPO_ID,
        commit_message=f"Repair missing full_text values ({datetime.date.today().isoformat()})",
    )
    print("Push complete.")


def main():
    dataset = load_working_dataset()
    df = dataset.to_pandas()
    missing = df[df["full_text"].isna() | (df["full_text"] == "")]
    print(f"Found {len(missing)} speeches with missing full_text")

    if missing.empty:
        print("Nothing to repair.")
        return 0

    fetcher = HttpFetcher(browser_first=True)
    fixed_count = 0
    first_error = None

    try:
        for i, (idx, row) in enumerate(missing.iterrows()):
            if i > 0:
                time.sleep(REPAIR_DELAY_SECONDS)
            print(f"[{i + 1}/{len(missing)}] Fetching {row['link']}")
            try:
                text = get_full_text(fetcher, row["link"])
            except SpeechExtractionError as exc:
                first_error = exc
                print(f"  FAILED: {exc}")
                break
            df.at[idx, "full_text"] = text
            fixed_count += 1
            print(f"  -> {len(text)} chars - saving checkpoint")
            save_checkpoint(df)
    finally:
        fetcher.close()

    remaining = df[df["full_text"].isna() | (df["full_text"] == "")]
    print(
        f"\nDone. Fixed: {fixed_count}, still missing: {len(remaining)}, "
        f"stopped_on_error: {first_error is not None}"
    )

    if fixed_count > 0:
        push_dataset(df, fixed_count)
        shutil.rmtree(CHECKPOINT_DIR, ignore_errors=True)
        print("Checkpoint cleaned up after push.")

    if first_error is not None:
        return 1

    if fixed_count == 0:
        print("No missing full_text values were repaired.")
    else:
        print("Repair run completed without fetch errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
