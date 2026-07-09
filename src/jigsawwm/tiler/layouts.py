"""

The ``layout`` module operates in Relative Coordinate, to that end, it defines 2 basic types:

``FloatRect`` is a tuple with 4 elements (left/top/right/bottom) to describe a rectangle in ratio form (0.0~1.0)

``Layout`` is a generator which generates FloatRects for given total number of windows

"""

from functools import partial
from typing import Callable, Iterator, Tuple, Union

# FloatRect holds relative coordinate for rectangle (left/top/right/bottom)
FloatRect = Tuple[float, float, float, float]

# Layout accepts an integer (total number of windows) and return a FloatRect generator
Layout = Callable[[int], Iterator[FloatRect]]


def mono(n: int) -> Iterator[FloatRect]:
    """The mono Layout

    .. code-block:: text

        +-----------+
        |           |
        |           |
        |           |
        |     1     |
        |           |
        |           |
        |           |
        +-----------+

    :param n: total number of windows
    :rtype: Iterator[FloatRect]
    """
    for i in range(n):
        yield 0.0, 0.0, 1.0, 1.0


def stack(n: int, master_ratio: float = 0.9) -> Iterator[FloatRect]:
    """The stack Layout

    .. code-block:: text

        +-----------+
        |2 +--------+--+
        |  |1          |
        |  |           |
        |  |           |
        |  |           |
        |  |           |
        |  |           |
        +--+           |
           +-----------+

    :param n: total number of windows
    :rtype: Iterator[FloatRect]
    """
    if n == 1:
        yield 0.05, 0.05, 0.95, 0.95
        return
    left, top, right, bottom = 1.0 - master_ratio, 1.0 - master_ratio, 1.0, 1.0
    step = (1 - master_ratio) / (n - 1) if n > 1 else 0
    for _ in range(n):
        yield left, top, right, bottom
        left -= step
        top -= step
        right -= step
        bottom -= step


def dwindle(n: int, master_ratio: float = 0.5) -> Iterator[FloatRect]:
    """The dwindle Layout

    .. code-block:: text

        +-----------+-----------+
        |           |           |
        |           |     2     |
        |           |           |
        |     1     +-----+-----+
        |           |     |  4  |
        |           |  3  +--+--+
        |           |     | 5|-.|
        +-----------+-----+-----+

    :param n: total number of windows
    :rtype: Iterator[FloatRect]
    """
    ratio = 1 - master_ratio
    l, t, r, b = 0.0, 0.0, 1.0, 1.0
    last_index = n - 1
    for i in range(n):
        # last window would occupy the whole area
        if i == last_index:
            yield l, t, r, b
        # or it should leave out half space for the other windows
        elif i % 2 == 0:
            nl = r - (r - l) * ratio
            yield l, t, nl, b
            l = nl
        else:
            nb = b - (b - t) * ratio
            yield l, t, r, nb
            t = nb


def static_bigscreen_8(n: int) -> Iterator[FloatRect]:
    """layout for a big screen (like a television) of 55 inches or more. here,
    the 'eye line' should define the upper (main) horizontal segregation. due
    to an attempt keep the eyes below it for main actions on the screen. the
    screen will be optimal for 8 application windows. if fewer windows were
    activated, the respective areas stay empty.

    .. code-block:: text

---------    +----------+----------+----------+----------+
 |  |  |     |          |          |          |          |
 |  |  |     |          |          |          |          |
 |  | <y1>   |     5    |     6    |     7    |          |
 |  |  |     |          |          |          |          |
 |  |  v     |          |          |          |          |
 |  | ---    +----------+--------+-+----------+          |
 |  |        |          |        |            |          |
 |  |        |          |        |            |          |
 |  |        |          |        |            |          |
 |  |        |          |        |            |     3    |
 |  |        |          |        |            |          |
 | <y2>      |     4    |    2   |      0     |          |
 |  |        |          |        |            |          |
 |  v        |          |        |            |          |
 | ---       |          +--------+------------|          |
 |           |          |                     |          |
 v           |          |          1          |          |
--- 100%     +----------+---------------------+----------+

             |-- <x1> ->|
             |-- <x2> ---------->|

    :param n: total number of currently active windows
    :rtype: Iterator[FloatRect]
    """


    #
    # set location parameters for window placement
    #

    # fix parameters to localize windows. the parameters are chosen to optimize
    # various aspects:
    #
    # - ability to create a shared screen area containing only of windows 0 and 2
    # - realizing communication-related windows on the left side of the screen
    # - realizing structure-related windows on the right side of the screen
    # - realizing planning-related windows on the top of the screen
    # - realizing windows for further info details on the bottom of the screen

    y_min, x_min, y_max, x_max = 0.0, 0.0, 1.0, 1.0
    y1 = 0.37 * 0.975
    y2 = 0.86 * 0.975
    x1 = 0.25
    x2 = 0.45


    #
    # evaluate influence of task bar activity
    #

    # in order to keep window 0 and window 2 at exactly the same locations on
    # the screen, regardless of the current task bar configuration, the y
    # coordinates might be adjustes to alleviate usable screen size changes.
    # the taskbar will reduce the maximum available vertical screen area by a
    # certain value. in future releases, this value should be given by the user
    # when choosing this layout. currently, it can only be changed within the
    # code.

    # _factor__remaining_screen_height = 0.975      # task bar active
    _factor__remaining_screen_height = 1          # task bar inactive
    y1 = y1 / _factor__remaining_screen_height
    y2 = y2 / _factor__remaining_screen_height


    #
    # set coordinates of windows on the screen
    #

    # number of windows as parameter
    if n == 1:
        yield 0.25, 0.37, 0.75, 1.00
    if n == 2:
        yield 0.25, 0.37, 0.75, 0.80
        yield 0.25, 0.80, 0.75, 1.00
    if n == 3:
        yield 0.45, 0.37, 0.75, 0.80
        yield 0.30, 0.80, 0.75, 1.00
        yield 0.30, 0.37, 0.45, 0.80
    if n == 4:
        yield 0.45, 0.37, 0.75, 0.80
        yield 0.30, 0.80, 0.75, 1.00
        yield 0.30, 0.37, 0.45, 0.80
        yield 0.75, 0.00, 1.00, 1.00
    if n == 5:
        yield 0.45, 0.37, 0.75, 0.80
        yield 0.30, 0.80, 0.75, 1.00
        yield 0.30, 0.37, 0.45, 0.80
        yield 0.75, 0.00, 1.00, 1.00
        yield 0.00, 0.37, 0.30, 1.00
    if n == 6:
        yield 0.45, 0.37, 0.75, 0.80
        yield 0.30, 0.80, 0.75, 1.00
        yield 0.30, 0.37, 0.45, 0.80
        yield 0.75, 0.00, 1.00, 1.00
        yield 0.00, 0.37, 0.30, 1.00
        yield 0.00, 0.00, 0.25, 0.37
    if n == 7:
        yield 0.45, 0.37, 0.75, 0.80
        yield 0.30, 0.80, 0.75, 1.00
        yield 0.30, 0.37, 0.45, 0.80
        yield 0.75, 0.00, 1.00, 1.00
        yield 0.00, 0.37, 0.30, 1.00
        yield 0.00, 0.00, 0.25, 0.37
        yield 0.25, 0.00, 0.50, 0.37
    if n == 8:
        yield    x2,    y1,  3*x1,    y2    # 0
        yield    x1,    y2,  3*x1, y_max    # 1
        yield    x1,    y1,    x2,    y2    # 2
        yield  3*x1, y_min, x_max, y_max    # 3
        yield x_min,    y1,    x1, y_max    # 4
        yield x_min, y_min,    x1,    y1    # 5
        yield    x1, y_min,  2*x1,    y1    # 6
        yield  2*x1, y_min,  3*x1,    y1    # 7


def widescreen_dwindle(n: int, master_ratio: float = 0.4) -> Iterator[FloatRect]:
    """A wide-screen friendly dwindle Layout

    .. code-block:: text

        +-----------+-----------+-----------+
        |           |           |           |
        |           |           |     3     |
        |           |           |           |
        |     1     |     2     +-----+-----+
        |           |           |     |  5  |
        |           |           |  4  +--+--+
        |           |           |     | 6|-.|
        +-----------+-----------+-----+-----+

    :param n: total number of windows
    :rtype: Iterator[FloatRect]
    """
    if n == 0:
        return
    #    wide_dwindle
    if n == 1:
        yield 0.0, 0.0, 1.0, 1.0
        return
    # master window on the left
    yield 0.0, 0.0, master_ratio, 1
    # other windows on the right with dwindle layout, just map the coordinate and we are good
    yield from map(
        partial(plug_rect, target=(master_ratio, 0.0, 1.0, 1.0)), dwindle(n - 1)
    )


Number = Union[int, float]
NumberRect = Tuple[Number, Number, Number, Number]


def plug_rect(source: FloatRect, target: NumberRect) -> NumberRect:
    """Plug the source rect into the target rect and compute the new dimensions,
    you may plug a Relative Rect into a Physical Rect, but not the other way around.

    :param source: the FloatRect to be moved
    :param target: the container, either a FloatRect or Rect(physical pixels)
    :returns: Rect or FloatRect depends on the type of the target
    :rtype: NumberRect
    """

    sl, st, sr, sb = source
    tl, tt, tr, tb = target
    tw = tr - tl
    th = tb - tt
    return (
        tl + sl * tw,  # left = target left + scaled source left
        tt + st * th,  # top = target top + scaled source top
        tl + sr * tw,  # right
        tt + sb * th,  # bottom
    )


if __name__ == "__main__":
    print("dwindle")
    for i in range(1, 5):
        print(list(stack(i)))
    # print("dwindle")
    # for i in range(1, 5):
    #     print(list(dwindle(i)))
    # print()
    # print("widescreen_dwindle")
    # for i in range(1, 5):
    #     print(list(widescreen_dwindle(i)))
