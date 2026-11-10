# Digital Midi Keyboard — art direction

## Intent

A playable desktop instrument with the clarity of a printed synthesizer panel. Combine the continuous keyboard of a studio MIDI controller, the 4×4 pad matrix of a drum machine, and the orange accents and disciplined labelling of vintage electronic instruments. The user supplied these references and explicitly chose the typography and palette below. Preserve this identity in future edits.

## Typography

Titles: Futura Display, uppercase, compact display proportions. Prefer an installed Futura Display font, including fonts loaded from `fonts/`. The exact face is not currently installed; use the system Futura Condensed ExtraBold as an explicitly documented fallback. Never label a fallback as the exact face. Controls: Helvetica, uppercase, with Helvetica Neue and the platform sans-serif as fallbacks. Use readable sizes and generous spacing for secondary labels. Do not distribute proprietary font files; the user may supply a licensed font in `fonts/`.

## Palette and material

Near-black canvas #141414; charcoal chassis #222222; recessed panels #191919; warm white #F2EFE7; secondary text #B9B6AE; signal orange #FF681F. Thin warm-white rules organize modules. Orange section bars and small signal indicators provide hierarchy. Ivory piano keys and near-black accidentals preserve familiar pitch geometry. Pads use muted warm tonal groups at rest and bright orange on activation. Extend the retro-futurist identity with an original ascending orange signal-block mark and DK—01 panel designation, a recessed monitor bezel, and concise signal labels. Do not copy the reference logos. Avoid rainbow decoration, generic dashboard cards, glossy gradients, and reference-brand logos.

## Layout

A single instrument face at a nominal 1280×860 logical size. Large typographic product name at top left, a compact live/pause control at right. Upper deck: performance and connection controls on the left, a large 4×4 pad matrix on the right. Lower deck: full-width two-octave keyboard with octave and velocity controls above it. Bottom rail: concise gesture guidance, shortcuts, and input status. Keep all essential playing surfaces visible; scale uniformly when the window changes size.

## Imagery and diagnostics

Use drawn instrument geometry rather than photography, copied logos, or generated background images. The main face includes a switchable performance monitor: a clean, mirrored camera view so the player can see themselves, or an audio-driven phase scope inspired by a vintage oscilloscope. Use a near-black screen, a restrained mint phosphor trace, a subtle graticule, and static scan lines inside the orange/charcoal chassis. This mint accent belongs only to the scope. The phase portrait uses delayed samples from the local synth output and rests at silence; it is not a decorative animation or an analysis of external DAW audio. The camera preview center-crops to fill the monitor without letterboxing or stretching. Main-view camera video must never show landmarks or technical overlays. Hand landmarks, tracking rate, and detailed device errors remain in a separate diagnostics window, explicitly opened with F2, the diagnostics button, or `--debug`.

## Motion and interaction

No ambient motion or decorative animation. Scope motion follows actual local audio; camera/scope switching must not release or retrigger held notes. Note illumination follows note-on/off immediately. Thin cursor rings indicate aiming and a filled center indicates a closed pinch. Preserve independent hand sources, release-on-tracking-loss, panic, and octave-change release. Capture and MediaPipe inference run off the UI thread; drain camera capture independently and consume only the newest frame and result to prevent queued latency. Use the lightweight hand model at a bounded input width, cache the instrument face between musical state changes, and paint the monitor opaquely so its refresh never repaints the full chassis. Bound scope path complexity and build its path only on audio refresh.

## Technology, accessibility, validation

Use Qt/PySide6 for the finished desktop UI, scalable QPainter geometry for playing surfaces, and native Qt buttons/sliders for controls, focus navigation, and accessibility labels. OpenCV is capture/diagnostics infrastructure only. Controls have visible keyboard focus, accessible names, and keyboard shortcuts. Support computer-keyboard notes and numbered drum-pad shortcuts. Do not communicate playing state by color alone: use a note readout and pad/key marks. Release notes on app deactivation and shutdown. Validate rendered default, active, small-window, and diagnostics states plus meaningful mouse, keyboard, gesture-loss, and MIDI routing interactions. Preserve FaceTime-by-name selection on macOS.
