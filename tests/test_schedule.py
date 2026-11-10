from datetime import time
from zoneinfo import ZoneInfo

import bot


class TestBattleTypesSchedule:
    def test_guild_timezone_is_madrid(self):
        assert bot.GUILD_TZ == ZoneInfo("Europe/Madrid")

    def test_bt_post_time_is_19_spain(self):
        cfg = bot.BATTLE_TYPES["bt"]
        assert cfg["post_hour"] == 19
        assert cfg["post_minute"] == 0

    def test_gt_post_time_stays_18_spain(self):
        cfg = bot.BATTLE_TYPES["gt"]
        assert cfg["post_hour"] == 18
        assert cfg["post_minute"] == 0

    def test_all_event_types_have_post_time(self):
        for key, cfg in bot.BATTLE_TYPES.items():
            assert "post_hour" in cfg, f"{key} missing post_hour"
            assert "post_minute" in cfg, f"{key} missing post_minute"
            assert isinstance(cfg["post_hour"], int), f"{key} post_hour not int"
            assert isinstance(cfg["post_minute"], int), f"{key} post_minute not int"
            assert 0 <= cfg["post_hour"] <= 23, f"{key} post_hour out of range"
            assert 0 <= cfg["post_minute"] <= 59, f"{key} post_minute out of range"

    def test_bt_task_time_is_madrid_aware(self):
        trigger = bot.task_time(
            bot.BATTLE_TYPES["bt"]["post_hour"],
            bot.BATTLE_TYPES["bt"]["post_minute"],
        )
        assert trigger == time(19, 0, tzinfo=ZoneInfo("Europe/Madrid"))
        assert trigger.tzinfo == bot.GUILD_TZ

    def test_bt_scheduler_loop_uses_madrid(self):
        # discord.py expone los triggers del loop en .time; el job real de BT
        # debe estar anclado a Europe/Madrid, no a UTC.
        triggers = bot.daily_bt_order.time
        assert triggers == [time(19, 0, tzinfo=bot.GUILD_TZ)]
        assert all(trigger.tzinfo == bot.GUILD_TZ for trigger in triggers)

    def test_gt_slots_are_spain_hours(self):
        expected = {6: 19, 7: 19, 8: 18, 9: 18, 10: 18, 11: 18, 12: 17, 13: 17}
        assert bot.GT_SLOT_TIMES == expected
