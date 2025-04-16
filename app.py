from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
import re

app = FastAPI()

# CORS to allow frontend to talk to backend
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
    max_duration: int

@app.get("/")
def read_root():
    return {"message": "TravelGenie backend is live!"}

@app.post("/search_flights")
def search_flights(query: FlightQuery):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for combo in query.date_combinations:
            try:
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

                page.goto(url, timeout=60000)
                page.wait_for_timeout(10000)  # wait for content to load

                html = page.content()
                prices = re.findall(r'[₹$€£]\s?[0-9,]+', html)
                durations = re.findall(r'\d+h\s?\d{0,2}m', html)
                stops = re.findall(r'(Direct|\d stop)', html)
                airlines = re.findall(r'alt="([A-Za-z0-9\s]+ Airlines?)"', html)

                if prices:
                    results.append({
                        "departure_date": combo.departure,
                        "return_date": combo.return_date,
                        "airline": airlines[0] if airlines else "Unknown",
                        "price": re.sub(r'[^\d]', '', prices[0]),
                        "currency": query.currency,
                        "duration_outbound": durations[0] if len(durations) > 0 else "Unknown",
                        "duration_return": durations[1] if query.journey_type.lower() == "return" and len(durations) > 1 else None,
                        "stops_outbound": stops[0] if len(stops) > 0 else "Unknown",
                        "stops_return": stops[1] if query.journey_type.lower() == "return" and len(stops) > 1 else None,
                        "fare_rules": "Non-refundable or carry-on only (estimate)"
                    })

            except Exception as e:
                print(f"Error scraping combo {combo}: {e}")
                continue

        browser.close()

    if not results:
        raise HTTPException(status_code=500, detail="No flights found or Playwright error.")
    return results
