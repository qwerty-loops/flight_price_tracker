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
        round_trip=(row['trip_type'] == 'Round-Trip'),
        currency=row['currency'],
        preferred_carriers = row.get("preferred_carriers")
    )

    if flights:
        df = transform_flights(flights,currency=row['currency'])
        preferred_carriers = row.get('preferred_carriers')
        if preferred_carriers and "Any" not in preferred_carriers:
                    df = df[df["airline"].isin(preferred_carriers)]
        email = row['user_email'] if row['user_email'] else None
        phone = row['user_phone'] if row['user_phone'] else None
        ca = check_alert(df, row['target_price'], row['currency'], booking_link, generic_link, email, phone)
        if ca:
            print(f"Alert triggered for row {index}: {row['origin']} → {row['destination']} | {row['date_from']} | {row['trip_type']} | ${row['target_price']}")
            print(f"Cheapest flight now: {df['price'].min()}")
            delete_alert(row['id'])
            print("Alert removed successfully.")

        else:
            print(f"No alert triggered for row {index}: {row['origin']} → {row['destination']} | {row['date_from']} | {row['trip_type']} | ${row['target_price']}")
    else:
        print(f"Failed to retrieve flight data for alert {index}")
