"""Low-latency hand tracking with newest-frame capture and result mailboxes."""
import threading
import time
from PySide6.QtCore import QThread
from PySide6.QtGui import QImage


class LatestCamera:
    """Drain capture independently; inference consumes the newest frame only."""
    def __init__(self, cap):
        self.cap = cap
        self.condition = threading.Condition()
        self.latest = None
        self.error = ''
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run, name='camera-capture', daemon=True)

    def start(self):
        self.thread.start()

    def publish(self, frame, timestamp):
        with self.condition:
            self.latest = (frame, timestamp)
            self.condition.notify()

    def take(self, timeout=.2):
        with self.condition:
            self.condition.wait_for(lambda: self.latest is not None or self.error or self.stopped.is_set(), timeout)
            if self.error:
                raise RuntimeError(self.error)
            latest, self.latest = self.latest, None
            return latest

    def run(self):
        try:
            while not self.stopped.is_set():
                ok, frame = self.cap.read()
                if not ok:
                    raise RuntimeError('Camera disconnected. Reconnect and restart, or use --no-camera.')
                self.publish(frame, time.monotonic())
        except Exception as exc:
            with self.condition:
                self.error = str(exc)
                self.condition.notify_all()
        finally:
            self.cap.release()

    def close(self):
        self.stopped.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread.is_alive():
            self.thread.join(timeout=1)


def qt_image(rgb):
    height, width = rgb.shape[:2]
    return QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()


class Tracker(QThread):
    def __init__(self, device=None):
        super().__init__()
        self.device = device
        self.debug = threading.Event()
        self.preview = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.error = ''

    def take(self):
        with self.lock:
            result, self.latest = self.latest, None
            return result, self.error

    def run(self):
        cap, capture = None, None
        try:
            import cv2 as cv
            import mediapipe as mp
            from camera import open_camera
            if not hasattr(mp, 'solutions'):
                raise RuntimeError('Unsupported MediaPipe version. Run ./setup.sh.')
            cap = open_camera(cv, self.device)
            capture = LatestCamera(cap)
            capture.start()
            with mp.solutions.hands.Hands(max_num_hands=2, model_complexity=0,
                                          min_detection_confidence=.75,
                                          min_tracking_confidence=.75) as hands:
                previous, fps = time.monotonic(), 0.
                while not self.isInterruptionRequested():
                    latest = capture.take()
                    if latest is None:
                        continue
                    frame, timestamp = latest
                    # Preserve normalized landmark geometry while bounding CV work.
                    if frame.shape[1] > 640:
                        frame = cv.resize(frame, (640, round(frame.shape[0] * 640 / frame.shape[1])))
                    frame = cv.flip(frame, 1)
                    rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
                    rgb.flags.writeable = False
                    result = hands.process(rgb)
                    found, seen, duplicates = {}, set(), set()
                    for landmarks, handedness in zip(result.multi_hand_landmarks or [], result.multi_handedness or []):
                        info = handedness.classification[0]
                        if info.label in seen:
                            duplicates.add(info.label)
                        seen.add(info.label)
                        if info.score >= .7:
                            found[info.label] = [(p.x, p.y) for p in landmarks.landmark]
                    for label in duplicates:
                        found.pop(label, None)
                    now = time.monotonic()
                    fps = .9 * fps + .1 / max(.001, now - previous)
                    previous = now
                    # Reuse the inference RGB buffer for the clean view, before overlays.
                    clean_image = qt_image(rgb) if self.preview.is_set() else None
                    debug_image = None
                    if self.debug.is_set():
                        for landmarks in result.multi_hand_landmarks or []:
                            mp.solutions.drawing_utils.draw_landmarks(frame, landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                        debug_image = qt_image(cv.cvtColor(frame, cv.COLOR_BGR2RGB))
                    with self.lock:
                        # Age is measured from capture, not from inference completion.
                        self.latest = (found, frame.shape[1] / frame.shape[0], clean_image, debug_image, fps, timestamp)
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
        finally:
            if capture is not None:
                capture.close()
            elif cap is not None:
                cap.release()
