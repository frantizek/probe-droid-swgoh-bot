import datetime

import bot as _bot


class TestGetPhase:
    def _freeze_time(self, monkeypatch, year: int, month: int, day: int):
        """Replace _bot.datetime with a mock class so get_phase uses our fixed time."""

        class FakeDatetime:
            @classmethod
            def now(cls, tz=None):  # noqa: N805
                return datetime.datetime(year, month, day, 12, 0, 0, tzinfo=datetime.timezone.utc)

            @classmethod
            def fromisoformat(cls, s):  # noqa: N805
                return datetime.date.fromisoformat(s)

        monkeypatch.setattr(_bot, "datetime", FakeDatetime)

    def test_unknown_event_type_returns_none(self, tmp_db):
        assert _bot.get_phase("unknown") is None

    def test_no_date_configured_returns_none(self, tmp_db):
        assert _bot.get_phase("bt") is None

    def test_future_date_returns_none(self, tmp_db, monkeypatch):
        self._freeze_time(monkeypatch, 2026, 6, 1)
        _bot.set_event_date("bt", "2026-07-20")
        assert _bot.get_phase("bt") is None

    def test_bt_phase_calculation(self, tmp_db, monkeypatch):
        _bot.set_event_date("bt", "2026-07-20")

        self._freeze_time(monkeypatch, 2026, 7, 20)
        assert _bot.get_phase("bt") == 1

        self._freeze_time(monkeypatch, 2026, 7, 21)
        assert _bot.get_phase("bt") == 2

    def test_bt_phase_over_max_returns_none(self, tmp_db, monkeypatch):
        _bot.set_event_date("bt", "2026-07-20")
        self._freeze_time(monkeypatch, 2026, 7, 26)
        assert _bot.get_phase("bt") is None

    def test_gt_phase_by_weekday(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-07-30")

        self._freeze_time(monkeypatch, 2026, 7, 30)  # jueves
        assert _bot.get_phase("gt") == 0

        self._freeze_time(monkeypatch, 2026, 7, 31)  # viernes
        assert _bot.get_phase("gt") == 1

        self._freeze_time(monkeypatch, 2026, 8, 1)  # sábado
        assert _bot.get_phase("gt") == 2

        self._freeze_time(monkeypatch, 2026, 8, 2)  # domingo
        assert _bot.get_phase("gt") == 0

        self._freeze_time(monkeypatch, 2026, 8, 3)  # lunes
        assert _bot.get_phase("gt") == 1

        self._freeze_time(monkeypatch, 2026, 8, 4)  # martes
        assert _bot.get_phase("gt") == 2

    def test_gt_wednesday_has_no_publication(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-07-30")
        self._freeze_time(monkeypatch, 2026, 8, 5)  # miércoles
        assert _bot.get_phase("gt") is None

    def test_gt_phase_repeats_weekly_ignoring_start_date(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-06-01")
        self._freeze_time(monkeypatch, 2026, 8, 3)  # lunes semanas después
        assert _bot.get_phase("gt") == 1

        self._freeze_time(monkeypatch, 2026, 8, 2)  # domingo
        assert _bot.get_phase("gt") == 0


class TestGetOrderDate:
    def _freeze_time(self, monkeypatch, year: int, month: int, day: int):
        class FakeDatetime:
            @classmethod
            def now(cls, tz=None):  # noqa: N805
                return datetime.datetime(year, month, day, 12, 0, 0, tzinfo=datetime.timezone.utc)

            @classmethod
            def fromisoformat(cls, s):  # noqa: N805
                return datetime.date.fromisoformat(s)

        monkeypatch.setattr(_bot, "datetime", FakeDatetime)

    def test_gt_uses_today_for_message_header(self, tmp_db, monkeypatch):
        self._freeze_time(monkeypatch, 2026, 8, 3)
        start = datetime.date(2026, 7, 30)
        assert _bot.get_order_date("gt", start, 1) == datetime.date(2026, 8, 3)

    def test_bt_uses_phase_date_for_message_header(self, tmp_db, monkeypatch):
        self._freeze_time(monkeypatch, 2026, 8, 3)
        start = datetime.date(2026, 7, 20)
        assert _bot.get_order_date("bt", start, 3) == datetime.date(2026, 7, 22)
