"""
Frontend API Integration Utilities

Provides functions for the frontend to communicate with the chatbot backend API.
All chatbot logic remains unchanged - this is just the communication layer.
"""

import httpx
import asyncio
from typing import Optional, Dict, Any

# API base URL (change if backend runs on different host/port)
API_BASE_URL = "http://localhost:8001"
TIMEOUT = 30.0

class ChatbotAPIClient:
    """Client for communicating with Pet AI Healthcare Chatbot API"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
    
    async def start_conversation(self, animal: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new conversation with the chatbot.
        
        Args:
            animal: 'dog' or 'cat'
            user_id: Optional user identifier
        
        Returns:
            {
                "session_id": str,
                "animal": str,
                "message": str  # Initial greeting
            }
        """
        response = await self.client.post(
            f"{self.base_url}/api/chat/start",
            json={
                "animal": animal,
                "user_id": user_id
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Send a message in an ongoing conversation.
        
        Args:
            session_id: Session ID from start_conversation
            message: User message (can include image path)
        
        Returns:
            {
                "session_id": str,
                "bot_response": str,
                "used_rag": bool,  # Whether RAG was used
                "disease_detected": str | None  # 'skin', 'eye', or None
            }
        """
        response = await self.client.post(
            f"{self.base_url}/api/chat/message",
            json={
                "session_id": session_id,
                "message": message
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def upload_image(
        self,
        session_id: str,
        disease_type: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Upload and analyze a pet image.
        
        Args:
            session_id: Session ID
            disease_type: 'skin' or 'eye'
            file_path: Path to image file
        
        Returns:
            {
                "session_id": str,
                "disease_class": str,
                "confidence": float,
                "explanation": str  # Detailed explanation from agentic RAG
            }
        """
        with open(file_path, "rb") as f:
            response = await self.client.post(
                f"{self.base_url}/api/chat/upload-image",
                data={
                    "session_id": session_id,
                    "disease_type": disease_type
                },
                files={"file": f}
            )
        response.raise_for_status()
        return response.json()
    
    async def get_chat_history(self, session_id: str) -> Dict[str, Any]:
        """
        Get conversation history.
        
        Args:
            session_id: Session ID
        
        Returns:
            {
                "session_id": str,
                "animal": str,
                "chat_history": str  # Formatted conversation history
            }
        """
        response = await self.client.get(
            f"{self.base_url}/api/chat/history/{session_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """
        End a conversation session.
        
        Args:
            session_id: Session ID
        
        Returns:
            {
                "session_id": str,
                "message": str
            }
        """
        response = await self.client.delete(
            f"{self.base_url}/api/chat/session/{session_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check API health.
        
        Returns:
            {
                "status": str,
                "service": str,
                "active_sessions": int
            }
        """
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client connection"""
        await self.client.aclose()


# Synchronous wrapper for ease of use in non-async contexts
class SyncChatbotAPIClient:
    """Synchronous wrapper around async client"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def start_conversation(self, animal: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Start conversation (sync)"""
        async def _run():
            client = ChatbotAPIClient(self.base_url)
            try:
                return await client.start_conversation(animal, user_id)
            finally:
                await client.close()
        return asyncio.run(_run())
    
    def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Send message (sync)"""
        async def _run():
            client = ChatbotAPIClient(self.base_url)
            try:
                return await client.send_message(session_id, message)
            finally:
                await client.close()
        return asyncio.run(_run())
    
    def upload_image(
        self,
        session_id: str,
        disease_type: str,
        file_path: str
    ) -> Dict[str, Any]:
        """Upload image (sync)"""
        async def _run():
            client = ChatbotAPIClient(self.base_url)
            try:
                return await client.upload_image(session_id, disease_type, file_path)
            finally:
                await client.close()
        return asyncio.run(_run())
    
    def get_chat_history(self, session_id: str) -> Dict[str, Any]:
        """Get chat history (sync)"""
        async def _run():
            client = ChatbotAPIClient(self.base_url)
            try:
                return await client.get_chat_history(session_id)
            finally:
                await client.close()
        return asyncio.run(_run())
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End session (sync)"""
        async def _run():
            client = ChatbotAPIClient(self.base_url)
            try:
                return await client.end_session(session_id)
            finally:
                await client.close()
        return asyncio.run(_run())
    
    def health_check(self) -> Dict[str, Any]:
        """Health check (sync)"""
        async def _run():
            client = ChatbotAPIClient(self.base_url)
            try:
                return await client.health_check()
            finally:
                await client.close()
        return asyncio.run(_run())


# Export both clients
__all__ = ["ChatbotAPIClient", "SyncChatbotAPIClient"]
