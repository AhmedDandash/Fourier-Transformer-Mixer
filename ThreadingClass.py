import threading
import time


class WorkerSignals:
    canceled = threading.Event()


class WorkerThread(threading.Thread, ):
    def __init__(self, seconds, signals, main_window):
        super().__init__()
        self.seconds = seconds
        self.signals = signals
        self.main_window = main_window
        # Initialize progress value
        self.progress_value = 0

    def run(self):
        for i in range(self.seconds):
            time.sleep(1) # Sleep for one second in each iteration
            self.progressbar()

    def cancel(self):
        self.signals.canceled.set()
        self.join()

    def progressbar(self):
        # Update the progress bar manually
        if self.progress_value == 0:
         # Call ccollect_piece_data on the mixer when progress is at 0
            self.main_window.mixer.collect_piece_data()

        self.progress_value += 20
        self.main_window.ui.progressBar.setValue(self.progress_value)
        # If progress reaches 100, call mix_images on the mixer
        if self.progress_value == 100:
            self.main_window.mixer.mix_images()
