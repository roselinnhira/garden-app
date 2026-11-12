import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB = Path("garden.db")

# Build the database the first time the app runs (or after a restart wipes it)
if not DB.exists():
    conn = sqlite3.connect(DB)
    conn.executescript("""
        CREATE TABLE bed (
            bed_id   INTEGER PRIMARY KEY,
            crop     TEXT NOT NULL,
            location TEXT
        );
        CREATE TABLE bed_log (
            log_id   INTEGER PRIMARY KEY,
            bed_id   INTEGER NOT NULL REFERENCES bed(bed_id),
            log_date TEXT,
            status   TEXT
        );
        INSERT INTO bed VALUES
            (1, 'kale', 'upper garden'),
            (2, 'garlic', 'hoop house'),
            (3, 'tomatoes', 'lower garden');
        INSERT INTO bed_log (bed_id, log_date, status) VALUES
            (1, '2026-09-01', 'seeded'),
            (1, '2026-09-20', 'sprouting'),
            (2, '2026-09-05', 'seeded');
    """)
    conn.commit()
    conn.close()

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")



st.title("Garden Beds by Rose")

# RESET: throw away garden.db so the app builds a fresh one
if st.button("Reset garden"):
    conn.close()
    DB.unlink()
    st.rerun()

orphans = pd.read_sql_query(
    "SELECT COUNT(*) AS n FROM bed_log WHERE bed_id NOT IN (SELECT bed_id FROM bed)",
    conn,
)["n"][0]
st.caption(f"Logs with no bed: {orphans}")



# READ: pick a bed, see its history
crops = pd.read_sql_query("SELECT crop FROM bed ORDER BY crop", conn)["crop"]
crop = st.selectbox("Pick a bed", crops)

history = pd.read_sql_query(
    """
    SELECT l.log_date, l.status
    FROM bed_log l
    JOIN bed b ON b.bed_id = l.bed_id
    WHERE b.crop = ?
    ORDER BY l.log_date
    """,
    conn,
    params=(crop,),
)
st.dataframe(history, hide_index=True)

# CREATE: add a visit for this bed
with st.form("add_visit"):
    visit_date = st.date_input("Visit date")
    status = st.selectbox("Status", ["seeded", "sprouting", "harvesting", "fallow", "failed"])
    if st.form_submit_button("Add visit"):
        conn.execute(
            "INSERT INTO bed_log (bed_id, log_date, status) "
            "SELECT bed_id, ?, ? FROM bed WHERE crop = ?",
            (str(visit_date), status, crop),
        )
        conn.commit()
        st.rerun()

# DELETE: remove the bed we picked
with st.form("remove_bed"):
    st.write("Remove the bed we picked above")
    if st.form_submit_button("Remove bed"):
        try:
            conn.execute("DELETE FROM bed WHERE crop = ?", (crop,))
            conn.commit()
            st.rerun()
        except sqlite3.IntegrityError:
            conn.rollback()
            st.error(f"Can't remove {crop}: it still has logs.")

# UPDATE: fix the name of the bed we picked
with st.form("fix_crop"):
    new_crop = st.text_input("Fix the name of this bed", value=crop)
    if st.form_submit_button("Fix name"):
        conn.execute("UPDATE bed SET crop = ? WHERE crop = ?", (new_crop, crop))
        conn.commit()
        st.rerun()

