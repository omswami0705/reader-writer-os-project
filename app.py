# ============================================================
# app.py
# Streamlit User Interface  (STEP 9b - full version)
#
# What this file does:
#   Shows the complete dashboard in the browser:
#     1. Shared Resource : live content of data.txt
#     2. System Status   : active/waiting Readers and Writers,
#                          resource status, current mode
#     3. Controls        : start Reader/Writer, start many,
#                          run demo, switch mode, reset
#     4. Live Activity   : the event log with icons
#
# IMPORTANT (for viva):
#   This file has NO synchronization logic. It only
#   (1) tells the Simulation to start threads, and
#   (2) reads status/events/file content from the Simulation.
#   The real Reader-Writer logic is in synchronization.py
#   (Python threading + Condition).
#
# Streamlit-specific tricks used here:
#   1. st.cache_resource
#        Streamlit re-runs this whole script on every click.
#        cache_resource keeps ONE Simulation object alive across
#        re-runs, so running threads are not lost.
#   2. st.fragment(run_every=1)
#        Only the dashboard parts refresh automatically every
#        second. The control buttons are NOT inside a fragment,
#        so they are not re-drawn and clicks never get lost.
#
# Project stage:
#   Step 9b - complete UI (file content, mode selector, multiple
#   threads, demo, reset).
#
# How to run:
#   streamlit run app.py
# ============================================================

import streamlit as st

from simulation import Simulation
from synchronization import READER_PREFERENCE, WRITER_PREFERENCE


st.set_page_config(page_title="Reader-Writer Synchronization")


# ------------------------------------------------------------
# ONE shared Simulation for the whole app (see trick 1 above)
# ------------------------------------------------------------

@st.cache_resource
def get_simulation():
    return Simulation()


sim = get_simulation()


# ------------------------------------------------------------
# Icons for the activity log (based on the event 'kind')
# ------------------------------------------------------------

ICONS = {
    "request": "📨",
    "waiting": "⏳",
    "acquired": "🔒",
    "started": "▶️",
    "finished": "✓",
    "info": "ℹ️",
    "error": "❌",
}

# Text shown in the mode selector -> real mode name
MODE_LABELS = {
    "Writer preference (fair, no Writer starvation)": WRITER_PREFERENCE,
    "Reader preference (Writer may starve)": READER_PREFERENCE,
}


# ------------------------------------------------------------
# PAGE TITLE
# ------------------------------------------------------------

st.title("Reader-Writer Synchronization System")
st.caption(
    "Streamlit is only the interface. The actual synchronization "
    "is done in Python using threading (synchronization.py)."
)


# ------------------------------------------------------------
# PART 1: SHARED RESOURCE + SYSTEM STATUS
# (auto-refreshes every 1 second)
# ------------------------------------------------------------

@st.fragment(run_every=1)
def shared_resource_and_status():

    # ---- Shared resource: data.txt ----
    st.subheader("Shared Resource: data.txt")

    content = sim.read_file_content()

    if content is None:
        st.error("data.txt NOT FOUND (Readers and Writers will "
                 "report an error). Click 'Reset Simulation' to "
                 "create it again.")
    elif content == "":
        st.info("(the file is empty)")
    else:
        st.code(content, language=None)

    # ---- System status ----
    status = sim.get_status()

    st.subheader("System Status")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Readers", status["active_readers"])
    c2.metric("Active Writers", status["active_writers"])
    c3.metric("Waiting Readers", status["waiting_readers"])
    c4.metric("Waiting Writers", status["waiting_writers"])

    st.write(f"**Resource Status:** {status['resource_status']}")
    st.write(f"**Mode:** {status['mode']}")


shared_resource_and_status()


# ------------------------------------------------------------
# PART 2: CONTROLS (normal part of the page, NOT auto-refreshed)
# A button click re-runs this script. The click calls the
# backend, which starts a thread and returns immediately.
# ------------------------------------------------------------

st.subheader("Controls")

# ---- Mode selector ----
current_mode = sim.get_status()["mode"]
labels = list(MODE_LABELS.keys())
default_index = 0 if current_mode == WRITER_PREFERENCE else 1

choice = st.radio(
    "Synchronization mode",
    labels,
    index=default_index,
    horizontal=True,
)

# Switch mode in the backend only if the user really changed it
if MODE_LABELS[choice] != current_mode:
    sim.set_mode(MODE_LABELS[choice])

# ---- Single Reader / Writer ----
writer_text = st.text_input(
    "Text for Writer (optional - empty means a default line)"
)

col1, col2 = st.columns(2)

with col1:
    if st.button("Start Reader"):
        sim.start_reader()

with col2:
    if st.button("Start Writer"):
        sim.start_writer(writer_text.strip() or None)

# ---- Multiple Readers / Writers ----
count = st.slider("How many threads to start together?", 1, 5, 3)

col3, col4 = st.columns(2)

with col3:
    if st.button("Start Multiple Readers"):
        sim.start_readers(count)

with col4:
    if st.button("Start Multiple Writers"):
        sim.start_writers(count)

# ---- Demo and Reset ----
col5, col6 = st.columns(2)

with col5:
    if st.button("Run Reader-Writer Demo"):
        sim.run_demo()

with col6:
    if st.button("Reset Simulation"):
        if sim.reset():
            st.success("Simulation reset. data.txt is back to "
                       "its starting content.")
        else:
            st.warning("Threads are still running. Wait for them "
                       "to finish, then click Reset again.")


# ------------------------------------------------------------
# PART 3: LIVE ACTIVITY LOG
# (auto-refreshes every 1 second)
# ------------------------------------------------------------

@st.fragment(run_every=1)
def live_activity():

    st.subheader("Live Activity")

    events = sim.get_events()

    if not events:
        st.info("No activity yet. Start a Reader or a Writer.")
        return

    # Newest event on top, show only the last 30
    lines = []
    for e in reversed(events[-30:]):
        icon = ICONS.get(e["kind"], "•")
        lines.append(
            f"[{e['time']:5.1f}s] {icon} "
            f"{e['thread']}: {e['message']}"
        )

    st.code("\n".join(lines), language=None)


live_activity()