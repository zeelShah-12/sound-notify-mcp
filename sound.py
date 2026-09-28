"""Cross-platform notification chimes, synthesized on the fly.

No bundled audio assets and no third-party audio library: each chime is a
short sine-wave sequence rendered to WAV bytes in memory, then handed to
whatever playback mechanism the current OS actually has.
"""

from __future__ import annotations

import io
import math
import os
import platform
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Literal

SAMPLE_RATE = 44100

# Each status maps to a short sequence of (frequency_hz, duration_seconds) tones.
TONE_SEQUENCES: dict[str, list[tuple[float, float]]] = {
    "success": [(880.00, 0.12), (1174.66, 0.18)],  # rising A5 -> D6 chime
    "error": [(392.00, 0.15), (261.63, 0.25)],  # falling G4 -> C4 buzz
    "info": [(659.25, 0.15)],  # single E5 blip
}

Status = Literal["success", "error", "info"]


def synthesize_wav(sequence: list[tuple[float, float]]) -> bytes:
    """Render a sequence of sine tones into a mono 16-bit PCM WAV file (as bytes)."""
    frames = bytearray()
    for freq, duration in sequence:
        n_samples = int(SAMPLE_RATE * duration)
        fade = max(1, int(n_samples * 0.08))  # short fade in/out avoids audible clicks
        for i in range(n_samples):
            amplitude = 0.5
            if i < fade:
                amplitude *= i / fade
            elif i > n_samples - fade:
                amplitude *= (n_samples - i) / fade
            sample = amplitude * math.sin(2 * math.pi * freq * (i / SAMPLE_RATE))
            frames += struct.pack("<h", int(sample * 32767))
        frames += b"\x00\x00" * int(SAMPLE_RATE * 0.02)  # tiny gap between notes

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(bytes(frames))
    return buffer.getvalue()


def play_notification(status: Status = "success") -> bool:
    """Play a short chime for the given status.

    Returns True if a real audio backend played the sound, False if playback
    fell back to the terminal bell because no backend was found for this OS.
    """
    sequence = TONE_SEQUENCES.get(status, TONE_SEQUENCES["success"])
    wav_bytes = synthesize_wav(sequence)
    system = platform.system()

    try:
        if system == "Windows":
            import winsound

            # SND_ASYNC is not supported together with SND_MEMORY on Windows,
            # so this blocks briefly (the chime is well under a second).
            winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
            return True

        fd, tmp_name = tempfile.mkstemp(suffix=".wav")
        os.close(fd)  # avoid leaking the descriptor -- blocks unlink() on Windows otherwise
        tmp_path = Path(tmp_name)
        try:
            tmp_path.write_bytes(wav_bytes)
            if system == "Darwin":
                subprocess.run(["afplay", str(tmp_path)], check=True, capture_output=True)
                return True
            for player in ("paplay", "aplay", "play"):
                try:
                    subprocess.run([player, str(tmp_path)], check=True, capture_output=True)
                    return True
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception:
        pass

    sys.stdout.write("\a")
    sys.stdout.flush()
    return False
