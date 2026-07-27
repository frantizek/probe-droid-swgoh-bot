from datetime import date

import bot


class TestFormatDateEs:
    def test_normal_date(self):
        d = date(2026, 7, 27)
        assert bot.format_date_es(d) == "27 de Julio"

    def test_january_first(self):
        d = date(2026, 1, 1)
        assert bot.format_date_es(d) == "1 de Enero"

    def test_december_thirty_first(self):
        d = date(2026, 12, 31)
        assert bot.format_date_es(d) == "31 de Diciembre"

    def test_february_leap(self):
        d = date(2024, 2, 29)
        assert bot.format_date_es(d) == "29 de Febrero"


class TestFormatWeekdayDateEs:
    def test_monday(self):
        d = date(2026, 7, 27)
        assert bot.format_weekday_date_es(d) == "LUNES 27 de Julio:"

    def test_saturday(self):
        d = date(2026, 7, 25)
        assert bot.format_weekday_date_es(d) == "SÁBADO 25 de Julio:"

    def test_sunday(self):
        d = date(2026, 7, 26)
        assert bot.format_weekday_date_es(d) == "DOMINGO 26 de Julio:"
