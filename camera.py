"""Prefer the built-in FaceTime camera on macOS; allow explicit overrides."""
import sys
from macos_cameras import list_cameras


def select_device(device=None):
    if device is not None:
        return device
    if sys.platform != 'darwin':
        return 0
    cameras = list_cameras()
    matches = [item for item in cameras if 'facetime' in item['name'].casefold()]
    if len(matches) == 1:
        return matches[0]['index']
    available = ', '.join(f"{item['index']}: {item['name']}" for item in cameras) or 'none'
    raise RuntimeError('Could not uniquely identify the FaceTime camera. '
                       f'Available cameras: {available}. Select one with --device INDEX.')


def open_camera(cv, device=None):
    index = select_device(device)
    cap = cv.VideoCapture(index, cv.CAP_AVFOUNDATION if sys.platform == 'darwin' else cv.CAP_ANY)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f'Camera {index} unavailable. Check camera permission, '
                           'or use --list-cameras / --device INDEX / --no-camera.')
    print(f'Using camera {index}.', flush=True)
    return cap
