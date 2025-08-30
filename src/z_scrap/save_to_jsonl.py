import json
from time import sleep

from src.z_scrap.main import extract_data


def run():
    page = 25
    # while True:
    _, speeches = extract_data(
        # f'https://www.president.gov.ua/en/news/speeches?date-from=11-12-2022&date-to=11-12-2023&page={page}')
        # f'https://www.president.gov.ua/en/news/speeches?date-from=21-11-2021&date-to=11-12-2022&page={page}')
        f'https://www.president.gov.ua/news/speeches',
        force=True)
    # if len(speeches) == 0:
    #     break
    with open('speeches_uk.jsonl', 'a') as outfile:
        for entry in speeches:
            entry_json = json.dumps(entry, ensure_ascii=False)
            outfile.write(entry_json)
            outfile.write('\n')
    page += 1
    sleep(5)


if __name__ == '__main__':
    run()
