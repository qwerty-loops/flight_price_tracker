from extractor import extract_flights
from transformer import transform_flights
from load import load_alerts,delete_alert
from notifications import check_alert
from datetime import datetime

alerts = load_alerts()

for index, row in alerts.iterrows():
    flights, insights, booking_link, generic_link = extract_flights(
        origin=row['origin'],
        destination=row['destination'],
        date_from=row['date_from'],
        date_to=row['date_to'] if row['date_to'] else None,
        max_layovers=row['max_layovers'],
        round_trip=(row['trip_type'] == 'Round-Trip')
    )

    if flights:
        df = transform_flights(flights)
        ca = check_alert(df, row['target_price'], booking_link, generic_link)
        if ca:
            print(f"Alert triggered for row {index}: {row['origin']} → {row['destination']} | {row['date_from']} | {row['trip_type']} | ${row['target_price']}")
            print(f"Cheapest flight now: {df['price'].min()}")
            delete_alert(row['rowid'])
            print("Alert removed successfully.")

        else:
            print(f"No alert triggered for row {index}: {row['origin']} → {row['destination']} | {row['date_from']} | {row['trip_type']} | ${row['target_price']}")
    else:
        print(f"Failed to retrieve flight data for alert {index}")