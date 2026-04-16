"""
app/database/database_schema.py

This module defines the Pydantic schemas (data models) for our FastAPI application.

Pydantic is used to strictly enforce what data is allowed into our API endpoints. 
By defining these schemas, we guarantee that the frontend must provide exactly 
the data we require (in the right format) before the application even attempts 
to communicate with the Supabase database.

"""
from pydantic import BaseModel, Field

# User Profile Schema

class CreateProfile(BaseModel):
    """
    Schema for creating a new user profile / field worker.
    
    This class inherits from BaseModel, allowing FastAPI to automatically parse
    incoming JSON requests into this Python object. The Field validation ensures 
    clear documentation for OpenAPI (Swagger) and enforces data presence.

    """
    
    # 'first_name' must exactly match the column name in our Supabase `profiles` table.
    # The '...' inside Field(...) means this field is strictly required.
    first_name: str = Field(..., description="First name of the employee using the app")
    
    # 'last_name' must exactly match the column name in our Supabase `profiles` table.
    last_name: str = Field(..., description="Last name of the employee using the app")

# AI Evaluation Schemas

class AIEvaluationFeedback(BaseModel):
    """
    Schema representing a single piece of itemized feedback from the AI Comparison Agent.
    
    This model mirrors the structure needed for the `ai_evaluation_feedback` table.
    The AI will generate multiple instances of this class (one for each campaign rule)
    to provide explicit, traceable reasoning for its deductions.
    """
    feedback_text: str = Field(
        ..., 
        description="A concise sentence explaining exactly why the specific campaign rule was passed or failed by the AI."
    )
    is_compliant: bool = Field(
        ..., 
        description="Must be strictly True if the rule is perfectly met, or False if the rule is violated."
    )


class AIEvaluation(BaseModel):
    """
    The master 'Transport Envelope' Schema forced upon the LangChain Comparison Agent.
    
    When `with_structured_output(AIEvaluation)` is called, the AI is physically forced 
    to generate this exact JSON block. It calculates the overall `ai_score` for the 
    parent `ai_evaluation` table, and nests all the `feedbacks` that will later be 
    unpacked and bulk-inserted into the `ai_evaluation_feedback` table.

    """
    ai_score: float = Field(
        ..., 
        description="The final calculated audit percentage (0.0 to 100.0) based on the ratio of compliant vs non-compliant rules."
    )
    feedbacks: list[AIEvaluationFeedback] = Field(
        ..., 
        description="The itemized list of specific evaluations for every single rule provided in the prompt."
    )

class AIEvaluationRules(BaseModel):
    """
    Schema for extracting structured rules from a marketing campaign PDF.
    
    This model is used by the ExtractionRulesAgent (GPT-4o-mini) to guarantee that 
    the unstructured text from the PDF is parsed into a clean, predictable JSON 
    object. This object is then saved as JSONB in the Supabase 'campaigns' table.

    """

    brand: str = Field(..., description="Name of the brand to analyze (e.g. Coca-Cola, Pepsi)")
    campaign_name: str = Field(..., description="The name of the marketing campaign (e.g. Lanzamiento Verano 2026)")
    portfolio_skus: list[str] = Field(..., description="List of expected supplementary products to find on the shelf")
    focus_product: str = Field(..., description="The primary specific product to analyze for compliance")
    target_price: float = Field(..., description="The exact expected price of the product at the store")
    min_facings: float = Field(..., description="The minimum number of product facings that should be visible (e.g. 4.0)")
    share_of_facing: int = Field(..., description="The expected percentage share of the total category (e.g. 15)")
    price_tag_required: bool = Field(..., description="Boolean indicating whether a proper price tag must be visible on site")
    rules: list[str] = Field(..., description="A clear, itemized list of specific text rules that the Vision AI must audit against")
