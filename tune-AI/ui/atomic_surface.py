"""Auto-Key surface assembled from the supplied clean atomic kit layers.

This widget owns presentation only. Commands and data come from MainWindow;
it does not capture audio or discover plug-ins itself.
"""
from math import cos, exp, log, pi, sin
from time import monotonic

from PyQt6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QRectF,
                          QSequentialAnimationGroup, Qt, QTimer, pyqtProperty,
                          pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QFont,
                         QLinearGradient, QPainter, QPainterPath, QPen,
                         QPixmap, QRadialGradient)
from PyQt6.QtWidgets import QLabel, QMenu, QPushButton, QSlider, QWidget

from core.constants import ASSETS_DIR
from ui.autokey_visual_tokens import (CHASSIS_SCREWS as _CHASSIS_SCREWS,
                                      COLORS, EQ_GRAPH, KEY_DISPLAY,
                                      MACRO_CENTERS, MACRO_DIAMETER, MAPPING,
                                      OUTPUT_METER, OUTPUT_MODULE,
                                      REFERENCE_HEIGHT, REFERENCE_WIDTH,
                                      system_font)
from ui.macro_surface_state import macro_at, macro_value_text

_ASSETS = ASSETS_DIR / "autokey_atomic"


def _draw_panel_ink(painter, rect, flags, text, colour):
    """Print text as a thin cured-ink layer bonded to the panel material."""
    painter.save()
    painter.setPen(QColor(0, 0, 0, 125))
    painter.drawText(QRectF(rect).translated(.45, .65), flags, str(text))
    painter.setPen(QColor(255, 249, 235, 24))
    painter.drawText(QRectF(rect).translated(-.18, -.22), flags, str(text))
    painter.setPen(QColor(colour))
    painter.drawText(QRectF(rect), flags, str(text))
    painter.restore()


def _paint_hardware_screw(painter, center, diameter, rotation=0.0):
    """Draw a crisp countersunk hex screw at reference resolution."""
    cx, cy = center
    radius = diameter / 2.0
    body = QRectF(cx - radius, cy - radius, diameter, diameter)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 170))
    painter.drawEllipse(body.translated(1.2, 1.8))

    rim = QConicalGradient(QPointF(cx, cy), rotation - 32)
    rim.setColorAt(0.00, QColor("#161717"))
    rim.setColorAt(0.12, QColor("#b8ad99"))
    rim.setColorAt(0.27, QColor("#3b3a37"))
    rim.setColorAt(0.45, QColor("#d5c9b5"))
    rim.setColorAt(0.61, QColor("#252624"))
    rim.setColorAt(0.82, QColor("#817869"))
    rim.setColorAt(1.00, QColor("#161717"))
    painter.setBrush(rim)
    painter.setPen(QPen(QColor("#060707"), 1.0))
    painter.drawEllipse(body)

    crown = body.adjusted(diameter * .13, diameter * .13,
                          -diameter * .13, -diameter * .13)
    face = QRadialGradient(crown.center().x() - diameter * .15,
                           crown.center().y() - diameter * .18,
                           diameter * .58)
    face.setColorAt(0.0, QColor("#77736b"))
    face.setColorAt(.32, QColor("#333431"))
    face.setColorAt(.72, QColor("#111212"))
    face.setColorAt(1.0, QColor("#050606"))
    painter.setBrush(face)
    painter.setPen(QPen(QColor(225, 214, 195, 65), .8))
    painter.drawEllipse(crown)

    # Recessed six-sided drive with a small inner highlight along one edge.
    socket = QPainterPath()
    socket_radius = diameter * .19
    for index in range(6):
        angle = rotation + pi / 6 + index * pi / 3
        point = QPointF(cx + cos(angle) * socket_radius,
                        cy + sin(angle) * socket_radius)
        socket.moveTo(point) if index == 0 else socket.lineTo(point)
    socket.closeSubpath()
    painter.setBrush(QColor("#050606"))
    painter.setPen(QPen(QColor(205, 194, 176, 95), .8))
    painter.drawPath(socket)
    painter.setPen(QPen(QColor(255, 248, 231, 85), .75,
                        Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    a = rotation + pi * .78
    painter.drawLine(QPointF(cx + cos(a) * diameter * .23,
                             cy + sin(a) * diameter * .23),
                     QPointF(cx + cos(a) * diameter * .34,
                             cy + sin(a) * diameter * .34))


class TactileButton(QPushButton):
    """Short-travel switch motion shared by every live hardware control."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._press_depth = 0.0
        self._press_animation = QPropertyAnimation(self, b"pressDepth", self)
        self._release_animation = QSequentialAnimationGroup(self)
        self.pressed.connect(self._compress)
        self.released.connect(self._rebound)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _animate_depth(self, end, duration, easing):
        self._release_animation.stop()
        self._press_animation.stop()
        self._press_animation.setDuration(duration)
        self._press_animation.setEasingCurve(easing)
        self._press_animation.setStartValue(self._press_depth)
        self._press_animation.setEndValue(end)
        self._press_animation.start()

    def _compress(self):
        self._animate_depth(1.55, 58, QEasingCurve.Type.OutCubic)

    def _rebound(self):
        self._press_animation.stop()
        self._release_animation.stop()
        self._release_animation.clear()
        lift = QPropertyAnimation(self, b"pressDepth", self._release_animation)
        lift.setDuration(76)
        lift.setEasingCurve(QEasingCurve.Type.OutCubic)
        lift.setStartValue(self._press_depth)
        lift.setEndValue(-.18)
        settle = QPropertyAnimation(self, b"pressDepth", self._release_animation)
        settle.setDuration(54)
        settle.setEasingCurve(QEasingCurve.Type.InOutQuad)
        settle.setStartValue(-.18)
        settle.setEndValue(0.0)
        self._release_animation.addAnimation(lift)
        self._release_animation.addAnimation(settle)
        self._release_animation.start()

    def _get_press_depth(self):
        return self._press_depth

    def _set_press_depth(self, value):
        self._press_depth = max(-.22, min(1.65, float(value)))
        self.update()

    pressDepth = pyqtProperty(float, fget=_get_press_depth, fset=_set_press_depth)


class HardwareButton(TactileButton):
    """Resolution-independent anodised hardware switch.

    The visual is assembled from independent material layers so labels and
    runtime state remain live.  This avoids scaling a photographed button or
    baking a selected state into an asset.
    """

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAccessibleName(text)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(0, self._press_depth)
        # Height controls the physical scale; narrow SAVE/INIT switches should
        # not inherit an unreadably small label merely because they are short.
        scale = max(.72, self.height() / 46.0)
        selected = bool(self.property("selected"))
        pressed = self.isDown()
        hover = self.underMouse()
        box = QRectF(2.5 * scale, 2.5 * scale,
                     self.width() - 5 * scale, self.height() - 5 * scale)

        # Soft contact shadow makes the switch read as a separate physical part.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.drawRoundedRect(box.translated(0, 2.2 * scale), 7 * scale, 7 * scale)

        rim = QLinearGradient(box.left(), box.top(), box.left(), box.bottom())
        rim.setColorAt(0.0, QColor("#8a8580" if selected else ("#737a7c" if hover else "#5b6264")))
        rim.setColorAt(.16, QColor("#2e2d2b"))
        rim.setColorAt(.78, QColor("#060707"))
        rim.setColorAt(1.0, QColor("#8a8176" if selected else "#454b4d"))
        painter.setBrush(rim)
        painter.setPen(QPen(QColor("#080909"), max(1.0, scale)))
        painter.drawRoundedRect(box, 7 * scale, 7 * scale)

        face = box.adjusted(2.2 * scale, 2.2 * scale,
                            -2.2 * scale, -3.1 * scale)
        material = QLinearGradient(face.left(), face.top(), face.left(), face.bottom())
        if selected or pressed:
            material.setColorAt(0.0, QColor("#176a6c"))
            material.setColorAt(.22, QColor("#0c4248"))
            material.setColorAt(.58, QColor("#071f25"))
            material.setColorAt(1.0, QColor("#041013"))
        else:
            material.setColorAt(0.0, QColor("#353534" if hover else "#292928"))
            material.setColorAt(.18, QColor("#1b1c1c"))
            material.setColorAt(.62, QColor("#0c0d0d"))
            material.setColorAt(1.0, QColor("#050606"))
        painter.setBrush(material)
        painter.setPen(QPen(QColor("#090909"), max(1.0, scale)))
        painter.drawRoundedRect(face, 5.5 * scale, 5.5 * scale)

        # Narrow reflection strip; restrained enough to remain premium.
        sheen = QLinearGradient(face.left(), face.top(), face.right(), face.top())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(.32, QColor(255, 248, 230, 34 if hover else 20))
        sheen.setColorAt(.58, QColor(255, 255, 255, 5))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(sheen)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(face.left() + 2 * scale,
                                       face.top() + 1.2 * scale,
                                       face.width() - 4 * scale,
                                       max(1.2, 2.0 * scale)),
                                2 * scale, 2 * scale)
        if selected:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COLORS["amber_bright"]), max(1.0, 1.2 * scale)))
            painter.drawRoundedRect(face.adjusted(.5, .5, -.5, -.5),
                                    5.5 * scale, 5.5 * scale)

        painter.setFont(system_font(max(7, round(11 * scale)), QFont.Weight.DemiBold))
        _draw_panel_ink(painter, face.translated(0, -.4 * scale), Qt.AlignmentFlag.AlignCenter,
                        self.text(), QColor("#fff0f2" if selected else "#e1e5e5"))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COLORS["amber_bright"]), max(1.0, scale)))
            painter.drawRoundedRect(box.adjusted(-1, -1, 1, 1), 8 * scale, 8 * scale)


class UtilityIconButton(TactileButton):
    """Compact hardware icon for secondary workflows on the command rail."""

    def __init__(self, kind, tooltip, parent=None, checkable=False):
        super().__init__(parent)
        self.kind = str(kind)
        self.setAccessibleName(tooltip)
        self.setToolTip(tooltip)
        self.setCheckable(checkable)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(0, self._press_depth)
        side = min(self.width(), self.height())
        box = QRectF((self.width() - side) / 2 + 2, (self.height() - side) / 2 + 2,
                     side - 4, side - 4)
        active = self.isChecked()
        hover = self.underMouse()

        rim = QLinearGradient(box.left(), box.top(), box.left(), box.bottom())
        rim.setColorAt(0.0, QColor("#778286" if hover or active else "#4a5356"))
        rim.setColorAt(.30, QColor("#1a2022"))
        rim.setColorAt(1.0, QColor("#050707"))
        painter.setBrush(rim)
        painter.setPen(QPen(QColor("#070808"), 1.0))
        painter.drawRoundedRect(box, 7, 7)

        face = box.adjusted(2, 2, -2, -3)
        painter.setBrush(QColor("#0b3034" if active else ("#202728" if hover else "#111516")))
        painter.setPen(QPen(QColor(COLORS["amber_bright"] if active else "#30383a"),
                            1.1 if active else .8))
        painter.drawRoundedRect(face, 5, 5)

        colour = QColor(COLORS["amber_bright"] if active else "#d7dcda")
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(colour, max(1.4, side * .045),
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        cx, cy = face.center().x(), face.center().y()
        unit = side / 40.0
        if self.kind == "karaoke":
            painter.drawRoundedRect(QRectF(cx - 9 * unit, cy - 7 * unit,
                                           18 * unit, 14 * unit), 2 * unit, 2 * unit)
            play = QPainterPath()
            play.moveTo(cx - 2 * unit, cy - 4 * unit)
            play.lineTo(cx + 5 * unit, cy)
            play.lineTo(cx - 2 * unit, cy + 4 * unit)
            play.closeSubpath()
            painter.setBrush(colour)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(play)
        elif self.kind == "library":
            for offset in (-6, 0, 6):
                painter.setBrush(colour)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx - 8 * unit, cy + offset * unit), 1.4 * unit, 1.4 * unit)
                painter.setPen(QPen(colour, 1.6 * unit, Qt.PenStyle.SolidLine,
                                    Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(cx - 3 * unit, cy + offset * unit),
                                 QPointF(cx + 8 * unit, cy + offset * unit))
        elif self.kind == "contact":
            painter.drawEllipse(QRectF(cx - 3.5 * unit, cy - 8 * unit,
                                       7 * unit, 7 * unit))
            painter.drawArc(QRectF(cx - 9 * unit, cy - 1 * unit,
                                   18 * unit, 13 * unit), 18 * 16, 144 * 16)
        elif self.kind == "settings":
            painter.drawEllipse(QRectF(cx - 4 * unit, cy - 4 * unit,
                                       8 * unit, 8 * unit))
            for index in range(8):
                angle = index * pi / 4
                painter.drawLine(QPointF(cx + cos(angle) * 7 * unit,
                                         cy + sin(angle) * 7 * unit),
                                 QPointF(cx + cos(angle) * 10 * unit,
                                         cy + sin(angle) * 10 * unit))
        elif self.kind == "mic":
            painter.drawRoundedRect(QRectF(cx - 4 * unit, cy - 9 * unit,
                                           8 * unit, 13 * unit), 4 * unit, 4 * unit)
            painter.drawArc(QRectF(cx - 8 * unit, cy - 5 * unit,
                                   16 * unit, 15 * unit), 180 * 16, 180 * 16)
            painter.drawLine(QPointF(cx, cy + 10 * unit), QPointF(cx, cy + 14 * unit))
            painter.drawLine(QPointF(cx - 5 * unit, cy + 14 * unit),
                             QPointF(cx + 5 * unit, cy + 14 * unit))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COLORS["amber_bright"]), 1.2))
            painter.drawRoundedRect(box.adjusted(-1, -1, 1, 1), 8, 8)


class PowerButton(TactileButton):
    """Native, scalable illuminated power control matching the target shell."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName("Power")
        self.setToolTip("Thoát StudioForge Auto-Key")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(0, self._press_depth)
        ui_scale = max(.5, self.height() / 61.0)
        diameter = self.height() - 13 * ui_scale
        circle = QRectF(self.width() - diameter - 6, (self.height() - diameter) / 2,
                        diameter, diameter)
        painter.setPen(QColor("#e8dfcf"))
        painter.setFont(system_font(max(7, round(10 * ui_scale)), QFont.Weight.DemiBold))
        painter.drawText(QRectF(0, 0, self.width() - diameter - 13, self.height()),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "POWER")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawEllipse(circle.translated(0, 1.5 * ui_scale))
        outer = QConicalGradient(circle.center(), -28)
        outer.setColorAt(0.00, QColor("#211b14"))
        outer.setColorAt(.12, QColor("#d4b078"))
        outer.setColorAt(.28, QColor("#5c4b38"))
        outer.setColorAt(.46, QColor("#f0d39e"))
        outer.setColorAt(.63, QColor("#3b3024"))
        outer.setColorAt(.82, QColor("#a9783d"))
        outer.setColorAt(1.0, QColor("#211b14"))
        painter.setBrush(outer)
        painter.setPen(QPen(QColor("#080808"), 1.0 * ui_scale))
        painter.drawEllipse(circle)
        bezel = circle.adjusted(diameter * .105, diameter * .105,
                                -diameter * .105, -diameter * .105)
        painter.setBrush(QColor("#151413"))
        painter.setPen(QPen(QColor("#5b4b36"), 1.0 * ui_scale))
        painter.drawEllipse(bezel)
        inner = circle.adjusted(diameter * .23, diameter * .23,
                                -diameter * .23, -diameter * .23)
        switch = QRadialGradient(inner.center().x() - inner.width() * .18,
                                 inner.center().y() - inner.height() * .22,
                                 inner.width() * .72)
        switch.setColorAt(0.0, QColor("#403522" if not self.isDown() else "#392711"))
        switch.setColorAt(.42, QColor("#171614"))
        switch.setColorAt(1.0, QColor("#050606"))
        painter.setBrush(switch)
        painter.setPen(QPen(QColor("#c58b42"), 1.15 * ui_scale))
        painter.drawEllipse(inner)

        # Illuminated power glyph, not a generic flat orange dot.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        glyph = inner.adjusted(inner.width() * .19, inner.height() * .19,
                               -inner.width() * .19, -inner.height() * .19)
        glow = QColor(255, 176, 69, 52 if not self.isDown() else 86)
        painter.setPen(QPen(glow, 2.6 * ui_scale, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawArc(glyph, 42 * 16, 276 * 16)
        painter.drawLine(QPointF(glyph.center().x(), glyph.top() - 1.0 * ui_scale),
                         QPointF(glyph.center().x(), glyph.center().y() + 1.5 * ui_scale))
        painter.setPen(QPen(QColor("#ffc568"), 1.35 * ui_scale,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(glyph, 42 * 16, 276 * 16)
        painter.drawLine(QPointF(glyph.center().x(), glyph.top() - 1.0 * ui_scale),
                         QPointF(glyph.center().x(), glyph.center().y() + 1.5 * ui_scale))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COLORS["amber_bright"]), 2))
            painter.drawEllipse(circle.adjusted(-2, -2, 2, 2))


class MappingButton(TactileButton):
    """Dedicated physical launcher; the link glyph is drawn, not baked."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName("Macro Mapping")
        self.setToolTip("Mở danh sách gán cho sáu macro")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(0, self._press_depth)
        ui_scale = max(.5, self.height() / 129.0)
        box = QRectF(5 * ui_scale, 5 * ui_scale,
                     self.width() - 10 * ui_scale, self.height() - 10 * ui_scale)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 165))
        painter.drawRoundedRect(box.translated(0, 3 * ui_scale), 9, 9)
        rim = QLinearGradient(box.left(), box.top(), box.right(), box.bottom())
        rim.setColorAt(0.0, QColor("#a7adae"))
        rim.setColorAt(.18, QColor("#383531"))
        rim.setColorAt(.58, QColor("#111212"))
        rim.setColorAt(1.0, QColor("#737b7d"))
        painter.setBrush(rim)
        painter.setPen(QPen(QColor("#080909"), 1.2 * ui_scale))
        painter.drawRoundedRect(box, 9, 9)
        face = box.adjusted(3 * ui_scale, 3 * ui_scale,
                            -3 * ui_scale, -4 * ui_scale)
        gradient = QLinearGradient(0, box.top(), 0, box.bottom())
        gradient.setColorAt(0, QColor("#282624" if not self.isDown() else "#3a2b19"))
        gradient.setColorAt(.22, QColor("#111212"))
        gradient.setColorAt(1, QColor("#080909"))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#272522"), 1.1))
        painter.drawRoundedRect(face, 6, 6)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 244, 220, 45), max(1.0, ui_scale)))
        painter.drawLine(int(face.left() + 7 * ui_scale), int(face.top() + 2 * ui_scale),
                         int(face.right() - 7 * ui_scale), int(face.top() + 2 * ui_scale))
        if self.width() > self.height() * 2.5:
            # Wide hardware-strip variant used by the new macro matrix.
            cy = face.center().y()
            icon_x = face.left() + 34 * ui_scale
            painter.setPen(QPen(QColor(COLORS["amber_bright"]), 2.7 * ui_scale,
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(QRectF(icon_x - 12 * ui_scale, cy - 8 * ui_scale,
                                   17 * ui_scale, 15 * ui_scale), 40 * 16, 220 * 16)
            painter.drawArc(QRectF(icon_x - 2 * ui_scale, cy - 13 * ui_scale,
                                   17 * ui_scale, 15 * ui_scale), 220 * 16, 220 * 16)
            painter.setPen(QColor("#e5e8e8"))
            painter.setFont(system_font(max(8, round(11 * ui_scale)), QFont.Weight.DemiBold))
            painter.drawText(QRectF(face.left() + 66 * ui_scale, face.top(),
                                    face.width() - 112 * ui_scale, face.height()),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             "MACRO MAPPING")
            painter.setPen(QPen(QColor(COLORS["amber"]), 3 * ui_scale))
            painter.drawLine(int(face.right() - 30 * ui_scale), int(cy),
                             int(face.right() - 12 * ui_scale), int(cy))
            if self.hasFocus():
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(COLORS["amber_bright"]), 2))
                painter.drawRoundedRect(box.adjusted(1, 1, -1, -1), 8, 8)
            return
        painter.setPen(QPen(QColor(COLORS["amber_bright"]), 3 * ui_scale,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cx = box.center().x()
        painter.drawArc(QRectF(cx - 17 * ui_scale, box.top() + 24 * ui_scale,
                               22 * ui_scale, 20 * ui_scale), 40 * 16, 220 * 16)
        painter.drawArc(QRectF(cx - 5 * ui_scale, box.top() + 17 * ui_scale,
                               22 * ui_scale, 20 * ui_scale), 220 * 16, 220 * 16)
        painter.setPen(QColor("#e5e8e8"))
        painter.setFont(system_font(max(7, round(10 * ui_scale)), QFont.Weight.Medium))
        painter.drawText(QRectF(box.left(), box.top() + 49 * ui_scale,
                                box.width(), 47 * ui_scale),
                         Qt.AlignmentFlag.AlignCenter, "MACRO\nMAPPING")
        painter.setPen(QPen(QColor(COLORS["amber"]), 3 * ui_scale))
        painter.drawLine(int(cx - 12 * ui_scale), int(box.bottom() - 13 * ui_scale),
                         int(cx + 12 * ui_scale), int(box.bottom() - 13 * ui_scale))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COLORS["amber_bright"]), 2))
            painter.drawRoundedRect(box.adjusted(1, 1, -1, -1), 8, 8)


class ToneStepButton(TactileButton):
    """Round metal step control without the rectangular raster underlay."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAccessibleName("Giảm Tone Shift" if text == "−" else "Tăng Tone Shift")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(0, self._press_depth)
        side = min(self.width(), self.height())
        pad = side * .075
        outer = QRectF((self.width() - side) / 2 + pad, (self.height() - side) / 2 + pad,
                       side - 2 * pad, side - 2 * pad)
        painter.setPen(QPen(QColor("#8e867b"), max(1.0, side * .018)))
        ring = QLinearGradient(outer.left(), outer.top(), outer.right(), outer.bottom())
        ring.setColorAt(0, QColor("#d5dbdc"))
        ring.setColorAt(.25, QColor("#62696b"))
        ring.setColorAt(.62, QColor("#181b1c"))
        ring.setColorAt(1, QColor("#959ea0"))
        painter.setBrush(ring)
        painter.drawEllipse(outer)
        # Fine radial machining around the aluminium collar.
        cx, cy = outer.center().x(), outer.center().y()
        painter.setPen(QPen(QColor(238, 224, 198, 55), max(.55, side * .006)))
        for index in range(48):
            angle = index * 2 * pi / 48
            painter.drawLine(round(cx + cos(angle) * outer.width() * .405),
                             round(cy + sin(angle) * outer.height() * .405),
                             round(cx + cos(angle) * outer.width() * .455),
                             round(cy + sin(angle) * outer.height() * .455))
        face = outer.adjusted(side * .09, side * .09, -side * .09, -side * .09)
        face_gradient = QLinearGradient(face.left(), face.top(), face.left(), face.bottom())
        face_gradient.setColorAt(0, QColor("#292a2a" if not self.isDown() else "#3b2d20"))
        face_gradient.setColorAt(.48, QColor("#111212"))
        face_gradient.setColorAt(1, QColor("#050606"))
        painter.setBrush(face_gradient)
        painter.setPen(QPen(QColor("#050505"), max(1.0, side * .025)))
        painter.drawEllipse(face)
        highlight = QRadialGradient(face.center().x() - face.width() * .18,
                                    face.center().y() - face.height() * .24,
                                    face.width() * .62)
        highlight.setColorAt(0.0, QColor(255, 250, 235, 44))
        highlight.setColorAt(.38, QColor(255, 255, 255, 8))
        highlight.setColorAt(1.0, QColor(0, 0, 0, 55))
        painter.setBrush(highlight)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(face.adjusted(side * .025, side * .025,
                                           -side * .025, -side * .025))
        painter.setPen(QColor(COLORS["warm_white"]))
        painter.setFont(system_font(max(9, round(side * .16)), QFont.Weight.DemiBold))
        painter.drawText(face, Qt.AlignmentFlag.AlignCenter, self.text())
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COLORS["amber_bright"]), 2))
            painter.drawEllipse(outer.adjusted(-2, -2, 2, 2))


class AtomicKnob(QSlider):
    def __init__(self, index, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.index = index
        # Three related cap constructions keep the programmable bank visually
        # legible like real console hardware without changing interaction or
        # implying a fixed parameter type.
        self._cap_variant = index % 3
        self.setRange(0, 1000)
        self.setSingleStep(5)
        self.setPageStep(50)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setAccessibleName(f"Macro {index + 1}")
        self.setToolTip("Chưa gán — chọn Mapping để gán parameter")
        self._assets = [QPixmap(str(_ASSETS / n)) for n in
                        ("bezel@2x.png", "ticks_unlit@2x.png", "face_blank_NO_VALUE@2x.png")]
        self._text = "—"
        self._status = "unassigned"
        self._drag_y = None
        self._drag_value = 0.0
        self._grabbed = False
        self.setEnabled(False)

    def set_snapshot(self, macro):
        active = isinstance(macro, dict) and macro.get("state") == 2
        self._status = "active" if active else (
            "offline" if macro is None else {1: "review", 3: "unavailable"}.get(macro.get("state"), "unassigned"))
        self.setEnabled(active)
        if active:
            if self._drag_y is None:
                self.blockSignals(True)
                self.setValue(round(max(0.0, min(1.0, float(macro.get("value", 0)))) * 1000))
                self.blockSignals(False)
            self._text = macro_value_text(macro) or "—"
            label = str(macro.get("macroName") or f"Macro {self.index + 1}")
            self.setAccessibleName(label)
            identity = " · ".join(filter(None, (macro.get("busName"), macro.get("pluginName"), macro.get("macroName"))))
            gesture_hint = "Kéo dọc để vặn · Shift: tinh chỉnh · Alt: siêu mịn · Wheel: chỉnh bước"
            self.setToolTip("\n".join(filter(None, (identity, gesture_hint))))
        else:
            self._text = "—"
            self.setAccessibleName(f"Macro {self.index + 1}, chưa khả dụng")
            self.setToolTip("Chưa khả dụng — mở Mapping để kiểm tra")
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_y = event.position().y()
            self._drag_value = float(self.value())
            self._grabbed = True
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_y is not None:
            modifiers = event.modifiers()
            gain = .45 if modifiers & Qt.KeyboardModifier.AltModifier else (
                1.35 if modifiers & Qt.KeyboardModifier.ShiftModifier else 5.5
            )
            current_y = event.position().y()
            self._drag_value += (self._drag_y - current_y) * gain
            self._drag_y = current_y
            self.setValue(round(self._drag_value))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_y = None
            self._grabbed = False
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            self.update()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        pixel_y = event.pixelDelta().y()
        if pixel_y:
            change = pixel_y * .55
        else:
            change = event.angleDelta().y() / 120.0 * 24.0
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.AltModifier:
            change *= .10
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            change *= .28
        if abs(change) < 1.0:
            change = 1.0 if change > 0 else (-1.0 if change < 0 else 0.0)
        self.setValue(round(self.value() + change))
        event.accept()

    def enterEvent(self, event):
        if self.isEnabled() and not self._grabbed:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        side = min(self.width(), self.height())
        box = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 105 if self._grabbed else 125))
        shadow_lift = side * (.062 if self._grabbed else .075)
        painter.drawEllipse(box.adjusted(side * .045, shadow_lift,
                                         -side * .045, -side * .015))

        # Modern-analog metal foundation: cool titanium base, dark knurled
        # collar and a restrained nickel shoulder.  Amber is reserved for live
        # value indication, never used as an all-over vintage plating colour.
        metal_box = box.adjusted(side * .045, side * .045,
                                 -side * .045, -side * .045)
        metal = QConicalGradient(metal_box.center(), -32)
        metal.setColorAt(0.00, QColor("#15191b"))
        metal.setColorAt(0.10, QColor("#8d9699"))
        metal.setColorAt(0.20, QColor("#343a3d"))
        metal.setColorAt(0.36, QColor("#c6ced0"))
        metal.setColorAt(0.49, QColor("#454a4c"))
        metal.setColorAt(0.68, QColor("#879195"))
        metal.setColorAt(0.84, QColor("#282d30"))
        metal.setColorAt(1.00, QColor("#15191b"))
        painter.setBrush(metal)
        painter.setPen(QPen(QColor("#080808"), max(1.0, side * .009)))
        painter.drawEllipse(metal_box)

        cx, cy = box.center().x(), box.center().y()
        painter.setPen(QPen(QColor(214, 222, 223, 72), max(.7, side * .006)))
        for index in range(64):
            angle = index * 2 * pi / 64
            painter.drawLine(round(cx + cos(angle) * side * .405),
                             round(cy + sin(angle) * side * .405),
                             round(cx + cos(angle) * side * .445),
                             round(cy + sin(angle) * side * .445))
        for asset in (self._assets[0], self._assets[2], self._assets[1]):
            if not asset.isNull():
                painter.drawPixmap(box, asset, QRectF(asset.rect()))
        inner = box.adjusted(side * .275, side * .275, -side * .275, -side * .275)
        # A second shoulder adds the depth missing from a flat sprite.
        shoulder = QConicalGradient(inner.center(), 18)
        shoulder.setColorAt(0.0, QColor("#7d8587"))
        shoulder.setColorAt(.18, QColor("#171918"))
        shoulder.setColorAt(.40, QColor("#b8c0c1"))
        shoulder.setColorAt(.62, QColor("#242625"))
        shoulder.setColorAt(.82, QColor("#687174"))
        shoulder.setColorAt(1.0, QColor("#7d8587"))
        painter.setBrush(shoulder)
        painter.setPen(QPen(QColor(8, 9, 9, 220), max(1.0, side * .012)))
        painter.drawEllipse(inner.adjusted(-side * .025, -side * .025,
                                           side * .025, side * .025))
        # Machined cap, deliberately low-gloss.  Console hardware reads as real
        # because adjacent facets respond differently to light; a radial glass
        # highlight made the previous control look like a glossy UI orb.
        cap = QConicalGradient(inner.center(), -24)
        if self._cap_variant == 1:
            # Bead-blasted titanium encoder cap.
            stops = ((0.00, "#3d4141"), (.12, "#b8b9b5"), (.27, "#606260"),
                     (.45, "#d2d0c9"), (.61, "#6a6b68"), (.82, "#a4a49f"),
                     (1.00, "#3d4141"))
        elif self._cap_variant == 2:
            # Dark gunmetal cap with slightly stronger machined facets.
            stops = ((0.00, "#101314"), (.12, "#51595b"), (.27, "#1a2022"),
                     (.45, "#697275"), (.61, "#202628"), (.82, "#3e474a"),
                     (1.00, "#101314"))
        else:
            # Warm graphite cap ties the controls to the ivory chassis.
            stops = ((0.00, "#151716"), (.12, "#55534d"), (.27, "#242624"),
                     (.45, "#777168"), (.61, "#292a28"), (.82, "#4a4843"),
                     (1.00, "#151716"))
        for position, colour in stops:
            cap.setColorAt(position, QColor(colour))
        painter.setBrush(cap)
        painter.setPen(QPen(QColor(210, 220, 222, 82), max(1.0, side * .007)))
        painter.drawEllipse(inner)

        # Each family has a distinct, physically plausible centre treatment:
        # recessed dimple, concentric spindle boss, or clean spun face.
        if self._cap_variant == 1:
            boss = inner.adjusted(side * .13, side * .13,
                                  -side * .13, -side * .13)
            painter.setBrush(QColor(26, 28, 28, 115))
            painter.setPen(QPen(QColor(238, 235, 225, 45), max(.6, side * .004)))
            painter.drawEllipse(boss)
        elif self._cap_variant == 2:
            dimple = inner.adjusted(side * .19, side * .19,
                                    -side * .19, -side * .19)
            painter.setBrush(QColor(4, 6, 7, 130))
            painter.setPen(QPen(QColor(160, 174, 178, 54), max(.6, side * .004)))
            painter.drawEllipse(dimple)

        # Subtle concentric lathe marks remain visible at 2x without turning
        # into decorative rings at normal UI scale.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for inset, alpha in ((side * .030, 24), (side * .052, 17),
                             (side * .074, 12)):
            painter.setPen(QPen(QColor(228, 235, 236, alpha),
                                max(.45, side * .0035)))
            painter.drawEllipse(inner.adjusted(inset, inset, -inset, -inset))

        # Broad diffuse reflection from the same upper-left softbox used by the
        # Blender chassis; no bloom and no isolated white hotspot.
        softbox = QRadialGradient(inner.center().x() - inner.width() * .24,
                                  inner.center().y() - inner.height() * .28,
                                  inner.width() * .92)
        softbox.setColorAt(0.0, QColor(242, 249, 250, 30))
        softbox.setColorAt(.34, QColor(255, 255, 255, 8))
        softbox.setColorAt(1.0, QColor(0, 0, 0, 46))
        painter.setBrush(softbox)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(inner.adjusted(side * .018, side * .018,
                                           -side * .018, -side * .018))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 248, 230, 42), max(.8, side * .006)))
        painter.drawArc(inner.adjusted(side * .018, side * .018,
                                       -side * .018, -side * .018), 28 * 16, 106 * 16)
        if self.isEnabled():
            # Segment lights and pointer are runtime layers, never baked values.
            fraction = self.value() / 1000.0
            painter.setPen(QPen(QColor(COLORS["amber"]), max(1.0, side * .017),
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            segments = 37 if self._cap_variant != 1 else 25
            for i in range(round(fraction * segments)):
                angle = (135 + 270 * i / (segments - 1)) * pi / 180
                painter.drawLine(round(cx + cos(angle) * side * .37),
                                 round(cy + sin(angle) * side * .37),
                                 round(cx + cos(angle) * side * .41),
                                 round(cy + sin(angle) * side * .41))
            angle = (135 + 270 * fraction) * pi / 180
            painter.setPen(QPen(QColor(0, 0, 0, 150), max(3.0, side * .025),
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(round(cx + cos(angle) * side * .23), round(cy + sin(angle) * side * .23),
                             round(cx + cos(angle) * side * .34), round(cy + sin(angle) * side * .34))
            painter.setPen(QPen(QColor(COLORS["amber_bright"]), max(2.0, side * .016),
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(round(cx + cos(angle) * side * .24), round(cy + sin(angle) * side * .24),
                             round(cx + cos(angle) * side * .33), round(cy + sin(angle) * side * .33))
        painter.setPen(QColor("#f4d295") if self.isEnabled() else QColor("#85837f"))
        painter.setFont(system_font(max(8, round(side * .10)), QFont.Weight.DemiBold))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter,
                         painter.fontMetrics().elidedText(self._text, Qt.TextElideMode.ElideRight, int(side * .55)))
        if self.isEnabled() and (self._grabbed or self.underMouse()):
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(244, 199, 125, 150 if self._grabbed else 48),
                                max(.8, side * (.010 if self._grabbed else .006))))
            painter.drawEllipse(metal_box.adjusted(side * .012, side * .012,
                                                   -side * .012, -side * .012))
        if self.hasFocus():
            painter.setPen(QPen(QColor("#f4c77d"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(box.adjusted(2, 2, -2, -2))


class AtomicSurface(QWidget):
    # Window-space enclosure lines.  These are deliberately not reference-
    # canvas units: they retain the same perceived thickness when the hardware
    # surface is resized or letterboxed, while Qt maps logical pixels to the
    # current screen DPI.
    OUTER_FRAME_WIDTH = 6.0
    OUTER_FRAME_KEYLINE_WIDTH = 1.0

    mappingRequested = pyqtSignal(int)
    eqControlRequested = pyqtSignal()
    eqParameterChanged = pyqtSignal(str, float)
    analysisSourceRequested = pyqtSignal(str, str)
    toneInputSourceRequested = pyqtSignal(str)
    macroChanged = pyqtSignal(int, float)
    legacyRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    resetRequested = pyqtSignal()
    toneShiftRequested = pyqtSignal(int)
    modeRequested = pyqtSignal(str)
    modeProfileRequested = pyqtSignal()
    modeStepRequested = pyqtSignal(int)
    karaokeRequested = pyqtSignal()
    songListRequested = pyqtSignal()
    contactRequested = pyqtSignal()
    settingsRequested = pyqtSignal()
    micToggleRequested = pyqtSignal()
    closeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Blender supplies only the data-free enclosure and material response.
        # Text, meters, waveforms, controls and mappings remain live Qt layers.
        self._background = QPixmap(
            str(_ASSETS / "autokey_chassis_blender_clean@2x.png"))
        self._grid = QPixmap(str(_ASSETS / "eq_grid_EMPTY_1054x207@2x.png"))
        self._meter_face = QPixmap(str(_ASSETS / "meter_two_channel_EMPTY_78x240@2x.png"))
        self._meter_leds = {
            "off": QPixmap(str(_ASSETS / "led_segment_off@2x.png")),
            "green": QPixmap(str(_ASSETS / "led_segment_green@2x.png")),
            "amber": QPixmap(str(_ASSETS / "led_segment_amber@2x.png")),
            "orange": QPixmap(str(_ASSETS / "led_segment_orange@2x.png")),
        }
        self._placements = []
        self._input_level = 0.0
        self._waveform = ()
        self._spectrum = ()
        self._waveform_target = ()
        self._spectrum_target = ()
        self._analysis_animation = QTimer(self)
        self._analysis_animation.setTimerType(Qt.TimerType.PreciseTimer)
        self._analysis_animation.setInterval(16)
        self._analysis_animation.timeout.connect(self._advance_analysis_animation)
        self._analysis_animation.start()
        self._capture_status = "WAITING"
        self._analysis_source_name = "Master Post-FX"
        self._analysis_sources = ()
        self._tone_input_source = "daw"
        self._eq_surface = None
        self._eq_drag = None
        self._eq_selected_band = ""
        self._eq_hover_band = ""
        self._eq_last_emit_at = 0.0
        self._tone = "Chờ tín hiệu"
        self._shift = 0
        self._preset_name = "—"
        self._connection_status = "DAW OFFLINE"
        self._autotune_status = "AUTOTUNE • CHƯA GÁN"
        self._autotune_applied = False
        self._labels = [f"NÚM {index + 1}" for index in range(6)]
        self._mode_buttons = {}
        # Keep every live control addressable. Besides making accessibility
        # state explicit, this prevents a visual redesign from silently
        # replacing a working button with an untested paint-only icon.
        self._utility_buttons = {}
        self.knobs = []
        for index, (cx, cy) in enumerate(MACRO_CENTERS):
            knob = AtomicKnob(index, self)
            knob.valueChanged.connect(lambda value, i=index: self.macroChanged.emit(i, value / 1000.0))
            self._place(knob, cx - MACRO_DIAMETER // 2, cy - MACRO_DIAMETER // 2,
                        MACRO_DIAMETER, MACRO_DIAMETER)
            self.knobs.append(knob)
        self._tone_minus_button = self._tone_button(
            "−", (940, 443, 56, 56), lambda: self.toneShiftRequested.emit(-1))
        self._tone_plus_button = self._tone_button(
            "+", (1289, 443, 56, 56), lambda: self.toneShiftRequested.emit(1))
        mode_specs = (("NATURAL", "natural", 937, 565), ("LOFI", "lofi", 1075, 565),
                      ("POP", "nhac_tre", 1213, 565), ("BOLERO", "bolero", 937, 640),
                      ("R&B", "rnb", 1075, 640), ("REMIX", "remix", 1213, 640))
        for name, key, x, y in mode_specs:
            button = self._button(name, (x, y, 120, 56),
                                  lambda _checked=False, k=key: self.modeRequested.emit(k))
            self._mode_buttons[key] = button
        self._mapping_button = MappingButton(self)
        self._mapping_button.clicked.connect(self._mapping_menu)
        self._place(self._mapping_button, *MAPPING.tuple())
        self._eq_button = self._button("EQ OFF", (604, 129, 118, 42), self.eqControlRequested.emit)
        self._eq_button.setToolTip("Chọn EQ thật trên bus hoặc master để điều khiển")
        self._analysis_button = self._button("MASTER  ▾", (732, 129, 118, 42), self._analysis_source_menu)
        self._analysis_button.setToolTip("Chọn nguồn analyzer: Master, track hoặc FX Bus Post-FX")
        self._tone_source_buttons = {}
        for label, source, x, width in (("DAW", "daw", 330, 78),
                                        ("YOUTUBE", "youtube", 410, 92),
                                        ("MIC", "microphone", 504, 78)):
            button = self._button(
                label, (x, 129, width, 42),
                lambda _checked=False, value=source: self.toneInputSourceRequested.emit(value))
            button.setToolTip({
                "daw": "Dò tone trực tiếp từ track đang chọn trong StudioForge",
                "youtube": "Dò tone từ video YouTube đang phát",
                "microphone": "Lắng nghe microphone và dò âm thanh bên ngoài",
            }[source])
            self._tone_source_buttons[source] = button
        self.set_tone_input_source("daw")
        # Target header functions are all bound to existing app operations.
        self._utility_buttons["karaoke"] = self._utility_button(
            "karaoke", (904, 36, 38, 38), self.karaokeRequested.emit, "Mở Karaoke YouTube")
        self._utility_buttons["library"] = self._utility_button(
            "library", (946, 36, 38, 38), self.songListRequested.emit, "Danh sách bài hát")
        self._utility_buttons["contact"] = self._utility_button(
            "contact", (988, 36, 38, 38), self.contactRequested.emit, "Liên hệ hỗ trợ")
        self._utility_buttons["settings"] = self._utility_button(
            "settings", (1030, 36, 38, 38), self.settingsRequested.emit, "Cài đặt")
        self._save_button = self._button("SAVE", (1076, 33, 88, 46), self.saveRequested.emit)
        self._mic_button = self._utility_button(
            "mic", (1170, 31, 44, 48), self.micToggleRequested.emit,
            "Bật hoặc tắt microphone", checkable=True)
        self._power_button = PowerButton(self)
        self._power_button.clicked.connect(self.closeRequested.emit)
        self._place(self._power_button, 1222, 25, 148, 58)
        # The header is a real mode instrument: centre edits the current mode,
        # while its two physical arrow keys step through the mode bank.
        self._mode_profile_button = self._hotspot(
            (538, 27, 298, 56), self.modeProfileRequested.emit,
            "Đổi tên và lưu thiết lập cho Vocal Mode hiện tại")
        self._mode_previous_button = self._hotspot(
            (488, 34, 48, 42), lambda: self.modeStepRequested.emit(-1), "Vocal Mode trước")
        self._mode_next_button = self._hotspot(
            (838, 34, 48, 42), lambda: self.modeStepRequested.emit(1), "Vocal Mode tiếp theo")
        self.setAccessibleName("StudioForge Auto-Key")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def showEvent(self, event):
        # Keep the first hardware button from looking selected on launch while
        # preserving normal Tab/keyboard focus once the user navigates.
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        super().showEvent(event)

    def _place(self, widget, x, y, width, height):
        self._placements.append((widget, x, y, width, height))
        widget.show()

    def _button(self, text, rect, callback, tone_step=False):
        button = HardwareButton(text, self)
        if callback is not None:
            button.clicked.connect(callback)
        self._place(button, *rect)
        return button

    def _tone_button(self, text, rect, callback):
        button = ToneStepButton(text, self)
        button.clicked.connect(callback)
        self._place(button, *rect)
        return button

    def _utility_button(self, kind, rect, callback, tooltip, checkable=False):
        button = UtilityIconButton(kind, tooltip, self, checkable=checkable)
        button.setObjectName(f"AtomicUtility_{kind}")
        button.clicked.connect(lambda _checked=False: callback())
        self._place(button, *rect)
        return button

    def set_mic_enabled(self, enabled):
        self._mic_button.setChecked(bool(enabled))
        self._mic_button.setToolTip("Microphone đang bật" if enabled else "Microphone đang tắt")
        self._mic_button.update()

    def set_tone_input_source(self, source):
        source = str(source or "daw").lower()
        self._tone_input_source = source
        for key, button in self._tone_source_buttons.items():
            button.setProperty("selected", key == source)
            button.setAccessibleDescription(
                "Nguồn dò tone đang bật" if key == source else "Nguồn dò tone")
            button.update()

    def clear_live_analysis(self):
        self._input_level = 0.0
        self._waveform = ()
        self._spectrum = ()
        self._waveform_target = ()
        self._spectrum_target = ()
        self.update()

    def _hotspot(self, rect, callback, tooltip):
        button = QPushButton(self)
        button.setAccessibleName(tooltip)
        button.setToolTip(tooltip)
        button.setStyleSheet("QPushButton { background: transparent; border: 0; }")
        button.clicked.connect(callback)
        self._place(button, *rect)
        return button

    def _mapping_menu(self):
        menu = QMenu(self)
        for i in range(6):
            action = menu.addAction(f"Núm {i + 1} — {self._labels[i]}")
            action.triggered.connect(lambda _checked=False, index=i: self.mappingRequested.emit(index))
        menu.exec(self.mapToGlobal(self.rect().center()))

    def _analysis_source_menu(self):
        menu = QMenu(self)
        if not self._analysis_sources:
            menu.addAction("Master Post-FX").setEnabled(False)
        for source in self._analysis_sources:
            if not isinstance(source, dict):
                continue
            action = menu.addAction(str(source.get("name", "Nguồn không tên")))
            kind, source_id = str(source.get("kind", "")), str(source.get("id", ""))
            action.setCheckable(True)
            action.setChecked(str(source.get("name", "")) == self._analysis_source_name)
            action.triggered.connect(
                lambda _checked=False, k=kind, i=source_id: self.analysisSourceRequested.emit(k, i))
        menu.exec(self.mapToGlobal(self.rect().center()))

    def set_snapshot(self, snapshot):
        if isinstance(snapshot, dict):
            self._connection_status = "DAW CONNECTED"
            sources = snapshot.get("analysisSources", [])
            self._analysis_sources = tuple(sources) if isinstance(sources, list) else ()
            analysis = snapshot.get("audioAnalysis")
            if isinstance(analysis, dict):
                self._analysis_source_name = str(analysis.get("sourceName") or "Master Post-FX")
                compact = self._analysis_source_name.replace(" Post-FX", "").upper()
                self._analysis_button.setText(f"{compact[:12]}  ▾")
        for i, knob in enumerate(self.knobs):
            macro = macro_at(snapshot, i)
            knob.set_snapshot(macro)
            if snapshot is None:
                self._labels[i] = f"NÚM {i + 1}"
            elif macro is None:
                self._labels[i] = f"NÚM {i + 1}"
            elif macro.get("state") == 2:
                self._labels[i] = str(macro.get("macroName") or "Đã gán")
            else:
                self._labels[i] = {1: "Cần kiểm tra", 3: "Đang bypass"}.get(macro.get("state"), "Chưa gán")
        if snapshot is None:
            self._connection_status = "DAW OFFLINE"
        self.update()

    def set_input_level(self, level):
        incoming = max(0.0, min(1.0, float(level)))
        # Display-only meter ballistics: quick attack, slower release.  Audio
        # and analysis values remain untouched; this only avoids a coarse,
        # flickering LED readout at the UI refresh rate.
        coefficient = .58 if incoming >= self._input_level else .16
        self._input_level += (incoming - self._input_level) * coefficient
        if incoming == 0.0 and self._input_level < .002:
            self._input_level = 0.0
        self.update()

    def set_waveform(self, values):
        """Set the next DAW envelope; the paint clock interpolates to it."""
        try:
            target = tuple(max(0.0, min(1.0, float(value))) for value in values)
            self._waveform_target = target
            if len(self._waveform) != len(target):
                self._waveform = target
        except (TypeError, ValueError):
            self._waveform_target = ()

    def set_spectrum(self, values):
        """Set the next spectrum; attack/release ballistics run at 60 Hz."""
        try:
            target = tuple(max(0.0, min(1.0, float(value))) for value in values)
            self._spectrum_target = target
            if len(self._spectrum) != len(target):
                self._spectrum = target
        except (TypeError, ValueError):
            self._spectrum_target = ()

    @staticmethod
    def _smooth_analysis_values(current, target, attack, release):
        if not target:
            return (), bool(current)
        if len(current) != len(target):
            return target, True
        changed = False
        values = []
        for shown, incoming in zip(current, target):
            coefficient = attack if incoming >= shown else release
            value = shown + (incoming - shown) * coefficient
            if abs(value - incoming) < .00035:
                value = incoming
            changed = changed or abs(value - shown) > .0001
            values.append(value)
        return tuple(values), changed

    def _advance_analysis_animation(self):
        self._waveform, waveform_changed = self._smooth_analysis_values(
            self._waveform, self._waveform_target, .46, .20)
        self._spectrum, spectrum_changed = self._smooth_analysis_values(
            self._spectrum, self._spectrum_target, .52, .13)
        if waveform_changed or spectrum_changed:
            self.update()

    def set_capture_status(self, text):
        self._capture_status = str(text or "WAITING")
        self._analysis_button.setToolTip(
            f"{self._analysis_source_name} — {self._capture_status}. Bấm để đổi nguồn analyzer")
        self.update()

    def set_eq_surface(self, descriptor):
        # A periodic DAW refresh must never cancel a physical drag gesture.
        if self._eq_drag is not None:
            return
        self._eq_surface = descriptor if isinstance(descriptor, dict) else None
        interactive = bool(self._eq_surface and self._eq_surface.get("capability") == "eq_interactive")
        self._eq_button.setText("EQ ON" if interactive else "EQ OFF")
        self._eq_button.setProperty("selected", interactive)
        self._eq_button.setToolTip(
            "Nhấp vùng trống: tạo band · kéo: Frequency/Gain · lăn: Q · nhấp đúp: xóa" if interactive
            else "Chọn EQ thật trên bus, track hoặc master để điều khiển")
        self._eq_button.update()
        if not interactive:
            self._eq_selected_band = ""
            self._eq_hover_band = ""
        self.update()

    @property
    def eq_gesture_active(self):
        return self._eq_drag is not None

    def _eq_nodes(self):
        descriptor = self._eq_surface
        if not isinstance(descriptor, dict) or descriptor.get("capability") != "eq_interactive":
            return []
        nodes = []
        for band in descriptor.get("bands", []):
            if not isinstance(band, dict):
                continue
            used, enabled = band.get("used"), band.get("enabled")
            if isinstance(used, dict) and float(used.get("normalizedValue", 0)) < .5:
                continue
            if isinstance(enabled, dict) and float(enabled.get("normalizedValue", 1)) < .5:
                continue
            frequency, gain = band.get("frequency"), band.get("gain")
            if isinstance(frequency, dict) and isinstance(gain, dict):
                nodes.append((band, frequency, gain))
        return nodes

    def _eq_node_position(self, frequency, gain):
        rect = QRectF(EQ_GRAPH.x, EQ_GRAPH.y, EQ_GRAPH.width, EQ_GRAPH.height)
        model = self._eq_surface.get("parameterModel", {})
        f_min, f_max = float(model.get("frequencyMinHz", 10)), float(model.get("frequencyMaxHz", 30000))
        g_min, g_max = float(model.get("gainMinDb", -30)), float(model.get("gainMaxDb", 30))
        f_norm = max(0.0, min(1.0, float(frequency.get("normalizedValue", .5))))
        g_norm = max(0.0, min(1.0, float(gain.get("normalizedValue", .5))))
        hz = f_min * exp(log(f_max / f_min) * f_norm)
        db = g_min + (g_max - g_min) * g_norm
        x = rect.left() + max(0.0, min(1.0, log(max(20.0, min(20000.0, hz)) / 20.0) / log(1000.0))) * rect.width()
        y = rect.center().y() - max(-12.0, min(12.0, db)) / 24.0 * rect.height()
        return x, y

    def _event_reference_point(self, event):
        ox, oy, scale = self._reference()
        return ((event.position().x() - ox) / scale,
                (event.position().y() - oy) / scale)

    def _eq_node_at(self, point, radius=20.0):
        nearest = None
        for band, frequency, gain in self._eq_nodes():
            x, y = self._eq_node_position(frequency, gain)
            distance = (x - point[0]) ** 2 + (y - point[1]) ** 2
            if distance <= radius ** 2 and (nearest is None or distance < nearest[0]):
                nearest = (distance, band, frequency, gain)
        return nearest

    def _emit_eq_drag_values(self, force=False):
        if self._eq_drag is None:
            return
        now = monotonic()
        if not force and now - self._eq_last_emit_at < 1.0 / 30.0:
            return
        _band, frequency, gain = self._eq_drag
        self.eqParameterChanged.emit(str(frequency.get("parameterId", "")),
                                     float(frequency["normalizedValue"]))
        self.eqParameterChanged.emit(str(gain.get("parameterId", "")),
                                     float(gain["normalizedValue"]))
        self._eq_last_emit_at = now

    def _set_eq_band_position(self, frequency, gain, point):
        x = max(float(EQ_GRAPH.x), min(float(EQ_GRAPH.x + EQ_GRAPH.width), point[0]))
        y = max(float(EQ_GRAPH.y), min(float(EQ_GRAPH.y + EQ_GRAPH.height), point[1]))
        hz = 20.0 * exp(log(1000.0) * ((x - EQ_GRAPH.x) / EQ_GRAPH.width))
        model = self._eq_surface["parameterModel"]
        f_norm = log(hz / float(model["frequencyMinHz"])) / log(
            float(model["frequencyMaxHz"]) / float(model["frequencyMinHz"]))
        db = ((EQ_GRAPH.y + EQ_GRAPH.height / 2) - y) / EQ_GRAPH.height * 24.0
        g_norm = (db - float(model["gainMinDb"])) / (
            float(model["gainMaxDb"]) - float(model["gainMinDb"]))
        frequency["normalizedValue"] = max(0.0, min(1.0, f_norm))
        gain["normalizedValue"] = max(0.0, min(1.0, g_norm))

    @staticmethod
    def _point_in_eq_graph(point):
        return (EQ_GRAPH.x <= point[0] <= EQ_GRAPH.x + EQ_GRAPH.width
                and EQ_GRAPH.y <= point[1] <= EQ_GRAPH.y + EQ_GRAPH.height)

    def _create_eq_band(self, point):
        if not self._point_in_eq_graph(point):
            return False
        descriptor = self._eq_surface
        if not isinstance(descriptor, dict) or descriptor.get("capability") != "eq_interactive":
            return False
        for band in descriptor.get("bands", []):
            if not isinstance(band, dict):
                continue
            used, enabled = band.get("used"), band.get("enabled")
            is_unused = isinstance(used, dict) and float(used.get("normalizedValue", 0)) < .5
            if not isinstance(used, dict):
                is_unused = isinstance(enabled, dict) and float(enabled.get("normalizedValue", 1)) < .5
            frequency, gain = band.get("frequency"), band.get("gain")
            if not is_unused or not isinstance(frequency, dict) or not isinstance(gain, dict):
                continue
            # Activate the DAW-owned band first, then position it. Signal
            # insertion order is preserved by the coalescing writer.
            for parameter in (used, enabled):
                if isinstance(parameter, dict) and parameter.get("parameterId"):
                    parameter["normalizedValue"] = 1.0
                    self.eqParameterChanged.emit(str(parameter["parameterId"]), 1.0)
            self._set_eq_band_position(frequency, gain, point)
            self._eq_drag = (band, frequency, gain)
            self._eq_selected_band = str(band.get("bandId", ""))
            self._eq_last_emit_at = 0.0
            self._emit_eq_drag_values(force=True)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            return True
        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            point = self._event_reference_point(event)
            nearest = self._eq_node_at(point)
            if nearest:
                self._eq_drag = nearest[1:]
                self._eq_selected_band = str(nearest[1].get("bandId", ""))
                self._eq_last_emit_at = 0.0
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
            if self._create_eq_band(point):
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._eq_drag is None:
            point = self._event_reference_point(event)
            nearest = self._eq_node_at(point)
            hover = str(nearest[1].get("bandId", "")) if nearest else ""
            if hover != self._eq_hover_band:
                self._eq_hover_band = hover
                self.update()
            interactive = bool(self._eq_surface and
                               self._eq_surface.get("capability") == "eq_interactive")
            self.setCursor(Qt.CursorShape.OpenHandCursor if hover else (
                Qt.CursorShape.CrossCursor if interactive and self._point_in_eq_graph(point)
                else Qt.CursorShape.ArrowCursor))
            super().mouseMoveEvent(event)
            return
        _band, frequency, gain = self._eq_drag
        self._set_eq_band_position(frequency, gain, self._event_reference_point(event))
        self._emit_eq_drag_values()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._eq_drag is not None:
            self._emit_eq_drag_values(force=True)
            self._eq_drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            nearest = self._eq_node_at(self._event_reference_point(event))
            if nearest:
                band = nearest[1]
                for key in ("enabled", "used"):
                    parameter = band.get(key)
                    if isinstance(parameter, dict) and parameter.get("parameterId"):
                        parameter["normalizedValue"] = 0.0
                        self.eqParameterChanged.emit(str(parameter["parameterId"]), 0.0)
                self._eq_drag = None
                self._eq_selected_band = ""
                self._eq_hover_band = ""
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.update()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        nearest = self._eq_node_at(self._event_reference_point(event))
        if nearest:
            band = nearest[1]
            q_parameter = band.get("q")
            if isinstance(q_parameter, dict) and q_parameter.get("parameterId"):
                steps = event.angleDelta().y() / 120.0
                if steps:
                    old_value = float(q_parameter.get("normalizedValue", .5))
                    q_parameter["normalizedValue"] = max(0.0, min(1.0, old_value + steps * .025))
                    self._eq_selected_band = str(band.get("bandId", ""))
                    self.eqParameterChanged.emit(str(q_parameter["parameterId"]),
                                                 float(q_parameter["normalizedValue"]))
                    self.update()
                    event.accept()
                    return
        super().wheelEvent(event)

    def set_tone(self, tone, shift):
        self._tone = str(tone or "Chờ tín hiệu")
        self._shift = int(shift)
        self.update()

    def set_autotune_status(self, text, applied=False):
        """Show only DAW-acknowledged pitch-correction state."""
        self._autotune_status = str(text or "AUTOTUNE • CHƯA GÁN")
        self._autotune_applied = bool(applied)
        self.update()

    def set_preset_name(self, name):
        """Render a name supplied by the existing persistence layer only."""
        self._preset_name = str(name or "—")
        self.update()

    def set_active_mode(self, mode):
        for key, button in self._mode_buttons.items():
            button.setProperty("selected", key == mode)
            button.update()

    def set_mode_labels(self, labels):
        if not isinstance(labels, dict):
            return
        for key, button in self._mode_buttons.items():
            if key in labels:
                button.setText(str(labels[key])[:14].upper())
                button.setAccessibleName(str(labels[key]))
                button.update()

    def resizeEvent(self, event):
        self._layout_children()
        super().resizeEvent(event)

    def _reference(self):
        scale = min(self.width() / REFERENCE_WIDTH, self.height() / REFERENCE_HEIGHT)
        return ((self.width() - REFERENCE_WIDTH * scale) / 2,
                (self.height() - REFERENCE_HEIGHT * scale) / 2, scale)

    def _layout_children(self):
        ox, oy, scale = self._reference()
        for widget, x, y, w, h in self._placements:
            widget.setGeometry(round(ox + x * scale), round(oy + y * scale), round(w * scale), round(h * scale))
            if isinstance(widget, QPushButton) and not isinstance(widget, (PowerButton, MappingButton,
                                                                            HardwareButton)):
                widget.setFont(system_font(max(7, round(11 * scale)), QFont.Weight.DemiBold))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#0a0b0c"))
        ox, oy, scale = self._reference()
        p.translate(ox, oy)
        p.scale(scale, scale)
        has_blender_chassis = not self._background.isNull()
        if has_blender_chassis:
            p.drawPixmap(QRectF(0, 0, REFERENCE_WIDTH, REFERENCE_HEIGHT),
                         self._background, QRectF(self._background.rect()))
        else:
            # Deterministic fallback for incomplete development/package assets.
            self._paint_outer_enclosure(p)
            self._paint_module_hierarchy(p)
            self._paint_detection_cluster(p)
            for screw_x, screw_y, screw_rotation in _CHASSIS_SCREWS:
                _paint_hardware_screw(p, (screw_x, screw_y), 14, screw_rotation)
        if not self._grid.isNull():
            p.setOpacity(.68)
            p.drawPixmap(QRectF(EQ_GRAPH.x, EQ_GRAPH.y, EQ_GRAPH.width, EQ_GRAPH.height),
                         self._grid, QRectF(self._grid.rect()))
            p.setOpacity(1)
        self._paint_header(p)
        self._paint_key_display(p)
        # The mode bank has a compact engraved legend between the upper
        # instruments and its full-width switch rail.
        mode_font = system_font(8, QFont.Weight.DemiBold)
        mode_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.2)
        p.setFont(mode_font)
        _draw_panel_ink(p, QRectF(920, 538, 445, 20), Qt.AlignmentFlag.AlignCenter,
                        "VOCAL MODE", QColor("#3b3a37"))
        legend_rule = QLinearGradient(330, 0, 1078, 0)
        legend_rule.setColorAt(0.0, QColor(128, 134, 132, 0))
        legend_rule.setColorAt(.35, QColor(52, 50, 46, 82))
        legend_rule.setColorAt(.65, QColor(52, 50, 46, 82))
        legend_rule.setColorAt(1.0, QColor(128, 134, 132, 0))
        p.setPen(QPen(QBrush(legend_rule), .8))
        p.drawLine(942, 549, 1032, 549)
        p.drawLine(1253, 549, 1343, 549)

        # Compact Tone Shift console with explicit title/readout/scale lanes.
        # Keeping those three baselines independent prevents translated text
        # or high-DPI font metrics from colliding with the numeric display.
        p.setFont(system_font(9, QFont.Weight.DemiBold))
        _draw_panel_ink(p, QRectF(920, 410, 445, 18), Qt.AlignmentFlag.AlignCenter,
                        "TONE SHIFT", QColor("#e3e5e2"))
        p.setFont(system_font(24, QFont.Weight.DemiBold))
        p.setPen(QColor(COLORS["warm_white"]))
        p.drawText(QRectF(1008, 438, 268, 32), Qt.AlignmentFlag.AlignCenter, f"{self._shift:+d}")
        for index in range(13):
            active_tick = index == max(0, min(12, self._shift + 6))
            p.setPen(QPen(QColor(COLORS["amber_bright"] if active_tick else "#747a78"),
                          2.2 if active_tick else 1.0))
            x = 1030 + index * 18.4
            p.drawLine(QPointF(x, 477), QPointF(x, 487 if active_tick else 484))
        p.setPen(QColor("#7f8b8f"))
        p.setFont(system_font(7, QFont.Weight.Medium))
        p.drawText(QRectF(1008, 490, 268, 14), Qt.AlignmentFlag.AlignCenter, "−6     SEMITONES     +6")

        p.setFont(system_font(11, QFont.Weight.DemiBold))
        _draw_panel_ink(p, QRectF(44, 128, 176, 44),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        "●  ANALYZER", QColor("#e2e4e1"))
        has_signal = bool(self._spectrum) and max(self._spectrum, default=0.0) > 0.002 and self._input_level > 0.001
        p.setFont(system_font(8, QFont.Weight.Medium))
        p.setPen(QColor(COLORS["amber_bright"]) if has_signal else QColor("#8f877a"))
        p.drawText(QRectF(448, 142, 132, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   "SIGNAL" if has_signal else self._capture_status)
        p.setFont(system_font(10))
        p.setPen(QColor("#aeb6b7"))
        frequency_labels = ("20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "20k")
        for index, label in enumerate(frequency_labels):
            x = EQ_GRAPH.x + 8 + (EQ_GRAPH.width - 16) * index / (len(frequency_labels) - 1)
            _draw_panel_ink(p, QRectF(x - 20, EQ_GRAPH.y + EQ_GRAPH.height + 8, 40, 20),
                            Qt.AlignmentFlag.AlignCenter, label, QColor("#aeb6b7"))
        for index, label in enumerate(("+12", "+6", "0", "−6", "−12")):
            y = EQ_GRAPH.y + EQ_GRAPH.height * index / 4
            _draw_panel_ink(p, QRectF(27, y - 9, 34, 18),
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                            label, QColor("#aeb6b7"))
        self._paint_spectrum(p, QRectF(EQ_GRAPH.x, EQ_GRAPH.y, EQ_GRAPH.width, EQ_GRAPH.height))
        self._paint_eq_curve(p)
        self._paint_eq_nodes(p)
        if (self._eq_surface and self._eq_surface.get("capability") == "eq_interactive"
                and not self._eq_nodes()):
            p.setPen(QColor(154, 178, 177, 150))
            p.setFont(system_font(9, QFont.Weight.DemiBold))
            p.drawText(QRectF(EQ_GRAPH.x, EQ_GRAPH.y, EQ_GRAPH.width, EQ_GRAPH.height),
                       Qt.AlignmentFlag.AlignCenter,
                       "NHẤP VÙNG TRỐNG ĐỂ TẠO BAND EQ")
        p.setFont(system_font(11, QFont.Weight.DemiBold))
        p.setPen(QColor("#e2e4e1"))
        output_available = self._connection_status == "DAW CONNECTED" or self._capture_status == "SIGNAL"
        _draw_panel_ink(p, QRectF(1255, 142, 110, 18), Qt.AlignmentFlag.AlignCenter,
                        "OUTPUT", QColor("#e2e4e1"))
        p.setFont(system_font(8, QFont.Weight.Medium))
        p.setPen(QColor(COLORS["green"] if output_available else "#8d877d"))
        p.drawText(QRectF(1255, 161, 110, 15), Qt.AlignmentFlag.AlignCenter,
                   "POST-FX" if output_available else "NO SIGNAL")
        p.setFont(system_font(12, QFont.Weight.DemiBold))
        p.setPen(QColor("#e8e3d9"))
        level_db = max(-60.0, 20.0 * log(max(.001, self._input_level), 10))
        level_text = f"{level_db:.1f}" if output_available else "—∞"
        p.drawText(QRectF(1255, 353, 110, 22), Qt.AlignmentFlag.AlignCenter,
                   f"{level_text}  dBFS")
        self._paint_meter(p, QRectF(OUTPUT_METER.x, OUTPUT_METER.y,
                                    OUTPUT_METER.width, OUTPUT_METER.height),
                          self._input_level, active=output_available)
        p.setPen(QColor("#d8c8b0"))
        p.setFont(system_font(12, QFont.Weight.Medium))
        for i, (cx, cy) in enumerate(MACRO_CENTERS):
            active = self.knobs[i].isEnabled()
            p.setPen(QColor("#efe3d3") if active else QColor("#a29a8e"))
            _draw_panel_ink(p, QRectF(cx - 72, 920, 144, 22), Qt.AlignmentFlag.AlignCenter,
                            p.fontMetrics().elidedText(self._labels[i], Qt.TextElideMode.ElideRight, 150),
                            QColor("#efe3d3") if active else QColor("#a29a8e"))
            p.setPen(QPen(QColor(COLORS["amber"] if active else "#595650"), 3))
            p.drawLine(cx - 12, 950, cx + 12, 950)
        p.setFont(system_font(8, QFont.Weight.Medium))
        p.setPen(QColor(COLORS["green"] if self._connection_status == "DAW CONNECTED" else "#8d877d"))
        p.drawText(QRectF(MAPPING.x - 8, 950, MAPPING.width + 16, 16),
                   Qt.AlignmentFlag.AlignCenter,
                   self._connection_status)
        # Draw the enclosure lip in window space, after all reference-space
        # content.  Baking this line into the 1408x1000 artwork made it appear
        # thick when enlarged and weak when reduced.
        p.resetTransform()
        self._paint_fixed_outer_frame(
            p, QRectF(ox, oy, REFERENCE_WIDTH * scale, REFERENCE_HEIGHT * scale))

    def _paint_fixed_outer_frame(self, painter, content_rect):
        """Paint the scale-independent outer shell lip around the plugin."""
        main_width = self.OUTER_FRAME_WIDTH
        frame = content_rect.adjusted(main_width / 2, main_width / 2,
                                      -main_width / 2, -main_width / 2)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#050708"), main_width,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        painter.drawRoundedRect(frame, 12.0, 12.0)

        inset = main_width + .5
        keyline = content_rect.adjusted(inset, inset, -inset, -inset)
        painter.setPen(QPen(QColor(95, 108, 111, 150),
                            self.OUTER_FRAME_KEYLINE_WIDTH))
        painter.drawRoundedRect(keyline, 8.0, 8.0)

    def _paint_outer_enclosure(self, painter):
        """Render the single clean enclosure beneath every removable module."""
        outer = QRectF(3.5, 8.5, 1401, 983)
        outer_material = QLinearGradient(0, outer.top(), 0, outer.bottom())
        outer_material.setColorAt(0.0, QColor("#36332e"))
        outer_material.setColorAt(.035, QColor("#0a0b0b"))
        outer_material.setColorAt(.50, QColor("#171716"))
        outer_material.setColorAt(1.0, QColor("#060707"))
        painter.setBrush(outer_material)
        painter.setPen(QPen(QColor("#050606"), 3.0))
        painter.drawRoundedRect(outer, 18, 18)

        chassis = QRectF(9, 43, 1390, 937)
        chassis_metal = QLinearGradient(chassis.left(), 0, chassis.right(), 0)
        chassis_metal.setColorAt(0.0, QColor("#111517"))
        chassis_metal.setColorAt(.055, QColor("#30373a"))
        chassis_metal.setColorAt(.28, QColor("#1c2225"))
        chassis_metal.setColorAt(.50, QColor("#343b3e"))
        chassis_metal.setColorAt(.75, QColor("#1a2023"))
        chassis_metal.setColorAt(.945, QColor("#2b3235"))
        chassis_metal.setColorAt(1.0, QColor("#0c1012"))
        painter.setBrush(chassis_metal)
        painter.setPen(QPen(QColor("#4b5559"), 1.2))
        painter.drawRoundedRect(chassis, 14, 14)
        painter.setPen(QPen(QColor(255, 255, 255, 16), .55))
        for y in range(48, 977, 4):
            painter.drawLine(13, y, 1395, y)

        top_rail = QRectF(4, 8, 1400, 31)
        rail = QLinearGradient(0, top_rail.top(), 0, top_rail.bottom())
        rail.setColorAt(0.0, QColor("#070808"))
        rail.setColorAt(.32, QColor("#34312d"))
        rail.setColorAt(.58, QColor("#151616"))
        rail.setColorAt(1.0, QColor("#050606"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(rail)
        painter.drawRoundedRect(top_rail, 17, 17)

        # Refinish the two narrow side rails.  The source chassis contained
        # oversized baked fastener holes; a clean metal strip lets the live,
        # smaller countersunk screws below define the final hardware scale.
        side_metal = QLinearGradient(8, 0, 41, 0)
        side_metal.setColorAt(0.0, QColor("#090d0f"))
        side_metal.setColorAt(.18, QColor("#3c464a"))
        side_metal.setColorAt(.52, QColor("#181e21"))
        side_metal.setColorAt(.82, QColor("#4b565a"))
        side_metal.setColorAt(1.0, QColor("#0b0f11"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(side_metal)
        painter.drawRect(QRectF(8, 48, 34, 935))
        right_metal = QLinearGradient(1366, 0, 1400, 0)
        right_metal.setColorAt(0.0, QColor("#0b0f11"))
        right_metal.setColorAt(.18, QColor("#4b565a"))
        right_metal.setColorAt(.52, QColor("#181e21"))
        right_metal.setColorAt(.82, QColor("#3c464a"))
        right_metal.setColorAt(1.0, QColor("#090d0f"))
        painter.setBrush(right_metal)
        painter.drawRect(QRectF(1366, 48, 34, 935))
        painter.setPen(QPen(QColor(255, 250, 236, 55), .7))
        painter.drawLine(12, 52, 12, 979)
        painter.drawLine(1396, 52, 1396, 979)

        header = QRectF(49, 47, 1311, 84)
        header_material = QLinearGradient(0, header.top(), 0, header.bottom())
        header_material.setColorAt(0.0, QColor("#33312d"))
        header_material.setColorAt(.10, QColor("#161717"))
        header_material.setColorAt(.72, QColor("#111212"))
        header_material.setColorAt(1.0, QColor("#050606"))
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(header.translated(0, 2), 14, 14)
        painter.setBrush(header_material)
        painter.setPen(QPen(QColor("#56656a"), 1.2))
        painter.drawRoundedRect(header, 14, 14)
        painter.setPen(QPen(QColor(255, 245, 224, 36), .7))
        painter.drawLine(65, 52, 1344, 52)

        frame = outer
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 210), 7.0))
        painter.drawRoundedRect(frame, 18, 18)
        painter.setPen(QPen(QColor("#66767b"), 2.2))
        painter.drawRoundedRect(frame.adjusted(3.5, 3.5, -3.5, -3.5), 15, 15)
        painter.setPen(QPen(QColor(255, 247, 229, 75), .8))
        painter.drawRoundedRect(frame.adjusted(6, 6, -6, -6), 13, 13)
        painter.setPen(QPen(QColor("#263034"), 1.2))
        painter.drawLine(20, 986, 1388, 986)

    def _paint_module_hierarchy(self, painter):
        """Build a legible hardware stack: chassis, module, then inset glass.

        The supplied shell contains broad baked panel shapes.  These calibrated
        overlays restore physical ownership without covering any runtime data:
        ivory rails belong to the chassis, dark plates are removable modules,
        and the analyzer glass sits visibly below its module face.
        """
        # Chassis rails remain visible between modules. They are intentionally
        # light and flat: only the removable black modules receive deep edges.
        rail = QLinearGradient(0, 0, REFERENCE_WIDTH, 0)
        rail.setColorAt(0.0, QColor("#111719"))
        rail.setColorAt(.10, QColor("#374145"))
        rail.setColorAt(.50, QColor("#1b2326"))
        rail.setColorAt(.90, QColor("#3b464a"))
        rail.setColorAt(1.0, QColor("#0e1416"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(rail)
        painter.drawRect(QRectF(18, 444, 1372, 23))
        painter.drawRect(QRectF(18, 719, 1372, 23))

        # Analyzer module: one restrained outer rim and one recessed screen.
        module = QRectF(29, 468, 1350, 247)
        painter.setBrush(QColor(0, 0, 0, 145))
        painter.drawRoundedRect(module.translated(0, 3), 15, 15)
        module_face = QLinearGradient(0, module.top(), 0, module.bottom())
        module_face.setColorAt(0.0, QColor("#273034"))
        module_face.setColorAt(.10, QColor("#141a1d"))
        module_face.setColorAt(.55, QColor("#0d1214"))
        module_face.setColorAt(.90, QColor("#182023"))
        module_face.setColorAt(1.0, QColor("#06090a"))
        painter.setBrush(module_face)
        painter.setPen(QPen(QColor("#46565b"), 1.35))
        painter.drawRoundedRect(module, 15, 15)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(232, 216, 190, 46), .8))
        painter.drawRoundedRect(module.adjusted(4, 4, -4, -4), 12, 12)

        graph_well = QRectF(EQ_GRAPH.x - 8, EQ_GRAPH.y - 8,
                            EQ_GRAPH.width + 16, EQ_GRAPH.height + 16)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 205))
        painter.drawRoundedRect(graph_well.translated(0, 2), 10, 10)
        well = QLinearGradient(0, graph_well.top(), 0, graph_well.bottom())
        well.setColorAt(0.0, QColor("#35464b"))
        well.setColorAt(.055, QColor("#090b0b"))
        well.setColorAt(.94, QColor("#030505"))
        well.setColorAt(1.0, QColor("#31535a"))
        painter.setBrush(well)
        painter.setPen(QPen(QColor("#080909"), 1.2))
        painter.drawRoundedRect(graph_well, 10, 10)

        # Macro module sits on its own lower deck; it does not share the
        # analyzer's bevel or shadow, so their depth relationship is obvious.
        macro = QRectF(29, 749, 1350, 213)
        macro_face = QLinearGradient(0, macro.top(), 0, macro.bottom())
        macro_face.setColorAt(0.0, QColor("#242d30"))
        macro_face.setColorAt(.045, QColor("#0e1315"))
        macro_face.setColorAt(.52, QColor("#151b1d"))
        macro_face.setColorAt(1.0, QColor("#070a0b"))
        painter.setBrush(macro_face)
        painter.setPen(QPen(QColor("#435156"), 1.25))
        painter.drawRoundedRect(macro, 11, 11)
        painter.setPen(QPen(QColor(235, 218, 190, 38), .7))
        painter.drawLine(43, 751, 1365, 751)
        painter.setPen(QPen(QColor(0, 0, 0, 150), 1.0))
        painter.drawLine(43, 758, 1365, 758)

    def _paint_detection_cluster(self, painter):
        """Replace the legacy split cut-outs with one centred instrument bay."""
        # First erase the legacy meter cut-out with chassis-matched aluminium;
        # the visible Tone Shift module below is intentionally much smaller.
        left_cover = QRectF(53, 145, 132, 307)
        cover = QLinearGradient(left_cover.left(), left_cover.top(),
                                left_cover.right(), left_cover.bottom())
        cover.setColorAt(0.0, QColor("#20282b"))
        cover.setColorAt(.48, QColor("#151c1f"))
        cover.setColorAt(1.0, QColor("#293236"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(cover)
        painter.drawRect(left_cover)
        painter.setPen(QPen(QColor(255, 255, 255, 18), .55))
        for y in range(149, 450, 4):
            painter.drawLine(55, y, 183, y)

        tone_plate = QRectF(60, 166, 118, 184)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 88))
        painter.drawRoundedRect(tone_plate.translated(0, 3), 14, 14)
        tone_metal = QLinearGradient(tone_plate.left(), tone_plate.top(),
                                     tone_plate.right(), tone_plate.bottom())
        tone_metal.setColorAt(0.0, QColor("#354044"))
        tone_metal.setColorAt(.24, QColor("#151b1e"))
        tone_metal.setColorAt(.55, QColor("#2c363a"))
        tone_metal.setColorAt(1.0, QColor("#101517"))
        painter.setBrush(tone_metal)
        painter.setPen(QPen(QColor("#56666b"), 1.1))
        painter.drawRoundedRect(tone_plate, 14, 14)
        tone_inset = QRectF(67, 202, 104, 78)
        inset_gradient = QLinearGradient(0, tone_inset.top(), 0, tone_inset.bottom())
        inset_gradient.setColorAt(0.0, QColor("#33444a"))
        inset_gradient.setColorAt(.08, QColor("#171817"))
        inset_gradient.setColorAt(.92, QColor("#070808"))
        inset_gradient.setColorAt(1.0, QColor("#31525a"))
        painter.setBrush(inset_gradient)
        painter.setPen(QPen(QColor("#4c463e"), 1.0))
        painter.drawRoundedRect(tone_inset, 8, 8)

        plate = QRectF(187, 145, 1056, 307)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 85))
        painter.drawRoundedRect(plate.translated(0, 3), 16, 16)
        aluminium = QLinearGradient(plate.left(), plate.top(),
                                    plate.left(), plate.bottom())
        aluminium.setColorAt(0.0, QColor("#303a3e"))
        aluminium.setColorAt(.18, QColor("#171e21"))
        aluminium.setColorAt(.52, QColor("#283236"))
        aluminium.setColorAt(.82, QColor("#12181a"))
        aluminium.setColorAt(1.0, QColor("#242d31"))
        painter.setBrush(aluminium)
        painter.setPen(QPen(QColor("#4f6066"), 1.2))
        painter.drawRoundedRect(plate, 15, 15)
        # Fine brushed grain keeps the plate integrated with the chassis.
        painter.setPen(QPen(QColor(255, 255, 255, 20), .6))
        for y in range(151, 447, 4):
            painter.drawLine(198, y, 1232, y)
        painter.setPen(QPen(QColor(58, 52, 45, 22), .5))
        for y in range(153, 447, 8):
            painter.drawLine(198, y, 1232, y)

        bezel = QRectF(205, 153, 1020, 207)
        painter.setBrush(QColor(0, 0, 0, 155))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bezel.translated(0, 3), 15, 15)
        bezel_metal = QLinearGradient(bezel.left(), bezel.top(),
                                      bezel.right(), bezel.bottom())
        bezel_metal.setColorAt(0.0, QColor("#6a7b80"))
        bezel_metal.setColorAt(.16, QColor("#273034"))
        bezel_metal.setColorAt(.58, QColor("#091012"))
        bezel_metal.setColorAt(1.0, QColor("#2f6770"))
        painter.setBrush(bezel_metal)
        painter.setPen(QPen(QColor("#161513"), 1.1))
        painter.drawRoundedRect(bezel, 15, 15)
        screen = bezel.adjusted(6, 6, -6, -6)
        screen_fill = QRadialGradient(screen.center().x(), screen.center().y() - 22,
                                      screen.width() * .62)
        screen_fill.setColorAt(0.0, QColor("#0a1111"))
        screen_fill.setColorAt(.58, QColor("#040909"))
        screen_fill.setColorAt(1.0, QColor("#010303"))
        painter.setBrush(screen_fill)
        painter.setPen(QPen(QColor("#050606"), 2.0))
        painter.drawRoundedRect(screen, 11, 11)

        tray = QRectF(205, 374, 1020, 69)
        painter.setBrush(QColor(0, 0, 0, 125))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(tray.translated(0, 2), 11, 11)
        tray_gradient = QLinearGradient(0, tray.top(), 0, tray.bottom())
        tray_gradient.setColorAt(0.0, QColor("#3f4c50"))
        tray_gradient.setColorAt(.12, QColor("#1b2225"))
        tray_gradient.setColorAt(.82, QColor("#070a0b"))
        tray_gradient.setColorAt(1.0, QColor("#29464c"))
        painter.setBrush(tray_gradient)
        painter.setPen(QPen(QColor("#41565c"), 1.0))
        painter.drawRoundedRect(tray, 11, 11)

    def _paint_header(self, painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Reconstruct the established THM identity as a compact product
        # wordmark. Expanded geometry, a baseline cut and tracked subtitle
        # make it read as branding rather than two ordinary text labels.
        thm_font = system_font(34, QFont.Weight.Black)
        thm_font.setStretch(118)
        thm_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        painter.setFont(thm_font)
        _draw_panel_ink(painter, QRectF(48, 22, 150, 54),
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                        "THM", QColor("#eee7dc"))
        painter.setPen(QPen(QColor(226, 174, 95, 145), 1.1))
        painter.drawLine(50, 79, 190, 79)
        font = system_font(11, QFont.Weight.DemiBold)
        font.setStretch(106)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.6)
        painter.setFont(font)
        _draw_panel_ink(painter, QRectF(214, 30, 220, 38),
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                        "VOCAL PANEL", QColor(COLORS["amber"]))
        painter.setPen(QPen(QColor(223, 172, 97, 95), .8))
        for index, height in enumerate((4, 9, 14, 7, 12, 5, 10)):
            x = 422 + index * 5
            painter.drawLine(QPointF(x, 55 - height / 2),
                             QPointF(x, 55 + height / 2))

        painter.setPen(QPen(QColor("#5f5548"), .8))
        painter.drawLine(468, 27, 468, 82)

        nav = QRectF(480, 27, 414, 56)
        gradient = QLinearGradient(0, nav.top(), 0, nav.bottom())
        gradient.setColorAt(0, QColor("#202122"))
        gradient.setColorAt(1, QColor("#080909"))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#55504a"), 1.2))
        painter.drawRoundedRect(nav, 8, 8)
        painter.setFont(system_font(9, QFont.Weight.Medium))
        _draw_panel_ink(painter, QRectF(538, 31, 298, 15), Qt.AlignmentFlag.AlignCenter,
                        "VOCAL MODE", QColor("#bdb7ad"))
        painter.setFont(system_font(17, QFont.Weight.DemiBold))
        _draw_panel_ink(painter, QRectF(538, 45, 298, 31), Qt.AlignmentFlag.AlignCenter,
                        self._preset_name, QColor("#efe8dc"))
        for x, glyph in ((488, "◀"), (838, "▶")):
            rect = QRectF(x, 34, 48, 42)
            painter.setBrush(QColor("#151616"))
            painter.setPen(QPen(QColor("#343536"), 1))
            painter.drawRoundedRect(rect, 5, 5)
            painter.setPen(QColor("#c8c5be"))
            painter.setFont(system_font(15))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, glyph)

    def _paint_key_display(self, painter):
        rect = QRectF(KEY_DISPLAY.x, KEY_DISPLAY.y, KEY_DISPLAY.width, KEY_DISPLAY.height)
        # Real captured envelope is optional and stays behind semantic text.
        self._paint_waveform(painter, QRectF(rect.x() + 64, rect.y() + 86,
                                             rect.width() - 128, 92))
        painter.setPen(QPen(QColor("#51c9c3"), 1.2))
        for x, sx in ((rect.left() + 20, 1), (rect.right() - 20, -1)):
            painter.drawLine(QPointF(x, rect.top() + 20), QPointF(x + 18 * sx, rect.top() + 20))
            painter.drawLine(QPointF(x, rect.top() + 20), QPointF(x, rect.top() + 38))
            painter.drawLine(QPointF(x, rect.bottom() - 20), QPointF(x + 18 * sx, rect.bottom() - 20))
            painter.drawLine(QPointF(x, rect.bottom() - 20), QPointF(x, rect.bottom() - 38))
        painter.setPen(QColor("#bcb8b1"))
        # The detector was narrowed to align its retaining bezel with the Tone
        # Shift module.  Keep the complete legend inside the corrected glass
        # instead of allowing wide display tracking to clip both end glyphs.
        font = system_font(10, QFont.Weight.Medium)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.8)
        painter.setFont(font)
        painter.drawText(QRectF(rect.x() + 34, rect.y() + 22, rect.width() - 68, 27),
                         Qt.AlignmentFlag.AlignCenter, "DETECTED KEY & SCALE")
        valid = self._tone.strip().lower() not in {"", "chờ tín hiệu", "waiting", "--", "—"}

        # THM pitch compass: a circular twelve-note instrument, deliberately
        # digital-modern rather than a borrowed vintage VU semicircle.
        center = QPointF(rect.center().x(), rect.center().y() + 20)
        radius = min(rect.height() * .355, 86.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        halo = QRadialGradient(center, radius * 1.35)
        halo.setColorAt(0.0, QColor(30, 211, 202, 25 if valid else 9))
        halo.setColorAt(.62, QColor(9, 75, 82, 12))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(halo)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius * 1.34, radius * 1.34)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(74, 226, 219, 70), 1.1))
        painter.drawEllipse(center, radius, radius)
        painter.setPen(QPen(QColor(222, 191, 142, 45), .8))
        painter.drawEllipse(center, radius - 8, radius - 8)
        for index in range(12):
            angle = (-90.0 + index * 30.0) * pi / 180.0
            outer = QPointF(center.x() + cos(angle) * radius,
                            center.y() + sin(angle) * radius)
            inner = QPointF(center.x() + cos(angle) * (radius - 11),
                            center.y() + sin(angle) * (radius - 11))
            painter.setPen(QPen(QColor(106, 221, 216, 100), 1.25))
            painter.drawLine(inner, outer)

        painter.setFont(system_font(39 if valid else 27, QFont.Weight.DemiBold))
        painter.setPen(QColor(COLORS["mint"]) if valid else QColor("#a9c1c0"))
        painter.drawText(QRectF(center.x() - 210, center.y() - 42, 420, 84),
                         Qt.AlignmentFlag.AlignCenter, self._tone)
        painter.setFont(system_font(7, QFont.Weight.DemiBold))
        status_color = QColor("#67d8b0") if self._autotune_applied else QColor("#918b82")
        _draw_panel_ink(painter, QRectF(rect.x() + 40, rect.bottom() - 46,
                                       rect.width() - 80, 14),
                        Qt.AlignmentFlag.AlignCenter, self._autotune_status, status_color)
        if valid:
            note_token = self._tone.strip().split()[0].upper().replace("♯", "#").replace("♭", "B")
            pitch_classes = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
                             "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7,
                             "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}
            pitch_index = pitch_classes.get(note_token, 6)
            marker_angle = (-90.0 + pitch_index * 30.0) * pi / 180.0
            marker = QPointF(center.x() + cos(marker_angle) * radius,
                             center.y() + sin(marker_angle) * radius)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(76, 239, 229, 62))
            painter.drawEllipse(QRectF(marker.x() - 8, marker.y() - 8, 16, 16))
            painter.setBrush(QColor("#bafff9"))
            painter.drawEllipse(QRectF(marker.x() - 3, marker.y() - 3, 6, 6))
            glow_y = rect.bottom() - 18
            glow = QLinearGradient(rect.left() + 120, glow_y, rect.right() - 120, glow_y)
            glow.setColorAt(0, QColor(31, 218, 208, 0))
            glow.setColorAt(.5, QColor(31, 218, 208, 170))
            glow.setColorAt(1, QColor(31, 218, 208, 0))
            painter.setPen(QPen(QBrush(glow), 2))
            painter.drawLine(QPointF(rect.left() + 120, glow_y),
                             QPointF(rect.right() - 120, glow_y))

    def _paint_waveform(self, painter, rect):
        if not self._waveform or max(self._waveform, default=0.0) <= .008:
            return
        count = len(self._waveform)
        def envelope_path(direction):
            points = [QPointF(rect.left() + rect.width() * index / max(1, count - 1),
                              rect.center().y() + direction * magnitude * rect.height() * .40)
                      for index, magnitude in enumerate(self._waveform)]
            result = QPainterPath(points[0])
            for index in range(1, len(points)):
                previous, point = points[index - 1], points[index]
                midpoint = QPointF((previous.x() + point.x()) * .5,
                                   (previous.y() + point.y()) * .5)
                result.quadTo(previous, midpoint)
            result.lineTo(points[-1])
            return result

        # The extraction output is absolute amplitude, reflected only for the
        # display. Quadratic joins remove the bucket-to-bucket stair-step.
        path = envelope_path(-1.0)
        painter.setPen(QPen(QColor(112, 220, 223, 185), 1.25))
        painter.drawPath(path)
        mirrored = envelope_path(1.0)
        painter.setPen(QPen(QColor("#ff9865"), 1.0))
        painter.drawPath(mirrored)

    def _paint_spectrum(self, painter, rect):
        """Render only analysis values derived from the current PCM frame."""
        if not self._spectrum or max(self._spectrum, default=0.0) <= .002:
            # Deliberate instrument standby state: a real zero line and source
            # identity, never a fabricated waveform or spectrum.
            baseline = rect.center().y() + 8
            line = QLinearGradient(rect.left(), baseline, rect.right(), baseline)
            line.setColorAt(0.0, QColor(120, 137, 139, 0))
            line.setColorAt(.18, QColor(120, 137, 139, 42))
            line.setColorAt(.50, QColor(141, 157, 158, 72))
            line.setColorAt(.82, QColor(120, 137, 139, 42))
            line.setColorAt(1.0, QColor(120, 137, 139, 0))
            painter.setPen(QPen(QBrush(line), 1.0))
            painter.drawLine(QPointF(rect.left() + 34, baseline),
                             QPointF(rect.right() - 34, baseline))
            for x in (rect.left() + 34, rect.center().x(), rect.right() - 34):
                painter.setPen(QPen(QColor(199, 211, 212, 72), 1.0))
                painter.drawLine(QPointF(x, baseline - 4), QPointF(x, baseline + 4))
            painter.setPen(QColor("#8f9a9b"))
            painter.setFont(system_font(9, QFont.Weight.Medium))
            source = self._analysis_source_name.upper().replace(" POST-FX", " · POST-FX")
            painter.drawText(QRectF(rect.left(), rect.center().y() - 25, rect.width(), 20),
                             Qt.AlignmentFlag.AlignCenter, source)
            painter.setPen(QColor("#697375"))
            painter.setFont(system_font(8, QFont.Weight.Medium))
            painter.drawText(QRectF(rect.left(), rect.center().y() + 17, rect.width(), 18),
                             Qt.AlignmentFlag.AlignCenter, "CHỜ TÍN HIỆU")
            return
        path = QPainterPath()
        count = len(self._spectrum)
        for index, magnitude in enumerate(self._spectrum):
            x = rect.left() + rect.width() * index / max(1, count - 1)
            y = rect.bottom() - magnitude * rect.height() * .86
            if index == 0:
                path.moveTo(x, rect.bottom())
                path.lineTo(x, y)
            else:
                path.lineTo(x, y)
        path.lineTo(rect.right(), rect.bottom())
        path.closeSubpath()
        painter.setPen(QPen(QColor(COLORS["amber_bright"]), 1.3))
        painter.setBrush(QColor(24, 200, 193, 40))
        painter.drawPath(path)

    def _paint_eq_nodes(self, painter):
        for band, frequency, gain in self._eq_nodes():
            x, y = self._eq_node_position(frequency, gain)
            band_id = str(band.get("bandId", ""))
            active = bool(band_id) and band_id in (
                self._eq_selected_band, self._eq_hover_band)
            if active:
                painter.setPen(QPen(QColor(28, 232, 223, 75), 5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QRectF(x - 13, y - 13, 26, 26))
            painter.setPen(QPen(QColor("#d4fffb"), 2.4 if active else 2))
            painter.setBrush(QColor(COLORS["amber_bright"]))
            painter.drawEllipse(QRectF(x - 9, y - 9, 18, 18))
            painter.setPen(QColor("#17130d"))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(x - 9, y - 9, 18, 18), Qt.AlignmentFlag.AlignCenter,
                             str(band.get("index", "")))
            if active:
                model = self._eq_surface.get("parameterModel", {})
                f_min = float(model.get("frequencyMinHz", 10))
                f_max = float(model.get("frequencyMaxHz", 30000))
                g_min = float(model.get("gainMinDb", -30))
                g_max = float(model.get("gainMaxDb", 30))
                f_norm = float(frequency.get("normalizedValue", .5))
                g_norm = float(gain.get("normalizedValue", .5))
                hz = f_min * exp(log(f_max / f_min) * f_norm)
                db = g_min + (g_max - g_min) * g_norm
                q = band.get("q")
                q_text = str(q.get("displayValue", "")) if isinstance(q, dict) else ""
                label = f"{hz / 1000:.2f} kHz" if hz >= 1000 else f"{hz:.0f} Hz"
                label += f"   {db:+.1f} dB" + (f"   Q {q_text}" if q_text else "")
                box = QRectF(max(EQ_GRAPH.x, min(x - 78,
                                                 EQ_GRAPH.x + EQ_GRAPH.width - 156)),
                             max(EQ_GRAPH.y + 4, y - 43), 156, 25)
                painter.setPen(QPen(QColor("#596563"), 1))
                painter.setBrush(QColor(5, 12, 13, 235))
                painter.drawRoundedRect(box, 5, 5)
                painter.setPen(QColor("#d8f8f4"))
                painter.setFont(system_font(8, QFont.Weight.DemiBold))
                painter.drawText(box, Qt.AlignmentFlag.AlignCenter, label)

    def _paint_eq_curve(self, painter):
        """Connect only real writable EQ band positions from the descriptor."""
        points = sorted((self._eq_node_position(frequency, gain)
                         for _band, frequency, gain in self._eq_nodes()), key=lambda item: item[0])
        if not points:
            return
        center_y = EQ_GRAPH.y + EQ_GRAPH.height / 2
        extended = [(EQ_GRAPH.x, center_y), *points,
                    (EQ_GRAPH.x + EQ_GRAPH.width, center_y)]
        path = QPainterPath()
        path.moveTo(*extended[0])
        for index in range(1, len(extended)):
            previous = extended[index - 1]
            current = extended[index]
            midpoint = (previous[0] + current[0]) / 2
            path.cubicTo(midpoint, previous[1], midpoint, current[1], current[0], current[1])
        painter.setPen(QPen(QColor(COLORS["amber_bright"]), 2.0,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _paint_horizontal_meter(self, painter, rect, level, active):
        """Draw two compact display-only LED rows from the real output level."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        shell = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        shell.setColorAt(0.0, QColor("#050606"))
        shell.setColorAt(.52, QColor("#141717"))
        shell.setColorAt(1.0, QColor("#030404"))
        painter.setBrush(shell)
        painter.setPen(QPen(QColor("#353a39"), 1.0))
        painter.drawRoundedRect(rect, 5, 5)
        steps = 24 if rect.width() < 230 else 30
        lit = round((max(0.0, min(1.0, float(level))) if active else 0.0) * steps)
        left = rect.left() + 10
        usable = rect.width() - 20
        pitch = usable / steps
        cell_width = max(2.0, pitch - 2.1)
        row_height = 10 if rect.height() > 70 else 8
        centre_y = rect.center().y()
        for row_y in (centre_y - row_height - 4, centre_y + 4):
            for index in range(steps):
                x = left + index * pitch
                if index >= lit:
                    colour = QColor(54, 61, 58, 115)
                elif index < round(steps * .70):
                    colour = QColor("#6ed486")
                elif index < round(steps * .90):
                    colour = QColor("#e8c45e")
                else:
                    colour = QColor(COLORS["amber_bright"])
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(colour)
                painter.drawRoundedRect(QRectF(x, row_y, cell_width, row_height), 1, 1)
        if rect.height() > 70:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setFont(system_font(7, QFont.Weight.Medium))
            painter.setPen(QColor("#78807d"))
            for fraction, label in ((0.0, "−48"), (.5, "−18"), (1.0, "0")):
                x = left + usable * fraction
                painter.drawText(QRectF(x - 16, rect.bottom() - 23, 32, 14),
                                 Qt.AlignmentFlag.AlignCenter, label)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    def _paint_meter(self, painter, rect, level, active):
        """Draw a fine, DPI-independent 48-step stereo meter.

        The DAW publishes one bounded display-rate level today, therefore both
        bars intentionally show that same real value.  No synthetic channel
        movement is introduced.  Smaller vector cells remain crisp when the
        window or OS display scale changes.
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        housing = rect.adjusted(2, 0, -2, 0)
        shell = QLinearGradient(housing.left(), housing.top(), housing.right(), housing.top())
        shell.setColorAt(0.0, QColor("#766d60"))
        shell.setColorAt(.08, QColor("#151717"))
        shell.setColorAt(.50, QColor("#050707"))
        shell.setColorAt(.92, QColor("#171918"))
        shell.setColorAt(1.0, QColor("#756b5d"))
        painter.setBrush(shell)
        painter.setPen(QPen(QColor("#242321"), 1.0))
        painter.drawRoundedRect(housing, 4, 4)

        steps = 48
        normalised = max(0.0, min(1.0, float(level))) if active else 0.0
        lit = round(normalised * steps)
        top, bottom = housing.top() + 9, housing.bottom() - 9
        available = bottom - top
        pitch = available / steps
        cell_height = max(1.35, pitch - 1.55)
        bar_width = 9.0
        gap = 6.0
        total_width = bar_width * 2 + gap
        first_x = housing.center().x() - total_width / 2
        for channel_x in (first_x, first_x + bar_width + gap):
            for index in range(steps):
                y = bottom - (index + 1) * pitch + (pitch - cell_height) * .5
                if index >= lit:
                    colour = QColor(63, 70, 65, 112)
                elif index < 32:
                    colour = QColor("#71d27d")
                elif index < 42:
                    colour = QColor("#e8c45e")
                else:
                    colour = QColor("#ef785e")
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(colour)
                painter.drawRect(QRectF(channel_x, y, bar_width, cell_height))
                if index < lit:
                    painter.setPen(QPen(QColor(255, 247, 216, 62), .55))
                    painter.drawLine(QPointF(channel_x + 1, y),
                                     QPointF(channel_x + bar_width - 1, y))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
