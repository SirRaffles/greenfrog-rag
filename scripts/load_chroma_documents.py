#!/usr/bin/env python3
"""
Load Matcha Initiative Documents into ChromaDB
Directly populates ChromaDB collection for RAG V2
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings

# Configuration
CHROMADB_URL = "http://chromadb:8000"  # Use Docker network hostname
COLLECTION_NAME = "greenfrog"
SCRAPED_DATA_DIR = "/app/data/scraped/Matchainitiative"  # Path inside Docker container

print("=" * 60)
print("GreenFrog ChromaDB Document Loader")
print("=" * 60)
print()

# Connect to ChromaDB
print(f"Connecting to ChromaDB at {CHROMADB_URL}...")
try:
    client = chromadb.HttpClient(
        host=CHROMADB_URL.replace("http://", "").split(":")[0],
        port=int(CHROMADB_URL.split(":")[-1])
    )
    # Test connection
    client.heartbeat()
    print("✓ Connected to ChromaDB")
except Exception as e:
    print(f"✗ Failed to connect to ChromaDB: {e}")
    print("  Make sure ChromaDB is running: docker compose up -d chromadb")
    exit(1)

print()

# Get or create collection
print(f"Getting/creating collection '{COLLECTION_NAME}'...")
try:
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "GreenFrog sustainability knowledge base"}
    )
    print(f"✓ Collection ready")
    existing_count = collection.count()
    print(f"  Current document count: {existing_count}")
except Exception as e:
    print(f"✗ Failed to get collection: {e}")
    exit(1)

print()

# Find all JSON files
scraped_dir = Path(SCRAPED_DATA_DIR)
if not scraped_dir.exists():
    print(f"✗ Scraped data directory not found: {SCRAPED_DATA_DIR}")
    exit(1)

json_files = list(scraped_dir.rglob("*.json"))
total_files = len(json_files)

print(f"Found {total_files} JSON files to process")
print()

# Process files in batches
BATCH_SIZE = 50
uploaded = 0
failed = 0
skipped = 0

def format_document(data: Dict, file_path: Path) -> str:
    """Convert JSON data to readable text format."""
    lines = []

    # Add title
    title = data.get("title", "Unknown")
    lines.append(f"Title: {title}")
    lines.append("")

    # Add URL
    if "url" in data:
        lines.append(f"URL: {data['url']}")
        lines.append("")

    # Add category from metadata
    if "metadata" in data and "category" in data["metadata"]:
        category = data["metadata"]["category"]
        lines.append(f"Category: {category.title()}")
        lines.append("")

    # Add content
    if "content" in data and data["content"]:
        content = data["content"]
        # Clean up the content (remove excessive whitespace)
        content = " ".join(content.split())
        lines.append(content)

    return "\n".join(lines)

# Process files
batch_docs = []
batch_ids = []
batch_metadatas = []

for i, file_path in enumerate(json_files, 1):
    relative_path = file_path.relative_to(scraped_dir)

    if i % 10 == 0:
        print(f"Processing [{i}/{total_files}] {relative_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Skip files without content
        if not data.get("content"):
            skipped += 1
            continue

        # Format document
        doc_text = format_document(data, file_path)

        # Generate document ID from file path
        doc_id = str(relative_path).replace("/", "_").replace(".json", "")

        # Prepare metadata
        metadata = {
            "source": data.get("url", str(relative_path)),
            "title": data.get("title", "Unknown"),
            "category": data.get("metadata", {}).get("category", "unknown"),
            "file_path": str(relative_path)
        }

        # Add to batch
        batch_docs.append(doc_text)
        batch_ids.append(doc_id)
        batch_metadatas.append(metadata)

        # Process batch when full or last file
        if len(batch_docs) >= BATCH_SIZE or i == total_files:
            try:
                collection.add(
                    documents=batch_docs,
                    ids=batch_ids,
                    metadatas=batch_metadatas
                )
                uploaded += len(batch_docs)
                print(f"  ✓ Uploaded batch of {len(batch_docs)} documents (total: {uploaded})")

                # Clear batch
                batch_docs = []
                batch_ids = []
                batch_metadatas = []

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"  ✗ Failed to upload batch: {e}")
                failed += len(batch_docs)
                batch_docs = []
                batch_ids = []
                batch_metadatas = []

    except Exception as e:
        failed += 1
        print(f"  ✗ Error processing {relative_path}: {e}")

# Summary
print()
print("=" * 60)
print("Upload Complete!")
print("=" * 60)
print(f"Total files:      {total_files}")
print(f"Uploaded:         {uploaded}")
print(f"Skipped (empty):  {skipped}")
print(f"Failed:           {failed}")
print()

# Verify final count
final_count = collection.count()
print(f"ChromaDB collection '{COLLECTION_NAME}' now has {final_count} documents")
print()
