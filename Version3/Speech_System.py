
import pyttsx3
import threading
import queue
import time
import System_Configuration as System_Configuration

speech_queue = queue.Queue()
speaking = threading.Event()


def speech_worker():
    engine = pyttsx3.init()

    voices = engine.getProperty('voices')

    if len(voices) > System_Configuration.AI_VOICE_INDEX:
        engine.setProperty(
            'voice',
            voices[System_Configuration.AI_VOICE_INDEX].id
        )

    # Start a non-blocking speech loop
    engine.startLoop(False)

    try:
        while True:

            # Process speech commands
            try:
                while True:
                    action, text = speech_queue.get_nowait()

                    if action == "stop":
                        engine.stop()
                        speaking.clear()

                    elif action == "speak":
                        engine.say(text)
                        speaking.set()

            except queue.Empty:
                pass

            # Process speech engine events
            engine.iterate()

            if not engine.isBusy():
                speaking.clear()

            time.sleep(0.01)

    except Exception as e:
        print(f"Speech worker error: {e}")

    finally:
        engine.endLoop()


# Start the speech engine worker once
worker = threading.Thread(
    target=speech_worker,
    daemon=True
)
worker.start()


def speak(text):
    print(f"\nAssistant: {text}")

    # Remove pending speech requests
    with speech_queue.mutex:
        speech_queue.queue.clear()

    # Stop current speech, then speak new response
    speech_queue.put(("stop", None))
    speech_queue.put(("speak", text))


def stop_speaking():
    # Remove all pending speech
    with speech_queue.mutex:
        speech_queue.queue.clear()

    # Send stop command
    speech_queue.put(("stop", None))



def is_speaking():
    return speaking.is_set()
