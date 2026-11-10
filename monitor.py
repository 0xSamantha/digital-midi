"""Clean self-view and mint-phosphor phase scope for the performance panel."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QWidget
from visualizer import phase_trace


def camera_crop(source_width, source_height, target_width, target_height):
    """Centered cover crop, preserving proportions while filling the monitor."""
    scale = max(target_width / source_width, target_height / source_height)
    width, height = target_width / scale, target_height / scale
    return QRectF((source_width - width) / 2, (source_height - height) / 2, width, height)


class PerformanceMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = 'scope'
        self.audio_enabled = True
        self.image = None
        self.message = 'CAMERA DISABLED / USE SCOPE'
        self.trace, self.peak = phase_trace([])
        self.path = QPainterPath()
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAccessibleName('Performance monitor')
        self.setAccessibleDescription('Switch between a mirrored camera self-view and an audio-driven phase scope.')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_audio_enabled(self, enabled):
        self.audio_enabled = enabled
        self.update()

    def set_audio(self, samples):
        self.trace, self.peak = phase_trace(samples)
        self.path = QPainterPath()
        if len(self.trace):
            self.path.moveTo(float(self.trace[0, 0]), float(self.trace[0, 1]))
            for x, y in self.trace[1:]:
                self.path.lineTo(float(x), float(y))
        if self.mode == 'scope':
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#080F0D'))
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setClipRect(bounds)
        if self.mode == 'camera':
            if self.image is not None:
                # Center-crop directly from the source: fill the screen without bars,
                # distortion, or allocating another scaled image on every repaint.
                source = camera_crop(self.image.width(), self.image.height(), bounds.width(), bounds.height())
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                p.drawImage(bounds, self.image, source)
            else:
                p.setPen(QColor('#B9B6AE'))
                font = QFont('Helvetica'); font.setPixelSize(11); p.setFont(font)
                p.drawText(bounds.adjusted(12, 12, -12, -12), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)
        else:
            cx, cy = self.width() / 2, self.height() / 2
            radius = min(self.width() * .45, self.height() * .44)
            p.setPen(QPen(QColor('#183029'), .6))
            for step in range(-4, 5):
                x, y = cx + step * radius / 4, cy + step * radius / 4
                p.drawLine(QPointF(x, cy - radius), QPointF(x, cy + radius))
                p.drawLine(QPointF(cx - radius, y), QPointF(cx + radius, y))
            p.setPen(QPen(QColor('#356050'), .7))
            p.drawLine(QPointF(cx - radius, cy), QPointF(cx + radius, cy))
            p.drawLine(QPointF(cx, cy - radius), QPointF(cx, cy + radius))
            if len(self.trace):
                path = QTransform(radius, 0, 0, -radius, cx, cy).map(self.path)
                for width, color in ((7, '#154835'), (3, '#429F7F'), (1, '#BEFFE7')):
                    p.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                    p.drawPath(path)
            else:
                p.setPen(QPen(QColor('#75AD94'), 1))
                p.drawLine(QPointF(cx - 5, cy), QPointF(cx + 5, cy))
            p.setPen(QPen(QColor(0, 0, 0, 35), 1))
            for y in range(0, self.height(), 4):
                p.drawLine(0, y, self.width(), y)
            font = QFont('Helvetica'); font.setPixelSize(9); p.setFont(font)
            p.setPen(QColor('#80B09A'))
            p.drawText(9, 15, 'PHASE / LOCAL AUDIO')
            if not len(self.trace):
                p.drawText(9, self.height() - 9, 'PLAY TO EXCITE' if self.audio_enabled else 'LOCAL SOUND IS OFF')
        p.setClipping(False)
        p.setPen(QPen(QColor('#77746E'), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(bounds)
        p.end()
