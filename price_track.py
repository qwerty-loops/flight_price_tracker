#Import necessary libraries
import os
from dotenv import load_dotenv
import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from twilio.rest import Client # For sending SMS and Email notifications
import smtplib
from email.mime.text import MIMEText
from serpapi import GoogleSearch


load_dotenv()
target_price = 250
SET_EMAIL_ALERT = True
SET_SMS_ALERT = True

#My Email credentials
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT')
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD')

# My Twilio credentials
TWILIO_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.getenv('TWILIO_FROM_NUMBER')
TWILIO_TO = os.getenv('TWILIO_TO_NUMBER')

# Load environment variables from .env file


#ETL Project : Flight Price Tracker

#Step 1: Extract flight data from Google Flights using SerpAPI
def extract_flights(origin, destination, date_from, date_to, max_layovers, round_trip):
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        st.error("API key not found. Please set up the environment variable !")
        return []
    
    # print(f"Searching flights from {origin} to {destination} on {date_from} with max layovers {max_layovers} (Round-trip: {round_trip})")

    params = {
        "engine": "google_flights",
        "departure_id":origin,
        "arrival_id": destination,
        "outbound_date": date_from,
        "type": 1 if round_trip else 2,
        "max_stops": max_layovers,
        "api_key": api_key,
        "no_cache": True
    }


    if round_trip and date_to:
        params["return_date"] = date_to

    # print(f"Searching flights from {origin} to {destination} on {date_from} returning on {date_to} with max layovers {max_layovers} (Round-trip: {round_trip})")

    results = GoogleSearch(params).get_dict()
    flights = results.get("best_flights", []) + results.get("other_flights", [])
    return flights 


#Step 2: Transform flight data into a DataFrame
def transform_flights(flights):
    if not flights:
        st.error("No flights found. Please check your search criteria.")
        return pd.DataFrame()
    
    rows = []
    for flight in flights:
        price = flight.get("total_price") or flight.get("price")
        legs = flight.get("flights") or []
        layovers = len(legs) -1
        rows.append({
            "airline": legs[0]["airline"],
            "price": float(price),
            "duration_min": flight.get("total_duration"),
            "layovers": layovers,
            "origin_to_destination": f"{legs[0]['departure_airport']['id']} - {legs[-1]['arrival_airport']['id']}",
            "departure_time": legs[0]["departure_airport"]["time"] if legs else None,
            "arrival_time": legs[-1]["arrival_airport"]["time"] if legs else None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        })
    df= pd.DataFrame(rows)
    df = df.sort_values(by="price", ascending=True)
    return df

#Step 3: Load flight data into SQLite database
def load_flights(df):
    conn=sqlite3.connect("flight_prices_streamlit.db")
    df.to_sql("flight_prices",conn,if_exists="append",index=False)
    conn.commit()
    conn.close()

def load_alert_preferences(data):
    try:
        conn = sqlite3.connect("flight_prices_streamlit.db")
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
        )
        """)
        df = pd.DataFrame([data])
        df.to_sql("alerts", conn, if_exists="append", index=False)
        conn.commit()
        st.success("Alert preferences saved successfully.")
        conn.close()
    except sqlite3.IntegrityError:
        st.warning("Alert already exists with the same parameters. Please modify your alert preferences.")

def check_alert(df,target_price):
    if df.empty:
        st.warning("No such flights found.")
        return
    
    price = df['price'].min()
    if price <= target_price:
        message = f"Flight Alert! The price for your selected flight from {df['origin_to_destination'].iloc[0]} has dropped from {target_price} to ${price:.2f} on {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}"
        print(message)
        if SET_SMS_ALERT:
            send_sms(message)

        if SET_EMAIL_ALERT:
            subject = "Flight Price Alert"
            # body = f"<p>{message}</p><p>Check the details in your flight tracker.</p>"
            send_email(subject, message, EMAIL_SENDER, EMAIL_RECIPIENT, EMAIL_APP_PASSWORD)

def send_sms(body):
    print("Sending SMS...")
    client = Client(TWILIO_SID,TWILIO_TOKEN)
    message = client.messages.create(
        body=body,
        from_ =TWILIO_FROM,
        to = TWILIO_TO
    )
    print(f"SMS sent: {message.sid}")

# IF an email is to be sent

def send_email(subject, body,sender,recepient,app_password):
    print("Sending Email...")
    msg = MIMEText(body,'html')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recepient

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)     # Show SMTP protocol for debugging
        server.ehlo() 
        server.starttls() # Upgrade the connection to a secure encrypted SSL/TLS connection
        server.login(sender, app_password)
        server.sendmail(sender, [recepient], msg.as_string())
        server.quit()
        print("Email sent to recepient", recepient)
    except Exception as e:
        print(f"Failed to send email: {e}")


# Streamlit UI

st.set_page_config(page_title="Flight Price Tracker",layout="centered")
st.title("Flight Price Tracker")

tab1, tab2, tab3 = st.tabs(["🔍 Search Flights", "🔔 Manage Alerts","Track Historical Prices"])


with tab1:

    is_round_trip = st.toggle("Round-Trip",value= True)
    trip_type = "Round-Trip" if is_round_trip else "One-Way"

    with st.form("alert_form"):
        
        origin = st.text_input("Departure Airport (IATA)", "SEA")
        destination = st.text_input("Destination Airport (IATA)", "SJC")
        date_from = st.date_input("Departure Date")
        if trip_type == "Round-Trip":
            date_to = st.date_input("Return Date")
        else:
            date_to = None
        max_layovers = st.slider("Max Layovers", 0, 3, 1)
        target_price = st.number_input("Your Target Price ($)", min_value=50, value=150)
        submit = st.form_submit_button("Search and Set Alert")

    #Main panel
    if submit:

        response_flag = True

        if not origin.strip():
            st.warning("Please enter a valid origin airport.", icon="⚠️")
            response_flag = False
        if not destination.strip():
            st.warning("Please enter a valid destination airport.", icon="⚠️")
            response_flag = False
        if date_from < datetime.now().date():
            st.warning("Departure date cannot be in the past.", icon="⚠️")
            response_flag = False
        if trip_type == "Round-Trip" and date_to and date_to < date_from:
            st.warning("Return date cannot be before departure date.", icon="⚠️")
            response_flag = False

        if response_flag:

            with st.spinner(" Searching for flights..."):
                flights = extract_flights(
                    origin = origin.upper(),
                    destination=destination.upper(),
                    date_from = date_from.strftime("%Y-%m-%d"),
                    date_to = date_to.strftime("%Y-%m-%d") if date_to else None,
                    max_layovers=max_layovers,
                    round_trip =(trip_type == "Round-Trip")
                )


            if not flights:
                st.warning("No flights found.")
            else:
                tf=transform_flights(flights)
                lf= load_flights(tf)
                st.success("Here are the 5 cheapest flights :")
                st.dataframe(tf[:5])
                check_alert(tf, target_price)

                csv =tf.to_csv(index=False).encode("utf-8")
                st.download_button("Download as CSV", data=csv, file_name = "flights.csv")

                matched = tf[tf["price"] <= target_price]
                if not matched.empty:
                    st.success(f"A flight for ${matched.iloc[0]['price']} matches your target price (${target_price})!")
                else:
                    st.info(f"🔔 No flights are currently below ${target_price}. We'll store your alert preferences.")

                    user_pref = {
                        "origin": origin.upper(),
                        "destination": destination.upper(),
                        "date_from": date_from.strftime("%Y-%m-%d"),
                        "date_to": date_to.strftime("%Y-%m-%d") if date_to else None,
                        "trip_type": trip_type,
                        "max_layovers": max_layovers,
                        "target_price": target_price,
                        "timestamp": datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
                    }
                    load_alert_preferences(user_pref)


with tab2:

    DB_PATH = "flight_prices_streamlit.db"

    def load_alerts():
        try:
            if not os.path.exists(DB_PATH):
                return pd.DataFrame()
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql("SELECT rowid, * FROM alerts", conn)
            conn.close()
            return df
        except Exception as e:
            return pd.DataFrame()

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

    alerts_df = load_alerts()

    if alerts_df.empty:
        st.info("No alert preferences found.")
    else:
        for i, row in alerts_df.iterrows():
            with st.expander(f"✈️ {row['origin']} → {row['destination']} | {row['date_from']} | Target ≤ ${row['target_price']}"):
                col1, col2, col3 = st.columns([2, 1, 1], gap="medium")
                with col1:
                    st.write(f"**Trip:** {row['trip_type']}")
                    st.write(f"**Max Layovers:** {row['max_layovers']}")
                    st.write(f"**Return Date:** {row['date_to'] or 'N/A'}")
                    st.write(f"**Set On:** {row['timestamp']}")
                with col2:
                    new_price = st.number_input(f"Update Price", min_value=50, value=int(row["target_price"]), key=f"price_{i}")
                    if st.button("💾 Save", key=f"save_{i}"):
                        update_alert_price(row['rowid'], new_price)
                        st.success("Alert updated.")
                        st.rerun()
                with col3:
                    if st.button("🗑 Delete", key=f"del_{i}"):
                        delete_alert(row['rowid'])
                        st.warning("Alert deleted.")
                        st.rerun()
