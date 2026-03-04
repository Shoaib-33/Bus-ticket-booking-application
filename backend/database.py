# backend/database.py
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import json

DATABASE_FILE = Path("bus_bookings.db")

def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            bus_provider TEXT NOT NULL,
            from_district TEXT NOT NULL,
            to_district TEXT NOT NULL,
            dropping_point TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            num_passengers INTEGER NOT NULL,
            fare INTEGER NOT NULL,
            total_amount INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            cancelled_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Chat history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            phone TEXT,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Deleted bookings history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deleted_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT NOT NULL,
            booking_data TEXT NOT NULL,
            deleted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_by_phone TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# Initialize database on import
init_database()

# ==================== Booking Operations ====================

def create_booking(booking_data: dict) -> dict:
    """Create a new booking"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO bookings (
            booking_id, name, phone, bus_provider, from_district, to_district,
            dropping_point, travel_date, num_passengers, fare, total_amount, booking_date, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking_data['booking_id'],
        booking_data['name'],
        booking_data['phone'],
        booking_data['bus_provider'],
        booking_data['from_district'],
        booking_data['to_district'],
        booking_data['dropping_point'],
        booking_data['travel_date'],
        booking_data['num_passengers'],
        booking_data['fare'],
        booking_data['total_amount'],
        booking_data['booking_date'],
        'active'
    ))
    
    conn.commit()
    conn.close()
    
    return booking_data

def get_all_bookings() -> List[dict]:
    """Get all bookings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
    bookings = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return bookings

def get_bookings_by_phone(phone: str) -> List[dict]:
    """Get bookings by phone number"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM bookings WHERE phone = ? ORDER BY created_at DESC", (phone,))
    bookings = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return bookings

def get_booking_by_id(booking_id: str) -> Optional[dict]:
    """Get a specific booking"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None

def delete_booking_permanently(booking_id: str) -> bool:
    """Permanently delete a booking"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get booking data first
    cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
    booking = cursor.fetchone()
    
    if not booking:
        conn.close()
        return False
    
    # Save to deleted bookings history
    booking_data = dict(booking)
    cursor.execute("""
        INSERT INTO deleted_bookings (booking_id, booking_data, deleted_by_phone)
        VALUES (?, ?, ?)
    """, (booking_id, json.dumps(booking_data), booking_data.get('phone')))
    
    # Delete from bookings table
    cursor.execute("DELETE FROM bookings WHERE booking_id = ?", (booking_id,))
    
    conn.commit()
    conn.close()
    
    return True

def cancel_booking(booking_id: str) -> bool:
    """Mark booking as cancelled (soft delete)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE bookings 
        SET status = 'cancelled', cancelled_date = ?
        WHERE booking_id = ? AND status = 'active'
    """, (datetime.now().isoformat(), booking_id))
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected > 0

def generate_booking_id() -> str:
    """Generate unique booking ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM bookings")
    count = cursor.fetchone()['count']
    
    conn.close()
    return f"BK{count + 1:05d}"

# ==================== Chat History Operations ====================

def save_chat_message(session_id: str, role: str, message: str, phone: str = None):
    """Save a chat message"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO chat_history (session_id, phone, role, message)
        VALUES (?, ?, ?, ?)
    """, (session_id, phone, role, message))
    
    conn.commit()
    conn.close()

def get_chat_history(session_id: str, limit: int = 10) -> List[dict]:
    """Get chat history for a session"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, message, timestamp 
        FROM chat_history 
        WHERE session_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (session_id, limit))
    
    history = [dict(row) for row in cursor.fetchall()]
    history.reverse()  # Oldest first
    
    conn.close()
    return history

def clear_chat_history(session_id: str):
    """Clear chat history for a session"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    
    conn.commit()
    conn.close()

# ==================== Statistics ====================

def get_booking_statistics() -> dict:
    """Get booking statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total bookings
    cursor.execute("SELECT COUNT(*) as count FROM bookings")
    total = cursor.fetchone()['count']
    
    # Active bookings
    cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'active'")
    active = cursor.fetchone()['count']
    
    # Cancelled bookings
    cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'cancelled'")
    cancelled = cursor.fetchone()['count']
    
    # Total revenue (active only)
    cursor.execute("SELECT SUM(total_amount) as revenue FROM bookings WHERE status = 'active'")
    revenue = cursor.fetchone()['revenue'] or 0
    
    # Provider statistics
    cursor.execute("""
        SELECT bus_provider, COUNT(*) as count, SUM(total_amount) as revenue
        FROM bookings
        WHERE status = 'active'
        GROUP BY bus_provider
    """)
    
    provider_stats = {}
    for row in cursor.fetchall():
        provider_stats[row['bus_provider']] = {
            'count': row['count'],
            'revenue': row['revenue']
        }
    
    conn.close()
    
    return {
        'total_bookings': total,
        'active_bookings': active,
        'cancelled_bookings': cancelled,
        'total_revenue': revenue,
        'provider_statistics': provider_stats
    }