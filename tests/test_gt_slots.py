import datetime
from datetime import date, timedelta, timezone

import bot as _bot


class _FakeDatetime:
    def __init__(self, year: int, month: int, day: int, hour: int = 12):
        self._now = datetime.datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)

    def now(self, tz=None):
        return self._now

    @classmethod
    def fromisoformat(cls, s):
        return date.fromisoformat(s)


class TestGtSlotTimes:
    def test_has_exactly_8_entries(self):
        assert len(_bot.GT_SLOT_TIMES) == 8

    def test_covers_days_6_through_13(self):
        assert set(_bot.GT_SLOT_TIMES) == set(range(6, 14))

    def test_hours_are_valid_utc(self):
        for day, hour in _bot.GT_SLOT_TIMES.items():
            assert 0 <= hour <= 23, f"día {day} hora {hour} fuera de rango"

    def test_slot_values_match_spec(self):
        expected = {6: 19, 7: 19, 8: 18, 9: 18, 10: 18, 11: 18, 12: 17, 13: 17}
        assert _bot.GT_SLOT_TIMES == expected

    def test_gt_a_defensa_is_19(self):
        assert _bot.GT_SLOT_TIMES[7] == 19

    def test_gt_a_ataque_is_18(self):
        assert _bot.GT_SLOT_TIMES[8] == 18

    def test_gt_b_ataque_is_17(self):
        assert _bot.GT_SLOT_TIMES[12] == 17

    def test_gt_b_fin_is_17(self):
        assert _bot.GT_SLOT_TIMES[13] == 17


class TestGtSlotMatches:
    def _setup_auto(self, tmp_db, anchor_date: date):
        _bot.set_cycle_anchor(anchor_date)
        _bot.set_auto_mode(True)

    def test_slot_6_sunday_19_matches(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_6_wrong_hour_no_match(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_slot_7_monday_19_matches(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 24, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_8_tuesday_18_matches(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 25, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_9_wednesday_18_matches(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 26, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_10_thursday_18_matches(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 27, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_11_friday_18_matches(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 28, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_12_saturday_17_matches(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 29, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_13_sunday_17_matches(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 30, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_no_match_when_auto_off(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(False)
        _bot.set_cycle_anchor(date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_no_match_without_anchor(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(True)
        now = datetime.datetime(2026, 8, 23, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_no_match_before_anchor(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 24))
        now = datetime.datetime(2026, 8, 23, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_no_match_on_bt_day(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 17, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_idempotent_no_double_post(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True
        _bot.mark_gt_posted(6, "2026-08-23")
        assert _bot.gt_slot_matches(now) is False


class TestGapBA:
    def test_no_slot_between_day9_and_day10(self, tmp_db, monkeypatch):
        """Entre día 9 18:00 y día 10 18:00 no hay ningún slot GT."""
        _bot.set_cycle_anchor(date(2026, 8, 17))
        _bot.set_auto_mode(True)
        # Día 9 = miércoles 26, hora 19 (después del slot 18:00) → no match
        now_after_close = datetime.datetime(2026, 8, 26, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now_after_close) is False
        # Día 10 = jueves 27, hora 17 (antes del slot 18:00) → no match
        now_before_open = datetime.datetime(2026, 8, 27, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now_before_open) is False

    def test_day10_18_is_first_slot_after_gap(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 17))
        _bot.set_auto_mode(True)
        now = datetime.datetime(2026, 8, 27, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True


class TestIdempotencyDb:
    def test_is_gt_posted_false_initially(self, tmp_db):
        assert _bot.is_gt_posted(6, "2026-08-23") is False

    def test_mark_and_check(self, tmp_db):
        _bot.mark_gt_posted(6, "2026-08-23")
        assert _bot.is_gt_posted(6, "2026-08-23") is True

    def test_different_day_not_marked(self, tmp_db):
        _bot.mark_gt_posted(6, "2026-08-23")
        assert _bot.is_gt_posted(7, "2026-08-23") is False

    def test_different_date_not_marked(self, tmp_db):
        _bot.mark_gt_posted(6, "2026-08-23")
        assert _bot.is_gt_posted(6, "2026-08-24") is False

    def test_mark_is_idempotent(self, tmp_db):
        _bot.mark_gt_posted(6, "2026-08-23")
        _bot.mark_gt_posted(6, "2026-08-23")
        assert _bot.is_gt_posted(6, "2026-08-23") is True
