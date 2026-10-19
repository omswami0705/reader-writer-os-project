# ============================================================
# main.py
# Reader-Writer Synchronization Based File Handling Utility
#
# Purpose:
# This version introduces both Reader and Writer threads.
#
# Readers read the shared data.txt file.
# Writers modify the same shared file.
#
# At this stage, synchronization is NOT implemented.
# This allows us to observe concurrent Reader and Writer
# operations before solving the synchronization problem.
# ============================================================

import threading
import time


FILE_NAME = "data.txt"


# A Lock allows only one thread at a time to enter
# the protected section of the program.
file_lock = threading.Lock()


# ============================================================
# READER
# ============================================================

def read_file(reader_name):
    """
    Reader function.

    The lock ensures that only one thread at a time
    can access the shared file.
    """

    print(f"{reader_name} requested to read.")

    time.sleep(1)

    print(f"{reader_name} is waiting for the lock...")

    with file_lock:

        print(f"{reader_name} acquired the lock.")
        print(f"{reader_name} started reading.")

        try:
            with open(FILE_NAME, "r") as file:
                content = file.read()

            print(f"{reader_name} read: {content.strip()}")

            # Simulate reading time
            time.sleep(2)

        except FileNotFoundError:
            print(f"{reader_name}: File not found.")

        print(f"{reader_name} finished reading.")

    print(f"{reader_name} released the lock.")

# ============================================================
# WRITER
# ============================================================

def write_file(writer_name, text):
    """
    Writer function.

    The writer must acquire the lock before modifying
    the shared file.
    """

    print(f"{writer_name} requested to write.")

    time.sleep(1)

    print(f"{writer_name} is waiting for the lock...")

    with file_lock:

        print(f"{writer_name} acquired the lock.")
        print(f"{writer_name} started writing.")

        try:
            with open(FILE_NAME, "a") as file:
                file.write(text + "\n")

            # Simulate writing time
            time.sleep(2)

        except Exception as error:
            print(f"{writer_name}: Error - {error}")

        print(f"{writer_name} finished writing.")

    print(f"{writer_name} released the lock.")
def run_reader_demo():
    """
    Creates multiple Reader threads.

    Multiple readers can execute concurrently.
    """

    print("\n--- Reader Thread Demo ---")

    reader1 = threading.Thread(
        target=read_file,
        args=("Reader-1",)
    )

    reader2 = threading.Thread(
        target=read_file,
        args=("Reader-2",)
    )

    reader3 = threading.Thread(
        target=read_file,
        args=("Reader-3",)
    )

    reader1.start()
    reader2.start()
    reader3.start()

    reader1.join()
    reader2.join()
    reader3.join()

    print("\nAll readers have finished.")


# ============================================================
# WRITER DEMO
# ============================================================

def run_writer_demo():
    """
    Creates multiple Writer threads.

    Multiple writers will attempt to modify the same file.
    Synchronization has not been added yet.
    """

    print("\n--- Writer Thread Demo ---")

    writer1 = threading.Thread(
        target=write_file,
        args=("Writer-1", "Data written by Writer-1")
    )

    writer2 = threading.Thread(
        target=write_file,
        args=("Writer-2", "Data written by Writer-2")
    )

    writer1.start()
    writer2.start()

    writer1.join()
    writer2.join()

    print("\nAll writers have finished.")


# ============================================================
# READER + WRITER DEMO
# ============================================================

def run_reader_writer_demo():
    """
    Runs Readers and Writers at approximately the same time.

    This is the important demonstration because both types
    of threads are accessing the same shared resource.
    """

    print("\n--- Reader + Writer Concurrent Demo ---")

    reader1 = threading.Thread(
        target=read_file,
        args=("Reader-1",)
    )

    reader2 = threading.Thread(
        target=read_file,
        args=("Reader-2",)
    )

    writer1 = threading.Thread(
        target=write_file,
        args=("Writer-1", "Data written by Writer-1")
    )

    # Start all threads
    reader1.start()
    reader2.start()
    writer1.start()

    # Wait for all threads to finish
    reader1.join()
    reader2.join()
    writer1.join()

    print("\nReader-Writer demo completed.")


# ============================================================
# MAIN MENU
# ============================================================

def main():
    """
    Main menu for the project.
    """

    while True:

        print("\n==========================================")
        print("     READER-WRITER FILE UTILITY")
        print("==========================================")

        print("1. Read File")
        print("2. Write to File")
        print("3. Run Reader Demo")
        print("4. Run Writer Demo")
        print("5. Run Reader + Writer Demo")
        print("6. Exit")

        choice = input("Enter your choice: ")

        # ----------------------------------------------------
        # Normal file reading
        # ----------------------------------------------------
        if choice == "1":

            try:
                with open(FILE_NAME, "r") as file:
                    print("\n--- File Content ---")
                    print(file.read())

            except FileNotFoundError:
                print("File not found.")

        # ----------------------------------------------------
        # Normal file writing
        # ----------------------------------------------------
        elif choice == "2":

            text = input("Enter text to write: ")

            with open(FILE_NAME, "a") as file:
                file.write(text + "\n")

            print("Data written successfully.")

        # ----------------------------------------------------
        # Reader demonstration
        # ----------------------------------------------------
        elif choice == "3":
            run_reader_demo()

        # ----------------------------------------------------
        # Writer demonstration
        # ----------------------------------------------------
        elif choice == "4":
            run_writer_demo()

        # ----------------------------------------------------
        # Reader + Writer demonstration
        # ----------------------------------------------------
        elif choice == "5":
            run_reader_writer_demo()

        # ----------------------------------------------------
        # Exit
        # ----------------------------------------------------
        elif choice == "6":
            print("Exiting program...")
            break

        else:
            print("Invalid choice. Please try again.")


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()