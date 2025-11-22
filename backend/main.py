# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import json
from pathlib import Path
import uuid

from .database import (
    create_booking, get_all_bookings, get_bookings_by_phone,
    get_booking_by_id, cancel_booking, delete_booking_permanently,
    generate_booking_id, get_booking_statistics, save_chat_message, get_chat_history
)
from .rag_pipeline import get_answer, get_answer_with_sources

app = FastAPI(title="Bus Ticket Booking System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load bus data
DATA_FILE = Path(__file__).parent.parent / "data.json"
with open(DATA_FILE, "r", encoding="utf-8") as f:
    bus_data = json.load(f)

# ==================== Models ====================

class BookingCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=11, max_length=15)
    bus_provider: str
    from_district: str
    to_district: str
    dropping_point: str
    travel_date: str
    num_passengers: int = Field(default=1, ge=1, le=10)

class BookingResponse(BaseModel):
    booking_id: str
    name: str
    phone: str
    bus_provider: str
    from_district: str
    to_district: str
    dropping_point: str
    travel_date: str
    num_passengers: int
    fare: int
    total_amount: int
    booking_date: str
    status: str

class QueryRequest(BaseModel):
    query: str
    phone: Optional[str] = None
    session_id: Optional[str] = None

# ==================== Helper Functions ====================

def get_fare(district: str, dropping_point: str) -> int:
    for dist in bus_data["districts"]:
        if dist["name"].lower() == district.lower():
            for dp in dist["dropping_points"]:
                if dp["name"].lower() == dropping_point.lower():
                    return dp["price"]
    return 0

def validate_route(provider: str, from_district: str, to_district: str) -> bool:
    for p in bus_data["bus_providers"]:
        if p["name"].lower() == provider.lower():
            coverage_lower = [d.lower() for d in p["coverage_districts"]]
            return from_district.lower() in coverage_lower and to_district.lower() in coverage_lower
    return False

def get_available_providers(from_district: str, to_district: str) -> List[str]:
    available = []
    for provider in bus_data["bus_providers"]:
        coverage_lower = [d.lower() for d in provider["coverage_districts"]]
        if from_district.lower() in coverage_lower and to_district.lower() in coverage_lower:
            available.append(provider["name"])
    return available

def get_dropping_points_by_district(district: str):
    for d in bus_data["districts"]:
        if d["name"].lower() == district.lower():
            return [{"name": dp["name"], "price": dp["price"]} for dp in d["dropping_points"]]
    return []

# ==================== Session Storage for AI Assistant ====================
sessions = {}  # session_id: {"awaiting_booking_id": bool, "pending_bookings": [], "phone": str}

# ==================== API Endpoints ====================

@app.get("/")
def root():
    return {"message": "Bus Ticket Booking System API", "version": "1.0"}

# -------------------- Bus Info --------------------

@app.get("/districts")
def get_districts():
    return {"districts": bus_data["districts"]}

@app.get("/providers")
def get_providers():
    return {"providers": bus_data["bus_providers"]}

@app.get("/providers/{provider_name}/policy")
def get_provider_policy(provider_name: str):
    provider_map = {
        "desh travel": "desh_travel.txt",
        "ena": "ena.txt",
        "green line": "green line.txt",
        "greenline": "green line.txt",
        "hanif": "hanif.txt",
        "shyamoli": "shyamoli.txt",
        "soudia": "soudia.txt"
    }

    normalized = provider_name.lower().strip()

    if normalized not in provider_map:
        raise HTTPException(status_code=404, detail="Policy not available for this provider")

    file_name = provider_map[normalized]
    file_path = Path(__file__).parent.parent / "attachment" / file_name

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Policy file not found")

    return {
        "provider": provider_name,
        "policy": content
    }

# -------------------- Dynamic Providers & Dropping Points --------------------

@app.get("/available-providers")
def available_providers(from_district: str, to_district: str):
    providers = get_available_providers(from_district, to_district)
    if not providers:
        return {"message": f"No bus providers operate between {from_district} and {to_district}", "providers": []}
    return {"providers": providers}

@app.get("/dropping-points/{district}")
def dropping_points(district: str):
    points = get_dropping_points_by_district(district)
    if not points:
        return {"message": f"No dropping points found for {district}", "dropping_points": []}
    return {"dropping_points": points}

# -------------------- Booking Management --------------------

@app.post("/bookings", response_model=BookingResponse)
def create_booking_endpoint(booking: BookingCreate):
    provider_exists = any(p["name"].lower() == booking.bus_provider.lower() for p in bus_data["bus_providers"])
    if not provider_exists:
        raise HTTPException(status_code=400, detail=f"Bus provider '{booking.bus_provider}' not found")
    if not validate_route(booking.bus_provider, booking.from_district, booking.to_district):
        raise HTTPException(status_code=400, detail=f"{booking.bus_provider} does not operate between {booking.from_district} and {booking.to_district}")
    fare = get_fare(booking.to_district, booking.dropping_point)
    if fare == 0:
        raise HTTPException(status_code=400, detail=f"Dropping point '{booking.dropping_point}' not found in {booking.to_district}")
    new_booking_data = {
        "booking_id": generate_booking_id(),
        "name": booking.name,
        "phone": booking.phone.strip(),
        "bus_provider": booking.bus_provider,
        "from_district": booking.from_district,
        "to_district": booking.to_district,
        "dropping_point": booking.dropping_point,
        "travel_date": booking.travel_date,
        "num_passengers": booking.num_passengers,
        "fare": fare,
        "total_amount": fare * booking.num_passengers,
        "booking_date": datetime.now().isoformat(),
        "status": "active"
    }
    saved_booking = create_booking(new_booking_data)
    return saved_booking

@app.get("/bookings")
def list_all_bookings():
    return {"bookings": get_all_bookings()}

@app.get("/bookings/phone/{phone}")
def bookings_by_phone(phone: str):
    bookings = get_bookings_by_phone(phone.strip())
    if not bookings:
        raise HTTPException(status_code=404, detail="No bookings found for this phone number")
    return {"bookings": bookings}

@app.get("/bookings/{booking_id}")
def booking_details(booking_id: str):
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.delete("/bookings/{booking_id}")
def delete_booking_endpoint(booking_id: str, permanent: Optional[bool] = False):
    if permanent:
        success = delete_booking_permanently(booking_id)
        if success:
            return {"message": f"Booking {booking_id} deleted permanently."}
        raise HTTPException(status_code=404, detail="Booking not found")
    else:
        success = cancel_booking(booking_id)
        if success:
            return {"message": f"Booking {booking_id} cancelled."}
        raise HTTPException(status_code=404, detail="Booking not found")

# -------------------- Smart Query (AI Assistant) --------------------

@app.post("/query/smart")
def query_smart(request: QueryRequest):
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = {
            "awaiting_booking_id": False,
            "awaiting_phone_for_cancel": False,
            "pending_bookings": [],
            "phone": None
        }
    session = sessions[session_id]
    query_text = request.query.strip()
    query_lower = query_text.lower()

    save_chat_message(session_id, "user", request.query, request.phone)

    # Cancellation logic (kept same as before)
    if session.get("awaiting_phone_for_cancel"):
        phone = query_text
        if phone.startswith("+88"):
            phone = phone[3:]
        session["phone"] = phone
        session["awaiting_phone_for_cancel"] = False
        bookings = get_bookings_by_phone(phone)
        active_bookings = [b for b in bookings if b['status'] == 'active']

        if not active_bookings:
            message = f"ℹ️ No active bookings found for phone number {phone}"
            save_chat_message(session_id, "assistant", message, phone)
            return {"message": message, "session_id": session_id}

        if len(active_bookings) == 1:
            booking_to_cancel = active_bookings[0]
            cancel_booking(booking_to_cancel['booking_id'])
            message = f"✅ Booking {booking_to_cancel['booking_id']} has been cancelled successfully."
            save_chat_message(session_id, "assistant", message, phone)
            return {"message": message, "session_id": session_id}

        session["awaiting_booking_id"] = True
        session["pending_bookings"] = active_bookings
        message = "You have multiple active bookings:\n"
        for b in active_bookings:
            message += f"{b['from_district']} → {b['to_district']} on {b['travel_date']} (ID: {b['booking_id']})\n"
        message += "\nPlease provide the Booking ID you want to cancel."
        save_chat_message(session_id, "assistant", message, phone)
        return {"message": message, "session_id": session_id}

    if session["awaiting_booking_id"]:
        booking_id = query_text
        booking = next((b for b in session["pending_bookings"] if b["booking_id"] == booking_id), None)
        if booking:
            cancel_booking(booking_id)
            session["awaiting_booking_id"] = False
            session["pending_bookings"] = []
            message = f"✅ Booking {booking_id} has been cancelled successfully."
            save_chat_message(session_id, "assistant", message, session.get("phone"))
            return {"message": message, "session_id": session_id}
        else:
            message = f"❌ Booking ID {booking_id} not found. Please check again."
            save_chat_message(session_id, "assistant", message, session.get("phone"))
            return {"message": message, "session_id": session_id}

    if any(k in query_lower for k in ["cancel", "cancellation"]):
        phone = (request.phone or session.get("phone") or "").strip()
        if not phone:
            session["awaiting_phone_for_cancel"] = True
            message = "📱 To cancel your booking, please provide your phone number."
            save_chat_message(session_id, "assistant", message, None)
            return {"message": message, "session_id": session_id}

        if phone.startswith("+88"):
            phone = phone[3:]
        session["phone"] = phone

        bookings = get_bookings_by_phone(phone)
        active_bookings = [b for b in bookings if b['status'] == 'active']

        if not active_bookings:
            message = f"ℹ️ No active bookings found for phone number {phone}"
            save_chat_message(session_id, "assistant", message, phone)
            return {"message": message, "session_id": session_id}

        if len(active_bookings) == 1:
            booking_to_cancel = active_bookings[0]
            cancel_booking(booking_to_cancel['booking_id'])
            message = f"✅ Booking {booking_to_cancel['booking_id']} has been cancelled successfully."
            save_chat_message(session_id, "assistant", message, phone)
            return {"message": message, "session_id": session_id}

        session["awaiting_booking_id"] = True
        session["pending_bookings"] = active_bookings
        message = "You have multiple active bookings:\n"
        for b in active_bookings:
            message += f"{b['from_district']} → {b['to_district']} on {b['travel_date']} (ID: {b['booking_id']})\n"
        message += "\nPlease provide the Booking ID you want to cancel."
        save_chat_message(session_id, "assistant", message, phone)
        return {"message": message, "session_id": session_id}

    # Default AI response
    answer = get_answer(request.query)
    save_chat_message(session_id, "assistant", answer, session.get("phone"))
    return {"message": answer, "session_id": session_id}


@app.post("/query/detailed")
def query_rag_with_sources(request: QueryRequest):
    result = get_answer_with_sources(request.query)
    return result

# -------------------- Statistics --------------------

@app.get("/stats")
def stats():
    return get_booking_statistics()

# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
