# ============================================================
# logger.py
# Thread-safe Activity Logger  (STEP 7a)
#
# What this file does:
#   Stores every event (request, waiting, started, finished...)
#   in a list, with the time and the thread name.
#
# Purpose:
#   print() only shows text in the terminal. Our Streamlit
#   dashboard needs to READ the events later and show them as
#   "Live Activity". So events must be STORED, not just printed.
#
# Real-life example:
#   A guard's register at a building gate. Whoever comes or
#   goes is written down with time and name. Later the manager
#   (our Streamlit UI) opens the register and reads it.
#
# Important components:
#   - ActivityLogger class
#   - log()        : add one event (thread-safe)
#   - get_events() : get a copy of all events
#   - clear()      : empty the register (for Reset Simulation)
#
# Why a Lock here?
#   The register itself is a SHARED RESOURCE. If 5 threads
#   write to the list at the same moment, entries can get
#   mixed up. So we protect it with a lock.
#
# Project stage:
#   Step 7a - logging support (no Streamlit yet).
#
# How to test this file alone:
#   python logger.py
# ============================================================

import threading
import time


class ActivityLogger:

    def __init__(self, echo=False):
        # Protects the events list (shared resource)
        self._lock = threading.Lock()

        # The "register": a list of event dictionaries
        self._events = []

        # All times are shown as seconds since the logger started
        self._start_time = time.time()

        # echo=True also prints each event in the terminal
        # (useful while testing)
        self.echo = echo

    def log(self, thread_name, message, kind="info"):
        """
        Add one event to the register.

        thread_name : e.g. "Reader-1"
        message     : e.g. "started reading"
        kind        : "request", "waiting", "acquired",
                      "started", "finished" or "info"
                      (UI will use this to pick an icon later)
        """

        with self._lock:
            event = {
                "time": round(time.time() - self._start_time, 1),
                "thread": thread_name,
                "message": message,
                "kind": kind,
            }
            self._events.append(event)

            if self.echo:
                print(f"[{event['time']:4.1f}s] "
                      f"{thread_name}: {message}")

    def get_events(self):
        """Return a COPY of all events (safe to read anywhere)."""

        with self._lock:
            return list(self._events)

    def clear(self):
        """Empty the register and restart the clock."""

        with self._lock:
            self._events.clear()
            self._start_time = time.time()


# ============================================================
# SELF-TEST (runs only when you do: python logger.py)
# 5 threads write 3 events each at the same time.
# If the lock works, we must get exactly 15 events.
# ============================================================

def _worker(logger, name):
    logger.log(name, "requested access", kind="request")
    time.sleep(0.1)
    logger.log(name, "started reading", kind="started")
    time.sleep(0.1)
    logger.log(name, "finished reading", kind="finished")


if __name__ == "__main__":

    logger = ActivityLogger(echo=True)

    threads = []
    for i in range(1, 6):
        t = threading.Thread(target=_worker, args=(logger, f"Reader-{i}"))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    events = logger.get_events()
    print(f"\nTotal events stored: {len(events)} (expected 15)")

    if len(events) == 15:
        print("PASS: logger is thread-safe.")
    else:
        print("FAIL: some events were lost.")