from serpapi import GoogleSearch
import os
from dotenv import load_dotenv
load_dotenv()


def extract_flights(origin, destination, date_from, date_to, max_layovers, round_trip):
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return [],None, "", ""
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": date_from,
        "type": 1 if round_trip else 2,
        "max_stops": max_layovers,
        "api_key": api_key,
        "no_cache": True
    }
    if round_trip and date_to:
        params["return_date"] = date_to

    results = GoogleSearch(params).get_dict()  # Debugging line to check API response

    if "error" in results:
        return {"error": results["error"]}, None , None , None 
    
    flights = results.get("best_flights", []) + results.get("other_flights", [])
    insights = results.get("price_insights", [])

    # Retrieving the first booking token
    booking_link = ""
    if flights:
        first_booking_token = flights[0].get("booking_token")
        if first_booking_token:
            params["booking_token"] = first_booking_token
            try:
                new_results = GoogleSearch(params).get_dict()
                booking_link = new_results.get("search_metadata", {}).get("google_flights_url", "")
            except Exception as e:
                print("Error retrieving booking link:", e)
                booking_link = ""

    generic_link = "https://www.google.com/travel/flights?q=flights+from+"
    query = f"{origin}+to+{destination}+on+{date_from}"
    if round_trip and date_to:
        query += f"+returning+{date_to}"
    generic_link = generic_link +  query    
    return flights, insights, booking_link , generic_link