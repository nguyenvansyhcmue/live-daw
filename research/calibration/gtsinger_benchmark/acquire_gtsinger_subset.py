#!/usr/bin/env python3
"""Download a small, attributed GTSinger research fixture outside this repo.

This tool intentionally downloads a tiny matched subset only. The audio must
never be checked into the VibeAutotune/StudioForge repositories or shipped in
any product build. See README.md for the CC BY-NC-SA 4.0 conditions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = "AaronZ345/GTSinger"
REVISION = "main"
LICENSE = "CC BY-NC-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
DATASET_URL = "https://huggingface.co/datasets/AaronZ345/GTSinger"
PAPER_URL = "https://arxiv.org/abs/2409.13832"
TECHNIQUES = ("Breathy", "Glissando", "Vibrato")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def require_external_root(root: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    try:
        root.resolve().relative_to(repo)
    except ValueError:
        return
    raise SystemExit(f"Refusing to download licensed audio inside source repository: {root}\nUse a directory outside the repository, for example ~/Library/Application Support/StudioForge/Research/GTSinger.")


def sidecars(wav_path: str, all_paths: set[str]) -> list[str]:
    stem = wav_path[:-4]
    return [path for path in (wav_path, stem + ".json", stem + ".musicxml", stem + "_TextGrid", stem + ".TextGrid") if path in all_paths]


def select_fixture(paths: list[str], voices: list[str], pairs_per_technique: int, clips_per_pair: int) -> list[dict]:
    """Select balanced technique pairs independently for every requested singer."""
    all_paths = set(paths)
    requested = set(voices)
    wav = re.compile(r"^English/(?P<voice>[^/]+)/(?P<technique>Breathy|Glissando|Vibrato)/(?P<song>[^/]+)/(?P<group>Control_Group|Breathy_Group|Glissando_Group|Vibrato_Group)/(?P<clip>[^/]+)\.wav$")
    grouped: dict[tuple[str, str, str], dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    for path in paths:
        match = wav.match(path)
        if match is None or match["voice"] not in requested:
            continue
        item = match.groupdict()
        grouped[(item["voice"], item["technique"], item["song"])][item["group"]][item["clip"]] = path

    selected: list[dict] = []
    for voice in voices:
        for technique in TECHNIQUES:
            technique_group = f"{technique}_Group"
            candidates = []
            for (candidate_voice, candidate_technique, song), groups in grouped.items():
                if candidate_voice != voice or candidate_technique != technique:
                    continue
                common = sorted(set(groups["Control_Group"]) & set(groups[technique_group]))
                if common:
                    candidates.append((song, common, groups))
            for song, clips, groups in sorted(candidates)[:pairs_per_technique]:
                for clip in clips[:clips_per_pair]:
                    for group in ("Control_Group", technique_group):
                        wav_path = groups[group][clip]
                        selected.append({"dataset_voice": voice, "technique": technique, "song": song, "group": group, "clip": clip, "files": sidecars(wav_path, all_paths)})
    if not selected:
        raise SystemExit(f"No matched Control_Group/technique WAV pairs found for {', '.join(voices)}. The remote dataset layout may have changed; do not broaden the download blindly.")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="External destination for licensed fixture data")
    parser.add_argument("--pairs-per-technique", type=int, default=2)
    parser.add_argument("--clips-per-pair", type=int, default=4)
    parser.add_argument("--voice", action="append", default=[], metavar="SINGER", help="English singer folder, repeatable (default: EN-Alto-1)")
    parser.add_argument("--accept-license", action="store_true", help="Record acceptance of CC BY-NC-SA 4.0 research-only use")
    args = parser.parse_args()
    if not args.accept_license:
        raise SystemExit("Pass --accept-license only after accepting CC BY-NC-SA 4.0.")
    if args.pairs_per_technique < 1 or args.clips_per_pair < 1:
        raise SystemExit("pair and clip limits must be positive")
    require_external_root(args.root)
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError as exc:
        raise SystemExit("Missing huggingface_hub. Install it with:\n  python3 -m pip install --user 'huggingface_hub>=0.25'") from exc

    api = HfApi()
    info = api.dataset_info(REPOSITORY, revision=REVISION)
    revision = getattr(info, "sha", REVISION)
    paths = [item.path for item in api.list_repo_tree(REPOSITORY, repo_type="dataset", revision=revision, recursive=True) if hasattr(item, "path") and getattr(item, "type", "file") == "file"]
    voices = args.voice or ["EN-Alto-1"]
    if len(set(voices)) != len(voices) or any("/" in voice or not voice.startswith("EN-") for voice in voices):
        raise SystemExit("--voice must be a unique English singer folder such as EN-Alto-1 or EN-Tenor-1")
    fixture = select_fixture(paths, voices, args.pairs_per_technique, args.clips_per_pair)
    args.root.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for item in fixture:
        for filename in item["files"]:
            local = Path(hf_hub_download(repo_id=REPOSITORY, repo_type="dataset", revision=revision, filename=filename, local_dir=args.root))
            downloaded.append({"path": str(local.relative_to(args.root)), "sha256": digest(local)})
    manifest = {
        "schema": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Internal, non-commercial VibeAutotune calibration and regression research only.",
        "source": {"repository": REPOSITORY, "revision": revision, "dataset_url": DATASET_URL, "paper": PAPER_URL},
        "license": {"name": LICENSE, "url": LICENSE_URL, "accepted_for_this_fixture": True},
        "prohibitions": ["Do not commit audio or annotations to source control.", "Do not bundle audio or annotations in StudioForge/VibeAutotune releases.", "Do not use this fixture for commercial model/product training or distribution without separate rights review."],
        "selection": {"voices": voices, "techniques": list(TECHNIQUES), "pairs_per_technique": args.pairs_per_technique, "clips_per_pair": args.clips_per_pair, "items": fixture},
        "files": downloaded,
    }
    manifest_path = args.root / "vibe-gtsinger-research-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Downloaded {len(downloaded)} files for {len(fixture)} matched clips.")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
