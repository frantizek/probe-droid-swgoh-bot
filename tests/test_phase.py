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

    def test_gt_phase_thursday_start_3_days(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-07-30")  # jueves

        self._freeze_time(monkeypatch, 2026, 7, 30)  # jueves (día 0)
        assert _bot.get_phase("gt") == 0

        self._freeze_time(monkeypatch, 2026, 7, 31)  # viernes (día 1)
        assert _bot.get_phase("gt") == 1

        self._freeze_time(monkeypatch, 2026, 8, 1)  # sábado (día 2)
        assert _bot.get_phase("gt") == 2

        self._freeze_time(monkeypatch, 2026, 8, 2)  # domingo (día 3, fuera de ventana)
        assert _bot.get_phase("gt") is None

    def test_gt_phase_sunday_start_7_days(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-08-02")  # domingo

        self._freeze_time(monkeypatch, 2026, 8, 2)  # domingo (día 0)
        assert _bot.get_phase("gt") == 0

        self._freeze_time(monkeypatch, 2026, 8, 3)  # lunes (día 1)
        assert _bot.get_phase("gt") == 1

        self._freeze_time(monkeypatch, 2026, 8, 4)  # martes (día 2)
        assert _bot.get_phase("gt") == 2

        self._freeze_time(monkeypatch, 2026, 8, 6)  # jueves (día 4, 2ª GT)
        assert _bot.get_phase("gt") == 0

        self._freeze_time(monkeypatch, 2026, 8, 7)  # viernes (día 5)
        assert _bot.get_phase("gt") == 1

        self._freeze_time(monkeypatch, 2026, 8, 8)  # sábado (día 6)
        assert _bot.get_phase("gt") == 2

        self._freeze_time(monkeypatch, 2026, 8, 9)  # domingo (día 7, fuera de ventana)
        assert _bot.get_phase("gt") is None

    def test_gt_wednesday_no_publication_inside_window(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-08-02")  # domingo, ventana de 7 días
        self._freeze_time(monkeypatch, 2026, 8, 5)  # miércoles (día 3)
        assert _bot.get_phase("gt") is None

    def test_gt_other_weekday_start_defaults_to_3_days(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-08-03")  # lunes (con aviso, ventana de 3 días)
        self._freeze_time(monkeypatch, 2026, 8, 3)
        assert _bot.get_phase("gt") == 1

        self._freeze_time(monkeypatch, 2026, 8, 6)  # jueves (día 3, fuera de ventana)
        assert _bot.get_phase("gt") is None


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
