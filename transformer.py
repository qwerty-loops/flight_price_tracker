import pandas as pd
from datetime import datetime

def transform_flights(flights):
    rows = []
    for flight in flights:
        if not isinstance(flight, dict):
            continue  # skip invalid records
        price = flight.get("total_price") or flight.get("price") or None
        legs = flight.get("flights") or []
        if price is None or not legs:
            continue

        # Calculate layovers info
        layover_details = []
        if len(legs) > 1:
            for i in range(len(legs)-1):
                arrival_leg = legs[i]
                next_leg = legs[i+1]
                arrival_airport  = arrival_leg["arrival_airport"]["id"]
                arrival_time = pd.to_datetime(arrival_leg["arrival_airport"]["time"])
                departure_time = pd.to_datetime(next_leg["departure_airport"]["time"])
                duration = departure_time - arrival_time
                duration_str = f"{int(duration.total_seconds()//3600)}h {int((duration.total_seconds()%3600)//60)}m"
                layover_details.append(f"{arrival_airport} ({duration_str})")

        rows.append({
            "airline": legs[0]["airline"],
            "price": float(price),
            "duration_min": flight.get("total_duration"),
            "layovers": len(legs) - 1,
            "layover_info": "; ".join(layover_details) if layover_details else "None",
            "origin_to_destination": f"{legs[0]['departure_airport']['id']} - {legs[-1]['arrival_airport']['id']}",
            "departure_time": legs[0]["departure_airport"]["time"],
            "arrival_time": legs[-1]["arrival_airport"]["time"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        })

    columns = [
        "airline", "price", "duration_min", "layovers",
        "layover_info", "origin_to_destination", "departure_time",
        "arrival_time", "timestamp"
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(by="price") if rows else pd.DataFrame(columns=columns)

