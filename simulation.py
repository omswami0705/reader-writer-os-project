# ============================================================
# simulation.py
# Simulation Controller  (STEP 8b)
#
# What this file does:
#   This is the "controller" of the project. It creates the
#   Reader and Writer THREADS and connects the 3 parts we
#   already built:
#       synchronization.py -> ReadWriteLock   (who may enter)
#       file_manager.py    -> read/append     (the real work)
#       logger.py          -> ActivityLogger  (the register)
#
# Purpose:
#   Streamlit (app.py) will talk ONLY to this file. It will
#   call methods like start_reader() / start_writer() and then
#   read get_status() / get_events() to show them on screen.
#   So the real OS logic stays in Python, not in the UI.
#
# Architecture:
#       Streamlit UI  ->  Simulation  ->  Reader/Writer threads
#                                             |
#                              ReadWriteLock + data.txt + Logger
#
# Important components:
#   - Simulation class
#   - _reader_task / _writer_task : what each thread does
#   - start_reader(), start_writer(), start_readers(n),
#     start_writers(n), run_demo()
#   - set_mode(), reset()
#   - get_status(), get_events(), read_file_content()
#
# IMPORTANT: every start_* method returns IMMEDIATELY. The
#   thread keeps running in the background. (If we waited for
#   the thread, the Streamlit button would hang for seconds.)
#
# Project stage:
#   Step 8b - connecting lock + file + logger (no Streamlit yet).
#
# How to test this file alone:
#   python simulation.py
#   (WARNING: the test resets data.txt to its starting content
#    and then adds one line to it.)
# ============================================================

import threading
import time

import file_manager
from logger import ActivityLogger
from synchronization import ReadWriteLock, WRITER_PREFERENCE


class Simulation:

    def __init__(self, mode=WRITER_PREFERENCE, read_time=4, write_time=3):
        # How long a Reader / Writer "works" (simulated with sleep)
        # so that states stay visible on the screen long enough.
        self.read_time = read_time
        self.write_time = write_time

        # The 2 shared helpers used by ALL threads
        self.lock = ReadWriteLock(mode=mode)
        self.logger = ActivityLogger()

        # Used only for giving names (Reader-1, Reader-2, ...)
        # and for the list of threads. A small lock protects them
        # because the UI and demo thread can call us at same time.
        self._state_lock = threading.Lock()
        self._reader_count = 0
        self._writer_count = 0
        self._threads = []

    # --------------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------------

    def _next_name(self, kind):
        """Create the next automatic name: Reader-1, Reader-2, ..."""

        with self._state_lock:
            if kind == "Reader":
                self._reader_count += 1
                return f"Reader-{self._reader_count}"
            else:
                self._writer_count += 1
                return f"Writer-{self._writer_count}"

    def _launch(self, target, args):
        """Start a background thread and remember it."""

        thread = threading.Thread(target=target, args=args, daemon=True)

        with self._state_lock:
            # Forget threads that are already finished
            self._threads = [t for t in self._threads if t.is_alive()]
            self._threads.append(thread)

        thread.start()

    # --------------------------------------------------------
    # WHAT A READER THREAD DOES
    # --------------------------------------------------------

    def _reader_task(self, name):

        self.logger.log(name, "requested access", kind="request")

        # Ask the lock for permission. If we must wait, the lock
        # calls on_wait() just before putting us to sleep.
        self.lock.acquire_read(
            on_wait=lambda: self.logger.log(
                name, "waiting for resource", kind="waiting")
        )

        # try/finally: even if something fails below, we MUST
        # release the lock, otherwise everyone waits forever
        # (that would be a deadlock-like situation).
        try:
            self.logger.log(name, "acquired shared access",
                            kind="acquired")
            self.logger.log(name, "started reading", kind="started")

            # ---- CRITICAL SECTION (reading) ----
            try:
                content = file_manager.read_data()
                if content == "":
                    self.logger.log(name, "file is empty", kind="info")
                else:
                    self.logger.log(
                        name, f"read {len(content)} characters",
                        kind="info")
            except FileNotFoundError:
                self.logger.log(name, "ERROR: data.txt not found",
                                kind="error")

            time.sleep(self.read_time)      # simulate reading time
            # ------------------------------------

            self.logger.log(name, "finished reading", kind="finished")

        finally:
            self.lock.release_read()

    # --------------------------------------------------------
    # WHAT A WRITER THREAD DOES
    # --------------------------------------------------------

    def _writer_task(self, name, text):

        self.logger.log(name, "requested access", kind="request")

        self.lock.acquire_write(
            on_wait=lambda: self.logger.log(
                name, "waiting for resource", kind="waiting")
        )

        try:
            self.logger.log(name, "acquired exclusive access",
                            kind="acquired")
            self.logger.log(name, "started writing", kind="started")

            # ---- CRITICAL SECTION (writing) ----
            try:
                file_manager.append_data(text)
                self.logger.log(name, "wrote one line to data.txt",
                                kind="info")
            except FileNotFoundError:
                self.logger.log(name, "ERROR: data.txt not found",
                                kind="error")

            time.sleep(self.write_time)     # simulate writing time
            # ------------------------------------

            self.logger.log(name, "finished writing", kind="finished")

        finally:
            self.lock.release_write()

    # --------------------------------------------------------
    # METHODS THAT STREAMLIT WILL CALL (all return immediately)
    # --------------------------------------------------------

    def start_reader(self):
        """Start ONE Reader thread. Returns its name."""

        name = self._next_name("Reader")
        self._launch(self._reader_task, (name,))
        return name

    def start_writer(self, text=None):
        """
        Start ONE Writer thread. Returns its name.
        text: what to write; if not given, a default line is used.
        """

        name = self._next_name("Writer")
        if not text:
            text = f"Data written by {name}"
        self._launch(self._writer_task, (name, text))
        return name

    def start_readers(self, n):
        """Start n Readers at (almost) the same moment."""

        return [self.start_reader() for _ in range(n)]

    def start_writers(self, n):
        """Start n Writers at (almost) the same moment."""

        return [self.start_writer() for _ in range(n)]

    def run_demo(self):
        """
        Reader-Writer demo (runs in the background):
          t=0  3 Readers arrive
          t=1  1 Writer arrives   (has to wait for the Readers)
          t=2  1 more Reader      (waits too, in writer_preference)
        """

        def demo_steps():
            self.start_readers(3)
            time.sleep(1)
            self.start_writer()
            time.sleep(1)
            self.start_reader()

        # The demo itself runs in its own thread so the UI is not blocked
        self._launch(demo_steps, ())

    # --------------------------------------------------------
    # MODE, STATUS, EVENTS, RESET
    # --------------------------------------------------------

    def set_mode(self, mode):
        """Switch between reader_preference and writer_preference."""

        self.lock.set_mode(mode)
        self.logger.log("System", f"mode changed to {mode}", kind="info")

    def is_busy(self):
        """True if any Reader/Writer/demo thread is still running."""

        with self._state_lock:
            self._threads = [t for t in self._threads if t.is_alive()]
            return len(self._threads) > 0

    def get_status(self):
        """Counters from the lock + whether threads are running."""

        status = self.lock.get_status()
        status["busy"] = self.is_busy()
        return status

    def get_events(self):
        """All logged events (a copy)."""

        return self.logger.get_events()

    def read_file_content(self):
        """
        Current file text for the dashboard.
        Returns None if the file is missing, "" if it is empty.
        (This is only for DISPLAY, it is not a Reader thread.)
        """

        try:
            return file_manager.read_data()
        except FileNotFoundError:
            return None

    def reset(self):
        """
        Clear logs, counters and put data.txt back to its starting
        content. Allowed ONLY when no thread is running.
        Returns True if reset was done, False if refused.
        """

        if self.is_busy():
            return False

        with self._state_lock:
            self._reader_count = 0
            self._writer_count = 0

        self.logger.clear()
        file_manager.reset_file()
        return True


# ============================================================
# SELF-TEST (runs only when you do: python simulation.py)
#
# Scenario (writer_preference mode):
#   t=0  Reader-1, Reader-2, Reader-3
#   t=1  Writer-1
#   t=2  Reader-4
# Then we replay the log to check:
#   - Writer never overlapped with a Reader or another Writer
#   - Several Readers really read together
# ============================================================

if __name__ == "__main__":

    file_manager.reset_file()          # start from clean data.txt

    sim = Simulation(read_time=3, write_time=2)

    print("\n=== Running simulation test (writer_preference) ===\n")

    sim.start_readers(3)
    time.sleep(1)
    sim.start_writer()
    time.sleep(1)
    sim.start_reader()

    # Show the live status every second until everything finishes
    while sim.is_busy():
        s = sim.get_status()
        print(f"STATUS -> {s['resource_status']:8} | "
              f"active R={s['active_readers']} W={s['active_writers']} | "
              f"waiting R={s['waiting_readers']} W={s['waiting_writers']}")
        time.sleep(1)

    # ---- Print the activity log ----
    print("\n--- Activity log ---")
    events = sim.get_events()
    for e in events:
        print(f"[{e['time']:4.1f}s] {e['thread']}: {e['message']}")

    # ---- Replay the log and check the rules ----
    readers_inside = 0
    writer_inside = False
    max_readers = 0
    violations = []

    for e in events:
        is_reader = e["thread"].startswith("Reader")
        is_writer = e["thread"].startswith("Writer")

        if e["kind"] == "started" and is_reader:
            if writer_inside:
                violations.append(f"{e['thread']} started during a write")
            readers_inside += 1
            max_readers = max(max_readers, readers_inside)

        elif e["kind"] == "started" and is_writer:
            if writer_inside or readers_inside > 0:
                violations.append(f"{e['thread']} was not exclusive")
            writer_inside = True

        elif e["kind"] == "finished" and is_reader:
            readers_inside -= 1

        elif e["kind"] == "finished" and is_writer:
            writer_inside = False

    # ---- Final file content ----
    print("\n--- data.txt now ---")
    print(sim.read_file_content())

    print("=== RESULT ===")
    print(f"Max Readers reading together : {max_readers}")
    print(f"Rule violations              : {len(violations)}")
    for v in violations:
        print("  -", v)

    file_ok = sim.read_file_content().endswith("Data written by Writer-1\n")

    if not violations and max_readers > 1 and file_ok:
        print("PASS: Readers overlapped, Writer was exclusive, "
              "file was updated.")
    else:
        print("FAIL: check the log above.")