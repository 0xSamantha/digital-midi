"""Charcoal and orange desktop instrument; camera diagnostics stay separate."""
from pathlib import Path
import time
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QEvent
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QPushButton, QSlider, QLabel,
                               QVBoxLayout, QDialog, QCheckBox)
from monitor import PerformanceMonitor
from controller import Notes, Pinch, note_name
from layout import WIDTH, HEIGHT, zones, hit, PAD_NOTES

ORANGE, WHITE, MUTED = '#FF681F', '#F2EFE7', '#B9B6AE'
KEYS = 'awsedftgyhujkol;'


def load_fonts():
    for path in (Path(__file__).parent / 'fonts').glob('*'):
        if path.suffix.lower() in ('.otf', '.ttf', '.ttc'):
            QFontDatabase.addApplicationFont(str(path))
    available = QFontDatabase.families()
    display = next((f for f in available if 'futura' in f.lower() and 'display' in f.lower()), None)
    return display or ('Futura' if 'Futura' in available else 'Arial'), display is not None


class VelocitySlider(QSlider):
    """Native slider behavior and accessibility with the instrument's linework."""
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = self.height() / 2
        x = 8 + (self.width() - 16) * (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        p.setPen(QPen(QColor('#77746E'), 2))
        p.drawLine(QPointF(8, y), QPointF(self.width() - 8, y))
        p.setPen(QPen(QColor(ORANGE), 2))
        p.drawLine(QPointF(8, y), QPointF(x, y))
        p.setPen(QPen(QColor('#141414'), 1))
        p.setBrush(QColor(WHITE))
        p.drawRect(QRectF(x - 7, y - 8, 14, 16))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(ORANGE), 1))
            p.drawRect(QRectF(1, 1, self.width() - 2, self.height() - 2))
        p.end()


class Diagnostics(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Digital Midi Keyboard — Diagnostics')
        self.setMinimumWidth(660)
        self.setStyleSheet('background:#191919; color:#F2EFE7; font:13px Helvetica;')
        layout = QVBoxLayout(self)
        self.status = QLabel('Waiting for camera frames. Diagnostics do not affect MIDI routing.')
        self.status.setWordWrap(True)
        self.image = QLabel('CAMERA PREVIEW\nCamera is disabled in mouse-only mode.')
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(640, 360)
        self.font_status = QLabel()
        self.audio_status = QLabel('AUDIO / Waiting for playback status')
        layout.addWidget(self.status)
        layout.addWidget(self.image)
        layout.addWidget(self.font_status)
        layout.addWidget(self.audio_status)


class InstrumentWindow(QWidget):
    def __init__(self, send, tracker=None, mouse_only=False, route='LOCAL PREVIEW', audio=True, scope_source=None):
        super().__init__()
        self.setWindowTitle('Digital Midi Keyboard')
        self.resize(WIDTH, HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._face_key = None
        self._face_cache = None
        self.setMinimumSize(1000, 672)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Digital Midi Keyboard playing surface')
        self.setAccessibleDescription('Play notes using A W S E D F T G Y H U J K O L semicolon. Drum pads use 1 through 8. Tab moves through controls.')
        self.display_font, self.exact_font = load_fonts()
        self.notes = Notes(send)
        self.tracker = tracker
        self.mouse_only = mouse_only
        self.route = route
        self.audio_available = audio
        self.octave, self.velocity, self.paused = 4, 100, False
        self.regions = zones()
        self.gestures = {name: Pinch() for name in ('Left', 'Right')}
        self.cursors = {}
        self.mouse_down = False
        self.input_active = True
        self.last_frame = time.monotonic()
        self.tracking_error = ''
        self.scale, self.offset = 1., QPointF()
        self.controls = []
        self.scope_source = scope_source
        self.last_scope = 0.
        self.monitor = PerformanceMonitor(self)
        self.monitor.audio_enabled = audio
        self.place(self.monitor, (64, 236, 360, 156))
        self.diagnostics = Diagnostics(self)
        self.diagnostics.font_status.setText('TITLE FONT: ' + ('FUTURA DISPLAY' if self.exact_font else 'FUTURA FALLBACK — add a licensed Futura Display font to fonts/'))
        self.setStyleSheet('''
            QPushButton { background:#292929; color:#F2EFE7; border:1px solid #77746E;
                          border-radius:0px; font:12px Helvetica; padding:0px; }
            QPushButton:hover { border-color:#FF681F; background:#35302C; }
            QPushButton:pressed, QPushButton:checked { background:#FF681F; color:#141414; border-color:#FF681F; }
            QPushButton:focus { border:2px solid #F2EFE7; }
            QCheckBox { color:#F2EFE7; font:12px Helvetica; spacing:8px; }
            QCheckBox::indicator { width:14px; height:14px; border:1px solid #B9B6AE; background:#191919; }
            QCheckBox::indicator:checked { background:#FF681F; }
            QCheckBox:focus { outline:1px solid #F2EFE7; }
        ''')
        self.camera_button = self.button('CAMERA', (64, 206, 174, 24), lambda: self.set_monitor_mode('camera'))
        self.scope_button = self.button('SCOPE  /  V', (250, 206, 174, 24), lambda: self.set_monitor_mode('scope'))
        self.camera_button.setCheckable(True)
        self.scope_button.setCheckable(True)
        self.set_monitor_mode('camera' if tracker else 'scope')
        self.pause_button = self.button('PAUSE  /  SPACE', (1078, 48, 170, 38), self.toggle_pause)
        self.pause_button.setCheckable(True)
        self.button('DIAGNOSTICS  /  F2', (1078, 94, 170, 24), self.toggle_diagnostics)
        self.button('ALL NOTES OFF  /  P', (460, 296, 180, 38), self.panic)
        self.button('−', (393, 427, 48, 36), lambda: self.change_octave(-1), 'Lower keyboard octave')
        self.button('+', (592, 427, 48, 36), lambda: self.change_octave(1), 'Raise keyboard octave')
        self.slider = VelocitySlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(1, 127)
        self.slider.setValue(100)
        self.slider.setAccessibleName('Note velocity')
        self.slider.setToolTip('Fixed note-on velocity. Minus / plus keys also adjust this value.')
        self.slider.valueChanged.connect(self.set_velocity)
        self.place(self.slider, (64, 430, 240, 32))
        self.preview = QCheckBox('LOCAL SOUND', self)
        self.preview.setChecked(audio)
        self.preview.setEnabled(audio)
        self.preview.toggled.connect(self.monitor.set_audio_enabled)
        self.preview.setAccessibleName('Enable local sound preview')
        self.place(self.preview, (460, 354, 180, 28))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(16)
        QApplication.instance().applicationStateChanged.connect(self.application_state)
        QApplication.instance().installEventFilter(self)

    def button(self, label, rect, callback, accessible=None):
        button = QPushButton(label, self)
        button.setAccessibleName(accessible or label)
        button.clicked.connect(lambda checked=False: callback())
        self.place(button, rect)
        return button

    def place(self, widget, rect):
        self.controls.append((widget, rect))
        widget.setGeometry(*rect)

    def set_velocity(self, value):
        self.velocity = value
        self.update()

    def resizeEvent(self, event):
        self.scale = min(self.width() / WIDTH, self.height() / HEIGHT)
        self.offset = QPointF((self.width() - WIDTH * self.scale) / 2, (self.height() - HEIGHT * self.scale) / 2)
        for widget, (x, y, w, h) in self.controls:
            widget.setGeometry(round(self.offset.x() + x * self.scale), round(self.offset.y() + y * self.scale),
                               round(w * self.scale), round(h * self.scale))
        super().resizeEvent(event)

    def logical(self, point):
        return (point.x() - self.offset.x()) / self.scale, (point.y() - self.offset.y()) / self.scale

    def panic(self):
        self.notes.panic()
        self.mouse_down = False
        for gesture in self.gestures.values():
            gesture.update(None)
        self.cursors.clear()
        self.update()

    def toggle_pause(self):
        self.panic()
        self.paused = not self.paused
        self.pause_button.setChecked(self.paused)
        self.pause_button.setText('RESUME  /  SPACE' if self.paused else 'PAUSE  /  SPACE')

    def change_octave(self, delta):
        self.panic()
        self.octave = max(0, min(7, self.octave + delta))
        self.regions = zones(self.octave)

    def toggle_diagnostics(self):
        self.diagnostics.setVisible(not self.diagnostics.isVisible())
        if self.tracker:
            self.tracker.debug.set() if self.diagnostics.isVisible() else self.tracker.debug.clear()

    def set_monitor_mode(self, mode):
        if mode not in ('camera', 'scope'):
            return
        if mode == 'camera' and self.monitor.mode != 'camera':
            self.monitor.image = None
        self.monitor.mode = mode
        self.camera_button.setChecked(mode == 'camera')
        self.scope_button.setChecked(mode == 'scope')
        if self.tracker:
            self.tracker.preview.set() if mode == 'camera' else self.tracker.preview.clear()
            self.monitor.message = 'STARTING CAMERA…' if not self.tracking_error else 'CAMERA UNAVAILABLE / SEE DIAGNOSTICS'
        else:
            self.monitor.message = 'CAMERA DISABLED / USE SCOPE'
        self.monitor.update()

    def application_state(self, state):
        self.input_active = state == Qt.ApplicationState.ApplicationActive
        if not self.input_active:
            self.panic()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyRelease and not event.isAutoRepeat():
            self.notes.set('key:' + str(event.key()), None)
            self.update()
        return super().eventFilter(watched, event)

    def update_hands(self, found, aspect):
        previous = (dict(self.cursors), dict(self.notes.sources))
        for name, gesture in self.gestures.items():
            position, down = gesture.update(found.get(name) if not self.paused and self.input_active else None, aspect)
            zone = None
            self.cursors.pop(name, None)
            if position:
                x, y = position[0] * WIDTH, position[1] * HEIGHT
                self.cursors[name] = x, y, down
                zone = hit(self.regions, x, y) if down else None
            self.notes.set(name, (zone.channel, zone.note) if zone else None, self.velocity)
        if previous != (self.cursors, self.notes.sources):
            self.update()

    def poll(self):
        now = time.monotonic()
        if self.scope_source and self.monitor.mode == 'scope' and now - self.last_scope >= 1 / 30:
            self.monitor.set_audio(self.scope_source())
            self.last_scope = now
        if not self.tracker:
            return
        if not self.diagnostics.isVisible():
            self.tracker.debug.clear()
        sample, error = self.tracker.take()
        if error and error != self.tracking_error:
            self.tracking_error = error
            self.monitor.image = None
            self.monitor.message = 'CAMERA UNAVAILABLE / SEE DIAGNOSTICS'
            self.monitor.update()
            self.panic()
            self.diagnostics.status.setText(error)
            self.diagnostics.show()
        if sample:
            found, aspect, clean_image, image, fps, timestamp = sample
            self.last_frame = timestamp
            if clean_image is not None and now - timestamp < .4:
                self.monitor.image = clean_image
                if self.monitor.mode == 'camera':
                    self.monitor.update()
            # Discard stale work after sleep, a blocked UI event, or a camera stall.
            self.update_hands(found if time.monotonic() - timestamp < .4 else {}, aspect)
            if not error:
                self.diagnostics.status.setText(f'{fps:.1f} FPS · {len(found)} HAND(S) · FaceTime preferred, unless overridden')
            if image is not None and self.diagnostics.isVisible():
                self.diagnostics.image.setPixmap(QPixmap.fromImage(image))
        elif now - self.last_frame > .4:
            if self.cursors:
                self.update_hands({}, 4 / 3)
            if self.monitor.image is not None:
                self.monitor.image = None
                self.monitor.message = 'WAITING FOR CAMERA…'
                self.monitor.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self.mouse_down = True
            self.play_mouse(event.position())

    def mouseMoveEvent(self, event):
        if self.mouse_down:
            self.play_mouse(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_down = False
            self.notes.set('mouse', None)
            self.update()

    def play_mouse(self, position):
        zone = hit(self.regions, *self.logical(position)) if not self.paused else None
        self.notes.set('mouse', (zone.channel, zone.note) if zone else None, self.velocity)
        self.update()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key, text = event.key(), event.text().lower()
        if key == Qt.Key.Key_Space:
            self.toggle_pause()
        elif text == 'p':
            self.panic()
        elif text == 'd' and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.toggle_diagnostics()
        elif text == 'v':
            self.set_monitor_mode('scope' if self.monitor.mode == 'camera' else 'camera')
        elif key == Qt.Key.Key_F2:
            self.toggle_diagnostics()
        elif text in ('[', ']'):
            self.change_octave(1 if text == ']' else -1)
        elif text in ('-', '=', '+'):
            self.slider.setValue(self.velocity + (-8 if text == '-' else 8))
        elif key == Qt.Key.Key_Escape:
            self.panic()
        elif not self.paused and text in KEYS and text:
            self.notes.set('key:' + str(key), (0, 12 * (self.octave + 1) + KEYS.index(text)), self.velocity)
        elif not self.paused and text in '12345678' and text:
            self.notes.set('key:' + str(key), (9, PAD_NOTES[int(text) - 1]), self.velocity)
        else:
            super().keyPressEvent(event)
        self.update()

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():
            self.notes.set('key:' + str(event.key()), None)
            self.update()
        super().keyReleaseEvent(event)

    def closeEvent(self, event):
        self.panic()
        if self.tracker and self.tracker.isRunning():
            self.tracker.requestInterruption()
            if not self.tracker.wait(100):
                event.ignore()
                QTimer.singleShot(100, self.close)
                return
        self.timer.stop()
        self.diagnostics.close()
        event.accept()

    def paintEvent(self, event):
        # Cursor motion should composite a cached face, not rebuild dozens of fonts,
        # labels, rules, keys, and pad rectangles for every tracking frame.
        ratio = max(1., self.devicePixelRatioF() * self.scale)
        key = (self.octave, self.velocity, self.paused, self.route,
               frozenset(self.notes.sources.values()), self.mouse_only,
               bool(self.tracking_error), len(self.cursors), round(ratio, 3))
        if key != self._face_key:
            cache = QPixmap(round(WIDTH * ratio), round(HEIGHT * ratio))
            cache.setDevicePixelRatio(ratio)
            cache.fill(QColor('#141414'))
            face = QPainter(cache)
            face.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.paint_face(face)
            face.end()
            self._face_cache, self._face_key = cache, key
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#141414'))
        p.translate(self.offset)
        p.scale(self.scale, self.scale)
        p.drawPixmap(0, 0, self._face_cache)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for name, (x, y, down) in self.cursors.items():
            p.setBrush(QColor(ORANGE) if down else Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(WHITE), 2))
            p.drawEllipse(QPointF(x, y), 12, 12)
            font = QFont('Helvetica'); font.setPixelSize(11); p.setFont(font)
            p.drawText(QPointF(min(x + 17, 1228), max(13, y - 8)), 'L' if name == 'Left' else 'R')
        p.end()

    def paint_face(self, p):

        def rect(x, y, w, h, fill, stroke=None):
            p.setBrush(QColor(fill))
            p.setPen(QPen(QColor(stroke), 1) if stroke else Qt.PenStyle.NoPen)
            p.drawRect(QRectF(x, y, w, h))

        def label(value, x, y, size=12, color=WHITE, title=False, width=1200):
            font = QFont(self.display_font if title else 'Helvetica')
            font.setPixelSize(size)
            if title:
                font.setWeight(QFont.Weight.ExtraBold)
                if not self.exact_font and self.display_font == 'Futura':
                    font.setStyleName('Condensed ExtraBold')
            else:
                font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.1)
            p.setFont(font)
            p.setPen(QColor(color))
            p.drawText(QRectF(x, y, width, size * 1.6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)

        def line(x, y, w, color=WHITE):
            p.setPen(QPen(QColor(color), .7))
            p.drawLine(QPointF(x, y), QPointF(x + w, y))

        def bar(number, name, x, y, w, tail):
            rect(x, y, w, 27, ORANGE)
            label(number + '  /  ' + name, x + 10, y + 2, 12, '#141414')
            # Tail is right aligned without shifting the section label.
            p.drawText(QRectF(x + w - 230, y + 3, 218, 22), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, tail)

        rect(16, 16, 1248, 828, '#222222')
        label('DIGITAL MIDI KEYBOARD', 32, 32, 47, title=True)
        label('A HANDS-ON INSTRUMENT. WITHOUT THE HARDWARE.', 34, 96, 11, MUTED)
        # Original panel motif: ascending orange signal blocks and a thin trajectory.
        for i, height in enumerate((8, 14, 22, 30)):
            rect(738 + i * 17, 88 - height, 11, height, ORANGE)
        label('DK—01', 822, 54, 16, WHITE, True)
        label('GESTURE / SIGNAL', 822, 83, 9, MUTED)
        line(32, 131, 1216)
        bar('01', 'PERFORMANCE', 32, 158, 636, 'CH 01 / MELODY')
        bar('02', 'DRUM PADS', 704, 158, 544, 'CH 10 / PERCUSSION')
        rect(32, 194, 636, 304, '#191919')
        rect(704, 194, 544, 304, '#191919')
        # A recessed monitor bezel, with restrained instrument-panel markings.
        rect(56, 232, 376, 164, '#101010', '#45453E')
        label('NOW PLAYING', 460, 210, 10, MUTED)
        active = set(self.notes.sources.values())
        names = [note_name(note) for channel, note in sorted(active) if channel == 0]
        pad_names = [z.label.upper() for z in self.regions if z.channel == 9 and (9, z.note) in active]
        readout = ' + '.join(names) if names else (pad_names[0] if pad_names else 'READY')
        label(readout if len(readout) <= 15 else readout[:14] + '…', 456, 234, 29 if len(readout) < 11 else 18, ORANGE if active else WHITE, True, 192)
        label('PAUSED' if self.paused else ('PINCH / CLICK / PLAY' if not active else 'NOTE ON / ' + str(len(active)) + ' VOICES'), 460, 277, 9, MUTED)
        route = self.route.upper()
        label('OUT / ' + (route if len(route) < 35 else route[:31] + '…'), 64, 395, 9, MUTED, width=570)
        label(f'VELOCITY  /  {self.velocity:03d}', 64, 410, 11, MUTED)
        label('OCTAVE', 393, 410, 11, MUTED)
        label(f'C{self.octave} — C{self.octave + 2}', 459, 428, 16)
        label('FIXED NOTE-ON VELOCITY', 64, 469, 9, MUTED)
        label('[ / ] TO TRANSPOSE', 393, 469, 9, MUTED)
        for index, z in enumerate(self.regions):
            if z.channel != 9:
                continue
            x, y, w, h = z.rect
            playing = (z.channel, z.note) in active
            fill = ORANGE if playing else ('#493A30', '#493B34', '#413B35', '#383A37')[index // 4]
            rect(x, y, w, h, fill, ORANGE if playing else '#807268')
            label(f'{index + 1:02d}', x + 9, y + 4, 10, '#141414' if playing else MUTED)
            label(z.label.upper(), x + 9, y + 33, 10, '#141414' if playing else WHITE, width=w - 12)
            rect(x + w - 16, y + 10, 6, 6, WHITE if playing else '#807268')
        bar('03', 'KEYBOARD', 32, 530, 1216, '25 KEYS / TWO OCTAVES')
        label('MELODY', 32, 565, 9, MUTED)
        label('A W S E D F T G Y H U J K O L  /  COMPUTER KEYS', 738, 565, 9, MUTED)
        for z in self.regions:
            if z.channel != 0:
                continue
            x, y, w, h = z.rect
            playing = (z.channel, z.note) in active
            rect(x, y, w, h, ORANGE if playing else ('#111111' if z.black else '#E5E1D6'))
            if not z.black:
                rect(x, y + h - 5, w, 5, '#B8B3A9' if not playing else '#B53E08')
            else:
                line(x + 4, y + 4, w - 8, '#595651')
            # LED-like note strip and note label supplement the fill color.
            rect(x + 5, y + 6, w - 10, 3, ORANGE if playing else ('#393632' if z.black else '#B9B6AE'))
            if playing:
                rect(x + w / 2 - 3, y + h - 38, 6, 6, WHITE if z.black else '#141414')
            label(z.label, x + 10, y + h - 29, 11, WHITE if z.black and not playing else '#24221F', width=w)
        line(32, 799, 1216, '#77746E')
        label('OPEN TO ARM. AIM YOUR HAND. PINCH TO PLAY.', 32, 813, 10, MUTED)
        status = 'PAUSED' if self.paused else ('MOUSE + COMPUTER KEYS' if self.mouse_only else ('CAMERA OFFLINE / OPEN DIAGNOSTICS' if self.tracking_error else 'HAND TRACKING / ' + str(len(self.cursors)) + ' HANDS'))
        label(status, 768, 813, 10, ORANGE if self.tracking_error else WHITE)
