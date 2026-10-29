import logging
from typing import List, Optional, Dict, Any
from google import genai
from google.genai import types
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service wrapper for Google Gemini API using the official google-genai SDK."""

    def __init__(self):
        self._client: Optional[genai.Client] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initializes the Gemini client if API key is present."""
        if settings.is_gemini_configured:
            try:
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info(f"Gemini client initialized with model: {settings.GEMINI_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._client = None
        else:
            self._client = None
            logger.warning("GEMINI_API_KEY is not configured. AI responses will require key configuration.")

    def is_configured(self) -> bool:
        """Returns True if Gemini client is active and configured."""
        return self._client is not None

    def get_model_name(self) -> str:
        return settings.GEMINI_MODEL

    def generate_chat_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
        context_documents: Optional[str] = None,
        web_search_context: Optional[str] = None,
        media_bytes: Optional[bytes] = None,
        media_mime_type: Optional[str] = None,
    ) -> str:
        """Generates a multimodal text response using Gemini API.

        Args:
            prompt: User's latest input text.
            conversation_history: List of {"role": "user"|"assistant", "content": str}.
            system_instruction: System prompt to guide tone, safeguards, or role.
            context_documents: Retrieved RAG context text.
            web_search_context: Retrieved web search results.
            media_bytes: Raw bytes of uploaded image or audio.
            media_mime_type: MIME type of media (e.g. 'image/png', 'audio/mp3').
        """
        if not self.is_configured():
            return (
                "⚠️ **Gemini API Key Required**\n\n"
                "The AI assistant requires a valid Google Gemini API key to generate answers.\n\n"
                "**Setup steps:**\n"
                "1. Open the `.env` file in the project root.\n"
                "2. Set `GEMINI_API_KEY=your_actual_key_here`\n"
                "3. Optionally set `GEMINI_MODEL=gemini-2.5-flash`\n"
                "4. Restart the backend service."
            )

        try:
            # Build parts for Gemini content
            contents_list = []

            # 1. Include past conversation history window (last 6 turns for context continuity)
            if conversation_history:
                recent_history = conversation_history[-6:]
                for msg in recent_history:
                    role = msg.get("role")
                    content = msg.get("content", "")
                    if role in ["user", "assistant"] and content:
                        # Format as history transcript
                        contents_list.append(f"[{role.capitalize()}]: {content}")

            # 2. Append RAG context if present
            if context_documents:
                contents_list.append(
                    f"--- RETRIEVED DOCUMENT CONTEXT ---\n"
                    f"{context_documents}\n"
                    f"--- END DOCUMENT CONTEXT ---"
                )

            # 3. Append Web Search context if present
            if web_search_context:
                contents_list.append(
                    f"--- REAL-TIME WEB SEARCH RESULTS ---\n"
                    f"{web_search_context}\n"
                    f"--- END WEB SEARCH RESULTS ---"
                )

            # 4. Include media part if uploaded
            if media_bytes and media_mime_type:
                logger.info(f"Attaching multimodal media Part: {media_mime_type} ({len(media_bytes)} bytes)")
                media_part = types.Part.from_bytes(
                    data=media_bytes,
                    mime_type=media_mime_type
                )
                contents_list.append(media_part)

            # 5. Append the current user prompt
            user_turn = f"[User]: {prompt}" if conversation_history else prompt
            contents_list.append(user_turn)

            # Configure request parameters
            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=system_instruction if system_instruction else None,
            )

            # Model fallback sequence for high reliability
            candidate_models = [settings.GEMINI_MODEL]
            for fallback in ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
                if fallback not in candidate_models:
                    candidate_models.append(fallback)

            last_error = None
            for model_id in candidate_models:
                try:
                    logger.info(f"Attempting generation with model: {model_id}")
                    response = self._client.models.generate_content(
                        model=model_id,
                        contents=contents_list,
                        config=config,
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    err_str = str(e)
                    last_error = e
                    if "503" in err_str or "UNAVAILABLE" in err_str or "404" in err_str or "NOT_FOUND" in err_str:
                        logger.warning(f"Model {model_id} returned {err_str[:80]}... Trying next fallback model.")
                        continue
                    else:
                        # For auth/key errors, re-raise immediately
                        raise e

            if last_error:
                raise last_error

            return "I received an empty response from the AI model. Please refine your prompt."

        except Exception as e:
            err_str = str(e)
            logger.error(f"Gemini API Error: {err_str}", exc_info=True)

            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "403" in err_str:
                return (
                    "❌ **Invalid Gemini API Key**: The provided API key is invalid or unauthorized. "
                    "Please check `GEMINI_API_KEY` in your `.env` file."
                )
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                return (
                    "⏳ **Quota Limit Reached**: The Gemini API rate limit or quota has been reached. "
                    "Please wait a moment before sending another request."
                )
            elif "NOT_FOUND" in err_str or "model" in err_str.lower() and "found" in err_str.lower():
                return (
                    f"⚠️ **Model Not Available**: The configured model `{settings.GEMINI_MODEL}` was not found. "
                    "Try updating `GEMINI_MODEL=gemini-2.5-flash` or `gemini-1.5-flash` in your `.env` file."
                )
            elif "connection" in err_str.lower() or "timeout" in err_str.lower():
                return (
                    "🌐 **Network Failure**: Unable to connect to Google Gemini API servers. "
                    "Please check your internet connection and proxy settings."
                )
            else:
                return f"⚠️ **AI Service Error**: An error occurred while communicating with the model: {err_str}"


# Singleton instance
llm_service = LLMService()

