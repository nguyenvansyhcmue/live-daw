#!/usr/bin/env python3
"""Create a deterministic side-by-side and amplified visual diff."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageStat


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    reference = Image.open(args.reference).convert("RGB")
    capture = Image.open(args.capture).convert("RGB")
    if reference.size != capture.size:
        raise SystemExit(f"size mismatch: reference={reference.size} capture={capture.size}")
    diff = ImageChops.difference(reference, capture)
    stats = ImageStat.Stat(diff)
    mean = sum(stats.mean) / len(stats.mean)
    rms = (sum(channel * channel for channel in stats.rms) / len(stats.rms)) ** .5
    amplified = ImageEnhance.Contrast(diff).enhance(2.0)
    amplified = ImageEnhance.Brightness(amplified).enhance(2.5)
    canvas = Image.new("RGB", (reference.width * 3, reference.height), "black")
    canvas.paste(reference, (0, 0))
    canvas.paste(capture, (reference.width, 0))
    canvas.paste(amplified, (reference.width * 2, 0))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output)
    print(f"mean_abs_channel_error={mean:.3f}")
    print(f"rgb_rms_error={rms:.3f}")
    print(f"comparison={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
