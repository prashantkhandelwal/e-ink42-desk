import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class WifiRecoveryTests(unittest.TestCase):
    def make_scope(self):
        source = Path(__file__).resolve().parents[1] / "main.py"
        tree = ast.parse(source.read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
        scope = {
            name: Mock()
            for name in (
                "connect_wifi", "create_api_server", "service_render_api", "Pin",
                "EPD_4in2", "synchronize_clock_with_retry", "get_stock_quote",
                "get_local_weather", "get_current_location", "update_local_clock",
                "show_dashboard", "show_wifi_disconnected", "show_error", "print",
                "wait_for_action",
            )
        }
        scope.update(
            VIEW_DASHBOARD=0, VIEW_FEED=1, VIEW_CUSTOM=2, ACTION_NEXT_FEED=3,
            KEY0_PIN=0, KEY1_PIN=1, CONFIG={},
            TIME_SYNC_INTERVAL_MS=1000, DATA_UPDATE_INTERVAL_MS=1000,
            time=SimpleNamespace(ticks_ms=lambda: 0, ticks_diff=lambda a, b: a - b),
            gc=SimpleNamespace(collect=Mock()),
            wifi_is_connected=lambda wlan: wlan is not None and wlan.connected,
        )
        scope["get_stock_quote"].return_value = {"price": 100}
        scope["update_local_clock"].return_value = 0
        scope["synchronize_clock_with_retry"].return_value = False
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), scope)
        return scope

    def test_connection_loss_shows_icon_and_reconnection_redraws(self):
        scope = self.make_scope()
        wlan = SimpleNamespace(connected=True)

        def disconnect():
            wlan.connected = False
            return None

        def connect():
            wlan.connected = True
            return wlan

        actions = iter((disconnect, connect))

        def wait(*args):
            action = next(actions, None)
            if action is None:
                raise KeyboardInterrupt
            return action()

        scope["connect_wifi"].side_effect = [wlan, RuntimeError("Wi-Fi connection timed out"), wlan]
        scope["wait_for_action"].side_effect = wait
        with self.assertRaises(KeyboardInterrupt):
            scope["main"]()
        scope["show_wifi_disconnected"].assert_called_once()
        scope["show_error"].assert_not_called()
        self.assertEqual(scope["show_dashboard"].call_count, 2)
        for call in scope["show_dashboard"].call_args_list:
            self.assertTrue(call.kwargs["clear_first"])
            self.assertFalse(call.kwargs["partial"])

    def test_initial_timeout_shows_icon(self):
        scope = self.make_scope()
        scope["connect_wifi"].side_effect = RuntimeError("Wi-Fi connection timed out")
        scope["wait_for_action"].side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            scope["main"]()
        scope["show_wifi_disconnected"].assert_called_once()
        scope["show_error"].assert_not_called()

    def test_connected_errors_keep_text_screen(self):
        scope = self.make_scope()
        scope["connect_wifi"].return_value = SimpleNamespace(connected=True)
        error = RuntimeError("Quote request failed")
        scope["get_stock_quote"].side_effect = error
        scope["wait_for_action"].side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            scope["main"]()
        scope["show_wifi_disconnected"].assert_not_called()
        scope["show_error"].assert_called_once_with(scope["EPD_4in2"].return_value, error)
