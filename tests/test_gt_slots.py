import datetime
from datetime import date, timedelta, timezone

import bot as _bot


class TestGtSlotTimes:
    def test_has_exactly_8_entries(self):
        assert len(_bot.GT_SLOT_TIMES) == 8

    def test_covers_days_6_through_13(self):
        assert set(_bot.GT_SLOT_TIMES) == set(range(6, 14))

    def test_each_cycle_day_has_exactly_one_slot(self):
        # Las claves son únicas por definición; este test documenta que no hay
        # días GT sin cubrir ni días duplicados en la tabla.
        assert sorted(_bot.GT_SLOT_TIMES) == list(range(6, 14))

    def test_hours_are_valid_spain_time(self):
        for day, hour in _bot.GT_SLOT_TIMES.items():
            assert 0 <= hour <= 23, f"día {day} hora {hour} fuera de rango"

    def test_slot_values_match_spec(self):
        expected = {6: 21, 7: 21, 8: 20, 9: 20, 10: 20, 11: 20, 12: 19, 13: 19}
        assert _bot.GT_SLOT_TIMES == expected

    def test_gt_a_defensa_is_21(self):
        assert _bot.GT_SLOT_TIMES[7] == 21

    def test_gt_a_ataque_is_20(self):
        assert _bot.GT_SLOT_TIMES[8] == 20

    def test_gt_b_ataque_is_19(self):
        assert _bot.GT_SLOT_TIMES[12] == 19

    def test_gt_b_fin_is_19(self):
        assert _bot.GT_SLOT_TIMES[13] == 19


class TestLocalSlotToUtc:
    def test_winter_uses_cet(self):
        expected = datetime.datetime(2026, 11, 9, 20, 0, tzinfo=timezone.utc)
        assert _bot.local_slot_to_utc(date(2026, 11, 9), 21) == expected

    def test_summer_uses_cest(self):
        expected = datetime.datetime(2026, 8, 17, 19, 0, tzinfo=timezone.utc)
        assert _bot.local_slot_to_utc(date(2026, 8, 17), 21) == expected

    def test_spring_forward_day_uses_cest(self):
        # 2026-03-29: a las 02:00 locales los relojes pasan a las 03:00 (CEST).
        expected = datetime.datetime(2026, 3, 29, 19, 0, tzinfo=timezone.utc)
        assert _bot.local_slot_to_utc(date(2026, 3, 29), 21) == expected

    def test_fall_back_day_uses_cet(self):
        # 2026-10-25: a las 03:00 locales los relojes vuelven a las 02:00 (CET).
        expected = datetime.datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)
        assert _bot.local_slot_to_utc(date(2026, 10, 25), 21) == expected

    def test_all_slot_hours_round_trip_to_spain(self):
        for day, hour in _bot.GT_SLOT_TIMES.items():
            slot_date = date(2026, 8, 17) + timedelta(days=day)
            utc_dt = _bot.local_slot_to_utc(slot_date, hour)
            local_dt = utc_dt.astimezone(_bot.GUILD_TZ)
            assert local_dt.date() == slot_date
            assert local_dt.hour == hour
            assert local_dt.minute == 0


class TestGtSlotMatches:
    def _setup_auto(self, tmp_db, anchor_date: date):
        _bot.set_cycle_anchor(anchor_date)
        _bot.set_auto_mode(True)

    def test_slot_6_sunday_21_madrid_matches_summer(self, tmp_db, monkeypatch):
        # Verano (CEST): 21:00 Madrid = 19:00 UTC.
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_6_wrong_hour_no_match_summer(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 20, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_slot_6_sunday_21_madrid_matches_winter(self, tmp_db, monkeypatch):
        # Invierno (CET): 21:00 Madrid = 20:00 UTC.
        self._setup_auto(tmp_db, date(2026, 11, 2))
        now = datetime.datetime(2026, 11, 8, 20, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_6_wrong_hour_no_match_winter(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 11, 2))
        now = datetime.datetime(2026, 11, 8, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_every_slot_matches_at_its_spain_hour(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        for cycle_day in range(6, 14):
            slot_date = date(2026, 8, 17) + timedelta(days=cycle_day)
            now = _bot.local_slot_to_utc(slot_date, _bot.GT_SLOT_TIMES[cycle_day])
            assert _bot.gt_slot_matches(now) is True, f"día {cycle_day}"

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
        """Entre el cierre del día 9 y la inscripción del día 10 no hay slot GT."""
        _bot.set_cycle_anchor(date(2026, 8, 17))
        _bot.set_auto_mode(True)
        # Día 9 = miércoles 26, slot 20:00 Madrid = 18:00 UTC; después, 19:00 UTC.
        now_after_close = datetime.datetime(2026, 8, 26, 19, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now_after_close) is False
        # Día 10 = jueves 27, antes del slot de 20:00 Madrid = 18:00 UTC.
        now_before_open = datetime.datetime(2026, 8, 27, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now_before_open) is False

    def test_day10_20_madrid_is_first_slot_after_gap(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 17))
        _bot.set_auto_mode(True)
        now = datetime.datetime(2026, 8, 27, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True


class TestDstScenarios:
    """Verificación DST end-to-end del calendario real BT/GT.

    Cada escenario ancla el ciclo a un lunes y comprueba los 8 slots GT de los
    días 6-13. El job debe disparar siempre a la hora local española exacta;
    el instante UTC equivalente cambia entre CET y CEST.
    """

    SCENARIOS = [
        # nombre, lunes de ancla, offset español esperado
        ("invierno_cet", date(2027, 1, 11), 1),
        ("verano_cest", date(2027, 7, 12), 2),
        # El domingo 28-mar-2027 es el día 6 del ciclo y ya usa CEST.
        ("cambio_marzo_cet_a_cest", date(2027, 3, 22), 2),
        # El domingo 31-oct-2027 es el día 6 del ciclo y ya usa CET.
        ("cambio_octubre_cest_a_cet", date(2027, 10, 25), 1),
    ]

    def test_every_gt_slot_fires_at_spain_hour_in_all_dst_scenarios(self, tmp_db):
        for name, anchor, expected_offset in self.SCENARIOS:
            _bot.set_cycle_anchor(anchor)
            _bot.set_auto_mode(True)
            for cycle_day in range(6, 14):
                slot_date = anchor + timedelta(days=cycle_day)
                hour = _bot.GT_SLOT_TIMES[cycle_day]
                expected_utc = _bot.local_slot_to_utc(slot_date, hour)
                local_dt = expected_utc.astimezone(_bot.GUILD_TZ)

                assert local_dt.date() == slot_date, name
                assert local_dt.hour == hour, name
                assert local_dt.utcoffset() == timedelta(hours=expected_offset), name
                assert _bot.gt_slot_matches(expected_utc) is True, (name, cycle_day)

    def test_utc_hour_oscillates_while_spain_hour_stays_fixed(self):
        # Mismo día de ciclo 6 (domingo), misma hora España, distinto UTC.
        summer = _bot.local_slot_to_utc(date(2027, 7, 18), 21)
        winter = _bot.local_slot_to_utc(date(2027, 1, 17), 21)
        assert summer.hour == 19
        assert winter.hour == 20
        assert summer.astimezone(_bot.GUILD_TZ).hour == 21
        assert winter.astimezone(_bot.GUILD_TZ).hour == 21

    def test_bt_trigger_fires_at_19_spain_in_all_dst_scenarios(self):
        # Usa el trigger real del job de BT (discord.ext.tasks), no una copia.
        trigger = _bot.daily_bt_order.time[0]
        scenarios = [
            ("invierno_cet", date(2026, 11, 9), 1, 18),
            ("verano_cest", date(2026, 8, 17), 2, 17),
            ("cambio_marzo_cet_a_cest", date(2026, 3, 29), 2, 17),
            ("cambio_octubre_cest_a_cet", date(2026, 10, 25), 1, 18),
        ]
        for name, day, expected_offset, expected_utc_hour in scenarios:
            local_dt = datetime.datetime.combine(day, trigger)
            assert local_dt.hour == 19, name
            assert local_dt.utcoffset() == timedelta(hours=expected_offset), name
            assert local_dt.astimezone(timezone.utc).hour == expected_utc_hour, name


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


class _FixedDatetime:
    """Reloj congelado que respeta la zona solicitada."""

    def __init__(self, utc_now: datetime.datetime):
        self._utc_now = utc_now

    def now(self, tz=None):
        return self._utc_now if tz is None else self._utc_now.astimezone(tz)

    @staticmethod
    def combine(*args, **kwargs):
        return datetime.datetime.combine(*args, **kwargs)


class _RecordingChannel:
    def __init__(self):
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)


class TestGtSchedulerLoopPublishing:
    """Invoca las tareas reales de discord.py con el reloj congelado."""

    def _setup(self, tmp_db, monkeypatch, utc_now):
        monkeypatch.setattr(_bot, "datetime", _FixedDatetime(utc_now))
        monkeypatch.setattr(_bot, "get_template_order", lambda templates, phase: "orden de prueba")
        channel = _RecordingChannel()
        monkeypatch.setattr(_bot.bot, "get_channel", lambda channel_id: channel)
        return channel

    async def test_each_gt_day_publishes_exactly_once_in_all_dst_scenarios(self, tmp_db, monkeypatch):
        for name, anchor, expected_offset in TestDstScenarios.SCENARIOS:
            _bot.set_cycle_anchor(anchor)
            _bot.set_auto_mode(True)
            for cycle_day in range(6, 14):
                slot_date = anchor + timedelta(days=cycle_day)
                hour = _bot.GT_SLOT_TIMES[cycle_day]
                slot_utc = _bot.local_slot_to_utc(slot_date, hour)
                local_dt = slot_utc.astimezone(_bot.GUILD_TZ)
                assert local_dt.hour == hour, (name, cycle_day)
                assert local_dt.utcoffset() == timedelta(hours=expected_offset), name

                channel = self._setup(tmp_db, monkeypatch, slot_utc)
                await _bot.gt_scheduler_loop.coro()
                assert len(channel.sent) == 1, (name, cycle_day)

                # Un segundo tick dentro del mismo slot no duplica la publicación.
                await _bot.gt_scheduler_loop.coro()
                assert len(channel.sent) == 1, (name, cycle_day)

    async def test_sunday_6_publishes_at_21_and_not_at_20(self, tmp_db, monkeypatch):
        anchor = date(2027, 1, 11)
        _bot.set_cycle_anchor(anchor)
        _bot.set_auto_mode(True)
        slot_date = anchor + timedelta(days=6)  # domingo

        early = _bot.local_slot_to_utc(slot_date, 20)
        channel = self._setup(tmp_db, monkeypatch, early)
        await _bot.gt_scheduler_loop.coro()
        assert channel.sent == []

        on_time = _bot.local_slot_to_utc(slot_date, 21)
        monkeypatch.setattr(_bot, "datetime", _FixedDatetime(on_time))
        await _bot.gt_scheduler_loop.coro()
        assert len(channel.sent) == 1

    async def test_sunday_13_publishes_at_19_and_not_at_20(self, tmp_db, monkeypatch):
        anchor = date(2027, 1, 11)
        _bot.set_cycle_anchor(anchor)
        _bot.set_auto_mode(True)
        slot_date = anchor + timedelta(days=13)  # domingo

        late = _bot.local_slot_to_utc(slot_date, 20)
        channel = self._setup(tmp_db, monkeypatch, late)
        await _bot.gt_scheduler_loop.coro()
        assert channel.sent == []

        on_time = _bot.local_slot_to_utc(slot_date, 19)
        monkeypatch.setattr(_bot, "datetime", _FixedDatetime(on_time))
        await _bot.gt_scheduler_loop.coro()
        assert len(channel.sent) == 1

    async def test_bt_loop_does_not_publish_on_gt_days(self, tmp_db, monkeypatch):
        anchor = date(2027, 1, 11)
        _bot.set_cycle_anchor(anchor)
        _bot.set_auto_mode(True)
        bt_time = _bot.local_slot_to_utc(anchor + timedelta(days=6), 19)
        channel = self._setup(tmp_db, monkeypatch, bt_time)

        await _bot.daily_bt_order.coro()

        assert channel.sent == []
