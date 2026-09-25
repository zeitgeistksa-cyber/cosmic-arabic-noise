#!/usr/bin/env python3
"""
Blend live space audio with phoneme synthesis.
"""
import subprocess, wave, numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from tv_space_synth import synth_message, SR


def capture_live_space(duration_sec, out_path):
    """Capture live space audio for N seconds."""
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i",
            "https://public.isekoi-radio.com/listen/ambient/ambientradio.mp3",
            "-t", str(duration_sec),
            "-ac", "1", "-ar", str(SR),
            "-acodec", "pcm_s16le",
            out_path
        ], capture_output=True, timeout=duration_sec + 30)
        return Path(out_path).exists()
    except Exception:
        return False


def blend(letters, live_audio_path, mix_ratio=0.5):
    """Mix phoneme message with live space audio."""
    # Load live space
    with wave.open(live_audio_path, "rb") as wf:
        n = wf.getnframes()
        live = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32)
    live = live[:len(live) // 2]  # truncate if needed
    live = live / (np.max(np.abs(live)) + 1e-9)

    # Synthesize phoneme message
    message = synth_message(letters)

    # Match lengths
    L = max(len(message), len(live))
    message = np.pad(message, (0, L - len(message)))
    live = np.pad(live, (0, L - len(live)))

    # Mix
    mixed = message * (1 - mix_ratio) + live * mix_ratio
    mixed = np.tanh(mixed * 1.2)  # soft clip
    mixed = mixed / (np.max(np.abs(mixed)) + 1e-9) * 0.94

    return mixed.astype(np.float32)


if __name__ == "__main__":
    import sys
    letters = list(sys.argv[1]) if len(sys.argv) > 1 else list("مرسنل")
    print(f">> Capturing 10s of live space audio...")
    capture_live_space(10, "space_live_capture.wav")
    print(f">> Blending with message {' '.join(letters)}...")
    mixed = blend(letters, "space_live_capture.wav", mix_ratio=0.4)
    int16 = (np.clip(mixed, -1, 1) * 32767).astype(np.int16)
    with wave.open("space_blend.wav", "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(int16.tobytes())
    print(">> wrote space_blend.wav")
