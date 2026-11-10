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


class TestLocalSlotToUtc:
    def test_winter_uses_cet(self):
        expected = datetime.datetime(2026, 11, 9, 18, 0, tzinfo=timezone.utc)
        assert _bot.local_slot_to_utc(date(2026, 11, 9), 19) == expected

    def test_summer_uses_cest(self):
        expected = datetime.datetime(2026, 8, 17, 17, 0, tzinfo=timezone.utc)
        assert _bot.local_slot_to_utc(date(2026, 8, 17), 19) == expected

    def test_spring_forward_day_uses_cest(self):
        # 2026-03-29: a las 02:00 locales los relojes pasan a las 03:00 (CEST).
        expected = datetime.datetime(2026, 3, 29, 17, 0, tzinfo=timezone.utc)
        assert _bot.local_slot_to_utc(date(2026, 3, 29), 19) == expected

    def test_fall_back_day_uses_cet(self):
        # 2026-10-25: a las 03:00 locales los relojes vuelven a las 02:00 (CET).
        expected = datetime.datetime(2026, 10, 25, 18, 0, tzinfo=timezone.utc)
        assert _bot.local_slot_to_utc(date(2026, 10, 25), 19) == expected

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

    def test_slot_6_sunday_19_madrid_matches_summer(self, tmp_db, monkeypatch):
        # Verano (CEST): 19:00 Madrid = 17:00 UTC.
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_6_wrong_hour_no_match_summer(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_slot_6_sunday_19_madrid_matches_winter(self, tmp_db, monkeypatch):
        # Invierno (CET): 19:00 Madrid = 18:00 UTC.
        self._setup_auto(tmp_db, date(2026, 11, 2))
        now = datetime.datetime(2026, 11, 8, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True

    def test_slot_6_wrong_hour_no_match_winter(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 11, 2))
        now = datetime.datetime(2026, 11, 8, 17, 0, 0, tzinfo=timezone.utc)
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
        now = datetime.datetime(2026, 8, 23, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_no_match_without_anchor(self, tmp_db, monkeypatch):
        _bot.set_auto_mode(True)
        now = datetime.datetime(2026, 8, 23, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_no_match_before_anchor(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 24))
        now = datetime.datetime(2026, 8, 23, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_no_match_on_bt_day(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 17, 18, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is False

    def test_idempotent_no_double_post(self, tmp_db, monkeypatch):
        self._setup_auto(tmp_db, date(2026, 8, 17))
        now = datetime.datetime(2026, 8, 23, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True
        _bot.mark_gt_posted(6, "2026-08-23")
        assert _bot.gt_slot_matches(now) is False


class TestGapBA:
    def test_no_slot_between_day9_and_day10(self, tmp_db, monkeypatch):
        """Entre el cierre del día 9 y la inscripción del día 10 no hay slot GT."""
        _bot.set_cycle_anchor(date(2026, 8, 17))
        _bot.set_auto_mode(True)
        # Día 9 = miércoles 26, slot 18:00 Madrid = 16:00 UTC; después, 17:00 UTC.
        now_after_close = datetime.datetime(2026, 8, 26, 17, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now_after_close) is False
        # Día 10 = jueves 27, antes del slot de 18:00 Madrid = 16:00 UTC.
        now_before_open = datetime.datetime(2026, 8, 27, 15, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now_before_open) is False

    def test_day10_18_madrid_is_first_slot_after_gap(self, tmp_db, monkeypatch):
        _bot.set_cycle_anchor(date(2026, 8, 17))
        _bot.set_auto_mode(True)
        now = datetime.datetime(2026, 8, 27, 16, 0, 0, tzinfo=timezone.utc)
        assert _bot.gt_slot_matches(now) is True


class TestDstScenarios:
    """Verificación DST end-to-end del calendario real BT/GT.

    Cada escenario ancla el ciclo a un lunes y comprueba los 8 slots GT de los
    días 6-13. El job debe disparar siempre a la hora local española exacta;
    el instante UTC equivalente cambia entre CET y CEST.
    """

    SCENARIOS = [
        # nombre, lunes de ancla, offset español esperado
        ("invierno_cet", date(2026, 11, 2), 1),
        ("verano_cest", date(2026, 8, 17), 2),
        ("cambio_marzo_cet_a_cest", date(2026, 3, 23), 2),
        ("cambio_octubre_cest_a_cet", date(2026, 10, 19), 1),
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
        summer = _bot.local_slot_to_utc(date(2026, 8, 23), 19)
        winter = _bot.local_slot_to_utc(date(2026, 11, 8), 19)
        assert summer.hour == 17
        assert winter.hour == 18
        assert summer.astimezone(_bot.GUILD_TZ).hour == 19
        assert winter.astimezone(_bot.GUILD_TZ).hour == 19

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
