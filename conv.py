#!/usr/bin/env python3
"""
Simple converter: loop.flac -> loop.wav

Tries to use system `ffmpeg` if available, otherwise falls back to `pydub`.
Run without arguments to convert `loop.flac` -> `loop.wav` in the current directory.
"""
import argparse
import os
import shutil
import subprocess
import sys


def convert_with_ffmpeg(src: str, dst: str) -> int:
    cmd = ["ffmpeg", "-y", "-i", src, dst]
    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        print("ffmpeg failed:", e, file=sys.stderr)
        return 2


def convert_with_pydub(src: str, dst: str) -> int:
    try:
        from pydub import AudioSegment
    except Exception as e:
        print("pydub not available:", e, file=sys.stderr)
        return 3

    try:
        audio = AudioSegment.from_file(src)
        audio.export(dst, format="wav")
        return 0
    except Exception as e:
        print("pydub conversion failed:", e, file=sys.stderr)
        return 4


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Convert FLAC to WAV (loop.flac -> loop.wav)")
    p.add_argument("src", nargs="?", default="loop.flac", help="Source file (default: loop.flac)")
    p.add_argument("dst", nargs="?", default="loop.wav", help="Destination file (default: loop.wav)")
    args = p.parse_args(argv)

    src = args.src
    dst = args.dst

    if not os.path.exists(src):
        print(f"Source file not found: {src}", file=sys.stderr)
        return 1

    if shutil.which("ffmpeg"):
        return convert_with_ffmpeg(src, dst)

    print("ffmpeg not found; attempting pydub fallback (requires ffmpeg or avlib installed)")
    return convert_with_pydub(src, dst)


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
