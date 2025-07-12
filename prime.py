import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from extractor import extract_flights
from transformer import transform_flights
from load import load_flights, load_alert_preferences, load_alerts, delete_alert, update_alert_price
from notifications import check_alert

url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
columns = [
    "id", "name", "city", "country", "IATA", "icao",
    "latitude", "longitude", "altitude", "timezone", "dst",
    "tz_database", "type", "source"
]

@st.cache_data
def load_airports():
    df = pd.read_csv(url, header=None, names=columns)
    df["label"] = df["city"] + " - " + df["name"] + " (" + df["IATA"] + ")"
    return df
airports_df = load_airports()
currency_symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥", "AUD": "A$", "CAD": "C$", "CNY": "¥", "CHF": "CHF", "RUB": "₽", "ZAR": "R"}

st.set_page_config(page_title="Flight Price Tracker", layout="centered")
st.title("✈️ Flight Price Tracker")

with st.sidebar:
    st.header("📧 Notification Preferences")
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = ""
    if "user_phone" not in st.session_state:
        st.session_state["user_phone"] = ""

    st.session_state["user_email"] = st.text_input("Your Email", value=st.session_state["user_email"], placeholder= "you@example.com")
    st.session_state["user_phone"] = st.text_input("Your Mobile Number (with country code)", value=st.session_state["user_phone"], placeholder= "+12345678900", max_chars=12)


tab1, tab2, tab3 = st.tabs(["🔍 Search Flights", "📈 Price Insights", "🔔 Manage Alerts"])

with tab1:
    is_round_trip = st.toggle("Round-Trip", value=True)
    trip_type = "Round-Trip" if is_round_trip else "One-Way"

    with st.form("search_form"):
        origin_label = st.selectbox(
            "Origin",
            options = airports_df["label"].tolist(),
            index=int(airports_df[airports_df["IATA"] == "SEA"].index[0]),
            placeholder="Type to search airports...")
        origin = airports_df.loc[airports_df["label"] == origin_label, "IATA"].values[0]
        destination_label = st.selectbox(
            "Destination",
            options = airports_df["label"].tolist(),
            index=int(airports_df[airports_df["IATA"] == "SJC"].index[0]),
            placeholder="Type to search airports...")
        destination = airports_df.loc[airports_df["label"] == destination_label, "IATA"].values[0]
        date_from = st.date_input("Departure Date")
        date_to = st.date_input("Return Date") if is_round_trip else None
        max_layovers = st.slider("Max Layovers", 0, 3, 1)
        target_price = st.number_input("Target Price", 50, 5000, 150)
        currency_options = ["USD", "EUR", "GBP", "INR", "JPY"]
        selected_currency = st.selectbox("Currency", currency_options, index=0)
        preferred_carriers = st.multiselect(
        "Preferred Airlines (Optional)",
        options=["Any", "Alaska", "Air India", "Emirates", "Etihad", "Oman Air", "Qatar Airways", "Delta", "United", "Lufthansa", "British Airways", "Singapore Airlines", "American Airlines", "Air Canada", "JetBlue", "Spirit", "Southwest", "Air France", "KLM", "Turkish Airlines", "IndiGo", "SpiceJet", "Vistara"],
        default=["Any"]
        )
        st.session_state["currency"] = selected_currency
        st.session_state["symbol"] = currency_symbols.get(selected_currency, "$")
        submit = st.form_submit_button("Search & Set Alert")

    if submit:
        # Input validation
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

        if not st.session_state["user_email"] or "@" not in st.session_state["user_email"]:
            st.warning("Please enter a valid email address in the sidebar.", icon="⚠️")
            response_flag = False
        if not st.session_state["user_phone"] or not st.session_state["user_phone"].startswith("+") or len(st.session_state["user_phone"]) < 10:
            st.warning("Please enter a valid phone number with country code in the sidebar.", icon="⚠️")
            response_flag = False

        if response_flag:
            with st.spinner("Searching for flights... This can take up to 15 seconds."):
                flights, insights, booking_link , generic_link = extract_flights(
                    origin = origin.upper(),
                    destination=destination.upper(),
                    date_from = date_from.strftime("%Y-%m-%d"),
                    date_to = date_to.strftime("%Y-%m-%d") if date_to else None,
                    max_layovers=max_layovers,
                    round_trip =(trip_type == "Round-Trip"),
                    currency=selected_currency,
                    preferred_carriers=preferred_carriers if "Any" not in preferred_carriers else None
                )  # Debugging line to check API response

            # print(flights)  # Debugging line to check API response
            if "error" in flights:
                st.error(f"Error: {flights['error']}", icon="🚫")

            elif not flights or insights is None:
                st.error("Failed to retrieve flight data. Please check your inputs and try again.", icon="🚫")
            else:
                st.session_state["price_insights"] = insights
                st.session_state["booking_link"] = booking_link
                st.session_state["generic_link"] = generic_link
                st.session_state["currency"] = selected_currency
                df = transform_flights(flights,st.session_state["currency"])

                if preferred_carriers and "Any" not in preferred_carriers:
                    df = df[df["airline"].isin(preferred_carriers)]

                if df.empty:
                    st.warning("No flights found for the given criteria. Please adjust your search.", icon="⚠️")
                else:
                    load_flights(df)
                    if len(df) >= 5:
                        st.dataframe(df[:5], hide_index=True, use_container_width=True)
                    else:
                        st.dataframe(df, hide_index=True, use_container_width=True)
                    if target_price < df["price"].min():          # target is NOT yet reached
                        alert = {
                            "origin"      : origin.upper(),
                            "destination" : destination.upper(),
                            "date_from"   : date_from.strftime("%Y-%m-%d"),
                            "date_to"     : date_to.strftime("%Y-%m-%d") if date_to else None,
                            "trip_type"   : trip_type,
                            "max_layovers": max_layovers,
                            "target_price": target_price,
                            "currency"    : selected_currency,
                            "preferred_carriers": preferred_carriers if "Any" not in preferred_carriers else None,
                            "timestamp"   : datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
                            "user_email": st.session_state["user_email"],
                            "user_phone": st.session_state["user_phone"],
                        }
                        load_alert_preferences(alert) 
                    else:
                        st.info(f"No alert was saved since the current lowest price is already below your target (${target_price}).", icon="ℹ️")
                


with tab2:
    st.subheader("Flight Price Insights")
    col1, col2, col3 = st.columns(3)
    lp = st.session_state.get("price_insights",None)
    if lp is None or lp == []:
        st.info("Please search for flights in Tab 1 to see insights.", icon="⚠️")
    else:
        price_history = lp['price_history'] if lp else []
        delta_map = {
        'low': ("Great Deal", "normal","Great time to book!"),
        'typical': ("Average", "off"," Prices are typical for this route."), 
        'high': ("Expensive", "inverse","Much better to wait or look for a better deal!"),
        }
        delta_text, delta_color, delta_obs = delta_map.get(lp['price_level'].lower(), (None, "normal", ""))
        symbol = st.session_state.get("symbol", "$")
        col1.metric(value = f"{symbol}{lp['lowest_price']}" if lp else "Search first in Tab 1 to see insights.",label = "Lowest Price",border=True)
        col2.metric(value = f"{lp['price_level'].upper()}" if lp else "Search first in Tab 1 to see insights.",label = "Current Price level",border=True,delta=delta_text, delta_color=delta_color)
        col3.metric(value = f"{symbol}{lp['typical_price_range'][0]} - {symbol}{lp['typical_price_range'][1]}" if lp else "Search first in Tab 1 to see insights.",label = "Typical Price range",border=True)

        options = ["Area Chart", "Histogram"]
        chart_type = st.selectbox(
            "📊 Visualize Price History",
            options=options,
            index=0,
            placeholder="Select Preferred mode of visualization"
        )
            
        if price_history:
            df = pd.DataFrame(price_history, columns=["timestamp", "price"])
            df["date"] = pd.to_datetime(df["timestamp"], unit='s')
            df["days_ago"] = (datetime.now() - df["date"]).dt.days
            df["hover_label"] = df["days_ago"].astype(str) + " days ago"

            if chart_type == "Area Chart":
                fig = px.area(
                    df,
                    x="days_ago",
                    y="price",
                    hover_name="hover_label",
                    title="📈 Price History (Across Last 60 days)",
                    labels={"days_ago": "Days Ago", "date": "Date", "price": "Price ($)"},
                )

                fig.update_layout(
                xaxis=dict(
                    autorange="reversed",
                    title="Days Ago",
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor",
                    showline=True,
                    spikedash="solid",
                    spikecolor="white",    
                    spikethickness=1
                ),
                yaxis_title="Price ($)",
                hovermode="x unified",
                template="plotly_dark",
                height=400,
                )

                fig.add_trace(go.Scatter(
                    x=df["days_ago"],
                    y=[lp['lowest_price']] * len(df),
                    mode="lines",
                    name=f"Current Lowest Price: {symbol}{lp['lowest_price']}",
                    line=dict(dash="dash", color="red")
                ))

                st.plotly_chart(fig, use_container_width=True)

            elif chart_type == "Histogram":
                fig_hist = px.histogram(
                    df,
                    x="price",
                    nbins=20,
                    title="🧮 Price Distribution (Across Last 60 days)",
                    labels={"price": f"Price ({symbol})"},
                    template="plotly_dark",
                )
                fig_hist.update_traces(marker_color='purple', marker_line_color='white', marker_line_width=2)
                fig_hist.update_layout(yaxis_title="Frequency")
                st.plotly_chart(fig_hist, use_container_width=True)

        st.subheader(
    f"Prices for this route typically range between {symbol}{lp['typical_price_range'][0]} and {symbol}{lp['typical_price_range'][1]}. "
    f"The current lowest price is {symbol}{lp['lowest_price']}, which is considered {delta_text}. {delta_obs}."
    )

with tab3:
    alerts = load_alerts()
    if alerts.empty:
        st.info("No alert preferences found.")
    else:
        for i, row in alerts.iterrows():
            formatted_date_from = datetime.fromisoformat(row['date_from']).strftime('%b %d, %Y')
            formatted_date_to = datetime.fromisoformat(row['date_to']).strftime('%b %d, %Y') if row['date_to'] else "N/A"
            formatted_timestamp = datetime.fromisoformat(row['timestamp']).strftime('%b %d, %Y %I:%M %p')
            with st.expander(f"{row['origin']} → {row['destination']} | {formatted_date_from} | {row['trip_type']} | {row['target_price']} {currency_symbols.get(row['currency'])} | {row['user_email']}"):
                col1, col2, col3 = st.columns([2, 1, 1], gap="medium")
                
                with col1:
                    st.write(f"**Trip:** {row['trip_type']}")
                    st.write(f"**Max Layovers:** {row['max_layovers']}")
                    st.write(f"**Return Date:** {formatted_date_to}")
                    st.write(f"**Set On:** {formatted_timestamp}")
                    st.write(f"**Preferred Airlines:** {row['preferred_carriers'] if row['preferred_carriers'] else 'Any'}")

                with col2:
                    new_price = st.number_input("Update Price", min_value=50, value=int(row["target_price"]), key=f"price_{i}")
                    if st.button("💾 Save", key=f"save_{i}"):
                        update_alert_price(row['id'], new_price)
                        st.success("Alert updated.")
                        st.rerun()

                with col3:
                    if st.button("🗑 Delete", key=f"del_{i}"):
                        delete_alert(row['id'])
                        st.warning("Alert deleted.")
                        st.rerun()
