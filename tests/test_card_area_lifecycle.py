"""Focused LuaJIT regressions against functions read from an external APK.

Run with ``uv run --with lupa python tests/test_card_area_lifecycle.py``.
An external APK fixture is required at build/release-5678.apk, or set
BALATRO_TEST_APK / pass --apk. No game source is vendored here, and these
API-level checks do not replace an Android playtest.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import unittest
import zipfile

from lupa.luajit21 import LuaRuntime


DEFAULT_APK = Path("build/release-5678.apk")
UTILS_PATH = "assets/smods_mods/Steamodded/src/utils.lua"
OVERRIDES_PATH = "assets/smods_mods/Steamodded/src/overrides.lua"


def source_section(source: str, start: str, stop: str) -> str:
    """Keep APK line numbers in Lua tracebacks while loading a focused section."""
    begin = source.index(start)
    end = source.index(stop, begin)
    return "\n" * source.count("\n", 0, begin) + source[begin:end]


class CardAreaLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apk = Path(os.environ.get("BALATRO_TEST_APK", DEFAULT_APK)).expanduser()
        if not cls.apk.is_file():
            raise FileNotFoundError(
                f"APK fixture missing: {cls.apk}. Set BALATRO_TEST_APK or --apk."
            )
        with zipfile.ZipFile(cls.apk) as apk:
            utils = apk.read(UTILS_PATH).decode("utf-8")
            overrides = apk.read(OVERRIDES_PATH).decode("utf-8")
        cls.utils_source = source_section(
            utils, "function SMODS.slot_number(raw)", "function SMODS.get_atlas("
        )
        cls.edition_helpers = source_section(
            overrides,
            "local function smods_slot_number(value)",
            "local function normalize_loaded_edition(card)",
        )
        cls.edition_source = source_section(
            overrides, "function Card:set_edition(", "function poll_edition("
        )
        # Both sections came from one file. Remove overlapping blank padding so
        # their shared lexical chunk still reports the APK's original lines.
        cls.edition_source = cls.edition_helpers + cls.edition_source[
            cls.edition_helpers.count("\n") :
        ]

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        # Boundary doubles: engine rendering/audio, event queue, centers, and the
        # big-number conversion API. Slot helpers, refresh, and set_edition below
        # are the APK's implementations, not rewritten test equivalents.
        self.lua.execute(
            """
            Card = {}
            CardArea = {}
            SMODS = {enh_cache = {write = function() end}}
            G = {
                P_CENTERS = {
                    e_base = {config = {}, discovered = true},
                    e_negative = {config = {card_limit = 1}, discovered = true},
                    e_foil = {config = {}, discovered = true},
                },
                CONTROLLER = {locks = {}},
                STATES = {DRAW_TO_HAND = 1, SELECTING_HAND = 2},
                STATE = 0,
                GAME = {blind = {config = {blind = {key = 'bl_small'}}}},
                FUNCS = {},
                E_MANAGER = {events = {}},
            }
            function G.E_MANAGER:add_event(event)
                self.events[#self.events + 1] = event
            end
            function Event(event) return event end
            function check_for_unlock() end
            function discover_card(center) center.discovered = true end
            function play_sound() end
            function copy_table(value)
                local result = {}
                for key, item in pairs(value) do
                    result[key] = type(item) == 'table' and copy_table(item) or item
                end
                return result
            end
            function to_number(value)
                if value.fail_conversion then error('cannot convert Big value') end
                return value.big_value
            end
            function SMODS.blind_modifies_draw() return false end
            function G.FUNCS.draw_from_deck_to_hand(amount)
                G.last_draw_amount = amount
            end
            function Card:set_cost() self.cost_refreshes = (self.cost_refreshes or 0) + 1 end
            function Card:juice_up() end
            function make_area(kind, base, mod)
                return setmetatable({
                    cards = {},
                    config = {
                        type = kind,
                        card_count = 71,
                        card_limits = {
                            base = base or 5,
                            mod = mod or 0,
                            total_slots = 37,
                            extra_slots = 0,
                            extra_slots_used = 0,
                            old_slots = 0,
                        },
                    },
                }, {__index = CardArea})
            end
            function make_card(area, card_set, card_limit, slots_used)
                local card = setmetatable({
                    area = area,
                    ability = {
                        set = card_set or 'Joker',
                        card_limit = card_limit or 0,
                        extra_slots_used = slots_used or 0,
                    },
                    ignore_base_shader = {},
                    ignore_shadow = {},
                }, {__index = Card})
                if area and type(area.cards) == 'table' then
                    area.cards[#area.cards + 1] = card
                end
                return card
            end
            """
        )
        self.lua.execute(self.utils_source, name="@" + UTILS_PATH)
        # Local helpers and Card:set_edition must share a lexical chunk.
        self.lua.execute(
            self.edition_source,
            name="@" + OVERRIDES_PATH,
        )

    def assert_lua_succeeds(self, source):
        result = self.lua.execute(
            "return xpcall(function()\n" + source + "\nend, debug.traceback)"
        )
        if isinstance(result, tuple):
            succeeded, detail = result[0], result[1]
        else:
            succeeded, detail = result, None
        self.assertTrue(succeeded, detail)

    def test_edition_refresh_ignores_removed_shop_owner(self):
        """The reported set_edition -> refresh -> #area.cards path must finish."""
        self.assert_lua_succeeds(
            """
            local area = make_area('shop', 5, 2)
            local card = make_card(area)
            area.cards = nil -- CardArea:remove() invalidates this field.
            local result = card:set_edition('e_negative', true, true)
            assert(result == nil)
            assert(card.edition.negative and card.ability.card_limit == 1)
            assert(card.ability.extra_slots_used == 0)
            assert(card.cost_refreshes == 1)
            assert(area.cards == nil)
            assert(area.config.card_count == 71)
            assert(area.config.card_limits.total_slots == 37)
            """
        )

    def test_edition_refresh_ignores_uninitialized_hand_owner(self):
        self.assert_lua_succeeds(
            """
            local area = make_area('hand', 8, 0)
            area.cards = nil
            local card = make_card(area, 'Enhanced')
            card:set_edition('e_negative', true, true)
            assert(card.ability.card_limit == 1)
            assert(area.cards == nil)
            assert(area.config.card_count == 71)
            assert(area.config.card_limits.total_slots == 37)
            """
        )

    def test_negative_removal_ignores_removed_owner(self):
        self.assert_lua_succeeds(
            """
            local area = make_area('shop')
            local card = make_card(area, 'Joker', 3, 1)
            card.edition = {negative = true, type = 'negative',
                key = 'e_negative', card_limit = 1}
            area.cards = nil
            assert(card:set_edition(nil, true, true) == nil)
            assert(card.edition == nil)
            assert(card.ability.card_limit == 2)
            assert(card.ability.extra_slots_used == 1)
            assert(card.cost_refreshes == 1)
            assert(area.cards == nil)
            assert(area.config.card_count == 71)
            assert(area.config.card_limits.total_slots == 37)
            """
        )

    def test_refresh_ignores_malformed_owner_state(self):
        cases = {
            "missing_config": "area.config = nil",
            "number_config": "area.config = 42",
            "false_config": "area.config = false",
            "missing_limits": "area.config.card_limits = nil",
            "number_limits": "area.config.card_limits = 42",
            "false_limits": "area.config.card_limits = false",
            "number_cards": "area.cards = 42",
            "false_cards": "area.cards = false",
        }
        for name, damage in cases.items():
            with self.subTest(name=name):
                self.assert_lua_succeeds(
                    """
                    local area = make_area('shop')
                    local card = make_card(area)
                    """
                    + damage
                    + """
                    local cards, config = area.cards, area.config
                    local limits = type(config) == 'table' and config.card_limits
                    card:set_edition('e_negative', true, true)
                    assert(card.ability.card_limit == 1)
                    assert(card.cost_refreshes == 1)
                    assert(area.cards == cards and area.config == config)
                    if type(config) == 'table' then
                        assert(config.card_count == 71)
                        assert(config.card_limits == limits)
                    end
                    if type(limits) == 'table' then
                        assert(limits.total_slots == 37)
                    end
                    """
                )

    def test_refresh_ignores_non_table_owner(self):
        for owner in ("42", "true", "'removed'"):
            with self.subTest(owner=owner):
                self.assert_lua_succeeds(
                    """
                    local card = make_card(nil)
                    card.area = """
                    + owner
                    + """
                    card:set_edition('e_negative', true, true)
                    assert(card.ability.card_limit == 1)
                    assert(card.cost_refreshes == 1)
                    """
                )

    def test_direct_handle_ignores_invalid_area_state(self):
        cases = {
            "removed": "area.cards = nil",
            "missing_config": "area.config = nil",
            "number_config": "area.config = 42",
            "missing_limits": "area.config.card_limits = nil",
            "number_limits": "area.config.card_limits = 42",
            "number_cards": "area.cards = 42",
        }
        for name, damage in cases.items():
            with self.subTest(name=name):
                self.assert_lua_succeeds(
                    "local area = make_area('shop')\n"
                    + damage
                    + """
                    local cards, config = area.cards, area.config
                    local limits = type(config) == 'table' and config.card_limits
                    assert(CardArea.handle_card_limit(area) == nil)
                    assert(area.cards == cards and area.config == config)
                    if type(config) == 'table' then
                        assert(config.card_count == 71)
                        assert(config.card_limits == limits)
                    end
                    if type(limits) == 'table' then
                        assert(limits.total_slots == 37)
                    end
                    """
                )

    def test_card_without_owner_keeps_edition_slot_bookkeeping(self):
        self.assert_lua_succeeds(
            """
            local card = make_card(nil, 'Joker', 2, 1)
            assert(card:set_edition('e_negative', true, true) == nil)
            assert(card.edition.negative)
            assert(card.ability.card_limit == 3)
            assert(card.ability.extra_slots_used == 1)
            assert(card.area == nil)
            card:set_edition(nil, true, true)
            assert(card.edition == nil and card.ability.card_limit == 2)
            assert(card.cost_refreshes == 2)
            """
        )

    def test_live_joker_consumable_and_hand_counts_include_slot_properties(self):
        for role in ("jokers", "consumeables", "hand"):
            with self.subTest(role=role):
                kind = "hand" if role == "hand" else "joker"
                self.assert_lua_succeeds(
                    """
                    G.jokers, G.consumeables, G.hand = nil, nil, nil
                    local area = make_area('"""
                    + kind
                    + """', 5, 2)
                    G."""
                    + role
                    + """ = area
                    make_card(area, 'Joker', 1, 0)
                    make_card(area, 'Tarot', 2, 1)
                    assert(area:handle_card_limit() == nil)
                    assert(area.config.card_limits.extra_slots == 3)
                    assert(area.config.card_limits.total_slots == 10)
                    assert(area.config.card_limits.extra_slots_used == 1)
                    assert(area.config.card_count == 3)
                    assert(area.config.card_limits.base == 5)
                    assert(area.config.card_limits.mod == 2)
                    """
                )

    def test_shop_and_fixed_limit_area_counts_keep_existing_behavior(self):
        for kind, fixed in (("shop", "false"), ("joker", "true")):
            with self.subTest(kind=kind, fixed=fixed):
                self.assert_lua_succeeds(
                    "local area = make_area('"
                    + kind
                    + "', 5, 2)\narea.config.fixed_limit = "
                    + fixed
                    + """
                    make_card(area, 'Joker', 3, 2)
                    make_card(area, 'Joker', 4, 1)
                    assert(area:handle_card_limit() == nil)
                    assert(area.config.card_count == 2)
                    assert(area.config.card_limits.total_slots == 7)
                    assert(area.config.card_limits.base == 5)
                    assert(area.config.card_limits.mod == 2)
                    """
                )

    def test_negative_add_repeat_and_remove_preserve_other_slot_contributions(self):
        for role in ("jokers", "consumeables", "hand"):
            with self.subTest(role=role):
                kind = "hand" if role == "hand" else "joker"
                card_set = {"jokers": "Joker", "consumeables": "Tarot", "hand": "Enhanced"}[role]
                self.assert_lua_succeeds(
                    """
                    G.jokers, G.consumeables, G.hand = nil, nil, nil
                    local area = make_area('"""
                    + kind
                    + """', 5, 2)
                    G."""
                    + role
                    + """ = area
                    local card = make_card(area, '"""
                    + card_set
                    + """', 2, 1)
                    area:handle_card_limit()
                    assert(area.config.card_limits.total_slots == 9)
                    card:set_edition('e_negative', true, true)
                    assert(card.ability.card_limit == 3)
                    assert(area.config.card_limits.total_slots == 10)
                    assert(area.config.card_count == 2)
                    card:set_edition('e_negative', true, true)
                    assert(card.ability.card_limit == 3)
                    assert(area.config.card_limits.total_slots == 10)
                    card:set_edition(nil, true, true)
                    assert(card.edition == nil and card.ability.card_limit == 2)
                    assert(card.ability.extra_slots_used == 1)
                    assert(area.config.card_limits.total_slots == 9)
                    assert(area.config.card_count == 2)
                    assert(area.config.card_limits.base == 5)
                    assert(area.config.card_limits.mod == 2)
                    """
                )

    def test_negative_slot_is_counted_after_owner_is_assigned(self):
        self.assert_lua_succeeds(
            """
            local card = make_card(nil)
            card:set_edition('e_negative', true, true)
            local area = make_area('joker')
            area.cards[1] = card
            card.area = area
            area:handle_card_limit()
            assert(card.ability.card_limit == 1)
            assert(area.config.card_limits.extra_slots == 1)
            assert(area.config.card_limits.total_slots == 6)
            assert(area.config.card_count == 1)
            """
        )

    def test_big_number_slot_fields_are_normalized_by_real_edition_helpers(self):
        self.assert_lua_succeeds(
            """
            local area = make_area('joker', 5, 2)
            G.jokers = area
            local card = make_card(area, 'Joker', {big_value = 2}, {big_value = 3})
            G.P_CENTERS.e_negative.config = {
                card_limit = {big_value = 1}, extra_slots_used = {big_value = -1},
            }
            card:set_edition('e_negative', true, true)
            assert(type(card.ability.card_limit) == 'number')
            assert(type(card.ability.extra_slots_used) == 'number')
            assert(card.ability.card_limit == 3 and card.ability.extra_slots_used == 2)
            assert(area.config.card_limits.total_slots == 10)
            assert(area.config.card_count == 3)
            card:set_edition('e_negative', true, true)
            assert(card.ability.card_limit == 3 and card.ability.extra_slots_used == 2)
            assert(area.config.card_limits.total_slots == 10)
            card:set_edition(nil, true, true)
            assert(card.ability.card_limit == 2 and card.ability.extra_slots_used == 3)
            assert(area.config.card_limits.total_slots == 9)
            assert(area.config.card_count == 4)
            """
        )

    def test_real_count_property_accepts_big_string_and_missing_slot_values(self):
        self.assert_lua_succeeds(
            """
            local area = make_area('joker', 5, 2)
            make_card(area, 'Joker', {big_value = 2}, {big_value = -1})
            make_card(area, 'Joker', '3', '2')
            area.cards[3] = {ability = {}}
            area.cards[4] = {ability = {card_limit = {fail_conversion = true}}}
            area.cards[5] = {} -- Lightweight UI card has no ability.
            area:handle_card_limit()
            assert(area.config.card_limits.extra_slots == 5)
            assert(area.config.card_limits.total_slots == 12)
            assert(area.config.card_limits.extra_slots_used == 1)
            assert(area.config.card_count == 6)
            """
        )

    def test_existing_negative_is_not_erased_by_later_ordinary_edition(self):
        self.assert_lua_succeeds(
            """
            local area = make_area('joker')
            G.jokers = area
            local card = make_card(area)
            card:set_edition('e_negative', true, true)
            card:set_edition('e_foil', true, true)
            assert(card.edition.negative and card.edition.key == 'e_negative')
            assert(card.ability.card_limit == 1)
            assert(area.config.card_limits.total_slots == 6)
            assert(card.cost_refreshes == 1)
            """
        )

    def test_valid_area_handler_errors_are_not_swallowed(self):
        self.assert_lua_succeeds(
            """
            local area = make_area('shop')
            area.handle_card_limit = function() error('handler failure sentinel') end
            local card = make_card(area)
            local ok, message = pcall(card.set_edition, card, 'e_negative', true, true)
            assert(not ok and tostring(message):find('handler failure sentinel', 1, true))
            """
        )

    def test_edition_callback_errors_are_not_swallowed(self):
        self.assert_lua_succeeds(
            """
            G.P_CENTERS.e_negative.on_apply = function()
                error('edition callback failure sentinel')
            end
            local card = make_card(make_area('joker'))
            local ok, message = pcall(card.set_edition, card, 'e_negative', true, true)
            assert(not ok and tostring(message):find('edition callback failure sentinel', 1, true))
            """
        )

    def test_deferred_edition_event_finishes_after_shop_owner_is_removed(self):
        self.assert_lua_succeeds(
            """
            local area = make_area('shop')
            local card = make_card(area)
            G.E_MANAGER:add_event(Event({trigger = 'immediate', func = function()
                card:set_edition('e_negative', true, true)
                return true
            end}))
            area.cards = nil
            assert(G.E_MANAGER.events[1].func() == true)
            assert(card.edition.negative and card.ability.card_limit == 1)
            assert(area.cards == nil)
            """
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--apk")
    options, unittest_args = parser.parse_known_args()
    if options.apk:
        os.environ["BALATRO_TEST_APK"] = options.apk
    unittest.main(argv=[sys.argv[0], *unittest_args])
