# AIR MIDI

A webcam-controlled MIDI keyboard and percussion pad instrument. Play a two-octave piano and 16 drum pads with hand gestures or a mouse, hear a built-in sound preview, and send MIDI to your music software.

## Requirements

- Python 3.11 (recommended) and a desktop environment.
- A webcam for gesture control, or mouse-only mode.
- Speakers or headphones for local preview.
- A DAW or software instrument for external MIDI playback.

The application uses OpenCV, MediaPipe Hands, NumPy, SoundDevice, Mido, and RtMidi. The pinned MediaPipe version uses the classic Hands API. This version is intended primarily for macOS; camera indices and MIDI routing can vary by platform.

## Install and launch

From the project directory:

```bash
./setup.sh
./run.sh
```

To select another Python installation:

```bash
PYTHON=/path/to/python3.11 ./setup.sh
```

Allow camera access for the terminal or application launching AIR MIDI when prompted. Video is processed locally and is not recorded or uploaded by the application.

To play without a camera:

```bash
./run.sh --no-camera
```

## Play

The upper-left panel contains 16 percussion pads. The bottom panel contains 25 chromatic piano keys, starting at C4. Black keys take priority where they overlap white keys.

1. Show one or both hands to the camera.
2. Open your thumb and index finger to prepare each hand.
3. Move your hand to position its cursor over a pad or key.
4. Pinch your thumb and index finger together to start a note.
5. Open the pinch to stop. Release and pinch again to retrigger a pad.

Moving a closed pinch to another key changes the note. Each hand controls one note independently; the mouse can add another. Tracking loss releases the affected hand's note, and reacquiring a hand requires an open pinch before playing again. Keep your hands separated for more reliable tracking.

Click and hold any pad or key to play with the mouse. Drag while holding to change notes. Move outside the playing areas to release.

- **Space:** pause or resume; releases all active notes.
- **[ / ]:** shift the keyboard down or up an octave (C0 through C7 starting notes).
- **- / +:** adjust note-on velocity (1–127).
- **P:** panic; release notes and send All Notes Off.
- **Q / Escape:** quit.

Velocity is a fixed adjustable value, not an estimate of hand movement speed. Drums use fixed General MIDI percussion note numbers on channel 10; the keyboard uses channel 1. Local percussion sounds are synthesized previews rather than a sample library. The local preview plays polyphonically; the gesture interface supports one selected note per hand.

## Connect to a DAW

Create a virtual MIDI port on macOS or a compatible Linux MIDI system:

```bash
./run.sh --midi virtual
```

In your DAW, enable **AIR MIDI** as an input. Route channel 1 to a melodic software instrument and channel 10 to a General MIDI-compatible drum instrument. Enable input monitoring or arm the receiving tracks. Actual sounds and drum mappings depend on the receiving instrument.

List existing MIDI destinations and connect using an exact name:

```bash
./run.sh --list-midi
./run.sh --midi "Your MIDI Port Name"
```

RtMidi virtual ports are not supported on Windows. Use an existing MIDI destination on that platform. See the [Mido RtMidi documentation](https://mido.github.io/mido/backends/rtmidi.html) for platform details.

Disable the local preview while monitoring your DAW:

```bash
./run.sh --midi virtual --no-audio
```

MIDI carries performance messages, not audio. A receiving instrument is required to hear external MIDI output. If a requested MIDI connection cannot open, the application stops with an error.

## Device options

```bash
./run.sh --list-cameras
./run.sh --device 1
./run.sh --audio-device 2
./run.sh --help
```

On macOS, the built-in FaceTime camera is selected by name automatically. OBS and other virtual cameras are not selected automatically. Use `--list-cameras` to see macOS camera names and indices, or `--device INDEX` to choose a camera explicitly. Other platforms default to index 0. Camera permission, lighting, camera frame rate, and audio buffer performance affect responsiveness. The application releases active notes on normal shutdown, camera read failure, pause, octave change, and panic. If the process is forcibly terminated, use your DAW's panic command.

## Troubleshooting

- **Camera unavailable:** grant camera access to your terminal, close other camera applications, select another index, or use `--no-camera`.
- **No local sound:** check the system output device and volume; select an audio device with `--audio-device` if needed.
- **No DAW sound:** enable the MIDI input, arm or monitor the receiving track, and check its MIDI channel and instrument.
- **Unstable tracking:** improve lighting, include your full hand in view, keep hands apart, and avoid covering the palm.
- **Dependency error:** use Python 3.11 and rerun setup. Do not replace the pinned MediaPipe version with a version that removes `mediapipe.solutions`.

## Development checks

```bash
.venv/bin/python -m unittest discover -v
```

Core gesture, geometry, and note-lifecycle checks do not require a camera, an audio device, or a MIDI port. Device integration should also be checked on the target computer before a performance.
