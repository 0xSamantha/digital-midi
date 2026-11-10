"""Digital Midi Keyboard — gesture-controlled piano and percussion pads."""
import argparse
import contextlib
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', type=int, help='camera override; FaceTime is preferred on macOS')
    parser.add_argument('--no-camera', action='store_true', help='mouse and computer-keyboard mode')
    parser.add_argument('--no-audio', action='store_true', help='disable local sound preview')
    parser.add_argument('--midi', help='exact MIDI output name, or "virtual"')
    parser.add_argument('--list-midi', action='store_true')
    parser.add_argument('--list-cameras', action='store_true')
    parser.add_argument('--audio-device', type=int)
    parser.add_argument('--debug', action='store_true', help='open the separate camera diagnostics window')
    parser.add_argument('--render', metavar='PNG', help='render the interface to a PNG without opening devices')
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
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    from audio import Synth
    from interface import InstrumentWindow
    from tracking import Tracker
    qt = QApplication(sys.argv[:1])
    qt.setApplicationName('Digital Midi Keyboard')
    qt.setStyle('Fusion')
    qt.setFont(QFont('Helvetica', 12))
    synth = Synth()
    port = None
    preview_enabled = not args.no_audio and not args.render
    midi_error = ['']
    with contextlib.ExitStack() as stack:
        if args.midi and not args.render:
            import mido
            port = stack.enter_context(mido.open_output('Digital Midi Keyboard' if args.midi == 'virtual' else args.midi,
                                                        virtual=args.midi == 'virtual', autoreset=True))
        if preview_enabled:
            import sounddevice as sd
            stack.enter_context(sd.OutputStream(samplerate=synth.samplerate, blocksize=0, latency=.04, channels=1,
                                               dtype='float32', device=args.audio_device, callback=synth.callback))

        def send(kind, channel, note, value):
            nonlocal port
            if port:
                import mido
                payload = dict(channel=channel)
                payload.update(dict(control=note, value=value) if kind == 'control_change' else dict(note=note, velocity=value))
                try:
                    port.send(mido.Message(kind, **payload))
                except Exception as exc:
                    midi_error[0] = f'MIDI output disconnected: {exc}. Reconnect and restart the application.'
                    port = None
            if preview_enabled or kind != 'note_on':
                synth.send(kind, channel, note, value)

        tracker = Tracker(args.device) if not args.no_camera and not args.render else None
        route = ('DIGITAL MIDI KEYBOARD' if args.midi == 'virtual' else args.midi) or ('LOCAL PREVIEW' if preview_enabled else 'SILENT / NO MIDI CONNECTED')
        window = InstrumentWindow(send, tracker, args.no_camera or bool(args.render), route, preview_enabled, scope_source=synth.scope.read)
        stack.callback(window.panic)

        def toggle_preview(enabled):
            nonlocal preview_enabled
            synth.send('control_change', 0, 123, 0)
            synth.send('control_change', 9, 123, 0)
            preview_enabled = enabled
        window.preview.toggled.connect(toggle_preview)

        def show_midi_error():
            if midi_error[0]:
                window.panic()
                window.route = 'MIDI DISCONNECTED'
                window.diagnostics.status.setText(midi_error[0])
                window.diagnostics.show()
                midi_error[0] = ''
        window.timer.timeout.connect(show_midi_error)
        def report_audio_health():
            if window.diagnostics.isVisible():
                window.diagnostics.audio_status.setText(
                    f'AUDIO / {synth.underflows} BUFFER UNDERRUNS / ' +
                    ('LOCAL PREVIEW ON' if preview_enabled else 'LOCAL PREVIEW OFF'))
        window.timer.timeout.connect(report_audio_health)
        window.show()
        if tracker:
            tracker.start()
        if args.debug:
            window.toggle_diagnostics()
        if args.render:
            def render():
                if not window.grab().save(args.render):
                    print(f'Could not write screenshot: {args.render}', file=sys.stderr)
                    qt.exit(1)
                    return
                window.close()
            QTimer.singleShot(150, render)
        return qt.exec()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        raise SystemExit(f'Digital Midi Keyboard stopped: {exc}')
