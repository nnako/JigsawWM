from jmk import hks
from log import *

from jigsawwm import daemon, ui
from jigsawwm.tiler import tilers
from jigsawwm.w32.vk import Vk
from jigsawwm.w32.window import inspect_active_window
from jigsawwm.wm import Theme, WindowManager

wm = WindowManager(
    themes=[
        # Theme(
        #     name="OBS Dwindle",
        #     layout_tiler=tilers.obs_dwindle_layout_tiler,
        #     icon_name="obs.png",
        #     gap=2,
        #     strict=True,
        # ),
        Theme(
            name="Mono",
            layout_tiler=tilers.mono_layout_tiler,
            strict=True,
        ),
        Theme(
            name="WideScreen Dwindle",
            layout_tiler=tilers.widescreen_dwindle_layout_tiler,
            icon_name="wide-dwindle.png",
            gap=2,
            strict=True,
            new_window_as_master=True,
        ),
        Theme(
            name="Dwindle",
            layout_tiler=tilers.dwindle_layout_tiler,
            strict=True,
            gap=2,
            new_window_as_master=True,
        ),
    ],
    ignore_exe_names=[
        "7zFM.exe",
        "explorer.exe",
        # "Feishu.exe",
        "fdm.exe",
        # "WeChat.exe",
        "foobar2000.exe",
        "ApplicationFrameHost.exe",
        "notepad++.exe",
        "PotPlayerMini64.exe",
        "mintty.exe",
        "openvpn-gui.exe",
        "Cloudflare WARP.exe",
        "MediaInfo.exe",
        "SnippingTool.exe",
    ],
    force_managed_exe_names=["Lens.exe"],
)

hotkeys = [
    ([Vk.WIN, Vk.J], wm.activate_next, ui.hide_windows_splash),
    ([Vk.WIN, Vk.K], wm.activate_prev, ui.hide_windows_splash),
    ([Vk.WIN, Vk.SHIFT, Vk.J], wm.swap_next),
    ([Vk.WIN, Vk.SHIFT, Vk.K], wm.swap_prev),
    ("Win+/", wm.set_master),
    ([Vk.WIN, Vk.SPACE], wm.next_theme),
    ([Vk.WIN, Vk.U], wm.prev_monitor),
    ([Vk.WIN, Vk.I], wm.next_monitor),
    ([Vk.WIN, Vk.SHIFT, Vk.U], wm.move_to_prev_monitor),
    ([Vk.WIN, Vk.SHIFT, Vk.I], wm.move_to_next_monitor),
    ([Vk.WIN, Vk.CONTROL, Vk.I], inspect_active_window),
]


class WindowManagerService(daemon.Service):
    name = "Window Manager"
    is_running = False

    def start(self):
        self.is_running = True
        wm.install_hooks()
        for args in hotkeys:
            hks.register(*args)

    def stop(self):
        wm.uninstall_hooks()
        for args in hotkeys:
            hks.unregister(args[0])
        self.is_running = False


daemon.register(WindowManagerService)

if __name__ == "__main__":
    daemon.message_loop()
