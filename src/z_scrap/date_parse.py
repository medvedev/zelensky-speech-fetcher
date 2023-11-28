from datetime import datetime

# Define the Ukrainian month names and their English equivalents
ukrainian_months = {
    'січня': 'January',
    'лютого': 'February',
    'березня': 'March',
    'квітня': 'April',
    'травня': 'May',
    'червня': 'June',
    'липня': 'July',
    'серпня': 'August',
    'вересня': 'September',
    'жовтня': 'October',
    'листопада': 'November',
    'грудня': 'December'
}


def parse(ukrainian_date_string):
    # Replace Ukrainian month names with English equivalents
    for ukr_month, eng_month in ukrainian_months.items():
        ukrainian_date_string = ukrainian_date_string.replace(ukr_month, eng_month)

    # Set the locale to Ukrainian
    # locale.setlocale(locale.LC_TIME, 'uk_UA.UTF-8')

    # Define the format for parsing
    date_format = "%d %B %Y року - %H:%M"
    return int(datetime.strptime(ukrainian_date_string, date_format).timestamp())
