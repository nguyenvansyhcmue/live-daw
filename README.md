# StudioForge ecosystem — source handoff

Snapshot of the current working trees on 2026-10-22, including uncommitted
source changes. This is not a release-quality certification.

- `Source`, `Tests`, `Tools`, `Packaging`, `Assets`: StudioForge DAW.
- `autotune`: current integrated Vibe source and vendored dependencies/licenses.
- `tune-AI`: Auto Key / Tune-AI application, UI/assets, tests and packaging.
- `router-link`: audio routing/virtual-device project.
- `research/vibe-core-rebuild`: new single-pipeline DSP prototype, NOT promoted.
- `research/calibration`: analysis, calibration and experiment scripts/patches.

The new core is deliberately not silently substituted into the DAW by this
export. Read `research/vibe-core-rebuild/DECISION.md`: transition/listening/live
latency gates remain incomplete. Historical scripts may refer to missing local
datasets or obsolete paths; do not run deployment/cleanup scripts indiscriminately.

## Build prerequisites

DAW: CMake 3.22+, a C++20 compiler, macOS SDK/Xcode command-line tools on macOS.
Root CMake fetches JUCE 8.0.7, so initial configuration needs network access.
ASIO SDK is optional and must be supplied under its applicable license.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --target StudioForgeDAW
```

Tune-AI dependencies and configuration: `tune-AI/pyproject.toml` and
`tune-AI/requirements.txt.txt`. Use a virtual environment. Configure local
audio devices and services separately; user credentials/settings are excluded.

Research prototype: see its own README. Its host runner/tools currently use
machine-specific paths and are not yet a portable release build. This export
has not been built from a fresh clone on another machine.

## Export boundaries

Included source, current UI assets (including Blender source), test code,
vendored DSP source/licenses, build/packaging scripts. Excluded generated builds,
apps/binaries, caches/venvs, bulk datasets, user song lists/device
settings, proprietary Artist binaries and memory dumps, backup archives.
No source from the original workspace was removed. No old Git history is
included in this source-only snapshot. See `SOURCE_EXPORT_MANIFEST.json`.

At the user's request, `research/benchmarks/hook2` now includes Hook 2 raw,
the archived Artist target, candidate bounces, current trace/measurements and
historical summary tables. See its README and SHA-256 manifest before reusing
results. This is an explicit audio-data exception; GTSinger audio, proprietary
plug-in binaries and debugger memory dumps remain excluded.

Publish to the requested destination without force-pushing or overwriting an
unknown main branch:

```sh
git push -u origin source-handoff-20261022
```

That command requires working GitHub network access and credentials with write
permission. The preparation session could not resolve github.com; publication
must be verified separately, not inferred from a local commit.
