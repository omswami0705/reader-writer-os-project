# ============================================================
# test_sync.py
# Terminal test for synchronization.py  (STEP 6)
#
# What this file does:
#   Runs a small scenario with Reader and Writer threads
#   using our ReadWriteLock, and prints a timeline so we can
#   SEE the synchronization working.
#
# Scenario (times are in seconds from start):
#   t=0  Reader-1, Reader-2, Reader-3 arrive (read for 4s)
#   t=1  Writer-1 arrives                     (write for 2s)
#   t=2  Reader-4 arrives                     (read for 4s)
#
# How to run:
#   python test_sync.py                      -> writer_preference
#   python test_sync.py reader_preference    -> reader_preference
#
# Project stage:
#   Step 6 - testing the lock WITHOUT Streamlit and WITHOUT
#   real file I/O (sleep() simulates the work).
#
# Self-check at the end:
#   - Did any Writer overlap with a Reader or another Writer?
#   - Did multiple Readers really read together?
# ============================================================

import sys
import threading
import time

from synchronization import (
    ReadWriteLock,
    READER_PREFERENCE,
    WRITER_PREFERENCE,
)

# ------------------------------------------------------------
# Helpers for clean, timestamped, non-garbled printing
# ------------------------------------------------------------

print_lock = threading.Lock()   # so two threads don't print mixed
start_time = time.time()

violations = []                 # any rule-breaking we detect
max_readers_together = 0        # most Readers seen reading at once


def log(message):
    """Print a message with seconds-since-start."""
    with print_lock:
        elapsed = time.time() - start_time
        print(f"[{elapsed:4.1f}s] {message}")


# ------------------------------------------------------------
# Reader and Writer thread functions
# ------------------------------------------------------------

def reader(rw, name, delay, read_time):
    global max_readers_together

    time.sleep(delay)                      # arrive at this time
    log(f"{name} requested access")

    rw.acquire_read()                      # <-- may WAIT here
    try:
        status = rw.get_status()
        log(f"{name} STARTED reading  "
            f"(readers inside={status['active_readers']})")

        # Self-check: no Writer may be active while we read
        if status["active_writers"] != 0:
            violations.append(f"{name} overlapped with a Writer!")

        with print_lock:
            max_readers_together = max(
                max_readers_together, status["active_readers"]
            )

        time.sleep(read_time)              # simulate reading
        log(f"{name} finished reading")
    finally:
        rw.release_read()


def writer(rw, name, delay, write_time):
    time.sleep(delay)
    log(f"{name} requested access")

    rw.acquire_write()                     # <-- may WAIT here
    try:
        status = rw.get_status()
        log(f"{name} STARTED writing (exclusive)")

        # Self-check: we must be completely alone
        if status["active_readers"] != 0 or status["active_writers"] != 1:
            violations.append(f"{name} was not exclusive!")

        time.sleep(write_time)             # simulate writing
        log(f"{name} finished writing")
    finally:
        rw.release_write()


# ------------------------------------------------------------
# Main: build the scenario, run it, show a live status monitor
# ------------------------------------------------------------

def main():
    mode = WRITER_PREFERENCE
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    rw = ReadWriteLock(mode=mode)
    print(f"\n=== Running test in mode: {rw.mode} ===\n")

    # (function, name, arrival delay, work time)
    plan = [
        (reader, "Reader-1", 0, 4),
        (reader, "Reader-2", 0, 4),
        (reader, "Reader-3", 0, 4),
        (writer, "Writer-1", 1, 2),
        (reader, "Reader-4", 2, 4),
    ]

    threads = []
    for func, name, delay, work in plan:
        t = threading.Thread(target=func, args=(rw, name, delay, work))
        threads.append(t)
        t.start()

    # Monitor: every second show the counters (like the future dashboard)
    while any(t.is_alive() for t in threads):
        s = rw.get_status()
        log(f"STATUS -> {s['resource_status']:8} | "
            f"active R={s['active_readers']} W={s['active_writers']} | "
            f"waiting R={s['waiting_readers']} W={s['waiting_writers']}")
        time.sleep(1)

    for t in threads:
        t.join()

    # --------------------------------------------------------
    # Final self-check report
    # --------------------------------------------------------
    print("\n=== RESULT ===")
    print(f"Max Readers reading together : {max_readers_together}")
    print(f"Rule violations              : {len(violations)}")
    for v in violations:
        print("  -", v)

    if not violations and max_readers_together > 1:
        print("PASS: Readers overlapped, Writer was exclusive.")
    else:
        print("FAIL: check the log above.")


if __name__ == "__main__":
    main()