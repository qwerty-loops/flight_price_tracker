#Import necessary libraries
import os
from dotenv import load_dotenv
import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from serpapi import GoogleSearch
load_dotenv()

def extract_flights(origin,destination, date, max_layovers=2, num_results =5):
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("API key not found. Please set up the environment variable SERPAPI_API_KEY.")
        # st.error("API key not found. Please set up the environment variable !")
        return []
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": date,
        "type": 2,  # One-way
        "max_stops": max_layovers,  # filter layovers
        "api_key": api_key,
        "no_cache": True
    }
    results = GoogleSearch(params).get_dict()
    flights = (results.get("best_flights", []) + results.get("other_flights", []))[:num_results]
    print (flights)
    return flights

def transform_flights(flights):
    if not flights:
        print ("No flights found. Please check your search criteria.")
        return pd.DataFrame()
    rows = []
    for flight in flights:
        price = flight.get("price") or flight.get("total_price")
        legs = flight.get("flights") or []
        layovers = len(legs) - 1 
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
    print(df)
    return df.sort_values(by="price", ascending=True)[:5]

def load_flights(df):
    conn = sqlite3.connect("flight_prices.db") #Establish a connection to the SQLite database
    df.to_sql("flight_prices",conn,if_exists="append",index=False) #Load the DataFrame into the SQLite database
    conn.commit()  # Commit the changes
    conn.close()
    
    
def run_etl(origin,destination,date,max_layovers):
    flights = extract_flights(origin, destination, date, max_layovers)
    tf = transform_flights(flights)
    load_flights(tf)  # Close the connection


if __name__ == "__main__":
    # Example usage
    origin = "SEA"  # Example origin airport code
    destination = "SJC"  # Example destination airport code
    date = "2025-06-19"  # Example departure date
    max_layovers = 2  # Example maximum layovers

    run_etl(origin, destination, date, max_layovers)
    

# {'flights': [{'departure_airport': {'name': 'John F. Kennedy International Airport', 'id': 'JFK', 'time': '2025-06-19 09:00'}, 'arrival_airport': {'name': 'Los Angeles International Airport', 'id': 'LAX', 'time': '2025-06-19 12:10'}, 'duration': 370, 'airplane': 'Airbus A321 (Sharklets)', 'airline': 'American', 'airline_logo': 'https://www.gstatic.com/flights/airline_logos/70px/AA.png', 'travel_class': 'Business Class', 'flight_number': 'AA 255', 'extensions': ['Lie flat seat', 'Wi-Fi for a fee', 'In-seat power & USB outlets', 'Stream media to your device', 'Carbon emissions estimate: 809 kg']}], 'total_duration': 370, 'carbon_emissions': {'this_flight': 809000, 'typical_for_this_route': 310000, 'difference_percent': 161}, 'price': 2130, 'type': 'One way', 'airline_logo': 'https://www.gstatic.com/flights/airline_logos/70px/AA.png', 'extensions': ['1 checked bag included'], 'booking_token': 'WyJDalJJUWpRMWJWWlNURUZmTFVGQlFUa3hha0ZDUnkwdExTMHRMUzB0TFhscFltWnhOMEZCUVVGQlIyaFVhRkozUkRCdVVtZEJFZ1ZCUVRJMU5Sb0xDTlQvREJBQ0dnTlZVMFE0SEhEVS93dz0iLFtbIkpGSyIsIjIwMjUtMDYtMTkiLCJMQVgiLG51bGwsIkFBIiwiMjU1Il1dXQ=='}