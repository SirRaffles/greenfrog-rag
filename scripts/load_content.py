#!/usr/bin/env python3
"""
Load Matcha Initiative Content into AnythingLLM
Uploads all scraped JSON files to the GreenFrog workspace
"""

import os
import json
import requests
import time
from pathlib import Path
from typing import List, Dict

# Configuration
ANYTHINGLLM_URL = "http://192.168.50.171:3001"
WORKSPACE_SLUG = "greenfrog"
SCRAPED_DATA_DIR = "/volume1/docker/greenfrog-rag/data/scraped/Matchainitiative"

# API endpoints
API_BASE = f"{ANYTHINGLLM_URL}/api/v1"

def check_anythingllm_health() -> bool:
    """Check if AnythingLLM is accessible"""
    try:
        response = requests.get(f"{ANYTHINGLLM_URL}/api/ping", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_workspaces() -> List[Dict]:
    """Get list of workspaces"""
    try:
        response = requests.get(f"{API_BASE}/workspaces")
        if response.status_code == 200:
            return response.json().get("workspaces", [])
    except Exception as e:
        print(f"Error getting workspaces: {e}")
    return []

def create_workspace(name: str, slug: str) -> Dict:
    """Create a new workspace"""
    try:
        response = requests.post(
            f"{API_BASE}/workspace/new",
            json={"name": name, "slug": slug}
        )
        if response.status_code == 200:
            return response.json().get("workspace", {})
        else:
            print(f"Error creating workspace: {response.text}")
    except Exception as e:
        print(f"Error creating workspace: {e}")
    return {}

def upload_document(workspace_slug: str, file_path: Path, content: str) -> bool:
    """Upload a document to workspace"""
    try:
        # Convert JSON to text format for better indexing
        data = json.loads(content)

        # Create readable text from JSON
        text_content = format_json_as_text(data, file_path)

        # Upload as text file
        files = {
            'file': (f"{file_path.stem}.txt", text_content.encode('utf-8'), 'text/plain')
        }

        response = requests.post(
            f"{API_BASE}/workspace/{workspace_slug}/upload",
            files=files,
            timeout=30
        )

        return response.status_code == 200
    except Exception as e:
        print(f"  ✗ Error uploading {file_path.name}: {e}")
        return False

def format_json_as_text(data: Dict, file_path: Path) -> str:
    """Convert JSON data to readable text format"""
    lines = []

    # Determine type from file path
    if "suppliers" in str(file_path):
        doc_type = "Supplier"
    elif "solutions" in str(file_path):
        doc_type = "Solution"
    elif "buddies" in str(file_path):
        doc_type = "Buddy"
    elif "resources" in str(file_path):
        doc_type = "Resource"
    else:
        doc_type = "Document"

    lines.append(f"=== {doc_type}: {data.get('name', data.get('title', 'Unknown'))} ===\n")

    # Add all fields as text
    for key, value in data.items():
        if isinstance(value, list):
            if value and isinstance(value[0], str):
                lines.append(f"{key.title()}: {', '.join(value)}")
            else:
                lines.append(f"{key.title()}:")
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            lines.append(f"  - {k}: {v}")
                    else:
                        lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"{key.title()}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{key.title()}: {value}")

    return "\n".join(lines)

def load_all_documents():
    """Load all scraped documents into AnythingLLM"""
    print("🐸 GreenFrog Content Loader")
    print("=" * 50)
    print()

    # Check AnythingLLM
    print("Checking AnythingLLM...")
    if not check_anythingllm_health():
        print("✗ AnythingLLM is not accessible at", ANYTHINGLLM_URL)
        print("  Make sure the service is running: docker compose up -d anythingllm")
        return
    print("✓ AnythingLLM is accessible")
    print()

    # Check/create workspace
    print(f"Checking workspace '{WORKSPACE_SLUG}'...")
    workspaces = get_workspaces()
    workspace_exists = any(w.get("slug") == WORKSPACE_SLUG for w in workspaces)

    if not workspace_exists:
        print(f"  Creating workspace '{WORKSPACE_SLUG}'...")
        workspace = create_workspace("GreenFrog Sustainability", WORKSPACE_SLUG)
        if workspace:
            print(f"  ✓ Workspace created")
        else:
            print(f"  ✗ Failed to create workspace")
            return
    else:
        print(f"  ✓ Workspace exists")
    print()

    # Find all JSON files
    scraped_dir = Path(SCRAPED_DATA_DIR)
    if not scraped_dir.exists():
        print(f"✗ Scraped data directory not found: {SCRAPED_DATA_DIR}")
        return

    json_files = list(scraped_dir.rglob("*.json"))
    total_files = len(json_files)

    print(f"Found {total_files} files to upload")
    print()

    # Upload files
    uploaded = 0
    failed = 0

    for i, file_path in enumerate(json_files, 1):
        relative_path = file_path.relative_to(scraped_dir)
        print(f"[{i}/{total_files}] Uploading {relative_path}...")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if upload_document(WORKSPACE_SLUG, file_path, content):
                uploaded += 1
                print(f"  ✓ Uploaded successfully")
            else:
                failed += 1
                print(f"  ✗ Upload failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ Error: {e}")

        # Rate limiting
        if i % 10 == 0:
            print(f"  ... pausing for 2 seconds ...")
            time.sleep(2)

    # Summary
    print()
    print("=" * 50)
    print(f"Upload complete!")
    print(f"  Total files: {total_files}")
    print(f"  Uploaded: {uploaded}")
    print(f"  Failed: {failed}")
    print()
    print(f"Access workspace at: {ANYTHINGLLM_URL}/workspace/{WORKSPACE_SLUG}")

if __name__ == "__main__":
    load_all_documents()
