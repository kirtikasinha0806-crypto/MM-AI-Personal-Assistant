import os
import requests
from typing import Dict, Any, Optional, List

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class APIClient:
    """HTTP client wrapper communicating with the FastAPI backend."""

    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url.rstrip("/")

    def get_health(self) -> Dict[str, Any]:
        try:
            res = requests.get(f"{self.base_url}/health", timeout=5)
            if res.status_code == 200:
                return res.json()
            return {"status": "error", "detail": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"status": "unreachable", "detail": str(e)}

    # Conversations & Chat
    def list_conversations(self) -> List[Dict[str, Any]]:
        try:
            res = requests.get(f"{self.base_url}/api/conversations", timeout=10)
            if res.status_code == 200:
                return res.json()
            return []
        except Exception:
            return []

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        try:
            res = requests.get(f"{self.base_url}/api/conversations/{conversation_id}", timeout=10)
            if res.status_code == 200:
                return res.json()
            return None
        except Exception:
            return None

    def delete_conversation(self, conversation_id: str) -> bool:
        try:
            res = requests.delete(f"{self.base_url}/api/conversations/{conversation_id}", timeout=10)
            return res.status_code == 200
        except Exception:
            return False

    def send_chat_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        mode: str = "standard",
        enable_web_search: bool = False,
        document_id: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        data = {
            "message": message,
            "mode": mode,
            "enable_web_search": "true" if enable_web_search else "false",
        }
        if conversation_id:
            data["conversation_id"] = conversation_id
        if document_id:
            data["document_id"] = document_id

        files = None
        if file_bytes and filename:
            files = {
                "file": (filename, file_bytes, mime_type or "application/octet-stream")
            }

        try:
            res = requests.post(url, data=data, files=files, timeout=60)
            if res.status_code == 200:
                return res.json()
            else:
                return {
                    "error": True,
                    "response": f"⚠️ Server Error (HTTP {res.status_code}): {res.text}",
                    "sources": [],
                }
        except Exception as e:
            return {
                "error": True,
                "response": f"🔌 Connection Failure: Could not reach backend API at {self.base_url}. {e}",
                "sources": [],
            }

    # Document Workspace
    def list_documents(self) -> List[Dict[str, Any]]:
        try:
            res = requests.get(f"{self.base_url}/api/documents", timeout=10)
            if res.status_code == 200:
                return res.json()
            return []
        except Exception:
            return []

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        try:
            res = requests.get(f"{self.base_url}/api/documents/{document_id}", timeout=10)
            if res.status_code == 200:
                return res.json()
            return None
        except Exception:
            return None

    def upload_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/documents/upload"
        files = {"file": (filename, file_bytes)}
        try:
            res = requests.post(url, files=files, timeout=40)
            if res.status_code == 200:
                return res.json()
            return {"error": True, "detail": res.text}
        except Exception as e:
            return {"error": True, "detail": str(e)}

    def create_document(self, title: str, prompt: str, file_type: str = "md") -> Dict[str, Any]:
        url = f"{self.base_url}/api/documents/create"
        payload = {"title": title, "prompt": prompt, "file_type": file_type}
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json()
            return {"error": True, "detail": res.text}
        except Exception as e:
            return {"error": True, "detail": str(e)}

    def update_document(
        self,
        document_id: str,
        instructions: Optional[str] = None,
        direct_content: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/documents/{document_id}"
        payload = {}
        if instructions:
            payload["instructions"] = instructions
        if direct_content is not None:
            payload["direct_content"] = direct_content

        try:
            res = requests.patch(url, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json()
            return {"error": True, "detail": res.text}
        except Exception as e:
            return {"error": True, "detail": str(e)}

    def delete_document(self, document_id: str) -> bool:
        try:
            res = requests.delete(f"{self.base_url}/api/documents/{document_id}", timeout=10)
            return res.status_code == 200
        except Exception:
            return False

    def query_document(self, document_id: str, query: str, top_k: int = 3) -> Dict[str, Any]:
        url = f"{self.base_url}/api/documents/{document_id}/query"
        payload = {"query": query, "top_k": top_k}
        try:
            res = requests.post(url, json=payload, timeout=45)
            if res.status_code == 200:
                return res.json()
            return {"error": True, "answer": res.text, "citations": []}
        except Exception as e:
            return {"error": True, "answer": str(e), "citations": []}

    def reindex_document(self, document_id: str) -> Dict[str, Any]:
        try:
            res = requests.post(f"{self.base_url}/api/documents/{document_id}/reindex", timeout=40)
            if res.status_code == 200:
                return res.json()
            return {"error": True, "detail": res.text}
        except Exception as e:
            return {"error": True, "detail": str(e)}


api_client = APIClient()

