import pymupdf
import os
from langchain_openai import ChatOpenAI
from app.database.database_schema import AIEvaluationRules


# Helper function.
def extract_text_from_pdf(pdf_name):

    # 1. Get the path to where this script lives (app/campaign_documents)
    base_dir = os.path.dirname(__file__)

    # 2. Go up one level to 'app/', then find the file in 'campaign_documents'
    pdf_path = os.path.join(base_dir, "..", "campaign_documents", pdf_name)

    # 3. Open it now with the absolute path
    doc = pymupdf.open(pdf_path)

    # Create a variable to hold all the text
    full_text_from_pdf = ""

    # Loop through every page in the PDF
    for page in doc:
        # Extract the text and add it to our variable
        full_text_from_pdf += page.get_text()

    # Now print it all to the console (Debug)
    print("\n--- PDF CONTENT START ---")
    print(full_text_from_pdf)
    print("--- PDF CONTENT END ---")

    return full_text_from_pdf


class ExtractionRulesAgent:

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
        self.structured_llm = self.llm.with_structured_output(AIEvaluationRules)


    async def create_campaign_rules(self, full_text_from_pdf):

        messages = [
            (
                "system",
                "You are a retail data analyst. Your job is to read marketing documents and extract structured campaign rules. "
                "You must identify the brand, the list of mandatory SKUs, the focus product, and all KPIs like target price and minimum facings."
            ),
            (
                "human",
                f"Here is the document: {full_text_from_pdf}",
            )
        ]

        # LangChain Execution
        try:
            # ainvoke() sends the image to OpenAI asynchronously so your server doesn't freeze
            ai_rules_response = await self.structured_llm.ainvoke(messages)

            return ai_rules_response

        except Exception as e:
            print(f"🚨 [AI Error] Failed!{str(e)}")
            raise e