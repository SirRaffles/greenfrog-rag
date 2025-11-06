#!/usr/bin/env python3
"""
Load Matcha Initiative Documents into ChromaDB with Ollama Embeddings
Uses nomic-embed-text:latest for 768-dimensional embeddings
"""

import os
import json
import time
import httpx
from pathlib import Path
from typing import List, Dict
import chromadb
import asyncio

# Configuration
CHROMADB_URL = "http://chromadb:8000"
COLLECTION_NAME = "greenfrog"
SCRAPED_DATA_DIR = "/app/data/scraped/Matchainitiative"
OLLAMA_URL = "http://host.docker.internal:11434"
EMBEDDING_MODEL = "nomic-embed-text:latest"

print("=" * 60)
print("GreenFrog ChromaDB Document Loader with Ollama Embeddings")
print("=" * 60)
print()

# Connect to ChromaDB
print(f"Connecting to ChromaDB at {CHROMADB_URL}...")
try:
    client = chromadb.HttpClient(
        host=CHROMADB_URL.replace("http://", "").split(":")[0],
        port=int(CHROMADB_URL.split(":")[-1])
    )
    client.heartbeat()
    print("✓ Connected to ChromaDB")
except Exception as e:
    print(f"✗ Failed to connect to ChromaDB: {e}")
    exit(1)

print()

# Get or create collection
print(f"Getting/creating collection '{COLLECTION_NAME}'...")
try:
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "GreenFrog sustainability knowledge base (768-dim embeddings)"}
    )
    print(f"✓ Collection ready")
    existing_count = collection.count()
    print(f"  Current document count: {existing_count}")
except Exception as e:
    print(f"✗ Failed to get/create collection: {e}")
    exit(1)

print()

# Test Ollama connection
print(f"Testing Ollama connection at {OLLAMA_URL}...")
async def test_ollama():
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        try:
            response = await http_client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": "test"}
            )
            data = response.json()
            embedding = data.get("embedding", [])
            print(f"✓ Ollama connected - embedding dimensions: {len(embedding)}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Ollama: {e}")
            return False

if not asyncio.run(test_ollama()):
    exit(1)

print()

# Find all JSON files
scraped_dir = Path(SCRAPED_DATA_DIR)
if not scraped_dir.exists():
    print(f"✗ Scraped data directory not found: {SCRAPED_DATA_DIR}")
    exit(1)

json_files = list(scraped_dir.rglob("*.json"))
# Filter out Mac OS metadata files
json_files = [f for f in json_files if not f.name.startswith("._")]
total_files = len(json_files)

print(f"Found {total_files} JSON files to process")
print()

# Process files in batches
BATCH_SIZE = 10  # Smaller batches due to embedding generation
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

async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using Ollama."""
    embeddings = []
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        for i, text in enumerate(texts):
            try:
                response = await http_client.post(
                    f"{OLLAMA_URL}/api/embeddings",
                    json={"model": EMBEDDING_MODEL, "prompt": text}
                )
                data = response.json()
                embedding = data.get("embedding", [])
                embeddings.append(embedding)

                if (i + 1) % 5 == 0:
                    print(f"    Generated {i + 1}/{len(texts)} embeddings...")
            except Exception as e:
                print(f"    ✗ Failed to generate embedding for text {i + 1}: {e}")
                embeddings.append([])  # Empty embedding as placeholder

    return embeddings

# Process files
batch_docs = []
batch_ids = []
batch_metadatas = []

async def process_batches():
    global uploaded, failed, skipped, batch_docs, batch_ids, batch_metadatas

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
                    print(f"  → Generating embeddings for batch of {len(batch_docs)} documents...")

                    # Generate embeddings
                    embeddings = await generate_embeddings(batch_docs)

                    # Filter out empty embeddings
                    valid_docs = []
                    valid_ids = []
                    valid_metadatas = []
                    valid_embeddings = []

                    for j, emb in enumerate(embeddings):
                        if emb and len(emb) > 0:
                            valid_docs.append(batch_docs[j])
                            valid_ids.append(batch_ids[j])
                            valid_metadatas.append(batch_metadatas[j])
                            valid_embeddings.append(emb)
                        else:
                            failed += 1

                    if valid_docs:
                        # Upload to ChromaDB
                        collection.add(
                            documents=valid_docs,
                            ids=valid_ids,
                            metadatas=valid_metadatas,
                            embeddings=valid_embeddings
                        )
                        uploaded += len(valid_docs)
                        print(f"  ✓ Uploaded batch of {len(valid_docs)} documents (total: {uploaded})")

                    # Clear batch
                    batch_docs = []
                    batch_ids = []
                    batch_metadatas = []

                    # Rate limiting
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"  ✗ Failed to upload batch: {e}")
                    failed += len(batch_docs)
                    batch_docs = []
                    batch_ids = []
                    batch_metadatas = []

        except Exception as e:
            failed += 1
            print(f"  ✗ Error processing {relative_path}: {e}")

# Run async processing
asyncio.run(process_batches())

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
