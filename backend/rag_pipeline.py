from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from .data_loader import all_chunks
import os
from dotenv import load_dotenv

load_dotenv()

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
#          Format retrieved docs into a string
# ======================================================
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# ======================================================
#          Build RAG chain
# ======================================================
def get_rag_chain(provider: str = None):
    if provider:
        retriever = vectordb.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 10, "filter": {"provider": provider.strip().lower()}}
        )
    else:
        retriever = vectordb.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 20}
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
#          Get answer
# ======================================================
def get_answer(query: str, provider: str = None):
    provider = provider or detect_provider_from_query(query)
    chain, _ = get_rag_chain(provider)
    return chain.invoke(query)

def get_answer_with_sources(query: str, provider: str = None):
    provider = provider or detect_provider_from_query(query)
    chain, retriever = get_rag_chain(provider)

    docs = retriever.invoke(query)
    answer = chain.invoke(query)

    return {
        "answer": answer,
        "source_documents": docs
    }