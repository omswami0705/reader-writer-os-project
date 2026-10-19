# ============================================================
# file_manager.py
# Shared File Handling  (STEP 7b)
#
# What this file does:
#   Does the actual work on the shared file data.txt:
#     - read_data()   : read the whole file
#     - append_data() : add a line at the end
#     - reset_file()  : put the file back to its starting content
#
# Purpose:
#   Keeps FILE WORK separate from SYNCHRONIZATION.
#   Real-life example: in a restaurant the chef cooks and the
#   waiter controls who goes to the kitchen. This file is the
#   chef; synchronization.py is the waiter.
#
# IMPORTANT: there is NO lock in this file on purpose.
#   If this file had its own lock, it would hide the real
#   Reader-Writer synchronization and the demo would be fake.
#   The lock (ReadWriteLock) is applied by the Reader/Writer
#   threads BEFORE they call these functions.
#
# Error handling (our decision):
#   If data.txt is missing, read_data() and append_data() raise
#   FileNotFoundError. The caller (Reader/Writer thread) will
#   catch it and log an error. An EMPTY file is NOT an error:
#   read_data() just returns an empty string "".
#
# Project stage:
#   Step 7b - file handling support (no Streamlit yet).
#
# How to test this file alone:
#   python file_manager.py
#   (the self-test uses a separate test_data_tmp.txt, so your
#    real data.txt is NOT touched)
# ============================================================

import os


FILE_NAME = "data.txt"

# Starting content of data.txt (also used by reset_file)
DEFAULT_CONTENT = (
    "This is the shared file.\n"
    "Reader-Writer synchronization project.\n"
)


def read_data(file_name=FILE_NAME):
    """
    Read and return the whole file content.

    Raises FileNotFoundError if the file does not exist.
    Returns "" if the file exists but is empty.
    """

    with open(file_name, "r") as file:
        return file.read()


def append_data(text, file_name=FILE_NAME):
    """
    Add one line of text at the END of the file.

    Raises FileNotFoundError if the file does not exist.
    (Normally open(..., "a") would silently create the file,
     so we check first to keep our missing-file rule.)
    """

    if not os.path.exists(file_name):
        raise FileNotFoundError(f"{file_name} not found")

    with open(file_name, "a") as file:
        file.write(text + "\n")


def reset_file(file_name=FILE_NAME):
    """
    Put the file back to its starting content.
    Creates the file if it is missing.
    Used by the 'Reset Simulation' button later.
    """

    with open(file_name, "w") as file:
        file.write(DEFAULT_CONTENT)


# ============================================================
# SELF-TEST (runs only when you do: python file_manager.py)
# Uses a temporary file, NOT your real data.txt
# ============================================================

def _check(label, condition):
    """Print PASS/FAIL for one check and return True/False."""
    print(f"{'PASS' if condition else 'FAIL'}: {label}")
    return condition


if __name__ == "__main__":

    test_file = "test_data_tmp.txt"
    results = []

    # Make sure the test file does not exist to begin with
    if os.path.exists(test_file):
        os.remove(test_file)

    # 1. Missing file -> read must raise FileNotFoundError
    try:
        read_data(test_file)
        results.append(_check("read on missing file raises error", False))
    except FileNotFoundError:
        results.append(_check("read on missing file raises error", True))

    # 2. Missing file -> append must raise FileNotFoundError
    try:
        append_data("hello", test_file)
        results.append(_check("append on missing file raises error", False))
    except FileNotFoundError:
        results.append(_check("append on missing file raises error", True))

    # 3. reset_file creates the file with the default content
    reset_file(test_file)
    results.append(_check(
        "reset_file creates file with default content",
        read_data(test_file) == DEFAULT_CONTENT
    ))

    # 4. Append adds a new line at the end
    append_data("Data written by Writer-1", test_file)
    results.append(_check(
        "append adds text at the end",
        read_data(test_file).endswith("Data written by Writer-1\n")
    ))

    # 5. Empty file is NOT an error, it returns ""
    with open(test_file, "w") as f:
        pass
    results.append(_check("empty file returns empty string",
                          read_data(test_file) == ""))

    # Clean up the temporary file
    os.remove(test_file)

    print()
    if all(results):
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")