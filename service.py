import os
import re
import threading
import time

from jnius import autoclass, PythonJavaClass, java_method


class RecognitionListener(PythonJavaClass):
    __javainterfaces__ = ["android/speech/RecognitionListener"]

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, params):
        pass

    @java_method("()V")
    def onBeginningOfSpeech(self):
        pass

    @java_method("([F)V")
    def onRmsChanged(self, rmsdB):
        pass

    @java_method("([B)V")
    def onBufferReceived(self, buffer):
        pass

    @java_method("()V")
    def onEndOfSpeech(self):
        pass

    @java_method("(I)V")
    def onError(self, error):
        self.owner.on_error(error)

    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):
        self.owner.on_results(results)

    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, results):
        self.owner.on_partial(results)

    @java_method("(Landroid/os/Bundle;)V")
    def onEvent(self, eventType, params):
        pass

    # Android 14 language detection callback.
    @java_method("(Landroid/os/Bundle;)V")
    def onLanguageDetection(self, results):
        pass


class VoiceService:
    def __init__(self):
        self.Context = autoclass("android.content.Context")
        self.Intent = autoclass("android.content.Intent")
        self.RecognizerIntent = autoclass("android.speech.RecognizerIntent")
        self.SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
        self.PythonService = autoclass("org.kivy.android.PythonService")
        self.TTS = autoclass("android.speech.tts.TextToSpeech")
        self.Locale = autoclass("java.util.Locale")

        self.context = self.PythonService.mService
        self.listener = RecognitionListener(self)
        self.recognizer = None
        self.tts = None
        self.active = True
        self.awake = False
        self.starting = False
        self.last_text = ""
        self.last_start = 0

        files = self.context.getFilesDir().getAbsolutePath()
        self.event_file = os.path.join(str(files), "jarvis_voice_event.txt")

        self.init_tts()
        self.restart_listener(0.8)

    def init_tts(self):
        class TTSListener(PythonJavaClass):
            __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]

            @java_method("(I)V")
            def onInit(self, status):
                pass

        self.tts = self.TTS(self.context, TTSListener())

    def speak(self, text):
        try:
            self.tts.speak(
                text,
                self.TTS.QUEUE_FLUSH,
                None,
                "jarvis_" + str(int(time.time() * 1000))
            )
        except Exception:
            pass

    def notify_app(self, event):
        try:
            with open(self.event_file, "w", encoding="utf-8") as f:
                f.write(event)
        except Exception:
            pass

    def make_intent(self):
        intent = self.Intent(self.RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(
            self.RecognizerIntent.EXTRA_LANGUAGE_MODEL,
            self.RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
        )
        intent.putExtra(self.RecognizerIntent.EXTRA_MAX_RESULTS, 3)
        intent.putExtra(self.RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)

        # Android 14+ can detect/switch between Hindi and English.
        try:
            intent.putExtra(
                self.RecognizerIntent.EXTRA_ENABLE_LANGUAGE_DETECTION, True
            )
            intent.putExtra(
                self.RecognizerIntent.EXTRA_ENABLE_LANGUAGE_SWITCH,
                self.RecognizerIntent.LANGUAGE_SWITCH_BALANCED
            )
            intent.putExtra(
                self.RecognizerIntent.EXTRA_LANGUAGE_DETECTION_ALLOWED_LANGUAGES,
                ["en-IN", "hi-IN"]
            )
            intent.putExtra(
                self.RecognizerIntent.EXTRA_LANGUAGE_SWITCH_ALLOWED_LANGUAGES,
                ["en-IN", "hi-IN"]
            )
        except Exception:
            intent.putExtra(self.RecognizerIntent.EXTRA_LANGUAGE, "en-IN")

        return intent

    def start_listening(self):
        if not self.active or self.starting:
            return

        self.starting = True
        try:
            if self.recognizer is not None:
                try:
                    self.recognizer.destroy()
                except Exception:
                    pass

            self.recognizer = self.SpeechRecognizer.createSpeechRecognizer(self.context)
            self.recognizer.setRecognitionListener(self.listener)
            self.last_start = time.time()
            self.recognizer.startListening(self.make_intent())
        except Exception:
            self.schedule_restart(1.5)
        finally:
            self.starting = False

    def stop_listening(self):
        try:
            if self.recognizer is not None:
                self.recognizer.stopListening()
        except Exception:
            pass

    def schedule_restart(self, delay=1.0):
        if not self.active:
            return
        threading.Timer(delay, self.start_listening).start()

    def restart_listener(self, delay=0.8):
        self.schedule_restart(delay)

    def on_partial(self, results):
        try:
            arr = results.getStringArrayList(
                self.SpeechRecognizer.RESULTS_RECOGNITION
            )
            if arr and arr.size() > 0:
                self.process_text(str(arr.get(0)), partial=True)
        except Exception:
            pass

    def on_results(self, results):
        try:
            arr = results.getStringArrayList(
                self.SpeechRecognizer.RESULTS_RECOGNITION
            )
            if arr and arr.size() > 0:
                self.process_text(str(arr.get(0)), partial=False)
        except Exception:
            self.schedule_restart(0.8)

    def on_error(self, error):
        # SpeechRecognizer reports many normal transient errors such as
        # NO_MATCH, TIMEOUT and BUSY. Recreate the recognizer instead of
        # leaving the assistant silent.
        self.schedule_restart(1.0)

    def process_text(self, text, partial=False):
        text = re.sub(r"\s+", " ", text.strip())
        if not text or text == self.last_text and partial:
            return

        if partial:
            low = text.lower()
            if not self.awake and self.contains_wake(low):
                self.activate_wake(text)
            return

        self.last_text = text
        low = text.lower()

        if not self.awake:
            if self.contains_wake(low):
                remainder = self.remove_wake(text)
                self.activate_wake(text)

                if remainder.strip():
                    self.execute_command(remainder.strip())
            return

        self.awake = False
        if low in {"cancel", "stop", "never mind", "नहीं", "रहने दो"}:
            self.speak("Okay Boss.")
            self.notify_app("COMMAND|" + low)
            self.schedule_restart(1.0)
            return

        self.execute_command(text)

    @staticmethod
    def contains_wake(text):
        normalized = re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", text.lower())
        return bool(re.search(r"\bjarvis\b", normalized)) or "जार्विस" in normalized

    @staticmethod
    def remove_wake(text):
        return re.sub(r"(?i)\bjarvis\b", "", text).replace("जार्विस", "").strip()

    def activate_wake(self, original):
        if self.awake:
            return

        self.awake = True
        self.stop_listening()
        self.notify_app("WAKE|" + original)

        # Required wake response.
        self.speak("Yes Boss. How can I help you?")

        # Give TTS a moment to finish before opening the microphone again.
        self.schedule_restart(2.2)

    def execute_command(self, command):
        try:
            # Import here so service startup stays light.
            from jarvis_core import JarvisCore

            files = self.context.getFilesDir().getAbsolutePath()
            data_file = os.path.join(str(files), "jarvis_data.json")
            core = JarvisCore(data_file)
            response = core.handle(command)

            self.notify_app("COMMAND|" + command)
            self.speak(self.clean_for_speech(response))
        except Exception:
            self.speak("Sorry Boss, I could not process that command.")
        finally:
            self.awake = False
            self.schedule_restart(1.0)

    @staticmethod
    def clean_for_speech(text):
        # Keep spoken responses concise; the GUI still shows the full content.
        text = text.replace("[DONE]", "done").replace("[ ]", "")
        text = re.sub(r"\s+", " ", text)
        if len(text) > 500:
            text = text[:500] + "."
        return text


def main():
    service = VoiceService()
    try:
        while service.active:
            time.sleep(1)
    except KeyboardInterrupt:
        service.active = False


if __name__ == "__main__":
    main()
