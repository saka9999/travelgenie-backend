# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
import re

app = FastAPI()

# Allow all CORS origins (safe here)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DateCombo(BaseModel):
    departure: str
    return_date: Optional[str]

class FlightQuery(BaseModel):
    origin: str
    destination: str
    journey_type: str
    passengers: int
    cabin_class: str
    currency: str
    date_combinations: List[DateCombo]
    max_stops: int
    max_duration: int  # in hours

@app.post("/search_flights")
def search_flights(query: FlightQuery):
    result_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for combo in query.date_combinations:
            dep_date = combo.departure.replace("-", "")[2:]
            rtn_date = combo.return_date.replace("-", "")[2:] if combo.return_date else ""
            rtn_flag = "rtn=1" if query.journey_type.lower() == "return" else "rtn=0"
            date_part = f"{dep_date}/{rtn_date}" if rtn_flag == "rtn=1" else dep_date

            url = (
                f"https://www.skyscanner.net/transport/flights/"
                f"{query.origin}/{query.destination}/{date_part}/"
                f"?adultsv2={query.passengers}&cabinclass={query.cabin_class.lower()}&"
                f"{rtn_flag}&currency={query.currency}&locale=en-US&market=US"
            )

            page.goto(url)
            page.wait_for_timeout(10000)  # Wait 10s for results to load

            content = page.content()
            prices = re.findall(r'[\₹\$€£]\s?[0-9,]+', content)
            durations = re.findall(r'\d+h\s?\d{0,2}m', content)
            stops = re.findall(r'(Direct|\d stop)', content)
            airlines = re.findall(r'alt="([A-Za-z0-9\s]+ Airlines?)"', content)

            if prices:
                result_list.append({
                    "departure_date": combo.departure,
                    "return_date": combo.return_date,
                    "airline": airlines[0] if airlines else "Unknown",
                    "price": re.sub(r'[^\d]', '', prices[0]),
                    "currency": query.currency,
                    "duration_outbound": durations[0] if len(durations) > 0 else "Unknown",
                    "duration_return": durations[1] if len(durations) > 1 else "Unknown" if rtn_flag == "rtn=1" else None,
                    "stops_outbound": stops[0] if stops else "Unknown",
                    "stops_return": stops[1] if rtn_flag == "rtn=1" and len(stops) > 1 else None,
                    "fare_rules": "Non-refundable or carry-on only (estimate)"
                })
        browser.close()

    return result_list