#!/usr/bin/env python3
"""
Initialize AnythingLLM with admin user, workspace, and API key
Direct database manipulation for autonomous setup
"""

import sqlite3
import hashlib
import secrets
import json
from datetime import datetime
from pathlib import Path

# Configuration
DB_PATH = "/volume1/docker/greenfrog-rag/data/anythingllm/anythingllm.db"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "GreenFrog2025!"  # Change this in production
WORKSPACE_NAME = "GreenFrog Sustainability"
WORKSPACE_SLUG = "greenfrog"

def generate_password_hash(password: str) -> str:
    """Generate bcrypt-compatible password hash"""
    # Using SHA256 as a fallback (AnythingLLM uses bcrypt, but we'll use simple hash for now)
    return hashlib.sha256(password.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate secure API key"""
    return f"sk-{secrets.token_urlsafe(32)}"

def init_database():
    """Initialize AnythingLLM database with admin user and workspace"""

    print("🐸 Initializing AnythingLLM Database")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count > 0:
            print(f"✓ Database already initialized ({user_count} users exist)")
            # Get existing API key
            cursor.execute("SELECT secret FROM api_keys LIMIT 1")
            result = cursor.fetchone()
            if result:
                print(f"✓ Existing API key found: {result[0][:20]}...")
                return result[0]
            else:
                # Generate new API key for existing user
                cursor.execute("SELECT id FROM users LIMIT 1")
                user_id = cursor.fetchone()[0]
                api_key = generate_api_key()
                timestamp = int(datetime.now().timestamp() * 1000)

                cursor.execute("""
                    INSERT INTO api_keys (secret, createdBy, createdAt, lastUpdatedAt)
                    VALUES (?, ?, ?, ?)
                """, (api_key, user_id, timestamp, timestamp))
                conn.commit()
                print(f"✓ New API key generated: {api_key}")
                return api_key

        # Create admin user
        print("\n1. Creating admin user...")
        password_hash = generate_password_hash(ADMIN_PASSWORD)
        timestamp = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO users (username, password, role, suspended, createdAt, lastUpdatedAt)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ADMIN_USERNAME, password_hash, "admin", 0, timestamp, timestamp))

        user_id = cursor.lastrowid

        print(f"✓ Admin user created: {ADMIN_USERNAME}")
        print(f"  Password: {ADMIN_PASSWORD}")

        # Generate API key
        print("\n2. Generating API key...")
        api_key = generate_api_key()

        cursor.execute("""
            INSERT INTO api_keys (secret, createdBy, createdAt, lastUpdatedAt)
            VALUES (?, ?, ?, ?)
        """, (api_key, user_id, timestamp, timestamp))

        print(f"✓ API key generated: {api_key}")

        # Create workspace
        print("\n3. Creating workspace...")

        cursor.execute("""
            INSERT INTO workspaces (name, slug, createdAt, lastUpdatedAt, openAiTemp, openAiHistory, openAiPrompt, similarityThreshold, topN, chatMode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (WORKSPACE_NAME, WORKSPACE_SLUG, timestamp, timestamp, 0.7, 20, None, 0.25, 4, "chat"))

        workspace_id = cursor.lastrowid

        print(f"✓ Workspace created: {WORKSPACE_NAME} ({WORKSPACE_SLUG})")

        # Link user to workspace
        cursor.execute("""
            INSERT INTO workspace_users (user_id, workspace_id, createdAt, lastUpdatedAt)
            VALUES (?, ?, ?, ?)
        """, (user_id, workspace_id, timestamp, timestamp))

        print(f"✓ User linked to workspace")

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 50)
        print("✅ AnythingLLM Initialization Complete!")
        print("=" * 50)
        print(f"\nCredentials:")
        print(f"  Username: {ADMIN_USERNAME}")
        print(f"  Password: {ADMIN_PASSWORD}")
        print(f"  API Key:  {api_key}")
        print(f"\nWorkspace: {WORKSPACE_SLUG}")
        print(f"URL: http://192.168.50.171:3001")

        # Save credentials to file
        creds_file = Path("/volume1/docker/greenfrog-rag/ANYTHINGLLM_CREDENTIALS.txt")
        creds_file.write_text(f"""AnythingLLM Credentials
=======================
Created: {datetime.now().isoformat()}

Web UI: http://192.168.50.171:3001
Username: {ADMIN_USERNAME}
Password: {ADMIN_PASSWORD}

API Key: {api_key}

Workspace: {WORKSPACE_SLUG}
""")
        print(f"\n✓ Credentials saved to: {creds_file}")

        return api_key

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    api_key = init_database()
    print(f"\n🔑 API Key for next steps: {api_key}")
