import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from extractor import extract_flights
from transformer import transform_flights
from load import load_flights, load_alert_preferences, load_alerts, delete_alert, update_alert_price
from notifications import check_alert

st.set_page_config(page_title="Flight Price Tracker", layout="centered")
st.title("✈️ Flight Price Tracker")

tab1, tab2, tab3 = st.tabs(["🔍 Search Flights", "📈 Price Insights", "🔔 Manage Alerts"])

with tab1:
    is_round_trip = st.toggle("Round-Trip", value=True)
    trip_type = "Round-Trip" if is_round_trip else "One-Way"

    with st.form("search_form"):
        origin = st.text_input("From (IATA Code)", "SEA")
        destination = st.text_input("To (IATA Code)", "SJC")
        date_from = st.date_input("Departure Date")
        date_to = st.date_input("Return Date") if is_round_trip else None
        max_layovers = st.slider("Max Layovers", 0, 3, 1)
        target_price = st.number_input("Target Price ($)", 50, 1000, 150)
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

        if response_flag:
            with st.spinner(" Searching for flights..."):
                flights, insights, booking_link , generic_link = extract_flights(
                    origin = origin.upper(),
                    destination=destination.upper(),
                    date_from = date_from.strftime("%Y-%m-%d"),
                    date_to = date_to.strftime("%Y-%m-%d") if date_to else None,
                    max_layovers=max_layovers,
                    round_trip =(trip_type == "Round-Trip")
                )

            if "error" in flights:
                st.error(f"Error: {flights['error']}", icon="🚫")

            elif not flights or insights is None:
                st.error("Failed to retrieve flight data. Please check your inputs and try again.", icon="🚫")
            else:
                st.session_state["price_insights"] = insights
                st.session_state["booking_link"] = booking_link
                st.session_state["generic_link"] = generic_link
                df = transform_flights(flights)
                load_flights(df)
                st.dataframe(df[:5], hide_index=True, use_container_width=True,)
                if target_price < df["price"].min():          # target is NOT yet reached
                    alert = {
                        "origin"      : origin.upper(),
                        "destination" : destination.upper(),
                        "date_from"   : date_from.strftime("%Y-%m-%d"),
                        "date_to"     : date_to.strftime("%Y-%m-%d") if date_to else None,
                        "trip_type"   : trip_type,
                        "max_layovers": max_layovers,
                        "target_price": target_price,
                        "timestamp"   : datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
                    }
                    load_alert_preferences(alert) 
                else:
                    st.info(f"No alert was saved since the current lowest price is already below your target (${target_price}).", icon="ℹ️")
                


with tab2:
    st.subheader("Flight Price Insights")
    col1, col2, col3 = st.columns(3)
    lp = st.session_state.get("price_insights",None)
    if lp is None:
        st.info("Please search for flights in Tab 1 to see insights.", icon="⚠️")
    else:
        price_history = lp['price_history'] if lp else []   
        delta_map = {
        'low': ("Great Deal", "normal","Great time to book!"),
        'typical': ("Average", "off"," Prices are typical for this route."), 
        'high': ("Expensive", "inverse","Much better to wait or look for a better deal!"),
        }
        delta_text, delta_color, delta_obs = delta_map.get(lp['price_level'].lower(), (None, "normal", ""))
        col1.metric(value = f"{lp['lowest_price']} $" if lp else "Search first in Tab 1 to see insights.",label = "Lowest Price",border=True)
        col2.metric(value = f"{lp['price_level'].upper()}" if lp else "Search first in Tab 1 to see insights.",label = "Current Price level",border=True,delta=delta_text, delta_color=delta_color)
        col3.metric(value = f"{lp['typical_price_range'][0]} $ - {lp['typical_price_range'][1]} $" if lp else "Search first in Tab 1 to see insights.",label = "Typical Price range",border=True)
        

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
                    name=f"Current Lowest Price: ${lp['lowest_price']}",
                    line=dict(dash="dash", color="red")
                ))

                st.plotly_chart(fig, use_container_width=True)

            elif chart_type == "Histogram":
                fig_hist = px.histogram(
                    df,
                    x="price",
                    nbins=20,
                    title="🧮 Price Distribution (Across Last 60 days)",
                    labels={"price": "Price ($)"},
                    template="plotly_dark",
                )
                fig_hist.update_traces(marker_color='purple', marker_line_color='white', marker_line_width=2)
                fig_hist.update_layout(yaxis_title="Frequency")
                st.plotly_chart(fig_hist, use_container_width=True)

        st.subheader(f"Prices for this route typically range between {lp['typical_price_range'][0]} $ and {lp['typical_price_range'][1]} $. The current lowest price is {lp['lowest_price']} $, which is considered {delta_text}. {delta_obs}.")

with tab3:
    alerts = load_alerts()
    if alerts.empty:
        st.info("No alert preferences found.")
    else:
        for i, row in alerts.iterrows():
            with st.expander(f"{row['origin']} → {row['destination']} | {row['date_from']} | {row['trip_type']} | ${row['target_price']}"):
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
