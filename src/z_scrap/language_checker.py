from transformers import pipeline


def is_english(text):
    pipe = pipeline("text-classification",
                    model="papluca/xlm-roberta-base-language-detection")
    result = pipe(text, top_k=1, truncation=True)
    return result[0]["label"] == "en"
