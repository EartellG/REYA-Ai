import threading
import simpleaudio as sa
import logging

class AudioController:
    def __init__(self):
        self._lock = threading.Lock()
        self._current_playback = None

    def play(self, wav_path: str, block: bool = False):
        with self._lock:
            self.stop()

            try:
                wave_obj = sa.WaveObject.from_wave_file(wav_path)
                self._current_playback = wave_obj.play()
            except Exception as e:
                logging.getLogger("uvicorn.error").warning(f"[Audio] Play failed: {e}")
                return

        if block and self._current_playback:
            self._current_playback.wait_done()

    def stop(self):
        with self._lock:
            if self._current_playback:
                try:
                    self._current_playback.stop()
                except Exception:
                    pass
                self._current_playback = None


# Singleton instance
audio_controller = AudioController()
