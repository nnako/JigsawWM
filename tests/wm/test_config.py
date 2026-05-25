"""Test wm.config module."""

from types import SimpleNamespace

from jigsawwm.wm.config import WmConfig, WmRule


def test_find_rule_for_window_terminal_title_specificity():
    """A title-specific rule should win before a generic exe-only fallback."""
    config = WmConfig(
        rules=[
            WmRule(exe="WindowsTerminal.exe", title="nvim", static_window_index=0),
            WmRule(exe="WindowsTerminal.exe", static_window_index=1),
        ]
    )

    nvim_window = SimpleNamespace(
        exe=r"C:\Program Files\WindowsApps\WindowsTerminal.exe",
        title="notes - nvim - Windows Terminal",
    )
    shell_window = SimpleNamespace(
        exe=r"C:\Program Files\WindowsApps\WindowsTerminal.exe",
        title="PowerShell - Windows Terminal",
    )

    assert config.find_rule_for_window(nvim_window).static_window_index == 0
    assert config.find_rule_for_window(shell_window).static_window_index == 1
