# Digital Midi Keyboard

A gesture-controlled desktop MIDI instrument with a two-octave piano and 16 percussion pads. Play with a webcam, a mouse, or computer keys, listen to a built-in sound preview, and send your performance to a DAW.

The instrument uses a charcoal face, orange section bars, ivory piano keys, and uppercase controls. The main panel has a switchable camera self-view and a mint-phosphor audio scope, set into a retro-futurist instrument face. Technical overlays remain in a separate diagnostics window.

## Requirements

- Python 3.11 recommended.
- macOS 13 or later for the pinned macOS dependencies; a desktop environment is required.
- A webcam for gesture control, or use mouse and computer-keyboard mode.
- Speakers or headphones for local sound preview.
- A DAW or software instrument for external MIDI playback.

The application uses Qt/PySide6 for the interface, MediaPipe and OpenCV for background hand tracking, NumPy and SoundDevice for sound preview, and Mido/RtMidi for MIDI output. Other platforms may require additional system dependencies and device configuration.

## Install and launch

From the project directory:

```bash
./setup.sh
./run.sh
```

Choose a Python installation if needed:

```bash
PYTHON=/path/to/python3.11 ./setup.sh
```

Allow camera access for the terminal or application launching the instrument. Frames are processed locally; the application does not record or upload video.

To play without a camera:

```bash
./run.sh --no-camera
```

## Play

Open your thumb and index finger to prepare a hand. Move your hand to aim its cursor over a key or pad, then pinch to play. Open the pinch to release. Release and pinch again to retrigger a pad. Moving a closed pinch to another playing surface changes the note.

Each hand selects one note independently. Mouse and computer-keyboard inputs can add notes. Lost tracking releases the affected hand, and a returning hand must open its pinch before playing again. The instrument also releases notes when paused, transposed, deactivated, or closed.

Click and hold a key or pad to play with the mouse. Drag while holding to change the note; release to stop. The window scales the interface while keeping playing geometry aligned.

Computer keys **A W S E D F T G Y H U J K O L ;** play the first 16 chromatic notes of the current keyboard range. Number keys **1–8** trigger the first eight drum pads. Hold several computer keys for chords. The playing surface must have keyboard focus; click it after using a control. Tab navigates the native controls, and the velocity slider supports arrow keys.

- **Space:** pause or resume. The on-screen button shows the current state.
- **[ / ]:** shift the keyboard down or up one octave.
- **- / +:** adjust fixed note-on velocity, from 1 to 127.
- **P / Escape:** panic; release notes and send All Notes Off.
- **V:** switch the performance monitor between CAMERA and SCOPE.
- **F2 / Control+D:** show or hide diagnostics.
- Close the window to quit.

On-screen controls provide pause, panic, velocity, octave, and local sound preview. Orange illumination, note marks, and the note readout indicate playing state. The keyboard has 25 chromatic notes; its starting octave ranges from C0 to C7. Pads retain fixed percussion note numbers when the keyboard is transposed.

## MIDI output

Create a virtual MIDI output on macOS or a compatible Linux MIDI system:

```bash
./run.sh --midi virtual
```

In your DAW, enable **Digital Midi Keyboard** as a MIDI input. Route **channel 1** to a melodic software instrument and **channel 10** to a General MIDI-compatible drum instrument. Enable input monitoring or arm the receiving tracks. The receiving instrument determines the final sounds and drum mappings.

List existing MIDI destinations, then connect using an exact name:

```bash
./run.sh --list-midi
./run.sh --midi "Your MIDI Port Name"
```

To monitor only the DAW:

```bash
./run.sh --midi virtual --no-audio
```

MIDI carries performance messages rather than audio. Without a receiving instrument, external MIDI alone produces no sound. Local percussion sounds are synthesized previews, not a sample library. RtMidi virtual ports are unsupported on Windows; use an existing MIDI destination there. See the [Mido RtMidi documentation](https://mido.github.io/mido/backends/rtmidi.html).

## Performance monitor

Choose **CAMERA** to see a clean, mirrored view of yourself, center-cropped to fill the screen without black side bars, or **SCOPE** to display an oscilloscope-inspired phase portrait. **V** switches between them without interrupting held notes. Camera mode is the default when the camera is enabled; mouse-only mode starts with the scope.

The mint trace follows the actual local sound preview using delayed waveform samples. Its shapes change with the notes, chords, and percussion you play, and settle to rest at silence. The recessed screen, fine grid, and scanlines evoke a vintage phosphor display without obscuring the playing surfaces.

The scope visualizes this application's local synth output; it does not listen to a microphone, system audio, or the DAW's return audio. With LOCAL SOUND turned off or `--no-audio`, the trace rests. Camera mode reports a disabled or unavailable camera rather than displaying a stale frame. Camera capture continuously replaces old frames, tracking uses a lightweight model at up to 640 pixels wide, and the monitor refreshes independently of the cached instrument panel to keep playback responsive.

## Cameras and diagnostics

On macOS, the app finds the built-in FaceTime camera by name. It does not silently fall back to OBS or another virtual camera. If FaceTime cannot be uniquely identified, select a device explicitly.

```bash
./run.sh --list-cameras
./run.sh --device 1
./run.sh --debug
./run.sh --audio-device 2
./run.sh --help
```

Camera listing is macOS-specific. Other platforms default to camera index 0 unless overridden. **Diagnostics** shows the camera feed, hand landmarks, tracking rate, and device errors. Open it with the button, F2, or `--debug`. The main playing surface shows gesture cursors and a clean camera self-view when CAMERA is selected; landmarks and frame-rate overlays appear only in diagnostics.

If the camera fails, the application releases hand-controlled notes and opens diagnostics. Mouse and computer-keyboard playback remain available. Reconnect the device and restart to restore camera tracking. A MIDI connection failure is reported in diagnostics and the output readout; reconnect and restart before continuing external playback.

## Typography

Titles prefer **Futura Display**, and controls use **Helvetica**. If Futura Display is unavailable, the app uses system **Futura Condensed ExtraBold**, falling back to a system sans-serif where needed. Diagnostics identifies whether the exact title font was found.

To use an owned, licensed Futura Display font, create a `fonts` directory beside `app.py`, place its `.otf`, `.ttf`, or `.ttc` file there, and restart. Font files are not bundled with the project. Helvetica falls back through Qt's system font substitution when unavailable.

## Troubleshooting

- **Camera unavailable:** grant camera permission to the launching application, close other camera apps, check diagnostics, or use `--no-camera`.
- **Unstable tracking:** improve lighting, show the whole hand, and keep both hands separated.
- **Crackling or breakup:** open diagnostics (F2) and check AUDIO buffer underruns. Playback uses driver-selected block sizes and requests a 40 ms device buffer to tolerate tracking and UI load. Device latency may vary. Close other heavy audio applications if underruns keep increasing.
- **No local sound:** check system output and the LOCAL SOUND control; select an audio device if needed.
- **No DAW sound:** check MIDI input, receiving channel, track monitoring, and software instrument.
- **Dependency error:** rerun setup using Python 3.11. Keep the pinned MediaPipe version, which supplies the classic Hands API.
- **Notes after a forced termination:** use the DAW's panic command. Normal shutdown sends note release messages.

## Development

The interface art direction is recorded in [DESIGN.md](DESIGN.md). Run checks in the installed environment:

```bash
.venv/bin/python -m unittest discover -v
```

For a headless render or interaction checks:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -v
QT_QPA_PLATFORM=offscreen .venv/bin/python app.py --render preview.png
```

Tests cover gesture gates, source ownership, sound generation, camera selection, scalable hit testing, mouse/keyboard releases, pause, deactivation, monitor switching, clean camera frames, and waveform snapshots. Rendering does not open camera, audio, or MIDI devices. Device integration should also be checked on the target computer before a performance.
