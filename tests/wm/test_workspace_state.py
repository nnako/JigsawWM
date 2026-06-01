"""Tests for wm.workspace_state."""

from jigsawwm.w32.window import Rect
from jigsawwm.wm.theme import static_bigscreen_8
from jigsawwm.wm.workspace_state import WorkspaceState


class FakeMonitor:
    """Minimal monitor stub for workspace tests."""

    def __init__(self, work_rect: Rect):
        self._work_rect = work_rect

    def get_work_rect(self) -> Rect:
        """Return the monitor work area used by the workspace."""
        return self._work_rect


class FakeWindow:
    """Minimal tilable window stub for workspace tests."""

    _next_handle = 1

    def __init__(self, name: str, static_window_index: int):
        self.name = name
        self.attrs = {"static_window_index": static_window_index}
        self.handle = FakeWindow._next_handle
        FakeWindow._next_handle += 1
        self.tilable = True
        self.is_iconic = False
        self.rects = []

    def __hash__(self):
        """Use the fake handle as the stable hash key."""
        return hash(self.handle)

    def __eq__(self, other):
        """Compare fake windows by handle to mimic real windows."""
        return isinstance(other, FakeWindow) and self.handle == other.handle

    def exists(self):
        """Report that the fake window is still available."""
        return True

    def get_rect(self):
        """Return a placeholder rect used by workspace helpers."""
        return Rect(0, 0, 100, 100)

    def set_restricted_rect(self, rect, _work_rect, _insert_after=None):
        """Capture the assigned tile rect for later assertions."""
        self.rects.append(rect)


def test_static_layout_preserves_sparse_static_slots(monkeypatch):
    """Windows keep their configured static slot even when earlier slots are empty."""
    monkeypatch.setattr(
        "jigsawwm.wm.workspace_state.get_foreground_window",
        lambda: None,
    )
    workspace = WorkspaceState(
        monitor_index=0,
        index=0,
        name="0",
        monitor=FakeMonitor(Rect(0, 0, 1000, 1000)),
        alter_rect=Rect(0, 1200, 1000, 2200),
        theme=static_bigscreen_8,
    )
    slot_0 = FakeWindow("slot-0", 0)
    slot_2 = FakeWindow("slot-2", 2)
    slot_5 = FakeWindow("slot-5", 5)

    workspace.windows.update({slot_0, slot_2, slot_5})

    workspace.sync_windows(force_arrange=True)

    assert workspace.tiling_windows == [
        slot_0,
        None,
        slot_2,
        None,
        None,
        slot_5,
        None,
        None,
    ]
    assert len(workspace.tiling_areas) == static_bigscreen_8.max_tiling_areas
    assert slot_0.rects == [workspace.tiling_areas[0]]
    assert slot_2.rects == [workspace.tiling_areas[2]]
    assert slot_5.rects == [workspace.tiling_areas[5]]


def test_duplicate_static_index_is_treated_as_overflow():
    """Duplicate static indices should not crash static sorting."""
    workspace = WorkspaceState(
        monitor_index=0,
        index=0,
        name="0",
        monitor=FakeMonitor(Rect(0, 0, 1000, 1000)),
        alter_rect=Rect(0, 1200, 1000, 2200),
        theme=static_bigscreen_8,
    )
    first = FakeWindow("first", 1)
    duplicate = FakeWindow("duplicate", 1)

    ordered = workspace.sort_by_static_index([first, duplicate])

    assert ordered[1] is first
    assert ordered[-1] is duplicate
