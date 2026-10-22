# GTSinger internal calibration fixture

This folder contains a downloader specification, not dataset content. It acquires a small matched subset of English recordings: `Control_Group` paired with `Breathy_Group`, `Glissando_Group`, and `Vibrato_Group`.

Each selected clip retains its WAV, JSON, MusicXML and TextGrid sidecars when present. The generated manifest records the source revision and SHA-256 of every file, allowing reproducible calibration without putting licensed audio in Git.

## License boundary

GTSinger is [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Use the fixture only for internal, non-commercial research. Attribute GTSinger and its authors, retain the license, document changes, and do not commit, bundle, redistribute, or commercially train on this data without a separate rights review.

## Acquire

```zsh
zsh /Users/hiimdrdey/autotune/gtsinger_benchmark/prepare_gtsinger_benchmark.zsh
```

The default remains `EN-Alto-1` for continuity. A promotion gate must include
an independent singer; retrieve Alto-2 and Tenor-1 with:

```zsh
GTSINGER_VOICES=EN-Alto-2,EN-Tenor-1 \\
  zsh /Users/hiimdrdey/autotune/gtsinger_benchmark/prepare_gtsinger_benchmark.zsh
```

The default target is outside the source tree: `~/Library/Application Support/StudioForge/Research/GTSinger`.

Next generate the key-aware test plan:

```zsh
zsh /Users/hiimdrdey/autotune/gtsinger_benchmark/build_gtsinger_test_plan.zsh
```

The current StudioForge calibration runner locks every render to `Alto / F# / Natural Minor`, which is valid only for Hook 2. It must accept this generated per-clip Voice/Key/Scale plan before GTSinger A/B bounces run. This prevents invalid correction measurements on songs in different keys.

Apply the runner upgrade, then rebuild it:

```zsh
zsh /Users/hiimdrdey/autotune/gtsinger_benchmark/apply_key_aware_calibration_runner.zsh
```

It resolves the hosted plug-in enum labels during offline setup rather than assuming Artist's private parameter indices. This keeps Vibe and Artist on the identical per-clip map.

Run a small balanced A/B batch first (one controlled pair per technique; six inputs). Derived bounces remain outside Git:

```zsh
zsh /Users/hiimdrdey/autotune/gtsinger_benchmark/run_gtsinger_artist_vibe_ab.zsh
```

Only after reviewing its three technique reports, expand to both pairs per technique:

```zsh
GTSINGER_PAIRS_PER_TECHNIQUE=2 zsh /Users/hiimdrdey/autotune/gtsinger_benchmark/run_gtsinger_artist_vibe_ab.zsh
```

Each run automatically writes `hard-tune-zero-summary.md`, separating the
general Control error from the extra error caused by a vocal technique.

The plan retains both score spelling and host spelling for enharmonic keys.
For example, a `Bb` score is sent as `A#` to VibeAutotune and as `Bb` to
Artist, so both hosts receive the same pitch class through the labels they
actually expose.

Likewise, Artist's middle vocal enum is `Alto-Tenor`: an `EN-Tenor-*` clip is
set to `Tenor` in VibeAutotune and `Alto-Tenor` in Artist. This is an explicit
host-label translation, not a change to either plug-in's correction controls.

Before the first cross-host run, apply the host lookup repair once. It restores
ID-first lookup with an exact public-label fallback, so a runner request such
as `Retune Speed` resolves Vibe's `retuneSpeed` parameter safely:

```zsh
zsh /Users/hiimdrdey/autotune/gtsinger_benchmark/repair_host_parameter_label_lookup.zsh
```

Jobs are selected only when the technique phoneme annotations contain positive
duration. Folder names alone are not treated as proof that a clip contains the
advertised technique.

After that host fix, create Artist/Vibe A/B bounces for every matched clip under identical key/scale/control settings, then score pitch trajectory, target-switch timing, onset/offset envelope, vibrato contour and sibilance independently. A technique result cannot alter the Hook-2 baseline until it passes its own evidence gate.
