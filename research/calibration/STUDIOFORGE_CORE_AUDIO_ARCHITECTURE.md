# StudioForge core audio architecture

This document defines the narrow, production-facing scope for the next host
work. It deliberately does not change VibeAutotune DSP, its presets, or its
sound. Auto Key remains a control-plane operation that writes Root Key and
Scale to Vibe; it is not an audio-node special case.

## Non-negotiable contracts

1. The realtime callback only reads immutable render snapshots and preallocated
   buffers. It may not take locks, allocate, scan plug-ins, create editors, or
   mutate the project model.
2. Every plug-in is hosted through one format-generic `AudioEffectProcessor`
   path. A product identifier can be used only by the control bridge to route
   Auto Key to Vibe.
3. A plug-in editor has exactly one UI-owned session. The session owns the
   processor reference while its native view is attached, creates/destroys the
   editor on the message thread, and invalidates safely when the slot changes.
4. Reported plug-in latency is topology data. A latency change invalidates and
   rebuilds the graph/PDC plan off the callback, then publishes one immutable
   render plan at a block boundary.
5. Studio and Stage are distinct policies over the same graph. Studio aligns
   parallel paths; Stage never adds latency from unrelated tracks or returns to
   a monitored input. Stage may protectively bypass a non-essential plug-in
   only through a published plan, never by mutating the callback.

## Render-plan model

The control thread compiles these values into `RenderStructureSnapshot`:

`track inserts -> pre/post sends -> bus inserts -> master inserts -> outputs`

For every summing node, compute the longest upstream path. Each incoming edge
gets `nodeLongestLatency - edgeLatency`. Edges, rather than whole tracks, own
delay lines. This is required for a track that reaches Master directly and
through a post-fader AUX simultaneously.

The first implementation must cover direct track, pre/post sends, AUX and
master. Nested busses and sidechains are admitted only once the graph model can
represent their dependency edges and reject cycles deterministically.

## Live latency policy

- `Studio`: full graph PDC; transport pre-roll is enabled when a plan has
  look-ahead/latency so playback starts with stable delay-line state.
- `Stage`: direct monitored input has intrinsic selected-insert latency only;
  no extra compensation for backing-track or AUX latency. Non-essential nodes
  beyond the user latency budget are marked protected before processing.
- `Stream`: use Studio graph timing on stream buses and Stage monitoring policy
  for the performer path.

The budget is a named setting in milliseconds, converted to samples whenever a
device sample rate changes. It is a host policy, not a Vibe control.

## Automation

Existing Volume, Pan and Send automation is block-accurate. The upgrade must
compile parameter events into fixed-capacity per-node event arrays with sample
offsets. The host splits a block only at those offsets and passes the exact
sub-block span to a plug-in. Parameter writes must occur at each event boundary
without UI-thread calls or heap allocation. This enables a future VST3/AU
parameter queue while retaining the existing snapshot model.

## Required proof

1. Impulse fixture for direct vs pre-send/post-send/AUX/master paths, exact to
   one sample after PDC.
2. Latency-change fixture: reported latency changes publish a new plan without
   a stale delay-line duplicate or crash.
3. Stage fixture: a high-latency backing/return does not delay monitored vocal.
4. Editor lifecycle test: create, resize, close, remove slot, and re-open VST3
   editor on the message thread; no retained editor pointer.
5. Automation fixture at 32, 64 and 128 frames: event offsets arrive exactly
   on the requested sample, including a plug-in parameter event.
6. Callback allocation/lock instrumentation stays at zero for all fixtures.

## Sources used to constrain this design

- Steinberg VST3 `IAudioProcessor`: a plug-in reports latency in samples and
  signals `kLatencyChanged` so the host recomputes compensation; live recording
  should use zero or low latency.
- Apple Audio Unit documentation: hosts cache a render block for realtime use;
  latency is a declared unit property and render resources are allocated before
  realtime rendering.
- Apple Audio Workgroups: only actual auxiliary realtime workers join an audio
  workgroup. StudioForge does not create a worker merely to imitate a large DAW.

