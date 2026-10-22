"""Reference-space tokens for the approved StudioForge Auto-Key skin.

Coordinates are presentation data measured from the 1408x1000 physical
chassis crop. Runtime values never live in this module.
"""
from __future__ import annotations

from dataclasses import dataclass


REFERENCE_WIDTH = 1408
REFERENCE_HEIGHT = 1000


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height


HEADER = Rect(36, 22, 1336, 70)
EQ_SECTION = Rect(25, 115, 870, 610)
EQ_GRAPH = Rect(75, 185, 770, 460)
EQ_CONTROL_POCKET = Rect(595, 130, 265, 44)
# The detector glass keeps an even 6 px retaining bezel.  Its outer routed
# aperture stops 10 px before OUTPUT so both instruments remain visibly
# separate pieces of fitted hardware.
KEY_DISPLAY = Rect(935, 135, 300, 255)
OUTPUT_MODULE = Rect(1255, 135, 110, 255)
OUTPUT_METER = Rect(1272, 184, 76, 164)
TONE_SHIFT = Rect(920, 404, 445, 116)
MODE_RAIL = Rect(920, 535, 445, 180)
MAPPING = Rect(642, 800, 124, 145)
CHASSIS_SCREWS = (
    (22, 26, .18), (1386, 26, .72),
    (22, 978, 1.30), (1386, 978, .68),
)

# Two symmetric three-control banks frame the central analyzer.  Keeping the
# coordinates explicit makes rendering, hit testing and visual tests share one
# source of truth.
MACRO_CENTERS = ((105, 864), (285, 864), (465, 864),
                 (943, 864), (1123, 864), (1303, 864))
MACRO_DIAMETER = 108
MACRO_GROOVES = (195, 375, 554, 854, 1033, 1213)

COLORS = {
    "warm_white": "#f2f4ef",
    "text_muted": "#92a7a8",
    "amber": "#18c8c1",
    "amber_bright": "#62f1e7",
    "amber_dim": "#155e61",
    "mint": "#c8fffb",
    "green": "#65d7a2",
    "red": "#ff795d",
    "graphite": "#102126",
    "glass": "#06171c",
    "divider": "#789194",
}


def system_font(point_size: int, weight=None):
    """Return a crisp platform font without depending on proprietary files."""
    from PyQt6.QtGui import QFont

    font = QFont("SF Pro Display", point_size)
    if weight is not None:
        font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font
