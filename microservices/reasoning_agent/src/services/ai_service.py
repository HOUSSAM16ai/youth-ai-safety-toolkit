import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from microservices.reasoning_agent.src.core.config import settings
from microservices.reasoning_agent.src.core.logging import get_logger

logger = get_logger("ai-service")

class AIService:
    def __init__(self):
        # Configure client (OpenRouter or OpenAI)
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        base_url = "https://openrouter.ai/api/v1" if settings.OPENROUTER_API_KEY else None

        if not api_key:
            logger.warning("No API Key provided. AI Service will fail on generation.")
            self.client = None
        else:
            self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

        self.model = settings.DEFAULT_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_text(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        """
        Generates text using the configured LLM with retries.
        """
        if not self.client:
            # For development/testing without keys, return a mock response or fail gracefully
            if settings.ENVIRONMENT == "development":
                logger.warning("Returning mock response due to missing API Key.")
                return "Mock response: AI Client not initialized."
            raise ValueError("AI Client is not initialized (Missing API Key).")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"AI Generation failed: {e}")
            raise

ai_service = AIService()
