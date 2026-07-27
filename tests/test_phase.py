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

    def test_gt_phase_calculation(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-07-24")

        self._freeze_time(monkeypatch, 2026, 7, 24)
        assert _bot.get_phase("gt") == 0

        self._freeze_time(monkeypatch, 2026, 7, 25)
        assert _bot.get_phase("gt") == 1

    def test_gt_phase_over_max_returns_none(self, tmp_db, monkeypatch):
        _bot.set_event_date("gt", "2026-07-24")
        self._freeze_time(monkeypatch, 2026, 7, 28)
        assert _bot.get_phase("gt") is None
