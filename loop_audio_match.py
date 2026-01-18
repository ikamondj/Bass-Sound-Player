#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path

import vlc


def _devices_from_enum(player):
    """
    Returns a list of (device_id, description) tuples for up to 10 audio devices.

    python-vlc has had two styles in the wild:
      1) audio_output_device_enum() returns a linked list you must release.
      2) audio_output_device_enum() returns a Python list (newer wrappers).
    """
    devs = []
    enum = player.audio_output_device_enum()

    if enum is None:
        return devs

    # Newer wrappers may return a list-like
    if isinstance(enum, (list, tuple)):
        for d in enum[:10]:
            device_id = getattr(d, "device", None) or getattr(d, "device_id", None)
            desc = getattr(d, "description", None) or getattr(d, "name", None) or str(device_id)
            if device_id:
                devs.append((device_id, desc))
        return devs

    # Older wrappers: linked list nodes with .device, .description, .next
    head = enum
    cur = enum
    try:
        while cur and len(devs) < 10:
            device_id = getattr(cur, "device", None)
            desc = getattr(cur, "description", None) or str(device_id)
            if device_id:
                devs.append((device_id, desc))
            cur = getattr(cur, "next", None)
    finally:
        # Per libVLC docs: must be freed after enumeration.
        try:
            player.audio_output_device_list_release(head)
        except Exception:
            pass

    return devs


def select_device(player, argv):
    devices = _devices_from_enum(player)

    if not devices:
        return None  # fall back to default output device

    choice = None
    if len(argv) >= 2:
        choice = argv[1].strip()
    else:
        print("Select audio output device (0-9). Press Enter to use default.\n")
        for i, (_, desc) in enumerate(devices):
            print(f"{i}: {desc}")
        try:
            choice = input("\nDevice #: ").strip()
        except EOFError:
            choice = ""

    if choice == "":
        return None

    if len(choice) == 1 and choice.isdigit():
        idx = int(choice)
        if 0 <= idx < len(devices):
            return devices[idx][0]

    # If user passed something else, try substring match against description.
    lowered = choice.lower()
    for device_id, desc in devices:
        if lowered in (desc or "").lower():
            return device_id

    print("Invalid selection; using default output device.")
    return None


def main():
    script_dir = Path(__file__).resolve().parent
    audio_path = script_dir / "loop.wav"
    if not audio_path.exists():
        print(f"Missing file: {audio_path}")
        sys.exit(1)

    # On headless Pi, avoid unnecessary interfaces; keep it simple.
    inst = vlc.Instance("--no-video", "--quiet")

    player = inst.media_player_new()

    device_id = select_device(player, sys.argv)
    if device_id:
        # Note: device selection support depends on the active VLC audio output module.
        # If it fails, VLC will still play on the default output.
        try:
            player.audio_output_device_set(None, device_id)
        except TypeError:
            # Some wrappers omit the module arg.
            try:
                player.audio_output_device_set(device_id)
            except Exception:
                pass
        except Exception:
            pass

    # Best-effort looping inside VLC:
    # Use MediaListPlayer with LOOP mode (more reliable than re-playing on Ended).
    media = inst.media_new_path(str(audio_path))
    mlist = inst.media_list_new([media])
    list_player = inst.media_list_player_new()
    list_player.set_media_player(player)
    list_player.set_media_list(mlist)

    try:
        list_player.set_playback_mode(vlc.PlaybackMode.loop)
    except Exception:
        # Fallback: some builds may not expose PlaybackMode; we can still start and keep alive.
        pass

    list_player.play()

    # Keep process alive forever (and let VLC loop internally).
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            list_player.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
