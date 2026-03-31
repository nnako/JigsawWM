"""An example of setting up all features"""

import logging
import os
import time
from functools import partial

log = logging.getLogger(__name__)

import requests

from jigsawwm.app.daemon import Daemon, MessageType
from jigsawwm.app.job import ProcessService
from jigsawwm.app.services import CaffeineService
from jigsawwm.app.tasks import DailyWebsites, WorkdayAutoStart
from jigsawwm.jmk.core import JmkKey, JmkTapHold, Vk
from jigsawwm.jmk.jmk_service import (ctrl_shift_w, ctrl_w, send_now,
                                      send_now_compact, send_today,
                                      send_today_compact)
from jigsawwm.ui.app import clipboard_helper
from jigsawwm.w32.sendinput import send_combination
from jigsawwm.w32.vk import Vk, parse_combination
from jigsawwm.w32.window import (Window, get_foreground_window,
                                 minimize_active_window)
from jigsawwm.wm.config import WmRule
from jigsawwm.wm.manager import WmConfig

# Window.enable_bound_compensation = False

daemon = Daemon()


daemon.jmk.core.register_layers(
    [
        {  # layer 0
            # map capslock to ctrl when held and `  when tapped
            Vk.CAPITAL: JmkTapHold(tap=Vk.ESCAPE, hold=Vk.LCONTROL),
            Vk.RETURN: JmkTapHold(tap=Vk.RETURN, hold=Vk.LCONTROL),
            # hold TAB to switch to layer 1
            Vk.TAB: JmkTapHold(tap=Vk.TAB, hold=1),
            # hold ' to switch to layer 2
            Vk.OEM_PERIOD: JmkTapHold(tap=Vk.OEM_PERIOD, hold=2),
            # hold space for SHIFT, tap for space
            Vk.SPACE: JmkTapHold(tap=Vk.SPACE, hold=Vk.LSHIFT),
            # hold backward mouse button to switch to layer 2
            Vk.XBUTTON1: JmkTapHold(tap=Vk.XBUTTON1, hold=2, term=0.4),
        },
        {  # layer 1
            # left hand
            Vk.A: JmkKey(Vk.HOME),
            Vk.E: JmkKey(Vk.END),
            Vk.D: JmkKey(Vk.DELETE),
            Vk.B: JmkKey("LCtrl+Left"),
            Vk.F: JmkKey("LCtrl+Right"),
            # right hand
            Vk.H: JmkKey(Vk.LEFT),
            Vk.J: JmkKey(Vk.DOWN),
            Vk.K: JmkKey(Vk.UP),
            Vk.L: JmkKey(Vk.RIGHT),
            Vk.U: JmkKey("LCtrl+Prior"),
            Vk.I: JmkKey("LCtrl+Next"),
            Vk.N: JmkKey(Vk.MEDIA_NEXT_TRACK),
            Vk.P: JmkKey(Vk.MEDIA_PREV_TRACK),
            Vk.OEM_COMMA: JmkKey(Vk.VOLUME_DOWN),
            Vk.OEM_PERIOD: JmkKey(Vk.VOLUME_UP),
            Vk.SLASH: JmkKey(Vk.MEDIA_PLAY_PAUSE),
            # helper
            Vk.T: JmkTapHold(on_tap=send_today, on_hold_down=send_now),
            Vk.C: JmkTapHold(on_tap=send_today_compact, on_hold_down=send_now_compact),
            # Vk.BACK: JmkKey(suspend_system),
            Vk.CAPITAL: JmkKey(Vk.CAPITAL),
        },
        {  # layer 2
            Vk.MBUTTON: JmkTapHold(on_tap=ctrl_w, hold=ctrl_shift_w),
            Vk.RBUTTON: JmkKey(daemon.wm.manager.toggle_splash),
        },
    ]
)
daemon.jmk.sysin.bypass_mouse_event = True


def send_comb_then_center_cursor_to_the_active_window(comb: str, delay: float = 0.5):
    """Send a hotkey combination then focus the active window"""
    send_combination(*parse_combination(comb))
    time.sleep(delay)
    fgw = get_foreground_window()
    if fgw:
        Window(fgw).center_cursor()


COPY_PASTE = (parse_combination("LCtrl+c"), parse_combination("LCtrl+v"))
COPY_PASTE_SHIFT = (
    parse_combination("LCtrl+LShift+c"),
    parse_combination("LCtrl+LShift+v"),
)


def smart_copy_paste(op: str = "copy"):
    """Send Ctrl+c/v or Ctrl+Shift+c/v base on the active window"""
    combs = COPY_PASTE
    fgwh = get_foreground_window()
    if fgwh:
        fgw = Window(fgwh)
        if fgw.exe_name.lower() in ("windowsterminal.exe", "code.exe"):
            combs = COPY_PASTE_SHIFT
    comb = combs[0 if op == "copy" else 1]
    send_combination(*comb)

def system_sleep():
    send_combination(Vk.LWIN, Vk.X)
    time.sleep(0.3)
    send_combination(Vk.U)
    send_combination(Vk.S)

def call_llm(system_prompt: str, user_prompt: str):
    # request OpenAI-compatible chat completion using the environment
    # variables `OPENAI_URL` and `OPENAI_KEY`.
    url = os.getenv("OPENAI_URL")
    key = os.getenv("OPENAI_KEY")
    model = os.getenv("OPENAI_MODEL", "deepseek/deepseek-v3.2-251201")
    log.debug("call_llm: url=%s model=%s", url, model)
    if not url or not key:
        raise RuntimeError("OPENAI_URL and OPENAI_KEY environment variables must be set")

    endpoint = url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 512,
        "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    log.debug("call_llm: POST %s payload_size=%d", endpoint, len(str(payload)))
    resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
    log.debug("call_llm: response status=%d", resp.status_code)
    resp.raise_for_status()
    data = resp.json()
    log.debug("call_llm: response data=%s", data)

    # Support OpenAI ChatCompletion-style responses
    if isinstance(data, dict) and "choices" in data and data["choices"]:
        first = data["choices"][0]
        if isinstance(first, dict):
            if "message" in first and isinstance(first["message"], dict):
                return first["message"].get("content", "")
            if "text" in first:
                return first.get("text", "")

    # Fallback: return a best-effort string representation
    log.warning("call_llm: unexpected response shape, returning str(data)")
    return str(data)


def _polish_selected_text_read(callback: callable, original: str):
    # Runs on main thread with clipboard text in hand
    log.info("_on_clipboard_read: clipboard text length=%d", len(original) if original else 0)
    try:
        if not original or not original.strip():
            log.warning("_on_clipboard_read: no text selected or clipboard is empty")
            daemon.show_buble_msg( "Polish Text", "No text selected or clipboard is empty.", MessageType.INFO)
            return

        system_prompt = (
            "You are a helpful assistant. Polished the user's text: correct grammar, "
            "improve clarity and conciseness while preserving meaning. Return only the polished text."
        )

        log.debug("_on_clipboard_read: calling LLM with %d chars", len(original))
        daemon.show_buble_msg( "Polish Text", "Polishing text...", MessageType.INFO)
        polished = call_llm(system_prompt, original)
        log.debug("_on_clipboard_read: LLM returned %d chars", len(polished) if polished else 0)
        if not polished:
            log.warning("_on_clipboard_read: LLM returned no result")
            # daemon.trayicon.showMessage(
            #     "Polish Text", "LLM returned no result.", QSystemTrayIcon.MessageIcon.Warning
            # )
            return

        clipboard_helper.set_text_async.emit(polished)
        time.sleep(0.1)
        if callback:
            callback()
        daemon.show_buble_msg("Polish Text", "Done")
    except Exception as exc:
        log.exception("_on_clipboard_read: unhandled exception: %s", exc)
        daemon.show_buble_msg( "Polish Text", f"{type(exc).__name__}: {exc}", MessageType.ERROR)


def polish_clipboard_text(callback: callable = None):
    smart_copy_paste("copy")
    clipboard_helper.get_text_async.emit(partial(_polish_selected_text_read, callback))

def polish_selected_text():
    log.debug("polish_selected_text: sending copy keystroke from hotkey thread")
    # Read clipboard on main thread after a delay for the copy to complete
    def callback():
        time.sleep(0.1)
        smart_copy_paste("paste")


daemon.jmk.hotkeys.register_triggers(
    [
        ("Win+q", "LAlt+F4"),
        ("Win+s", "RCtrl+s"),
        ("Win+z", "RCtrl+z"),
        ("Win+p", polish_selected_text),
        ("Win+c", partial(smart_copy_paste, "copy")),
        ("Win+v", partial(smart_copy_paste, "paste")),
        ("Win+Shift+v", "RWin+v"),
        (
            "Win+Ctrl+w",
            partial(send_comb_then_center_cursor_to_the_active_window, "RCtrl+RAlt+w"),
        ),
        (
            "Win+Ctrl+e",
            partial(send_comb_then_center_cursor_to_the_active_window, "RCtrl+RAlt+e"),
        ),
        ("Win+Ctrl+l", "LWin+LCtrl+Right"),
        ("Win+Ctrl+h", "LWin+LCtrl+Left"),
        ("Win+Ctrl+q", daemon.quit_act.triggered.emit),
        ("Win+Ctrl+f1", system_sleep),
        ([Vk.WIN, Vk.N], minimize_active_window),
        ([Vk.RCONTROL, Vk.SLASH], "RCtrl+x"),
        ([Vk.RCONTROL, Vk.PERIOD], "RCtrl+c"),
        ([Vk.RCONTROL, Vk.COMMA], "RCtrl+v"),
    ]
)

daemon.wm.hotkeys = [
    ([Vk.WIN, Vk.CTRL, Vk.J], daemon.wm.manager.next_window),
    ([Vk.WIN, Vk.CTRL, Vk.K], daemon.wm.manager.prev_window),
    ([Vk.WIN, Vk.SHIFT, Vk.J], daemon.wm.manager.swap_next),
    ([Vk.WIN, Vk.SHIFT, Vk.K], daemon.wm.manager.swap_prev),
    ("Win+Ctrl+/", daemon.wm.manager.set_master),
    ("Win+Ctrl+.", daemon.wm.manager.roll_next),
    ("Win+Ctrl+,", daemon.wm.manager.roll_prev),
    ([Vk.WIN, Vk.CONTROL, Vk.SPACE], daemon.wm.manager.next_theme),
    ([Vk.WIN, Vk.CTRL, Vk.U], daemon.wm.manager.prev_monitor),
    ([Vk.WIN, Vk.CTRL, Vk.I], daemon.wm.manager.next_monitor),
    ([Vk.WIN, Vk.SHIFT, Vk.U], daemon.wm.manager.move_to_prev_monitor),
    ([Vk.WIN, Vk.SHIFT, Vk.I], daemon.wm.manager.move_to_next_monitor),
    ("Win+Ctrl+a", partial(daemon.wm.manager.switch_to_workspace, 0)),
    ("Win+Ctrl+s", partial(daemon.wm.manager.switch_to_workspace, 1)),
    ("Win+Ctrl+d", partial(daemon.wm.manager.switch_to_workspace, 2)),
    ("Win+Ctrl+f", partial(daemon.wm.manager.switch_to_workspace, 3)),
    # ("Win+Ctrl+j", partial(daemon.wm.manager.next_workspace)),
    # ("Win+Ctrl+k", partial(daemon.wm.manager.prev_workspace)),
    ("Win+Ctrl+Shift+a", partial(daemon.wm.manager.move_to_workspace, 0)),
    ("Win+Ctrl+Shift+s", partial(daemon.wm.manager.move_to_workspace, 1)),
    ("Win+Ctrl+Shift+d", partial(daemon.wm.manager.move_to_workspace, 2)),
    ("Win+Ctrl+Shift+f", partial(daemon.wm.manager.move_to_workspace, 3)),
    ("Win+Ctrl+Shift+j", partial(daemon.wm.manager.move_to_next_workspace)),
    ("Win+Ctrl+Shift+k", partial(daemon.wm.manager.move_to_prev_workspace)),
    ("Win+Shift+Space", daemon.wm.manager.toggle_tilable),
    ("Win+Ctrl+p", daemon.wm.manager.inspect_state),
    ([Vk.WIN, Vk.CONTROL, Vk.O], daemon.wm.manager.inspect_active_window),
    ([Vk.WIN, Vk.CONTROL, Vk.M], daemon.wm.manager.toggle_mono),
    (
        [Vk.WIN, Vk.CONTROL, Vk.ALT, Vk.S],
        partial(daemon.wm.manager.set_theme, "Stack"),
    ),
    (
        [Vk.WIN, Vk.CONTROL, Vk.ALT, Vk.D],
        partial(daemon.wm.manager.set_theme, "Dwindle"),
    ),
    ([Vk.CTRL, Vk.ESCAPE], daemon.wm.manager.show_floating_windows),
]

daemon.wm.manager.config = WmConfig(
    rules=[
        # WmRule(exe="WindowsTerminal.exe", manageable=False),
        WmRule(exe="SnippingTool.exe", manageable=False),
        WmRule(exe="Flow.Launcher.exe", manageable=False),
        WmRule(exe="msedgewebview2.exe", manageable=False),
        WmRule(exe="WeChat.exe", manageable=False),
        WmRule(exe="Weixin.exe", manageable=False),
        WmRule(exe="MediaInfo.exe", tilable=False),
        WmRule(exe="Cloudflare WARP.exe", tilable=False),
        WmRule(exe="7zFM.exe", tilable=False),
        WmRule(exe="fdm.exe", tilable=False),
        WmRule(exe="foobar2000.exe", tilable=False),
        WmRule(exe="notepad++.exe", tilable=False),
        WmRule(exe="PotPlayerMini64.exe", tilable=False),
        WmRule(exe="openvpn-gui.exe", tilable=False),
        # WmRule(
        #     exe="Feishu.exe",
        #     title="(Feishu Meetings|飞书会议)",
        #     title_is_literal=False,
        #     manageable=True,
        #     tilable=False,
        # ),
        WmRule(exe="Feishu.exe", manageable=False),
        WmRule(exe="peazip.exe", tilable=False),
        WmRule(exe="clash-verge.exe", manageable=False),
        WmRule(exe="WXWork.exe", manageable=False),
        WmRule(exe="vmware.exe", tilable=False),
        # WmRule(
        #     exe="ApplicationFrameHost.exe", title="PDF Reader by Xodo", tilable=True
        # ),
        # WmRule(exe="ApplicationFrameHost.exe", tilable=False),
        WmRule(exe="YouTube Music.exe", manageable=False),
    ],
    # themes=["Dwindle", "Stack", "Mono"],
)

daemon.register(
    ProcessService(
        name="syncthing",
        args=[
            r"syncthing.exe",
            "--no-browser",
            "--no-restart",
            "--no-upgrade",
        ],
        log_path=os.path.join(os.getenv("LOCALAPPDATA"), "syncthing.log"),
    )
)

daemon.register(CaffeineService())

daemon.register(
    DailyWebsites(
        browser_name="brave",
        fav_folder="daily",
        test_url="https://google.com",
        proxy_url="http://localhost:7890",
    )
)
daemon.register(
    WorkdayAutoStart(
        country_code="CN",
        apps=[
            # r"C:\Users\Klesh\AppData\Local\Feishu\Feishu.exe",
            r"C:\Program Files\Betterbird\betterbird.exe",
            r"C:\Users\Klesh\AppData\Local\Programs\obsidian\Obsidian.exe",
        ],
    )
)

daemon.start()
