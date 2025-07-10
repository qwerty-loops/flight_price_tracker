from supabase import create_client, Client
import pandas as pd
import datetime
import streamlit as st
import os
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_flights(df):
    records = df.to_dict(orient='records') # Print first 5 records for debugging
    for record in records:
        supabase.table("flight_prices").insert(record).execute()


def load_alert_preferences(data):
    try:
        # Normalize all inputs
        data["origin"] = data["origin"].strip()
        data["destination"] = data["destination"].strip()
        data["trip_type"] = data["trip_type"].strip()
        data["user_email"] = data["user_email"].strip()
        data["user_phone"] = data["user_phone"].strip()
        data["max_layovers"] = int(data["max_layovers"])
        data["target_price"] = float(data["target_price"])
        data["currency"] = data["currency"].strip()

        # Convert "None" string to real None for date_to
        if not data.get("date_to") or data["date_to"] in ["None", "", None]:
            data["date_to"] = None

        # Ensure timestamp is set correctly
        if not data.get("timestamp") or data["timestamp"] in ["None", "", None]:
            from datetime import datetime
            data["timestamp"] = datetime.now().isoformat()

        # Check for duplicate
        query = (
            supabase.table("alerts")
            .select("id")
            .eq("origin", data["origin"])
            .eq("destination", data["destination"])
            .eq("date_from", data["date_from"])
            .eq("trip_type", data["trip_type"])
            .eq("max_layovers", data["max_layovers"])
            .eq("target_price", data["target_price"])
            .eq("currency", data["currency"])
            .eq("user_email", data["user_email"])
            .eq("user_phone", data["user_phone"])
        )

        # date_to can be null or a date
        if data["date_to"] is None:
            query = query.is_("date_to", None)
        else:
            query = query.eq("date_to", data["date_to"])

        existing = query.execute()

        if existing.data and len(existing.data) > 0:
            st.warning("Alert already exists with the same parameters.")
            return

        # Insert only if no duplicate
        response = supabase.table("alerts").insert(data).execute()

        if response.data:
            st.success("Alert saved.")
        else:
            st.warning("Alert could not be saved.")
    except Exception as e:
        st.warning(f"Error occurred: {e}")


def load_alerts():
    try:
        response = supabase.table("alerts").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Failed to fetch alerts: {e}")
        return pd.DataFrame()

def delete_alert(rowid):
    try:
        supabase.table("alerts").delete().eq("id", rowid).execute()
    except Exception as e:
        st.warning(f"Failed to delete alert: {e}")

def update_alert_price(rowid, new_price):
    try:
        supabase.table("alerts").update({"target_price": new_price}).eq("id", rowid).execute()
    except Exception as e:
        st.warning(f"Failed to update alert: {e}")


        
