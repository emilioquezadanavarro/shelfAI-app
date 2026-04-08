import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import base64
from app.database.database_schema import AIEvaluation

# Load environment variables
load_dotenv()

# Helper function. It translates the image into a giant string of text characters.
def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


class EvaluationAgent:
    """
    Multimodal Vision Agent responsible for evaluating shelf photos against deterministic text rules.

    """
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0):
        # Defensively retrieve and validate the OpenAI API Key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("🚨 Missing OpenAI API Key in .env file!")
            
        # Initialize the LangChain Chat model
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )
        
        # Bind the Pydantic schema to the LLM so it forces rigid JSON output
        self.structured_llm = self.llm.with_structured_output(AIEvaluation)

    async def analyze_shelf_image(self, base64_image: str, campaign_rules: str):
        """
        Takes a base64 encoded image and a text block of rules, constructs the prompt, 
        and invokes the Vision Model.

        """
        # Build the Multimodal Prompt
        messages = [
            (
                "system",
                f"You are an expert retail merchandising auditor.\n"
                f"Your job is to evaluate shelf photos strictly against these Campaign Rules:\n\n{campaign_rules}\n\n"
                "Analyze the image meticulously. For every rule, determine if it is compliant or not. "
                "Calculate the final ai_score from 0.0 to 100.0 based on the results."
            ),
            (
                "human",
                [
                    {"type": "text", "text": "Evaluate this shelf photo."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            )
        ]

        # LangChain Execution
        try:
            # ainvoke() sends the image to OpenAI asynchronously so your server doesn't freeze
            ai_response = await self.structured_llm.ainvoke(messages)
            return ai_response
        except Exception as e:
            print(f"🚨 [AI Error] Failed to analyze image: {str(e)}")
            raise e