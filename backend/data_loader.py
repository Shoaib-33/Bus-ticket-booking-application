# backend/data_loader.py
import json
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter

DATASET_FILE = Path("data.json")
POLICY_FOLDER = Path("attachment")

# ---------------------------
# Load main dataset
# ---------------------------
with open(DATASET_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

districts = data["districts"]
providers = data["bus_providers"]

# ---------------------------
# Chunk storage container
# ---------------------------
all_chunks = []

# ---------------------------
# District & Dropping Point Chunks
# ---------------------------
for district in districts:
    # District block summary
    text = f"District: {district['name']}\nDropping points:\n"

    for dp in district["dropping_points"]:
        text += f"• {dp['name']} — {dp['price']} Taka\n"

    all_chunks.append({
        "content": text,
        "metadata": {
            "type": "district",
            "district": district["name"]
        }
    })

    # Individual dropping points
    for dp in district["dropping_points"]:
        dp_text = (
            f"Dropping point: {dp['name']} in {district['name']}.\n"
            f"Fare: {dp['price']} Taka."
        )

        all_chunks.append({
            "content": dp_text,
            "metadata": {
                "type": "dropping_point",
                "district": district["name"],
                "point": dp["name"],
                "price": dp["price"]
            }
        })

# ---------------------------
# Provider Chunks (Desh, Hanif, Ena, etc.)
# ---------------------------
for provider in providers:
    provider_text = (
        f"Bus Provider: {provider['name']}\n"
        f"Coverage Districts: {', '.join(provider['coverage_districts'])}"
    )

    all_chunks.append({
        "content": provider_text,
        "metadata": {
            "type": "provider",
            "provider": provider["name"].lower(),
            "districts": provider["coverage_districts"]
        }
    })

# ---------------------------
# Policy Chunks (Hanif.txt, Ena.txt, etc.)
# ---------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=150
)

policy_files = list(POLICY_FOLDER.glob("*.txt"))

for txt_file in policy_files:
    provider_name = txt_file.stem.lower()

    with open(txt_file, "r", encoding="utf-8") as f:
        policy_text = f.read().strip()

    wrapped_text = f"Policy of {provider_name} bus:\n\n{policy_text}"

    chunks = text_splitter.split_text(wrapped_text)

    for i, chunk in enumerate(chunks):
        all_chunks.append({
            "content": chunk,
            "metadata": {
                "type": "policy",
                "provider": provider_name,
                "chunk_index": i
            }
        })

# --------------- SUMMARY ----------------
print("\n======================================")
print("Total Chunks Created:", len(all_chunks))
print("======================================\n")

OUTPUT_FILE = "chunks.txt"

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for index, chunk in enumerate(all_chunks):
        f.write("============================================================\n")
        f.write(f"CHUNK #{index}\n")
        f.write("------------------------------------------------------------\n")
        f.write("CONTENT:\n")
        f.write(chunk["content"] + "\n\n")
        f.write("METADATA:\n")
        for k, v in chunk["metadata"].items():
            f.write(f"  {k}: {v}\n")
        f.write("============================================================\n\n")

print(f"Dumped {len(all_chunks)} chunks to chunks.txt")