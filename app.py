"""AIR MIDI: a camera-controlled keyboard and percussion pad instrument."""
import argparse
import contextlib
from controller import Notes, Pinch
from layout import WIDTH, HEIGHT, zones, hit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', type=int, default=None, help='camera index override (default: FaceTime on macOS, index 0 elsewhere)')
    parser.add_argument('--no-camera', action='store_true', help='mouse-only mode')
    parser.add_argument('--no-audio', action='store_true', help='disable local preview sound')
    parser.add_argument('--midi', help='exact existing MIDI output name, or "virtual"')
    parser.add_argument('--list-midi', action='store_true')
    parser.add_argument('--list-cameras', action='store_true', help='list macOS camera names and indices')
    parser.add_argument('--audio-device', type=int)
    args = parser.parse_args()
    if args.list_cameras:
        from macos_cameras import list_cameras
        for camera in list_cameras():
            print(f"{camera['index']}: {camera['name']}")
        return
    if args.list_midi:
        import mido
        for name in mido.get_output_names():
            print(name)
        return
    import cv2 as cv
    import numpy as np
    from audio import Synth
    synth = Synth()
    title = 'AIR MIDI / Keyboard + Pads'
    octave, velocity, paused = 4, 100, False
    regions = zones(octave)
    gestures = {name: Pinch() for name in ('Left', 'Right')}
    cursors = {}
    mouse_down = False
    midi = None

    with contextlib.ExitStack() as stack:
        if args.midi:
            import mido
            midi = stack.enter_context(mido.open_output('AIR MIDI' if args.midi == 'virtual' else args.midi,
                                                        virtual=args.midi == 'virtual', autoreset=True))
        if not args.no_audio:
            import sounddevice as sd
            stack.enter_context(sd.OutputStream(samplerate=synth.samplerate, blocksize=256, channels=1,
                                               dtype='float32', device=args.audio_device, callback=synth.callback))

        def send(kind, channel, note, value):
            if midi:
                import mido
                payload = dict(channel=channel)
                payload.update(dict(control=note, value=value) if kind == 'control_change' else dict(note=note, velocity=value))
                midi.send(mido.Message(kind, **payload))
            synth.send(kind, channel, note, value)

        notes = Notes(send)
        stack.callback(notes.panic)
        cap, hands = None, None
        if not args.no_camera:
            import mediapipe as mp
            if not hasattr(mp, 'solutions'):
                raise RuntimeError('MediaPipe version mismatch. Run ./setup.sh to install the supported version.')
            from camera import open_camera
            cap = open_camera(cv, args.device)
            stack.callback(cap.release)
            hands = stack.enter_context(mp.solutions.hands.Hands(max_num_hands=2,
                min_detection_confidence=.75, min_tracking_confidence=.75))

        cv.namedWindow(title, cv.WINDOW_AUTOSIZE)
        stack.callback(cv.destroyAllWindows)

        def mouse(event, x, y, flags, param):
            nonlocal mouse_down
            if event == cv.EVENT_LBUTTONDOWN:
                mouse_down = True
            elif event == cv.EVENT_LBUTTONUP:
                mouse_down = False
            zone = hit(regions, x, y) if mouse_down and not paused else None
            notes.set('mouse', (zone.channel, zone.note) if zone else None, velocity)

        cv.setMouseCallback(title, mouse)
        while True:
            frame = None
            cursors.clear()
            if cap:
                ok, frame = cap.read()
                if not ok:
                    notes.panic()
                    raise RuntimeError('Camera disconnected. Notes stopped. Reconnect or use --no-camera.')
                frame = cv.flip(frame, 1)
                result = hands.process(cv.cvtColor(frame, cv.COLOR_BGR2RGB))
                found = {}
                duplicates = set()
                for landmarks, handedness in zip(result.multi_hand_landmarks or [], result.multi_handedness or []):
                    label = handedness.classification[0].label
                    if label in found:
                        duplicates.add(label)
                    if handedness.classification[0].score >= .7:
                        found[label] = [(p.x, p.y) for p in landmarks.landmark]
                    mp.solutions.drawing_utils.draw_landmarks(frame, landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                for name, gesture in gestures.items():
                    points = found.get(name) if name not in duplicates and not paused else None
                    position, down = gesture.update(points, frame.shape[1] / frame.shape[0])
                    zone = None
                    if position:
                        x, y = int(position[0] * (WIDTH - 1)), int(position[1] * (HEIGHT - 1))
                        cursors[name] = (x, y, down)
                        zone = hit(regions, x, y) if down else None
                    notes.set(name, (zone.channel, zone.note) if zone else None, velocity)

            canvas = np.full((HEIGHT, WIDTH, 3), (24, 21, 19), dtype=np.uint8)
            def text(value, x, y, size=.55, color=(173, 171, 166)):
                cv.putText(canvas, value, (x, y), cv.FONT_HERSHEY_SIMPLEX, size, color, 1, cv.LINE_AA)
            text('AIR MIDI', 36, 54, 1.1, (222, 241, 231))
            text('KEYBOARD + PADS  /  GESTURE PERFORMANCE', 265, 49, .5)
            text('PAUSED' if paused else 'LIVE', 1070, 48, .6, (137, 223, 154))
            text('16 PADS', 36, 137, .65, (222, 241, 231))
            text('DRUM CHANNEL 10', 375, 137, .45)
            active = set(notes.sources.values())
            for zone in regions:
                x, y, w, h = zone.rect
                playing = (zone.channel, zone.note) in active
                color = (144, 222, 166) if playing else ((72, 57, 48) if zone.channel == 9 else ((35, 30, 27) if zone.black else (219, 226, 225)))
                cv.rectangle(canvas, (x, y), (x + w - 1, y + h - 1), color, -1)
                if zone.channel == 9:
                    text(zone.label, x + 10, y + 26, .43, (236, 242, 236))
                    text(str(zone.note), x + 10, y + 49, .35)
                else:
                    text(zone.label, x + 9, y + h - 15, .4, (162, 165, 158) if zone.black else (61, 64, 56))
            if frame is not None:
                canvas[170:440, 650:1160] = cv.resize(frame, (510, 270))
                text('CAMERA / two hands, two independent notes', 650, 463, .45)
            else:
                text('MOUSE MODE', 690, 257, .9, (222, 241, 231))
                text('Click + hold to play. Drag to change note.', 690, 297, .45)
            text('KEYBOARD', 36, 510, .65, (222, 241, 231))
            text(f'OCTAVE {octave}   /   VELOCITY {velocity}   /   MELODY CHANNEL 1', 300, 508, .45)
            for name, (x, y, down) in cursors.items():
                color = (120, 220, 255) if name == 'Left' else (235, 184, 133)
                cv.circle(canvas, (x, y), 13 if down else 9, color, 3, cv.LINE_AA)
                text(name, min(x + 17, 1120), max(y - 12, 18), .4, color)
            text('Open thumb + index to prepare. Move hand to aim. Pinch to play; release to stop.', 36, 92, .5)
            text('SPACE Pause    [ / ] Octave    - / + Velocity    P Panic    Q Quit', 36, 772, .48)
            route = args.midi or 'Preview only'
            text(f'OUT: {route[:34]}', 790, 772, .4)
            cv.imshow(title, canvas)
            key = cv.waitKey(1) & 0xff
            if key in (27, ord('q')) or cv.getWindowProperty(title, cv.WND_PROP_VISIBLE) < 1:
                break
            if key in (ord('p'), ord(' '), ord('['), ord(']')):
                notes.panic()
                mouse_down = False
                for gesture in gestures.values():
                    gesture.update(None)
                if key == ord(' '):
                    paused = not paused
                elif key in (ord('['), ord(']')):
                    octave = max(0, min(7, octave + (1 if key == ord(']') else -1)))
                    regions = zones(octave)
            elif key in (ord('='), ord('+'), ord('-')):
                velocity = max(1, min(127, velocity + (-8 if key == ord('-') else 8)))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        raise SystemExit(f'AIR MIDI stopped: {exc}')
