import os
from langchain_openai import ChatOpenAI
import base64
from app.database.database_schema import AIEvaluation

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
                f"You are a strict, expert retail merchandising auditor.\n"
                f"Your job is to evaluate shelf photos meticulously against these Campaign Rules:\n\n{campaign_rules}\n\n"
                "CRITICAL INSTRUCTIONS FOR EVALUATION:\n"
                "1. PRICE TAGS: You MUST read the actual numbers printed on the price tags in the image. If a 'target_price' is specified in the rules, the price tag in the image must exactly match that number. If it says $1.50 but the rule requires $3.50, this is a FAILURE.\n"
                "2. FACINGS: Count the exact number of physical units facing front. Do not guess.\n"
                "3. COMPETITORS: Scan carefully for forbidden competitor brands.\n\n"
                "4. FEEDBACK FORMAT: Each feedback_text MUST be bilingual. Follow this exact format: 'EN: [english text] / ES: [spanish text]'. Example: 'EN: The focus product is present on the shelf / ES: El producto focus está presente en la estantería'. NEVER write feedback in only one language.\n\n" # Few shot prompting.
                "For every rule, determine if it is compliant or not. Be ruthlessly strict. "
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