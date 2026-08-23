import datetime
from datetime import date

import bot as _bot


class _FakeDatetime:
    def __init__(self, year: int, month: int, day: int):
        self._now = datetime.datetime(year, month, day, 12, 0, 0, tzinfo=datetime.timezone.utc)

    def now(self, tz=None):
        return self._now

    @classmethod
    def fromisoformat(cls, s):
        return datetime.date.fromisoformat(s)


class _MockUser:
    def __init__(self, user_id: int):
        self.id = user_id


class _MockCtx:
    """Simula un contexto de comando de Discord (DM con usuario whitelisted)."""

    def __init__(self, user_id: int):
        self.author = _MockUser(user_id)
        self.guild = None
        self.sent = []

    async def send(self, msg):
        self.sent.append(msg)


class TestCycleTable:
    def test_covers_exactly_14_days(self):
        assert len(_bot.CYCLE_DAY_EVENT) == 14
        assert set(_bot.CYCLE_DAY_EVENT) == set(range(14))

    def test_bt_occupies_days_0_to_5(self):
        for day, (event, phase) in _bot.CYCLE_DAY_EVENT.items():
            if day < 6:
                assert event == "bt"
                assert phase == day + 1
            else:
                assert event == "gt"

    def test_gt_has_two_full_phase_cycles(self):
        gt_phases = [phase for day, (event, phase) in _bot.CYCLE_DAY_EVENT.items() if event == "gt"]
        assert gt_phases == [0, 1, 2, 3, 0, 1, 2, 3]

    def test_gt_attack_lands_tuesday_and_saturday_from_anchor(self):
        # ancla = lunes (día 0). Día 8 = martes (GT#1 ataque), día 12 = sábado (GT#2 ataque).
        assert _bot.CYCLE_DAY_EVENT[8] == ("gt", 2)
        assert _bot.CYCLE_DAY_EVENT[12] == ("gt", 2)


class TestCyclePhase:
    def _freeze(self, monkeypatch, year: int, month: int, day: int):
        monkeypatch.setattr(_bot, "datetime", _FakeDatetime(year, month, day))

    def test_issue_example_sequence(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)

        self._freeze(monkeypatch, 2026, 8, 12)  # miércoles, día 9 → GT#1 cierre
        assert _bot.get_phase("gt") == 3
        assert _bot.get_phase("bt") is None

        self._freeze(monkeypatch, 2026, 8, 13)  # jueves, día 10 → GT#2 signup
        assert _bot.get_phase("gt") == 0

        self._freeze(monkeypatch, 2026, 8, 17)  # lunes, día 14 → BT fase 1
        assert _bot.get_phase("bt") == 1
        assert _bot.get_phase("gt") is None

    def test_full_cycle_sequence(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        expected = [
            ("bt", 1), ("bt", 2), ("bt", 3), ("bt", 4), ("bt", 5), ("bt", 6),
            ("gt", 0), ("gt", 1), ("gt", 2), ("gt", 3),
            ("gt", 0), ("gt", 1), ("gt", 2), ("gt", 3),
            ("bt", 1),
        ]
        for i, (event, phase) in enumerate(expected):
            self._freeze(monkeypatch, 2026, 8, 3 + i)
            assert _bot.get_phase(event) == phase, f"día {i}"
            other = "bt" if event == "gt" else "gt"
            assert _bot.get_phase(other) is None, f"día {i}"

    def test_cycle_auto_advances_past_14_days(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        self._freeze(monkeypatch, 2026, 8, 31)  # día 28 → 28 % 14 = 0 → BT fase 1
        assert _bot.get_phase("bt") == 1

    def test_auto_mode_without_anchor_returns_none(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(True)
        self._freeze(monkeypatch, 2026, 8, 12)
        assert _bot.get_phase("bt") is None
        assert _bot.get_phase("gt") is None

    def test_before_anchor_returns_none(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(True)
        _bot.set_cycle_anchor(date(2026, 8, 17))
        self._freeze(monkeypatch, 2026, 8, 12)
        assert _bot.get_phase("bt") is None

    def test_auto_mode_off_uses_manual_dates(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(False)
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_event_date("bt", "2026-07-20")
        self._freeze(monkeypatch, 2026, 7, 20)
        assert _bot.get_phase("bt") == 1


class TestAutoSettingsDb:
    def test_auto_mode_default_off(self, tmp_db):
        assert _bot.get_auto_mode() is False

    def test_set_and_get_auto_mode(self, tmp_db):
        assert _bot.set_auto_mode(True) is True
        assert _bot.get_auto_mode() is True
        assert _bot.set_auto_mode(False) is True
        assert _bot.get_auto_mode() is False

    def test_cycle_anchor_defaults_none(self, tmp_db):
        assert _bot.get_cycle_anchor() is None

    def test_set_and_get_cycle_anchor(self, tmp_db):
        assert _bot.set_cycle_anchor(date(2026, 8, 3)) is True
        assert _bot.get_cycle_anchor() == date(2026, 8, 3)


class TestResolveCycleAnchor:
    def test_provided_monday_used(self, tmp_db):
        assert _bot.resolve_cycle_anchor("2026-08-03") == (date(2026, 8, 3), False)

    def test_non_monday_aligned_to_previous_monday(self, tmp_db):
        assert _bot.resolve_cycle_anchor("2026-08-05") == (date(2026, 8, 3), True)

    def test_invalid_date_returns_none(self, tmp_db):
        assert _bot.resolve_cycle_anchor("no-es-fecha") == (None, False)

    def test_stored_bt_date_used(self, tmp_db):
        _bot.set_event_date("bt", "2026-08-03")
        assert _bot.resolve_cycle_anchor(None) == (date(2026, 8, 3), False)

    def test_defaults_to_most_recent_monday(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "datetime", _FakeDatetime(2026, 8, 12))  # miércoles
        assert _bot.resolve_cycle_anchor(None) == (date(2026, 8, 10), True)


class TestGtSlots:
    def test_gt_slots_mapping(self):
        expected = {6: (6, 19), 7: (0, 19), 8: (1, 18), 9: (2, 18), 10: (3, 18), 11: (4, 18), 12: (5, 17), 13: (6, 17)}
        assert _bot.GT_SLOTS == expected

    def test_gt_slot_6_sunday_nineteen(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))  # lunes -> día 0
        _bot.set_auto_mode(True)
        # frozen a Sunday at 19:00 UTC = day 6
        self._freeze_utc(monkeypatch, 2026, 8, 23, 19, 0)  # domingo 19:00
        assert _bot._gt_slot_matches() is True

    def test_gt_slot_7_monday_nineteen(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        # frozen a Monday at 19:00 UTC = day 7
        self._freeze_utc(monkeypatch, 2026, 8, 24, 19, 0)  # lunes 19:00
        assert _bot._gt_slot_matches() is True

    def test_gt_slot_8_tuesday_eighteen(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        # frozen a Tuesday at 18:00 UTC = day 8
        self._freeze_utc(monkeypatch, 2026, 8, 25, 18, 0)  # martes 18:00
        assert _bot._gt_slot_matches() is True

    def test_gt_slot_9_wednesday_eighteen(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        # frozen a Wednesday at 18:00 UTC = day 9
        self._freeze_utc(monkeypatch, 2026, 8, 26, 18, 0)  # miércoles 18:00
        assert _bot._gt_slot_matches() is True

    def test_gt_slot_10_thursday_eighteen(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        # frozen a Thursday at 18:00 UTC = day 10
        self._freeze_utc(monkeypatch, 2026, 8, 27, 18, 0)  # jueves 18:00
        assert _bot._gt_slot_matches() is True

    def test_gt_slot_11_friday_eighteen(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        # frozen a Friday at 18:00 UTC = day 11
        self._freeze_utc(monkeypatch, 2026, 8, 28, 18, 0)  # viernes 18:00
        assert _bot._gt_slot_matches() is True

    def test_gt_slot_12_saturday_seventeen(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        # frozen a Saturday at 17:00 UTC = day 12
        self._freeze_utc(monkeypatch, 2026, 8, 29, 17, 0)  # sábado 17:00
        assert _bot._gt_slot_matches() is True

    def test_gt_slot_13_sunday_seventeen(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        # frozen a Sunday at 17:00 UTC = day 13
        self._freeze_utc(monkeypatch, 2026, 8, 30, 17, 0)  # domingo 17:00
        assert _bot._gt_slot_matches() is True

    def test_no_slot_outside_gt_days(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 3))
        _bot.set_auto_mode(True)
        # frozen a BT day (e.g. day 1 Tuesday) at noon -> should be False
        # day 1 with anchor 2026-08-03 = 2026-08-04 (mon). Day 1 is BT.
        # Let's use a day that's not in GT_SLOTS (day 0-5 are BT)
        # Actually all days 6-13 are GT, days 0-5 are BT
        # Freeze a BT day at any hour -> should be False
        # Day 0 with anchor: 2026-08-03, so day -3 would be before anchor
        # Let's just freeze a day that maps to a BT day
        # With anchor 2026-08-03, cycle day 0 = 2026-08-03 (mon)
        # So day 0 is BT, freeze at 2026-08-03 12:00
        self._freeze_utc(monkeypatch, 2026, 8, 3, 12, 0)  # lunes 12:00 = día 0 BT
        assert _bot._gt_slot_matches() is False

    def test_no_slot_without_anchor(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(True)
        # No anchor set
        self._freeze_utc(monkeypatch, 2026, 8, 24, 19, 0)
        assert _bot._gt_slot_matches() is False

    def test_no_slot_before_anchor(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 17))
        _bot.set_auto_mode(True)
        # before anchor date
        self._freeze_utc(monkeypatch, 2026, 8, 16, 19, 0)
        assert _bot._gt_slot_matches() is False

    def _freeze_utc(self, monkeypatch, year, month, day, hour, minute):
        class FakeDateTime:
            @classmethod
            def now(cls, tz=None):
                tz = tz or timezone.utc
                return datetime.datetime(year, month, day, hour, minute, 0, tzinfo=tz)

            @classmethod
            def fromisoformat(cls, s):
                return datetime.date.fromisoformat(s)

        monkeypatch.setattr(_bot, "datetime", FakeDateTime)


class TestGapBA:
    """Tests for the gap between GT-A close and GT-B open."""

    def _freeze_utc(self, monkeypatch, year, month, day, hour, minute):
        class FakeDateTime:
            @classmethod
            def now(cls, tz=None):
                tz = tz or timezone.utc
                return datetime.datetime(year, month, day, hour, minute, 0, tzinfo=tz)

            @classmethod
            def fromisoformat(cls, s):
                return datetime.date.fromisoformat(s)

        monkeypatch.setattr(_bot, "datetime", FakeDateTime)

    def test_no_gt_alert_between_9_18_and_10_18(self, tmp_db, monkeypatch):
        """Verify no GT alert is published between day 9 18:00 UTC and day 10 18:00 UTC."""
        _bot.set_cycle_anchor(date(2026, 8, 3))  # lunes, day 0
        _bot.set_auto_mode(True)

        # Day 9 = Wednesday, should close A at 18:00
        # Day 10 = Thursday, should open B at 18:00
        # Between these there should be no GT alert

        # Simulate just after day 9 18:00 (Thursday 00:00) - no GT should fire
        self._freeze_utc(monkeypatch, 2026, 8, 27, 0, 0)  # jueves 00:00 = día 10 pero antes las 18:00
        assert _bot._gt_slot_matches() is False

        # At day 9 18:00 exactly (Wednesday 18:00) - this IS a GT slot (should match)
        self._freeze_utc(monkeypatch, 2026, 8, 26, 18, 0)  # miércoles 18:00 = día 9
        assert _bot._gt_slot_matches() is True

        # Just after day 9 18:00 (Wednesday 19:00) - should NOT match day 9 (wrong hour)
        # and should NOT match day 10 yet (wrong day)
        self._freeze_utc(monkeypatch, 2026, 8, 26, 19, 0)  # miércoles 19:00
        assert _bot._gt_slot_matches() is False

        # At day 10 18:00 exactly (Thursday 18:00) - should match day 10 slot
        self._freeze_utc(monkeypatch, 2026, 8, 27, 18, 0)  # jueves 18:00 = día 10
        assert _bot._gt_slot_matches() is True

        # Just after day 10 18:00 (Thursday 19:00) - should NOT match
        self._freeze_utc(monkeypatch, 2026, 8, 27, 19, 0)  # jueves 19:00
        assert _bot._gt_slot_matches() is False
    async def test_set_bt_date_ignored_when_auto(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(True)
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._set_date_cmd(ctx, "bt", "2026-08-03")
        assert ctx.sent
        assert "modo automático" in ctx.sent[0].lower()
        assert _bot.get_event_date("bt") is None

    async def test_set_gt_date_ignored_when_auto(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(True)
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._set_date_cmd(ctx, "gt", "2026-08-06")
        assert "modo automático" in ctx.sent[0].lower()
        assert _bot.get_event_date("gt") is None

    async def test_set_bt_date_works_when_auto_off(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(False)
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._set_date_cmd(ctx, "bt", "2026-08-03")
        assert _bot.get_event_date("bt") == "2026-08-03"


class TestAvisosCommand:
    async def test_status_shows_default_off(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._avisos_cmd(ctx, None, None)
        assert "detenido" in ctx.sent[0].lower()

    async def test_iniciar_enables_and_sets_anchor(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._avisos_cmd(ctx, "iniciar", "2026-08-03")
        assert _bot.get_auto_mode() is True
        assert _bot.get_cycle_anchor() == date(2026, 8, 3)

    async def test_iniciar_aligns_non_monday_to_previous_monday(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._avisos_cmd(ctx, "iniciar", "2026-08-05")  # miércoles
        assert _bot.get_cycle_anchor() == date(2026, 8, 3)
        assert any("no es lunes" in m for m in ctx.sent)

    async def test_iniciar_with_invalid_date_fails(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._avisos_cmd(ctx, "iniciar", "no-es-fecha")
        assert _bot.get_auto_mode() is False
        assert any("inválido" in m.lower() for m in ctx.sent)

    async def test_detener_disables_auto_mode(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(True)
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._avisos_cmd(ctx, "detener", None)
        assert _bot.get_auto_mode() is False

    async def test_unknown_action_shows_usage(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(1)
        await _bot._avisos_cmd(ctx, "borrar", None)
        assert _bot.get_auto_mode() is False
        assert any("inválida" in m for m in ctx.sent)

    async def test_unauthorized_user_denied(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(999)
        await _bot._avisos_cmd(ctx, "iniciar", "2026-08-03")
        assert _bot.get_auto_mode() is False
        assert any("permisos" in m for m in ctx.sent)
