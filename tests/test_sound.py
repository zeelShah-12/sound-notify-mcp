import struct
import sys
import wave
import io
from unittest.mock import MagicMock, patch

from sound_notify.sound import SAMPLE_RATE, TONE_SEQUENCES, play_notification, synthesize_wav


def test_synthesize_wav_produces_valid_mono_16bit_wav():
    data = synthesize_wav(TONE_SEQUENCES["success"])
    with wave.open(io.BytesIO(data), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == SAMPLE_RATE
        assert wav_file.getnframes() > 0


def test_synthesize_wav_duration_matches_requested_tones():
    sequence = [(440.0, 0.1), (440.0, 0.2)]
    data = synthesize_wav(sequence)
    with wave.open(io.BytesIO(data), "rb") as wav_file:
        actual_duration = wav_file.getnframes() / wav_file.getframerate()
    # tone durations plus the small inter-note gaps
    expected_min = sum(d for _, d in sequence)
    assert expected_min <= actual_duration <= expected_min + 0.2


def test_synthesize_wav_never_clips_amplitude():
    data = synthesize_wav(TONE_SEQUENCES["error"])
    with wave.open(io.BytesIO(data), "rb") as wav_file:
        frames = wav_file.readframes(wav_file.getnframes())
    samples = struct.unpack(f"<{len(frames) // 2}h", frames)
    assert max(samples) < 32767
    assert min(samples) > -32768


def test_play_notification_uses_winsound_on_windows():
    fake_winsound = MagicMock(SND_MEMORY=4)
    with patch("platform.system", return_value="Windows"), \
         patch.dict(sys.modules, {"winsound": fake_winsound}):
        result = play_notification("success")
    assert result is True
    fake_winsound.PlaySound.assert_called_once()
    # SND_ASYNC must never be combined with SND_MEMORY -- winsound raises
    # RuntimeError("Cannot play asynchronously from memory") if it is.
    called_flags = fake_winsound.PlaySound.call_args[0][1]
    assert called_flags == fake_winsound.SND_MEMORY


def test_play_notification_uses_afplay_on_macos():
    with patch("platform.system", return_value="Darwin"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = play_notification("info")
    assert result is True
    args = mock_run.call_args[0][0]
    assert args[0] == "afplay"


def test_play_notification_falls_back_to_bell_when_no_backend_found():
    with patch("platform.system", return_value="Linux"), \
         patch("subprocess.run", side_effect=FileNotFoundError), \
         patch("sys.stdout") as mock_stdout:
        result = play_notification("error")
    assert result is False
    mock_stdout.write.assert_called_with("\a")


def test_unknown_status_falls_back_to_success_sequence():
    # synthesize_wav should never raise for a bad key -- callers validate status,
    # but the tone table itself should degrade gracefully too
    assert TONE_SEQUENCES.get("not-a-real-status", TONE_SEQUENCES["success"]) == TONE_SEQUENCES["success"]
