# 🚌 Bus Ticket Booking Application

A comprehensive bus ticket booking system with AI-powered search capabilities, built using FastAPI (backend), Streamlit (frontend), and RAG (Retrieval-Augmented Generation) pipeline for intelligent query handling.

## 🎯 Project Overview

This application allows users to:
- 🔍 Search for buses using natural language queries
- 🎫 Book tickets with basic information (name and phone number)
- 📋 View and manage their bookings
- 🚌 Access detailed bus provider information (routes, fares, policies, contact details)
- 💬 Ask questions about bus services and get AI-powered responses

## ✨ Key Features

- **RAG Pipeline Integration**: Uses LangChain with Google Generative AI for intelligent query processing
- **Vector Search**: ChromaDB with sentence transformers for semantic search capabilities
- **Natural Language Queries**: Ask questions like "Are there any buses from Dhaka to Rajshahi under 500 taka?"
- **SQLite Database**: Reliable booking data persistence
- **JSON-based Route Data**: Flexible data management for districts, routes, and providers
- **Complete CRUD Operations**: Create, read, update, and delete bookings
- **User-friendly Interface**: Streamlit-based frontend for easy interaction

## 📂 Project Structure

```
bus_ticket/
│
├── frontend/
│   └── app.py                  # Streamlit application
│
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── database.py             # SQLite database configuration
│   ├── models.py               # Pydantic models
│   ├── rag_pipeline.py         # RAG implementation
│   └── data_loader.py          # Data loading utilities
│
├── data.json                   # Main data file (routes, districts, providers)
│
├── attachments/
│   ├── hanif.txt               # Hanif bus provider information
│   ├── ena.txt                 # Ena bus provider information
│   └── ...                     # Other bus provider files
│
├── bus_booking.db              # SQLite database (auto-generated)
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create this)
└── README.md                   # This file
```

## 🚀 Installation & Setup

### Prerequisites

- Python 3.10
- pip (Python package manager)
- Git

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/Bus-ticket-booking-application.git
cd Bus-ticket-booking-application
```

### 2️⃣ Create a Virtual Environment

```bash
python -m venv venv
```

### 3️⃣ Activate the Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 5️⃣ Configure Environment Variables

Create a `.env` file in the backend directory:

```env
# Google Generative AI API Key
GOOGLE_API_KEY=your_google_api_key_here

# Database Configuration
DATABASE_PATH=./bus_booking.db

# ChromaDB Configuration (optional)
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

**To get a Google API Key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste it into your `.env` file

### 6️⃣ Run the Application

**Terminal 1 - Start the Backend (FastAPI):**
```bash
uvicorn backend.main:app --reload --port 8000
```

If successful, you will see:
```
Uvicorn running on http://127.0.0.1:8000
```

**Terminal 2 - Start the Frontend (Streamlit):**
```bash
streamlit run frontend/app.py
```

### 7️⃣ Access the Application

- **Frontend (Streamlit)**: [http://localhost:8501](http://localhost:8501)
- **Backend API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend API Docs (Redoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)


## 🤖 RAG Pipeline Architecture

The application implements a Retrieval-Augmented Generation pipeline:

1. **Data Ingestion**: Bus provider information, policies, and route data are loaded from `data.json` and text files in `attachments/`
2. **Embedding Generation**: Sentence transformers convert text into vector embeddings
3. **Vector Storage**: ChromaDB stores embeddings for fast semantic search
4. **Query Processing**: User questions are embedded and matched against stored vectors
5. **Context Retrieval**: Relevant information is retrieved from the vector database
6. **Response Generation**: Google Generative AI (Gemini) generates natural language responses based on retrieved context

## 📦 Dependencies

```txt
fastapi
uvicorn[standard]
pydantic
requests
streamlit
sqlite-utils
langchain
langchain-community
langchain-core
langchain-text-splitters
huggingface-hub
langchain-huggingface
langchain-chroma
sentence-transformers
chromadb
langchain-google-genai
google-generativeai
python-dotenv
```

## 📝 Example Queries

The application can handle natural language questions like:

- "Are there any buses from Dhaka to Rajshahi under 500 taka?"
- "Show all bus providers operating from Chittagong to Sylhet."
- "What are the contact details of Hanif Bus?"
- "Can I cancel my booking for the bus from Dhaka to Barishal on 15th November?"
- "What is the privacy policy of Ena Paribahan?"
- "Which bus is cheapest from Dhaka to Cox's Bazar?"

## 💡 Important Notes

- Ensure the `data.json` file is present in the root directory with route and provider information
- All bus provider detailed information should be placed in `attachments/` as individual `.txt` files
- The SQLite database (`bus_booking.db`) will be created automatically when you first run the backend
- If you encounter any database issues, you can delete `bus_booking.db` and it will be recreated on the next run
- Make sure to create a `.env` file with your Google API key before running the application


## 🛠️ Troubleshooting

**Issue: Google API Key Error**
- Ensure your `.env` file contains a valid `GOOGLE_API_KEY`
- Check that the API key has access to Generative AI services

**Issue: ChromaDB Permission Error**
- Delete the `chroma_db` directory and restart the application
- Ensure proper write permissions in the project directory

**Issue: Database Locked**
- Close any other processes accessing the SQLite database
- Restart the FastAPI server

**Issue: Module Not Found**
- Make sure you've activated the virtual environment
- Run `pip install -r requirements.txt` again

## 🎥 Demo Video

[https://youtu.be/wBabHF555jU]


## 📄 License

This project is open source and available under the [MIT License](LICENSE).


For questions or support, please open an issue in the GitHub repository.

---

**Built with:** FastAPI • Streamlit • LangChain • Google Generative AI • ChromaDB • SQLite
