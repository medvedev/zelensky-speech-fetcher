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


def to_timestamp(date_string, format_str):
    return int(datetime.strptime(date_string, format_str).timestamp())


def parse(date_string):
    # Replace Ukrainian month names with English equivalents
    for ukr_month, eng_month in ukrainian_months.items():
        new_date_string = date_string.replace(ukr_month, eng_month)
        if new_date_string != date_string:
            date_string = new_date_string
            return to_timestamp(date_string, "%d %B %Y року - %H:%M")

    return to_timestamp(date_string, '%d %B %Y - %H:%M')

