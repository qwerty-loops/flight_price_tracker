import sqlite3
import pandas as pd
import os
import streamlit as st

DB_PATH = "flight_prices_streamlit.db"

def load_flights(df):
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("flight_prices", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

def load_alert_preferences(data):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            origin TEXT,
            destination TEXT,
            date_from TEXT,
            date_to TEXT,
            trip_type TEXT,
            max_layovers INTEGER,
            target_price REAL,
            timestamp TEXT,
            UNIQUE(origin, destination, date_from, date_to, trip_type, max_layovers, target_price)
        )""")
        
        normalized_data = (
            str(data["origin"]).strip(),
            str(data["destination"]).strip(), 
            str(data["date_from"]),
            str(data["date_to"]),
            str(data["trip_type"]).strip(),
            int(data["max_layovers"]),
            float(data["target_price"]),
            data["timestamp"]
        )

        conn.execute("""INSERT OR IGNORE INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", normalized_data)
        conn.commit()
        if conn.total_changes == 0:
            st.warning("Alert already exists with the same parameters.")
        else:
            st.success("Alert saved.")
    except Exception as e:
        st.warning(f"Error occurred: {e}")
    finally:
        conn.close()

def load_alerts():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT rowid, * FROM alerts", conn)
    conn.close()
    return df

def delete_alert(rowid):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM alerts WHERE rowid = ?", (rowid,))
    conn.commit()
    conn.close()

def update_alert_price(rowid, new_price):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE alerts SET target_price = ? WHERE rowid = ?", (new_price, rowid))
    conn.commit()
    conn.close()
