import pandas as pd
from datetime import datetime

def transform_flights(flights):
    rows = []
    for flight in flights:
        price = flight.get("total_price") or flight.get("price")
        legs = flight.get("flights") or []
        if price is None:
            continue
        rows.append({
            "airline": legs[0]["airline"],
            "price": float(price),
            "duration_min": flight.get("total_duration"),
            "layovers": len(legs) - 1,
            "origin_to_destination": f"{legs[0]['departure_airport']['id']} - {legs[-1]['arrival_airport']['id']}",
            "departure_time": legs[0]["departure_airport"]["time"] if legs else None,
            "arrival_time": legs[-1]["arrival_airport"]["time"] if legs else None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        })
    return pd.DataFrame(rows).sort_values(by="price")
