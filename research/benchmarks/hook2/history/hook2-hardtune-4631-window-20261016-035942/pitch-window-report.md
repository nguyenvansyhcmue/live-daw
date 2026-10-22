# Hook-2 pitch-window forensic report

- Window: 4.200–4.850 s on the raw timeline
- Artist delay vs raw: 2689 samples (56.02 ms)
- Vibe delay vs raw: 1601 samples (33.35 ms)
- Jointly reliable frames: 487
- Median |Vibe − Artist|: 7.28 cents
- P90 |Vibe − Artist|: 26.95 cents
- Largest difference: 94.27 cents at 4.769333 s
- At that point, Artist correction relative to raw: -38.61 cents
- At that point, Vibe correction relative to raw: 55.67 cents

Interpretation: a difference while the committed MIDI target is unchanged is a continuous correction/renderer contour issue, not evidence to make the target selector switch earlier.
