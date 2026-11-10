# Project guidance

Read [DESIGN.md](DESIGN.md) before changing this interface. Preserve its project-specific Futura Display/Helvetica, charcoal, white-rule, and orange-bar identity unless the user requests a change.

- Keep the instrument UI in Qt; camera capture and debug rendering must not determine the finished interface.
- The main view may show a clean camera self-view or an audio-driven scope in its switchable performance monitor. Keep landmarks, frame rate, and technical diagnostics in the separate diagnostics view. Preserve the monitor styling recorded in DESIGN.md.
- Preserve note release, independent input ownership, responsive audio/MIDI, accessibility, and keyboard operation; validate rendering and relevant interactions after UI changes.
- On this Mac, discover FaceTime by name; do not default to OBS. Preserve explicit device overrides.
- Write published READMEs for clients. Omit source ZIPs, handoff history, and conversation-specific instructions.
