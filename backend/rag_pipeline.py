from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from .data_loader import all_chunks, providers as raw_providers
import re
import os
from dotenv import load_dotenv

load_dotenv()

# --- API Key ---
os.environ["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY", "")

# ======================================================
#          Embeddings & Vector DB
# ======================================================
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectordb = Chroma(
    collection_name="bus_data",
    embedding_function=embedding_model,
    persist_directory="vectorstore"
)


# ======================================================
#          Metadata Cleaner
# ======================================================
def clean_metadata(metadata: dict) -> dict:
    """Convert list values to comma-separated strings for Chroma compatibility."""
    cleaned = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            cleaned[key] = ", ".join(str(v) for v in value)
        elif isinstance(value, int) or isinstance(value, float):
            cleaned[key] = value          # keep numbers as numbers for filtering
        else:
            cleaned[key] = value
    return cleaned


# ======================================================
#          Load Chunks into Vector DB (once)
# ======================================================
if len(vectordb.get()["ids"]) == 0:
    print("Adding chunks to vector DB...")
    for chunk in all_chunks:
        metadata = chunk["metadata"].copy()
        if "provider" in metadata and metadata["provider"]:
            metadata["provider"] = metadata["provider"].strip().lower()
        vectordb.add_texts(
            [chunk["content"]],
            metadatas=[clean_metadata(metadata)]
        )
    print(f"✅ Added {len(all_chunks)} chunks.")
else:
    print(f"ℹ️ Vector DB already has {len(vectordb.get()['ids'])} chunks.")


# ======================================================
#          LLM
# ======================================================
gemini_llm = ChatGoogleGenerativeAI(
    temperature=0.3,
    model="gemini-2.5-flash",
    google_api_key=os.environ["GOOGLE_API_KEY"]
)


# ======================================================
#          Prompt
# ======================================================
prompt_template = """You are a friendly and helpful bus service assistant for Bangladesh bus services.
CRITICAL INSTRUCTIONS:
1. If the user asks about a SPECIFIC bus provider (Hanif, Ena, Desh Travel, etc.), ONLY use information from that provider's context.
2. NEVER mix contact information, policies, or details between different providers.
3. When answering about contact info, address, or policy — make sure you're reading the correct provider's data.
4. If you're not certain which provider the information belongs to, say you don't know.
GENERAL INSTRUCTIONS:
- Answer ONLY from the context provided below.
- Be conversational, friendly, and concise.
- Always mention prices in "Taka".
- Use bullet points for lists.
- If information is missing, say: "I don't have that information. Please contact the bus service directly."
Context Information:
{context}
User Question: {question}
Helpful Answer:"""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)


# ======================================================
#          Query Understanding Helpers
# ======================================================

# Build known provider list dynamically from data
KNOWN_PROVIDERS = [p["name"].lower() for p in raw_providers]


def detect_provider_from_query(query: str) -> str | None:
    """Detect if user is asking about a specific bus provider."""
    query_lower = query.lower()
    for provider in KNOWN_PROVIDERS:
        if provider in query_lower:
            return provider
    return None


def detect_query_type(query: str) -> str | None:
    """
    Detect the type of information the user is looking for.
    Returns: 'policy' | 'dropping_point' | 'provider' | None
    """
    query_lower = query.lower()

    policy_keywords = ["policy", "cancel", "refund", "reschedule", "terms", "rules", "luggage"]
    fare_keywords   = ["fare", "price", "taka", "cost", "cheap", "expensive", "affordable", "route", "ticket"]
    provider_keywords = ["contact", "phone", "address", "office", "helpline", "number", "location"]

    if any(w in query_lower for w in policy_keywords):
        return "policy"
    if any(w in query_lower for w in fare_keywords):
        return "dropping_point"
    if any(w in query_lower for w in provider_keywords):
        return "provider"

    return None  # broad search — no type filter applied


def extract_price_filter(query: str) -> dict | None:
    """
    Extract numeric price constraints from natural language.
    Returns a Chroma-compatible filter dict or None.
    """
    # between X and Y
    match = re.search(r'between\s*(\d+)\s*and\s*(\d+)', query, re.IGNORECASE)
    if match:
        return {
            "$and": [
                {"price": {"$gte": int(match.group(1))}},
                {"price": {"$lte": int(match.group(2))}}
            ]
        }

    # under / below / less than X
    match = re.search(r'(under|below|less than)\s*(\d+)', query, re.IGNORECASE)
    if match:
        return {"price": {"$lte": int(match.group(2))}}

    # above / over / more than X
    match = re.search(r'(above|over|more than)\s*(\d+)', query, re.IGNORECASE)
    if match:
        return {"price": {"$gte": int(match.group(2))}}

    # exactly X taka
    match = re.search(r'exactly\s*(\d+)', query, re.IGNORECASE)
    if match:
        return {"price": {"$eq": int(match.group(1))}}

    return None


def build_filter(provider: str = None, query: str = None) -> dict | None:
    """
    Combine all filters (provider + type + price) into a single
    Chroma-compatible where clause.
    """
    conditions = []

    # 1. Provider filter
    if provider:
        conditions.append({"provider": {"$eq": provider.strip().lower()}})

    if query:
        # 2. Type filter
        query_type = detect_query_type(query)
        if query_type:
            conditions.append({"type": {"$eq": query_type}})

        # 3. Price filter — only applies to dropping_point type
        price_filter = extract_price_filter(query)
        if price_filter:
            # Force type to dropping_point when price is involved
            if not query_type:
                conditions.append({"type": {"$eq": "dropping_point"}})
            conditions.append(price_filter)

    if len(conditions) == 0:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


# ======================================================
#          Format Retrieved Docs
# ======================================================
def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


# ======================================================
#          Build RAG Chain
# ======================================================
def get_rag_chain(provider: str = None, query: str = None):
    """
    Build a LangChain RAG chain with smart filtering.
    - Provider filter: only chunks from that provider
    - Type filter: policy / dropping_point / provider
    - Price filter: $lte / $gte / $eq on metadata price field
    """
    where_filter = build_filter(provider=provider, query=query)

    # Adaptive k:
    # Policy queries need more chunks (long text split into many pieces)
    # Fare/price queries need fewer (very specific records)
    query_type = detect_query_type(query) if query else None
    if query_type == "policy":
        k = 8
    elif query_type == "dropping_point":
        k = 6
    else:
        k = 10

    search_kwargs = {"k": k}
    if where_filter:
        search_kwargs["filter"] = where_filter

    retriever = vectordb.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs
    )

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | PROMPT
        | gemini_llm
        | StrOutputParser()
    )

    return chain, retriever


# ======================================================
#          Public API
# ======================================================
def get_answer(query: str, provider: str = None) -> str:
    """
    Get a plain answer string for a user query.
    Provider is auto-detected from query if not passed explicitly.
    """
    provider = provider or detect_provider_from_query(query)
    chain, _ = get_rag_chain(provider=provider, query=query)
    return chain.invoke(query)


def get_answer_with_sources(query: str, provider: str = None) -> dict:
    """
    Get answer + source documents for debugging or display.
    Returns: { answer: str, source_documents: list[Document] }
    """
    provider = provider or detect_provider_from_query(query)
    chain, retriever = get_rag_chain(provider=provider, query=query)

    docs = retriever.invoke(query)
    answer = chain.invoke(query)

    return {
        "answer": answer,
        "source_documents": docs,
        "debug": {
            "provider_detected": provider,
            "query_type": detect_query_type(query),
            "price_filter": extract_price_filter(query),
            "chunks_retrieved": len(docs)
        }
    }
