# frontend/app.py
import streamlit as st
import requests
from datetime import datetime, timedelta
import uuid

BACKEND_URL = "http://127.0.0.1:8000"

# Page config
st.set_page_config(
    page_title="Bus Ticket Booking System",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🚌 Bus Ticket Booking System")
st.markdown("---")

# Sidebar Navigation
menu = st.sidebar.radio(
    "Navigation",
    ["🎫 Book Ticket", "📋 My Bookings", "🚌 Bus Providers", "🗺️ Routes & Fares", "💬 Ask AI Assistant"]
)

# ensure session_id exists for AI assistant sessions
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# ---------------------------
# Helper functions
# ---------------------------
def get_districts():
    try:
        response = requests.get(f"{BACKEND_URL}/districts")
        if response.status_code == 200:
            return response.json()["districts"]
        return []
    except Exception as e:
        st.error(f"Error fetching districts: {e}")
        return []

def get_providers():
    try:
        response = requests.get(f"{BACKEND_URL}/providers")
        if response.status_code == 200:
            return response.json()["providers"]
        return []
    except Exception as e:
        st.error(f"Error fetching providers: {e}")
        return []

def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    phone = phone.strip()
    if phone.startswith("+88"):   # <-- FIXED
        phone = phone[3:]
    return phone

# ---------------------------
# 1. BOOK TICKET (FIXED - Outside Form)
# ---------------------------
if menu == "🎫 Book Ticket":
    st.header("🎫 Book Your Ticket")
    
    districts = get_districts()
    providers = get_providers()
    
    if not districts or not providers:
        st.error("⚠️ Unable to load data. Please ensure the backend server is running.")
    else:
        # Selection Section (OUTSIDE FORM)
        st.subheader("Step 1: Select Route Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Bus Provider
            provider_names = [p["name"] for p in providers]
            selected_provider = st.selectbox(
                "Bus Provider *", 
                provider_names, 
                key="provider_select_main"
            )
            
            provider_data = next((p for p in providers if p["name"] == selected_provider), None)
            coverage_districts = provider_data["coverage_districts"] if provider_data else []
            
            # From District
            from_district = st.selectbox(
                "From District *", 
                coverage_districts, 
                key="from_district_main"
            )
        
        with col2:
            # To District
            to_district_options = [d for d in coverage_districts if d != from_district]
            
            if to_district_options:
                to_district = st.selectbox(
                    "To District *",
                    to_district_options,
                    key="to_district_main"
                )
            else:
                st.warning("No available districts to travel to from this district with this provider.")
                to_district = None
            
            # Dropping Point - This will now update dynamically!
            dropping_point_name = None
            dropping_point_price = 0
            
            if to_district:
                # Find the district data for the TO district
                district_data = next((d for d in districts if d["name"] == to_district), None)
                
                if district_data and district_data["dropping_points"]:
                    # Show info about the destination
                    st.info(f"📍 Available dropping points in **{to_district}**")
                    
                    # Format dropping points with prices
                    dp_options = [f"{dp['name']} - {dp['price']} Taka" for dp in district_data["dropping_points"]]
                    
                    selected_dp = st.selectbox(
                        "Dropping Point *",
                        dp_options,
                        key=f"dropping_point_{to_district}"  # Dynamic key based on district
                    )
                    
                    if selected_dp:
                        dropping_point_name = selected_dp.split(" - ")[0].strip()
                        # Extract price
                        for dp in district_data["dropping_points"]:
                            if dp["name"] == dropping_point_name:
                                dropping_point_price = dp["price"]
                                break
                else:
                    st.warning("No dropping points available for this district.")
        
        # Show current selection summary
        if to_district and dropping_point_name:
            st.success(f"✅ Route: **{from_district}** → **{to_district}** | Dropping Point: **{dropping_point_name}** | Fare: **{dropping_point_price} Taka/person**")
        
        st.markdown("---")
        
        # Booking Form (ONLY passenger details and submission)
        st.subheader("Step 2: Enter Passenger Details")
        
        with st.form("booking_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                name = st.text_input("Name *", placeholder="Enter your full name")
            
            with col2:
                phone = st.text_input("Phone Number *", placeholder="01XXXXXXXXX")
            
            with col3:
                num_passengers = st.number_input(
                    "Number of Passengers *", 
                    min_value=1, 
                    max_value=10, 
                    value=1
                )
            
            travel_date = st.date_input(
                "Travel Date *",
                min_value=datetime.now().date(),
                value=datetime.now().date() + timedelta(days=1)
            )
            
            # Calculate total
            if dropping_point_price and num_passengers:
                total_amount = dropping_point_price * num_passengers
                st.info(f"💰 **Total Amount:** {total_amount} Taka ({num_passengers} passenger(s) × {dropping_point_price} Taka)")
            
            # Submit Button
            submitted = st.form_submit_button("🎫 Confirm Booking", use_container_width=True)
            
            if submitted:
                if not name or not phone:
                    st.error("❌ Please enter your name and phone number!")
                elif not to_district or not dropping_point_name:
                    st.error("❌ Please select route details above!")
                else:
                    phone_norm = normalize_phone(phone)
                    if len(phone_norm) < 11 or not phone_norm.isdigit():
                        st.error("❌ Please enter a valid phone number (11 digits)!")
                    else:
                        booking_data = {
                            "name": name,
                            "phone": phone_norm,
                            "bus_provider": selected_provider,
                            "from_district": from_district,
                            "to_district": to_district,
                            "dropping_point": dropping_point_name,
                            "travel_date": travel_date.isoformat(),
                            "num_passengers": num_passengers
                        }
                        
                        try:
                            response = requests.post(f"{BACKEND_URL}/bookings", json=booking_data)
                            if response.status_code == 200:
                                result = response.json()
                                st.markdown(f"""
<div style='background-color: #d4edda; padding: 20px; border-radius: 10px; border: 2px solid #28a745; margin-top: 20px;'>
    <h3 style='color: #155724;'>✅ Booking Confirmed!</h3>
    <p><strong>Booking ID:</strong> {result['booking_id']}</p>
    <p><strong>Name:</strong> {result['name']}</p>
    <p><strong>Provider:</strong> {result['bus_provider']}</p>
    <p><strong>Route:</strong> {result['from_district']} → {result['to_district']}</p>
    <p><strong>Dropping Point:</strong> {result['dropping_point']}</p>
    <p><strong>Date:</strong> {result['travel_date']}</p>
    <p><strong>Passengers:</strong> {result['num_passengers']}</p>
    <p><strong>Total Amount:</strong> {result['total_amount']} Taka</p>
</div>
                                """, unsafe_allow_html=True)
                                st.balloons()
                            else:
                                error = response.json()
                                st.error(f"❌ Booking failed: {error.get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

# ---------------------------
# 2. MY BOOKINGS
# ---------------------------
elif menu == "📋 My Bookings":
    st.header("📋 My Bookings")
    
    phone = st.text_input("Enter Your Phone Number", placeholder="01XXXXXXXXX", key="mybookings_phone")
    phone_norm = normalize_phone(phone)
    
    if st.button("🔍 Search Bookings"):
        if not phone_norm:
            st.warning("⚠️ Please enter your phone number")
        else:
            try:
                response = requests.get(f"{BACKEND_URL}/bookings/phone/{phone_norm}")
                if response.status_code == 200:
                    bookings = response.json().get("bookings", [])
                    st.session_state["last_bookings"] = bookings
                else:
                    st.session_state["last_bookings"] = []
                    st.info("ℹ️ No bookings found for this phone number.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.session_state["last_bookings"] = []
    
    bookings = st.session_state.get("last_bookings", [])
    
    if bookings:
        st.success(f"✅ Found {len(bookings)} booking(s)")
        for booking in bookings:
            status_color = "🟢" if booking["status"] == "active" else "🔴"
            with st.expander(f"{status_color} Booking ID: {booking['booking_id']} - {booking['status'].upper()}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**Passenger Details:**")
                    st.write(f"Name: {booking['name']}")
                    st.write(f"Phone: {booking['phone']}")
                    st.write(f"Passengers: {booking['num_passengers']}")
                
                with col2:
                    st.write("**Journey Details:**")
                    st.write(f"Provider: {booking['bus_provider']}")
                    st.write(f"Route: {booking['from_district']} → {booking['to_district']}")
                    st.write(f"Dropping Point: {booking['dropping_point']}")
                    st.write(f"Travel Date: {booking['travel_date']}")
                
                with col3:
                    st.write("**Payment Details:**")
                    st.write(f"Fare per person: {booking['fare']} Taka")
                    st.write(f"Total Amount: {booking['total_amount']} Taka")
                    st.write(f"Booking Date: {booking['booking_date'][:10]}")
                
                if booking["status"] == "active":
                    if st.button(f"❌ Cancel Booking", key=f"cancel_{booking['booking_id']}"):
                        try:
                            del_resp = requests.delete(
                                f"{BACKEND_URL}/bookings/{booking['booking_id']}",
                                params={"permanent": "false"},
                                timeout=10
                            )
                            if del_resp.status_code == 200:
                                st.success("✅ Booking cancelled successfully!")
                                updated = []
                                for b in st.session_state.get("last_bookings", []):
                                    if b["booking_id"] == booking["booking_id"]:
                                        b["status"] = "cancelled"
                                    updated.append(b)
                                st.session_state["last_bookings"] = updated
                                st.rerun()
                            else:
                                try:
                                    err = del_resp.json()
                                    st.error(f"❌ Failed to cancel: {err.get('detail', del_resp.text)}")
                                except:
                                    st.error(f"❌ Failed to cancel booking (status {del_resp.status_code})")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    else:
        st.info("No bookings to show. Search above using phone number.")

# ---------------------------
# 3. BUS PROVIDERS
# ---------------------------
elif menu == "🚌 Bus Providers":
    st.header("🚌 Bus Providers")
    
    providers = get_providers()
    
    if not providers:
        st.error("⚠️ Unable to load providers data")
    else:
        cols = st.columns(2)
        for idx, provider in enumerate(providers):
            with cols[idx % 2]:
                st.markdown(f"### 🚌 {provider['name']}")
                st.write(f"**Coverage Districts:** {len(provider['coverage_districts'])}")
                with st.expander("View Coverage"):
                    for district in provider['coverage_districts']:
                        st.write(f"• {district}")
                
                if st.button(f"📄 View Policy", key=f"policy_{provider['name']}"):
                    try:
                        response = requests.get(f"{BACKEND_URL}/providers/{provider['name']}/policy")
                        if response.status_code == 200:
                            policy_data = response.json()
                            st.text_area(f"{provider['name']} Policy", policy_data['policy'], height=300)
                        else:
                            st.warning("⚠️ Policy not available")
                    except Exception as e:
                        st.error(f"❌ Error loading policy: {e}")
                
                st.markdown("---")

# ---------------------------
# 4. ROUTES & FARES
# ---------------------------
elif menu == "🗺️ Routes & Fares":
    st.header("🗺️ Routes & Fares")
    
    districts = get_districts()
    
    if not districts:
        st.error("⚠️ Unable to load districts data")
    else:
        search_term = st.text_input("🔍 Search District or Dropping Point", placeholder="Enter district name...")
        
        filtered_districts = districts
        if search_term:
            filtered_districts = [
                d for d in districts
                if search_term.lower() in d['name'].lower()
                or any(search_term.lower() in dp['name'].lower() for dp in d['dropping_points'])
            ]
        
        cols = st.columns(2)
        for idx, district in enumerate(filtered_districts):
            with cols[idx % 2]:
                st.markdown(f"### 📍 {district['name']}")
                st.write(f"**Total Dropping Points:** {len(district['dropping_points'])}")
                
                prices = [dp['price'] for dp in district['dropping_points']]
                st.write(f"**Price Range:** {min(prices)} - {max(prices)} Taka")
                
                with st.expander("View Dropping Points"):
                    for dp in district['dropping_points']:
                        st.write(f"🚏 **{dp['name']}** - {dp['price']} Taka")
                
                st.markdown("---")

# ---------------------------
# 5. AI ASSISTANT
# ---------------------------
elif menu == "💬 Ask AI Assistant":
    st.header("💬 AI Bus Assistant")
    st.markdown("""
<div style='background-color: #e7f3ff; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
    💡 Ask me anything about bus routes, fares, policies, or travel information!
    You can also ask about your bookings if you provide your phone number.
</div>
    """, unsafe_allow_html=True)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "user_phone" not in st.session_state:
        st.session_state.user_phone = ""
    
    # Optional phone input
    with st.expander("📱 Optional: Enter Phone Number for Booking Queries"):
        st.session_state.user_phone = st.text_input(
            "Phone Number (for booking-related questions)",
            value=st.session_state.user_phone,
            key="ai_phone"
        )
        phone_normalized = normalize_phone(st.session_state.user_phone)
        st.session_state.user_phone = phone_normalized
    
    # Display previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if question := st.chat_input("Ask your question here..."):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "query": question,
                        "session_id": st.session_state.session_id
                    }
                    if st.session_state.user_phone:
                        payload["phone"] = st.session_state.user_phone
                    
                    response = requests.post(f"{BACKEND_URL}/query/smart", json=payload, timeout=30)
                    
                    if response.status_code != 200:
                        st.error(f"Backend error (Status {response.status_code})")
                        answer = "Backend error"
                    else:
                        result = response.json()
                        answer = result.get("message", "I couldn't process that request.")
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
    
    # Clear chat
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.user_phone = ""
        try:
            requests.post(f"{BACKEND_URL}/chat/clear", params={"session_id": st.session_state.session_id})
        except:
            pass
        st.rerun()

# ---------------------------
# SIDEBAR INFO
# ---------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📊 System Status")
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=2)
        if response.status_code == 200:
            st.success("🟢 Backend Connected")
        else:
            st.error("🔴 Backend Error")
    except:
        st.error("🔴 Backend Offline")
    
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.info("""
This is a Bus Ticket Booking System powered by:
- FastAPI Backend
- RAG with Google Gemini
- Streamlit Frontend
    """)
    
    try:
        stats_response = requests.get(f"{BACKEND_URL}/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            st.markdown("---")
            st.markdown("### 📈 Statistics")
            st.metric("Total Bookings", stats.get("total_bookings", 0))
            st.metric("Active Bookings", stats.get("active_bookings", 0))
            st.metric("Total Revenue", f"{stats.get('total_revenue', 0)} Taka")
    except:
        pass