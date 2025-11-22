from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from .data_loader import all_chunks
import os

# --- API Key ---
os.environ["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY", "")

# --- Embeddings ---
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# --- Vector DB ---
vectordb = Chroma(
    collection_name="bus_data",
    embedding_function=embedding_model,
    persist_directory="vectorstore"
)

# Convert list metadata → strings
def clean_metadata(metadata):
    cleaned = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            cleaned[key] = ", ".join(str(v) for v in value)
        else:
            cleaned[key] = value
    return cleaned

# Load chunks if empty
if len(vectordb.get()["ids"]) == 0:
    print("Adding chunks to vector DB...")
    for chunk in all_chunks:
        metadata = chunk["metadata"].copy()
        if "provider" in metadata and metadata["provider"]:
            metadata["provider"] = metadata["provider"].strip().lower()
        vectordb.add_texts([chunk["content"]], metadatas=[clean_metadata(metadata)])
    print(f"✅ Added {len(all_chunks)} chunks.")
else:
    print(f"ℹ️ Vector database already contains {len(vectordb.get()['ids'])} chunks.")

# --- Gemini LLM ---
gemini_llm = ChatGoogleGenerativeAI(
    temperature=0.3,
    model="gemini-2.5-flash",
    google_api_key=os.environ["GOOGLE_API_KEY"]
)

# --- Enhanced Prompt ---
prompt_template = """You are a friendly and helpful bus service assistant for Bangladesh bus services.

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. If the user asks about a SPECIFIC bus provider (like Hanif, Ena, Desh Travel, etc.), ONLY use information from that provider's context.
2. NEVER mix contact information, policies, or details between different providers.
3. When answering about contact information, address, or policy, make absolutely sure you're looking at the correct provider's data.
4. If you're not certain which provider the information belongs to, say you don't know.

GENERAL INSTRUCTIONS:
- Answer ONLY from the context provided below
- Be conversational, friendly, and concise
- Always mention prices in "Taka"
- Use bullet points for lists
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
#          Detect provider from query
# ======================================================
def detect_provider_from_query(query: str):
    query_lower = query.lower()
    providers = ["hanif", "ena", "desh travel", "green line", "soudia", "shyamoli"]
    for provider in providers:
        if provider in query_lower:
            return provider
    return None

# ======================================================
#          Create Conversational Retrieval Chain
# ======================================================
def get_conversational_chain(provider: str = None):
    # Filter by provider if given
    if provider:
        retriever = vectordb.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 10, "filter": {"provider": provider.strip().lower()}}
        )
    else:
        retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 20})
    
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    conv_chain = ConversationalRetrievalChain.from_llm(
        llm=gemini_llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": PROMPT}
    )
    
    return conv_chain

# ======================================================
#          Get answer with memory
# ======================================================
def get_answer(query: str, provider: str = None):
    provider = provider or detect_provider_from_query(query)
    chain = get_conversational_chain(provider)
    result = chain.run(query)
    return result

def get_answer_with_sources(query: str, provider: str = None):
    provider = provider or detect_provider_from_query(query)
    chain = get_conversational_chain(provider)
    result = chain({"question": query, "chat_history": []})  # can pass previous history if needed
    return result
