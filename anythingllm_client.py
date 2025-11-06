#!/usr/bin/env python3
"""
AnythingLLM Document Upload & Embedding Client

A Python client for the AnythingLLM API that handles the complete
document workflow: upload → embed.

Usage:
    from anythingllm_client import AnythingLLMClient

    client = AnythingLLMClient(
        base_url="http://localhost:3001",
        api_key="sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA"
    )

    # Upload and embed a document
    client.upload_and_embed(
        file_path="/path/to/document.pdf",
        workspace_slug="greenfrog"
    )

    # Or do it step by step
    doc_location = client.upload_document("/path/to/document.pdf")
    result = client.embed_in_workspace("greenfrog", [doc_location])
"""

import requests
import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


@dataclass
class UploadResult:
    """Result of document upload"""
    success: bool
    document_id: Optional[str] = None
    location: Optional[str] = None
    name: Optional[str] = None
    message: str = ""
    raw_response: Dict[str, Any] = None


@dataclass
class EmbedResult:
    """Result of document embedding"""
    success: bool
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    documents: List[Dict[str, Any]] = None
    message: str = ""
    raw_response: Dict[str, Any] = None


class AnythingLLMClient:
    """Client for AnythingLLM API"""

    def __init__(
        self,
        base_url: str = "http://localhost:3001",
        api_key: str = "",
        log_level: LogLevel = LogLevel.INFO,
        timeout: int = 30
    ):
        """
        Initialize AnythingLLM client

        Args:
            base_url: Base URL of AnythingLLM instance (without trailing slash)
            api_key: API authentication key
            log_level: Logging verbosity level
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.log_level = log_level
        self.timeout = timeout

        self.headers = {
            "Authorization": f"Bearer {api_key}"
        }

        # Verify connectivity
        self._log(LogLevel.INFO, f"Initializing AnythingLLM client: {self.base_url}")

    def _log(self, level: LogLevel, message: str):
        """Log message based on log level"""
        if level.value >= self.log_level.value:
            prefix = {
                LogLevel.DEBUG: "[DEBUG]",
                LogLevel.INFO: "[INFO]",
                LogLevel.WARNING: "[WARNING]",
                LogLevel.ERROR: "[ERROR]"
            }[level]
            print(f"{prefix} {message}", file=sys.stderr if level == LogLevel.ERROR else sys.stdout)

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> tuple[int, Dict[str, Any]]:
        """
        Make HTTP request to AnythingLLM API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            json_data: JSON payload
            files: Files for multipart upload
            timeout: Request timeout

        Returns:
            Tuple of (status_code, response_json)
        """
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.timeout

        self._log(LogLevel.DEBUG, f"{method} {endpoint}")

        try:
            if method.upper() == "POST":
                if files:
                    # Don't include Content-Type header for multipart (requests handles it)
                    response = requests.post(
                        url,
                        headers=self.headers,
                        files=files,
                        timeout=timeout
                    )
                else:
                    headers = {**self.headers, "Content-Type": "application/json"}
                    response = requests.post(
                        url,
                        headers=headers,
                        json=json_data,
                        timeout=timeout
                    )
            elif method.upper() == "GET":
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            self._log(LogLevel.DEBUG, f"Response status: {response.status_code}")

            try:
                response_json = response.json()
            except:
                response_json = {"raw_text": response.text}

            return response.status_code, response_json

        except requests.exceptions.Timeout:
            self._log(LogLevel.ERROR, f"Request timeout ({timeout}s)")
            raise
        except requests.exceptions.RequestException as e:
            self._log(LogLevel.ERROR, f"Request failed: {str(e)}")
            raise

    def upload_document(self, file_path: str) -> str:
        """
        Upload document to AnythingLLM storage

        This is Step 1 of the workflow. The document is converted to text
        and stored in custom-documents/ folder.

        Args:
            file_path: Path to document file to upload

        Returns:
            Document location (e.g., "custom-documents/filename.txt")

        Raises:
            FileNotFoundError: If file doesn't exist
            requests.RequestException: If API request fails
            RuntimeError: If upload fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self._log(LogLevel.INFO, f"Uploading document: {file_path.name}")

        with open(file_path, 'rb') as f:
            files = {'file': f}

            status_code, response = self._request(
                "POST",
                "/api/v1/document/upload",
                files=files
            )

        self._log(LogLevel.DEBUG, f"Upload response: {json.dumps(response, indent=2)}")

        if status_code not in (200, 201):
            raise RuntimeError(
                f"Upload failed with status {status_code}: {response}"
            )

        # Extract document location from response
        if 'document' in response and 'location' in response['document']:
            location = response['document']['location']
            self._log(LogLevel.INFO, f"Document uploaded: {location}")
            return location
        else:
            raise RuntimeError(
                f"Unexpected response format: {response}"
            )

    def embed_in_workspace(
        self,
        workspace_slug: str,
        document_paths: List[str]
    ) -> EmbedResult:
        """
        Embed documents in workspace

        This is Step 2 of the workflow. Documents are chunked and vectors
        are created and stored in the vector database.

        Args:
            workspace_slug: Workspace slug/identifier (e.g., "greenfrog")
            document_paths: List of document paths (e.g., ["custom-documents/file.txt"])

        Returns:
            EmbedResult object with embedding status

        Raises:
            requests.RequestException: If API request fails
        """
        self._log(
            LogLevel.INFO,
            f"Embedding {len(document_paths)} document(s) in workspace: {workspace_slug}"
        )

        payload = {"adds": document_paths}

        status_code, response = self._request(
            "POST",
            f"/api/v1/workspace/{workspace_slug}/update-embeddings",
            json_data=payload
        )

        self._log(LogLevel.DEBUG, f"Embed response: {json.dumps(response, indent=2)}")

        # Parse response
        result = EmbedResult(
            success=status_code in (200, 201),
            raw_response=response
        )

        if result.success:
            if 'workspace' in response:
                workspace = response['workspace']
                result.workspace_id = workspace.get('id')
                result.workspace_name = workspace.get('name')
                result.documents = workspace.get('documents', [])

            result.message = response.get('message', 'Embedded successfully')
            self._log(LogLevel.INFO, result.message)
        else:
            result.message = response.get(
                'message',
                f"Embedding failed with status {status_code}"
            )
            self._log(LogLevel.ERROR, result.message)

        return result

    def upload_and_embed(
        self,
        file_path: str,
        workspace_slug: str,
        wait_before_embed: float = 1.0
    ) -> tuple[UploadResult, EmbedResult]:
        """
        Complete workflow: Upload and embed document

        Args:
            file_path: Path to document to upload
            workspace_slug: Workspace to embed document in
            wait_before_embed: Seconds to wait between upload and embed

        Returns:
            Tuple of (UploadResult, EmbedResult)
        """
        self._log(
            LogLevel.INFO,
            f"Starting upload and embed workflow for: {Path(file_path).name}"
        )

        # Step 1: Upload
        try:
            doc_location = self.upload_document(file_path)
            upload_result = UploadResult(
                success=True,
                location=doc_location,
                name=Path(file_path).name
            )
        except Exception as e:
            self._log(LogLevel.ERROR, f"Upload failed: {str(e)}")
            return (
                UploadResult(success=False, message=str(e)),
                EmbedResult(success=False, message="Upload failed")
            )

        # Wait for file processing
        if wait_before_embed > 0:
            self._log(
                LogLevel.INFO,
                f"Waiting {wait_before_embed}s for file processing..."
            )
            time.sleep(wait_before_embed)

        # Step 2: Embed
        try:
            embed_result = self.embed_in_workspace(
                workspace_slug,
                [doc_location]
            )
        except Exception as e:
            self._log(LogLevel.ERROR, f"Embedding failed: {str(e)}")
            embed_result = EmbedResult(
                success=False,
                message=str(e)
            )

        return upload_result, embed_result

    def upload_multiple(
        self,
        file_paths: List[str],
        workspace_slug: str,
        wait_before_embed: float = 2.0
    ) -> EmbedResult:
        """
        Upload and embed multiple documents

        Args:
            file_paths: List of file paths to upload
            workspace_slug: Workspace to embed documents in
            wait_before_embed: Seconds to wait before embedding all

        Returns:
            EmbedResult from embedding all documents
        """
        self._log(
            LogLevel.INFO,
            f"Uploading {len(file_paths)} document(s)..."
        )

        doc_locations = []

        for file_path in file_paths:
            try:
                location = self.upload_document(file_path)
                doc_locations.append(location)
            except Exception as e:
                self._log(
                    LogLevel.WARNING,
                    f"Failed to upload {file_path}: {str(e)}"
                )

        if not doc_locations:
            return EmbedResult(
                success=False,
                message="No documents uploaded successfully"
            )

        self._log(
            LogLevel.INFO,
            f"Waiting {wait_before_embed}s before embedding..."
        )
        time.sleep(wait_before_embed)

        return self.embed_in_workspace(workspace_slug, doc_locations)

    def get_workspace_info(self, workspace_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get workspace information

        Args:
            workspace_slug: Workspace slug/identifier

        Returns:
            Workspace info dict or None if failed
        """
        self._log(LogLevel.INFO, f"Fetching workspace info: {workspace_slug}")

        status_code, response = self._request(
            "GET",
            f"/api/v1/workspace/{workspace_slug}"
        )

        if status_code == 200:
            return response
        else:
            self._log(LogLevel.ERROR, f"Failed to get workspace: {response}")
            return None

    def verify_document_embedded(
        self,
        workspace_slug: str,
        document_name: str
    ) -> bool:
        """
        Verify that a document is embedded in workspace

        Args:
            workspace_slug: Workspace slug/identifier
            document_name: Document name to look for (without "custom-documents/" prefix)

        Returns:
            True if document found in workspace, False otherwise
        """
        workspace = self.get_workspace_info(workspace_slug)

        if not workspace:
            return False

        # Check if document is in workspace documents
        if 'documents' in workspace:
            for doc in workspace['documents']:
                if document_name in doc.get('name', ''):
                    return True

        # Also check by location
        doc_location = f"custom-documents/{document_name}"
        if 'documents' in workspace:
            for doc in workspace['documents']:
                if doc_location in doc.get('location', ''):
                    return True

        return False


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="AnythingLLM Document Upload & Embedding Client"
    )

    parser.add_argument(
        "action",
        choices=["upload", "embed", "upload-embed", "verify"],
        help="Action to perform"
    )

    parser.add_argument(
        "--url",
        default="http://localhost:3001",
        help="AnythingLLM base URL"
    )

    parser.add_argument(
        "--key",
        help="API key (or set ANYTHINGLLM_API_KEY env var)"
    )

    parser.add_argument(
        "--workspace",
        default="greenfrog",
        help="Workspace slug"
    )

    parser.add_argument(
        "--file",
        help="File to upload/process"
    )

    parser.add_argument(
        "--doc-path",
        help="Document path for embedding (e.g., custom-documents/file.txt)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Get API key from arg or environment
    api_key = args.key or os.environ.get("ANYTHINGLLM_API_KEY", "")

    if not api_key:
        print("ERROR: API key required (--key or ANYTHINGLLM_API_KEY env var)")
        sys.exit(1)

    # Initialize client
    log_level = LogLevel.DEBUG if args.verbose else LogLevel.INFO
    client = AnythingLLMClient(
        base_url=args.url,
        api_key=api_key,
        log_level=log_level
    )

    # Perform action
    if args.action == "upload":
        if not args.file:
            print("ERROR: --file required for upload action")
            sys.exit(1)

        try:
            location = client.upload_document(args.file)
            print(f"SUCCESS: Document uploaded to {location}")
        except Exception as e:
            print(f"ERROR: {str(e)}")
            sys.exit(1)

    elif args.action == "embed":
        if not args.doc_path:
            print("ERROR: --doc-path required for embed action")
            sys.exit(1)

        result = client.embed_in_workspace(args.workspace, [args.doc_path])
        if result.success:
            print(f"SUCCESS: {result.message}")
        else:
            print(f"ERROR: {result.message}")
            sys.exit(1)

    elif args.action == "upload-embed":
        if not args.file:
            print("ERROR: --file required for upload-embed action")
            sys.exit(1)

        upload_result, embed_result = client.upload_and_embed(
            args.file,
            args.workspace
        )

        if upload_result.success and embed_result.success:
            print(f"SUCCESS: Document uploaded and embedded")
            print(f"  Location: {upload_result.location}")
            print(f"  Workspace: {args.workspace}")
        else:
            if not upload_result.success:
                print(f"ERROR: Upload failed - {upload_result.message}")
            if not embed_result.success:
                print(f"ERROR: Embedding failed - {embed_result.message}")
            sys.exit(1)

    elif args.action == "verify":
        if not args.file:
            print("ERROR: --file required for verify action")
            sys.exit(1)

        doc_name = Path(args.file).stem  # filename without extension

        is_embedded = client.verify_document_embedded(args.workspace, doc_name)

        if is_embedded:
            print(f"SUCCESS: Document '{doc_name}' is embedded in workspace '{args.workspace}'")
        else:
            print(f"NOT FOUND: Document '{doc_name}' not found in workspace")
            sys.exit(1)


if __name__ == "__main__":
    import os
    main()
