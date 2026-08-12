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


class TestManualDatesIgnoredInAutoMode:
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
