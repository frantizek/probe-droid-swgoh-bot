import bot


class TestBattleTypesSchedule:
    def test_bt_post_time(self):
        cfg = bot.BATTLE_TYPES["bt"]
        assert cfg["post_hour"] == 17
        assert cfg["post_minute"] == 0

    def test_gt_post_time(self):
        cfg = bot.BATTLE_TYPES["gt"]
        assert cfg["post_hour"] == 19
        assert cfg["post_minute"] == 0

    def test_bt_and_gt_have_different_hours(self):
        bt_hour = bot.BATTLE_TYPES["bt"]["post_hour"]
        gt_hour = bot.BATTLE_TYPES["gt"]["post_hour"]
        assert bt_hour != gt_hour, "BT and GT should post at different hours"

    def test_all_event_types_have_post_time(self):
        for key, cfg in bot.BATTLE_TYPES.items():
            assert "post_hour" in cfg, f"{key} missing post_hour"
            assert "post_minute" in cfg, f"{key} missing post_minute"
            assert isinstance(cfg["post_hour"], int), f"{key} post_hour not int"
            assert isinstance(cfg["post_minute"], int), f"{key} post_minute not int"
            assert 0 <= cfg["post_hour"] <= 23, f"{key} post_hour out of range"
            assert 0 <= cfg["post_minute"] <= 59, f"{key} post_minute out of range"
