# Hook 2 — resume tracing without re-rendering reference data

## Start here

1. `audio/hook2-raw.wav`: original input, 48 kHz; SHA
   `c241b07c23528541960b45ca4889a1ae105200ab9ba1a4a239c81683f98bac28`.
2. `audio/artist-target.wav`: archived Artist reference used in the current
   measurements; SHA
   `fe8fcafac41f18fe7c5b823e52bf94b988fcf1a0270e93722bfe4db5a21caadb`.
3. `audio/vibe-new-core-host.wav`: new prototype rendered in StudioForge,
   not a production-approved build; SHA
   `8de6266ec336e2c3b57395b54c438f1112732ebed1ee52036b181d918898d723`.
4. `current/DECISION.md`: interpretation and failed/pending gates.
5. `current/v2-audit/metrics.json`, `transitions.csv`, `pitch-frames.csv`:
   full/region pitch metrics, transition landmarks and frame-level data.
6. `current/final-trace/full_default_intervals.csv`: sample-index control,
   excitation, synthesis, fractional read positions/weights and stream epoch.
7. `listening/Artist.wav` and `listening/Vibe-new-core.wav`: aligned, level-matched
   listening copies. `levels.json` records gain. Do not confuse these with the
   unmodified target used by the analyser.

Current intended configuration: Alto, F# Natural Minor, Retune/Flex/Humanize/
Natural Vibrato all zero. Archived Artist metadata is not a fresh runtime
verification. A known F-versus-F# bug in the older calibration runner is discussed
in the decision report; do not automatically trust every historical preset.

`INDEX.csv` and `MANIFEST.json` link all bundled evidence to its original path,
SHA-256, role and size. Original reports retain their original absolute paths as
provenance; the portable entry point below uses only paths relative to this repo.
This evidence package does not grant a new license for the recording or third-party
material. Use only within the permissions you hold; avoid public redistribution
of audio without the necessary rights.

## Recheck on another machine

From the repository root, in an environment with NumPy/SciPy installed:

```sh
python3 research/benchmarks/hook2/verify_and_measure.py
python3 research/benchmarks/hook2/verify_and_measure.py --measure --output /tmp/hook2-check
```

First command only checks SHA-256. Second reuses the bundled WAVs; it does not
load Artist, rebuild Vibe or render anything. See `requirements.txt` for the
versions used to verify the portable path. No absolute `/Users/...` dependency
is needed for this measurement entry point.

## Historical evidence — not an approval list

`history/` retains old calibration/transfer/transition summaries and decisions
under original run names, including rejected candidates. They are evidence to
avoid repeating failed experiments, not compatible scores to rank blindly.
Compare sample rate, key, controls, renderer hash and measurement method first.
Only selected small summary/report files are included, not all historical WAVs,
raw frame traces, builds, proprietary binaries or memory dumps.

`current/independent/` contains existing independent-fixture measurement tables,
not GTSinger source audio. Re-running those fixtures requires obtaining the
dataset separately under its license and restoring the appropriate references.
The active bundle contains ONE hard-zero Artist target, not a verified full
four-knob Artist render matrix.
