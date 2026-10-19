# ============================================================
# synchronization.py
# Reader-Writer Synchronization Simulator  (STEP 5 + 8a + 10a)
#
# What this file does:
#   It contains the REAL Reader-Writer synchronization logic.
#   Nothing in this file prints anything or knows about
#   Streamlit. It only decides: "Can this thread enter now,
#   or must it wait?"
#
# Purpose:
#   - Many Readers may read the shared file TOGETHER.
#   - A Writer must get EXCLUSIVE access (no Reader, no
#     other Writer at the same time).
#   - Three policies (modes) that can be switched:
#       1. "reader_preference" -> Readers go first
#                                 (Writer may starve)
#       2. "writer_preference" -> a waiting Writer blocks ALL
#                                 new Readers (strict; no Writer
#                                 starvation, but Readers that
#                                 could have joined are blocked)
#       3. "balanced"          -> a waiting Writer lets at most
#                                 K new Readers join, then blocks
#                                 the rest. Readers still share
#                                 the file, and the Writer's wait
#                                 is BOUNDED (no starvation).
#
# Important components:
#   - ReadWriteLock class
#   - counters: active_readers, active_writers,
#               waiting_readers, waiting_writers,
#               readers_bypassed (used only in balanced mode)
#   - 4 methods : acquire_read, release_read,
#                 acquire_write, release_write
#   - set_mode(), set_max_bypass()
#   - get_status(): safe snapshot of counters for the dashboard
#   - on_wait (optional callback) : lets the caller know, at the
#     exact moment, that its thread is about to WAIT
#
# OS concept used by "balanced" mode:
#   BOUNDED WAITING - no thread should wait forever; there must
#   be a limit on how many others can go ahead of it.
#   (Critical-section requirements: Mutual Exclusion, Progress,
#    Bounded Waiting.)
#
# Project stage:
#   Step 5  - actual Reader-Writer synchronization.
#   Step 8a - added the optional on_wait callback.
#   Step 10a- added the "balanced" (bounded bypass) mode.
#
# How this maps to the CLASSIC textbook solution:
#   Textbook                 ->  This file
#   ------------------------------------------------------
#   read_count               ->  active_readers
#   mutex (protects count)   ->  the lock inside Condition
#   rw_lock / wrt (resource) ->  the rule in _writer_can_enter()
#   "first reader locks,     ->  Readers enter only if no
#    last reader unlocks"        Writer is active; Writer enters
#                                only when active_readers == 0
#   Same idea, same mutual exclusion - just written with a
#   Condition so we can also track WAITING threads.
#
# How to test this file alone:
#   python synchronization.py
# ============================================================

import threading


# The three policies (modes) supported by our lock
READER_PREFERENCE = "reader_preference"
WRITER_PREFERENCE = "writer_preference"
BALANCED = "balanced"

ALL_MODES = (READER_PREFERENCE, WRITER_PREFERENCE, BALANCED)

# In balanced mode: how many new Readers may go ahead of a
# waiting Writer before new Readers are blocked
DEFAULT_MAX_BYPASS = 2


class ReadWriteLock:
    """
    A Reader-Writer lock built using threading.Condition.

    Think of a Condition as a RECEPTIONIST:
      - Every thread must ask the receptionist before entering.
      - If the rule says "not allowed", the thread sits in the
        waiting area (wait()).
      - When someone leaves, the receptionist rings a bell
        (notify_all()) and every waiting thread checks the
        rule again.
    """

    def __init__(self, mode=WRITER_PREFERENCE,
                 max_bypass=DEFAULT_MAX_BYPASS):
        # One Condition = one lock + waiting area + bell.
        # ALL counters below are changed ONLY while holding
        # this lock, so they never get corrupted
        # (this is how we avoid a race condition).
        self._condition = threading.Condition()

        self.mode = mode

        # Balanced mode: the limit K, and how many Readers have
        # already gone ahead of the CURRENT waiting Writer(s)
        self.max_bypass = max_bypass
        self.readers_bypassed = 0

        # How many threads are INSIDE the critical section now
        self.active_readers = 0
        self.active_writers = 0

        # How many threads are WAITING outside right now
        self.waiting_readers = 0
        self.waiting_writers = 0

    # --------------------------------------------------------
    # MODE SWITCH AND SETTINGS
    # --------------------------------------------------------

    def set_mode(self, mode):
        """Switch between the three modes."""

        if mode not in ALL_MODES:
            raise ValueError(f"Unknown mode: {mode}")

        with self._condition:
            self.mode = mode
            # Start counting afresh in the new mode
            self.readers_bypassed = 0
            # Rules changed, so wake everyone to re-check
            self._condition.notify_all()

    def set_max_bypass(self, max_bypass):
        """
        Change K for balanced mode.
        K = 0 means: no Reader may go ahead of a waiting Writer
        (same behaviour as strict writer_preference).
        """

        if max_bypass < 0:
            raise ValueError("max_bypass cannot be negative")

        with self._condition:
            self.max_bypass = max_bypass
            self._condition.notify_all()

    # --------------------------------------------------------
    # THE RULES (who is allowed to enter?)
    # These are always called while the Condition lock is held.
    # --------------------------------------------------------

    def _reader_can_enter(self):
        # Rule 1: a Reader can NEVER enter while a Writer is writing
        if self.active_writers > 0:
            return False

        # Rule 2: what to do when a Writer is WAITING
        if self.waiting_writers > 0:

            # Strict writer preference: block every new Reader.
            # This is what prevents Writer starvation.
            if self.mode == WRITER_PREFERENCE:
                return False

            # Balanced: let at most K Readers go ahead of the
            # waiting Writer, then block the rest.
            # (bounded waiting for the Writer)
            if (self.mode == BALANCED
                    and self.readers_bypassed >= self.max_bypass):
                return False

        # reader_preference mode never blocks a Reader here
        return True

    def _writer_can_enter(self):
        # A Writer needs EXCLUSIVE access:
        # nobody reading AND nobody writing.
        return self.active_readers == 0 and self.active_writers == 0

    # --------------------------------------------------------
    # READER SIDE
    # --------------------------------------------------------

    def acquire_read(self, on_wait=None):
        """
        Called by a Reader BEFORE reading the file.

        on_wait (optional): a small function that is called ONCE,
        just before this thread has to wait. It runs inside the
        lock, so keep it tiny (for example: just write a log line).
        """

        with self._condition:
            # I have arrived and I am waiting (until proven otherwise)
            self.waiting_readers += 1

            told_caller = False

            # Sleep in the waiting area until the rule allows us.
            # 'while' (not 'if') because after waking up we must
            # check the rule AGAIN.
            while not self._reader_can_enter():

                # Tell the caller "I am about to wait" - only ONCE,
                # even if we wake up and have to wait again
                if on_wait is not None and not told_caller:
                    on_wait()
                    told_caller = True

                self._condition.wait()

            # Allowed: move from "waiting" to "active"
            # (both changes happen inside ONE lock, so the
            #  dashboard never sees a thread "disappear")
            self.waiting_readers -= 1
            self.active_readers += 1

            # Balanced mode: if a Writer is waiting right now,
            # this Reader has just gone AHEAD of it - count it.
            if self.mode == BALANCED and self.waiting_writers > 0:
                self.readers_bypassed += 1

    def release_read(self):
        """Called by a Reader AFTER reading the file."""

        with self._condition:
            self.active_readers -= 1

            # Last Reader leaving? A waiting Writer may now enter.
            if self.active_readers == 0:
                self._condition.notify_all()

    # --------------------------------------------------------
    # WRITER SIDE
    # --------------------------------------------------------

    def acquire_write(self, on_wait=None):
        """
        Called by a Writer BEFORE writing to the file.

        on_wait (optional): same idea as in acquire_read().
        """

        with self._condition:
            self.waiting_writers += 1

            told_caller = False

            while not self._writer_can_enter():

                if on_wait is not None and not told_caller:
                    on_wait()
                    told_caller = True

                self._condition.wait()

            self.waiting_writers -= 1
            self.active_writers += 1

            # The Writer finally got its turn, so the
            # "Readers who went ahead of it" count starts again
            self.readers_bypassed = 0

    def release_write(self):
        """Called by a Writer AFTER writing to the file."""

        with self._condition:
            self.active_writers -= 1

            # Wake everyone: waiting Readers AND waiting Writers
            # will re-check their rules.
            self._condition.notify_all()

    # --------------------------------------------------------
    # STATUS SNAPSHOT (for logs / dashboard)
    # --------------------------------------------------------

    def get_status(self):
        """
        Returns all counters together, taken under the lock,
        so the numbers are always consistent with each other.
        """

        with self._condition:

            if self.active_writers > 0:
                resource_status = "WRITING"
            elif self.active_readers > 0:
                resource_status = "READING"
            else:
                resource_status = "IDLE"

            return {
                "mode": self.mode,
                "active_readers": self.active_readers,
                "active_writers": self.active_writers,
                "waiting_readers": self.waiting_readers,
                "waiting_writers": self.waiting_writers,
                "resource_status": resource_status,
                "readers_bypassed": self.readers_bypassed,
                "max_bypass": self.max_bypass,
            }


# ============================================================
# SELF-TEST
# (runs only when you do: python synchronization.py)
#
# Part 1: on_wait callback
# Part 2: balanced mode (limit K = 2)
# Part 3: balanced mode with K = 0 (same as strict)
# ============================================================

def _check(label, condition):
    print(f"{'PASS' if condition else 'FAIL'}: {label}")
    return condition


def _try_enter_read(rw):
    """
    Start a helper thread that calls acquire_read().
    Returns an Event that becomes 'set' once the Reader is INSIDE.
    (We use a thread so that a blocked Reader cannot freeze the test.)
    """

    entered = threading.Event()

    def task():
        rw.acquire_read()
        entered.set()

    threading.Thread(target=task, daemon=True).start()
    return entered


if __name__ == "__main__":

    import time

    results = []

    # --------------------------------------------------------
    # PART 1: on_wait callback
    # --------------------------------------------------------

    rw = ReadWriteLock(mode=WRITER_PREFERENCE)
    calls = []

    # Test 1: nobody inside -> Writer enters at once,
    #         callback must NOT be called
    rw.acquire_write(on_wait=lambda: calls.append("writer-free"))
    rw.release_write()
    results.append(_check("no waiting -> callback not called",
                          calls == []))

    # Test 2: a Reader is inside -> Writer must wait,
    #         callback must be called exactly once
    rw.acquire_read()

    def waiting_writer():
        rw.acquire_write(on_wait=lambda: calls.append("writer-waited"))
        rw.release_write()

    t1 = threading.Thread(target=waiting_writer)
    t1.start()
    time.sleep(0.5)                      # let the Writer start waiting

    results.append(_check(
        "Writer is counted as waiting",
        rw.get_status()["waiting_writers"] == 1))

    rw.release_read()                    # Reader leaves -> Writer enters
    t1.join()
    results.append(_check("Writer waited -> callback called once",
                          calls == ["writer-waited"]))

    # Test 3: a Writer is inside -> Reader must wait,
    #         callback must be called exactly once
    calls.clear()
    rw.acquire_write()

    def waiting_reader():
        rw.acquire_read(on_wait=lambda: calls.append("reader-waited"))
        rw.release_read()

    t2 = threading.Thread(target=waiting_reader)
    t2.start()
    time.sleep(0.5)

    rw.release_write()
    t2.join()
    results.append(_check("Reader waited -> callback called once",
                          calls == ["reader-waited"]))

    # --------------------------------------------------------
    # PART 2: balanced mode, K = 2
    #   Reader-1 inside, Writer-1 waiting
    #   Reader-2 and Reader-3 may go ahead, Reader-4 must wait
    # --------------------------------------------------------

    rw2 = ReadWriteLock(mode=BALANCED, max_bypass=2)
    let_writer_finish = threading.Event()

    def balanced_writer():
        rw2.acquire_write()
        let_writer_finish.wait()         # hold the file until told
        rw2.release_write()

    rw2.acquire_read()                   # Reader-1 is inside
    tw = threading.Thread(target=balanced_writer)
    tw.start()
    time.sleep(0.3)                      # Writer-1 is now waiting

    ev2 = _try_enter_read(rw2)
    results.append(_check(
        "balanced: Reader-2 goes ahead of waiting Writer",
        ev2.wait(0.5)))

    ev3 = _try_enter_read(rw2)
    results.append(_check(
        "balanced: Reader-3 goes ahead (limit K = 2 reached)",
        ev3.wait(0.5)))

    ev4 = _try_enter_read(rw2)
    results.append(_check(
        "balanced: Reader-4 is BLOCKED after the limit",
        not ev4.wait(0.5)))

    # Reader-1, 2, 3 leave -> Writer-1 must go before Reader-4
    rw2.release_read()
    rw2.release_read()
    rw2.release_read()
    time.sleep(0.3)

    status = rw2.get_status()
    results.append(_check(
        "balanced: Writer got exclusive access before Reader-4",
        status["active_writers"] == 1
        and status["active_readers"] == 0
        and not ev4.is_set()))

    results.append(_check(
        "balanced: bypass counter reset when Writer entered",
        status["readers_bypassed"] == 0))

    let_writer_finish.set()              # Writer-1 finishes
    tw.join()

    results.append(_check(
        "balanced: Reader-4 enters after the Writer finished",
        ev4.wait(1)))
    rw2.release_read()                   # Reader-4 leaves

    # --------------------------------------------------------
    # PART 3: balanced mode with K = 0 behaves like strict
    # --------------------------------------------------------

    rw3 = ReadWriteLock(mode=BALANCED, max_bypass=0)
    rw3.acquire_read()                   # Reader-1 inside

    def quick_writer():
        rw3.acquire_write()
        rw3.release_write()

    tw3 = threading.Thread(target=quick_writer)
    tw3.start()
    time.sleep(0.3)                      # Writer is waiting

    ev_late = _try_enter_read(rw3)
    results.append(_check(
        "K = 0: new Reader is blocked (same as strict writer preference)",
        not ev_late.wait(0.5)))

    rw3.release_read()                   # Writer goes, then Reader
    tw3.join()
    ev_late.wait(1)
    rw3.release_read()

    print()
    print("ALL TESTS PASSED" if all(results) else "SOME TESTS FAILED")