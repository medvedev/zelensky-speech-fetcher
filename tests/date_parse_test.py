import datetime
import unittest

from src.z_scrap.date_parse import parse


class MyTestCase(unittest.TestCase):
    def tast_datetime_parse(self):
        parsed = parse('13 листопада 2023 року - 20:34')
        self.assertEqual(parsed, datetime.datetime(2023, 11, 13, 20, 34))


if __name__ == '__main__':
    unittest.main()
