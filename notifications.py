from twilio.rest import Client
import smtplib
import datetime
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
load_dotenv()

def send_sms(body, to_phone):
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    client.messages.create(
        body=body,
        from_=os.getenv("TWILIO_FROM_NUMBER"),
        to=to_phone
    )

def send_email(subject, body, to_email):
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = os.getenv("EMAIL_SENDER")
    msg['To'] = to_email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_APP_PASSWORD"))
    server.sendmail(msg['From'], [msg['To']], msg.as_string())
    server.quit()

def check_alert(df, target_price, currency, booking_link=None, generic_link=None, user_email=None, user_phone=None):
    flag = False
    if df.empty:
        return

    price = df['price'].min()
    flight_currency = df.iloc[0]['currency']
    cheapest_flight = df[df['price'] == price].iloc[0]

    departure_time_raw = cheapest_flight['departure_time']
    arrival_time_raw = cheapest_flight['arrival_time']

    try:
        departure_time = datetime.fromisoformat(departure_time_raw).strftime("%b %d, %Y %I:%M %p")
    except Exception:
        departure_time = departure_time_raw

    try:
        arrival_time = datetime.fromisoformat(arrival_time_raw).strftime("%b %d, %Y %I:%M %p")
    except Exception:
        arrival_time = arrival_time_raw

    origin_to_destination = cheapest_flight['origin_to_destination']

    print("DEBUG: Cheapest flight price:", price)
    print("DEBUG: Target price:", target_price)
    print("DEBUG: user_email:", user_email)
    print("DEBUG: user_phone:", user_phone)
    print("DEBUG: SET_SMS_ALERT:", os.getenv("SET_SMS_ALERT"))
    print("DEBUG: SET_EMAIL_ALERT:", os.getenv("SET_EMAIL_ALERT"))

    if flight_currency == currency and price <= target_price:

        # ✉️ SMS Message (Plain Text)
        sms_message = (
        f"Flight deal alert! : ${price:.0f} (target {target_price})\n"
        )
        if booking_link:
            sms_message += f"{booking_link}"
        if generic_link:
            sms_message += f"{generic_link}"

        # 📧 HTML Email
        html_message = f"""
        <p>✈️ <strong>Flight deal alert! </strong></p>
        <ul>
            <li><strong>Price:</strong> ${price:.2f} (below your target of ${target_price})</li>
            <li><strong>Airline:</strong> {cheapest_flight['airline']}</li>
            <li><strong>Duration:</strong> {int(cheapest_flight['duration_min'] // 60)}h {int(cheapest_flight['duration_min'] % 60)}m</li>
            <li><strong>Layovers:</strong> {cheapest_flight['layovers']}</li>
            <li><strong>Layover Details:</strong> {cheapest_flight['layover_info']}</li>
            <li><strong>Departure:</strong> {departure_time}</li>
            <li><strong>Arrival:</strong> {arrival_time}</li>
        </ul>
        """

        if booking_link:
            html_message += f'<p><a href="{booking_link}">🔗 Book Now</a></p>'
        if generic_link:
            html_message += f'<p><a href="{generic_link}">🌐 Explore more flights</a></p>'

        if os.getenv("SET_SMS_ALERT") == "True" and user_phone:
            print("Sending SMS alert...")
            send_sms(sms_message, user_phone)

        if os.getenv("SET_EMAIL_ALERT") == "True" and user_email:
            print("Sending Email alert...")
            send_email(f"Flight Price Alert [{origin_to_destination}]", html_message, user_email)

        return True

    return False

        
