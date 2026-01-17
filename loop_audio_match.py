#!/usr/bin/env python3
import sys
import pathlib
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

Gst.init(None)

MATCH_WORDS = ("audio", "box", "go", "usb")

def path_to_uri(p: str) -> str:
    path = pathlib.Path(p).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.as_uri()

def pick_matching_audio_sink():
    """
    Look through audio sink devices and return an alsasink configured
    for the first device whose name/description contains any MATCH_WORDS.
    """
    monitor = Gst.DeviceMonitor()
    monitor.add_filter("Audio/Sink", None)
    monitor.start()
    devices = monitor.get_devices()
    monitor.stop()

    for dev in devices:
        name = (dev.get_display_name() or "").lower()
        props = dev.get_properties()
        desc = ""

        if props and props.contains("description"):
            desc = props.get_string("description").lower()

        text = f"{name} {desc}"

        if any(word in text for word in MATCH_WORDS):
            # Try to extract ALSA device string
            if props and props.contains("device"):
                device_str = props.get_string("device")
            elif props and props.contains("alsa.card") and props.contains("alsa.device"):
                card = props.get_int("alsa.card")[1]
                adev = props.get_int("alsa.device")[1]
                device_str = f"hw:{card},{adev}"
            else:
                continue

            sink = Gst.ElementFactory.make("alsasink", None)
            if sink:
                sink.set_property("device", device_str)
                print(f"Using audio device: {dev.get_display_name()} ({device_str})")
                return sink

    print("No matching audio device found; using default output")
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: loop_audio_match.py /path/to/audio.(wav|flac|mp3)")
        sys.exit(2)

    uri = path_to_uri(sys.argv[1])

    playbin = Gst.ElementFactory.make("playbin", "player")
    if not playbin:
        print("Failed to create playbin")
        sys.exit(1)

    sink = pick_matching_audio_sink()
    if sink:
        playbin.set_property("audio-sink", sink)

    playbin.set_property("uri", uri)

    # Seamless looping
    def on_about_to_finish(player):
        player.set_property("uri", uri)

    playbin.connect("about-to-finish", on_about_to_finish)

    bus = playbin.get_bus()
    bus.add_signal_watch()

    loop = GLib.MainLoop()

    def on_message(bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, dbg = message.parse_error()
            print(f"ERROR: {err.message}")
            if dbg:
                print(dbg)
            playbin.set_state(Gst.State.NULL)
            loop.quit()

    bus.connect("message", on_message)

    playbin.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    finally:
        playbin.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()
