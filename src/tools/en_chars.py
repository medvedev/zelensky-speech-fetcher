import string

from datasets import load_dataset

from src.z_scrap.dataset_updater import REPO_ID

dataset = load_dataset(REPO_ID, split="train", cache_dir="./cache")

dataset = dataset.filter(lambda x: x['lang'] == 'en')

allowed_chars = set(string.ascii_letters + string.digits + string.punctuation + " ")

def calculate_invalid_percentage(text: str) -> float:
    """
    Calculate the percentage of characters in `text` that are not:
    - Letters (a-z, A-Z)
    - Digits (0-9)
    - Punctuation (from string.punctuation)
    - A space (" ")

    Returns the percentage as a float.
    """
    if not text:
        return 0.0  # Avoid division by zero for empty strings

    # Count characters that are not in allowed_chars.
    invalid_count = sum(1 for char in text if char not in allowed_chars)

    # Calculate percentage of invalid characters.
    percentage = (invalid_count / len(text)) * 100
    return percentage


# Define a function to apply to each example in the dataset.
def add_invalid_percentage(example):
    # Assuming the text is stored under the key 'text'
    example["invalid_percentage"] = calculate_invalid_percentage(example["full_text"])
    return example


# Map over the dataset to add the new field.
dataset = dataset.map(add_invalid_percentage)

# Get the maximum percentage value from the dataset.
max_invalid_percentage = max(dataset["invalid_percentage"])

print(
    f"The maximum percentage of characters outside [0-9a-zA-Z], spaces, and punctuation is: {max_invalid_percentage:.2f}%")
