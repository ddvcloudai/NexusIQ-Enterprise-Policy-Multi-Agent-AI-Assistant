# main.py
# FastAPI application entry point for NexusIQ Enterprise Policy Assistant.
# Exposes REST API endpoints consumed by the Streamlit frontend.

from fastapi import FastAPI, HTTPException   
from fastapi.middleware.cors import CORSMiddleware  
from pydantic import BaseModel, Field, field_validator  
from agents import process_query            
import logging                              

# ─── LOGGING SETUP ───────────────────────────────────────────────────────────


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__) 


# ─── FASTAPI APP INITIALISATION ──────────────────────────────────────────────

app = FastAPI(
    title="NexusIQ Enterprise Policy Assistant API", 
    description=(
        "Multi-agent REST API for routing employee queries to HR, IT, and Finance "
        "policy agents. Includes guardrails, governance, and structured responses."
    ),
    version="1.0.0", 
    docs_url="/docs",  
    redoc_url="/redoc", 
)

# ─── CORS MIDDLEWARE ─────────────────────────────────────────────────────────


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_credentials=True,       
    allow_methods=["*"],          
    allow_headers=["*"],          
)


# ─── PYDANTIC SCHEMAS ────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """
    Pydantic model for the incoming query request body.
    Validates and sanitises input before it reaches the agent layer.
    """
    query: str = Field(
        ...,                      
        min_length=3,              
        max_length=2000,          
        description="The employee's policy-related question.",
        example="How many days of annual leave am I entitled to?",
    )

    @field_validator("query")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace from the query before processing."""
        return v.strip()


class QueryResponse(BaseModel):
    """
    Pydantic model for the structured API response returned to the frontend.
    All fields are explicitly typed for clarity and documentation.
    """
    department: str = Field(..., description="Department that handled the query (HR, IT, Finance, or Security).")
    answer: str = Field(..., description="Policy-grounded answer from the department agent.")
    flagged: bool = Field(..., description="True if the query was flagged by the guardrail layer.")
    flag_reason: str | None = Field(None, description="Reason for flagging, if applicable.")


# ─── API ROUTES ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """
    Root health check endpoint.
    Returns a simple status message to confirm the API is running.
    """
    return {"status": "ok", "message": "NexusIQ API is live. Visit /docs for the Swagger UI."}


@app.get("/health", tags=["Health"])
def health_check():
    """
    Dedicated health check endpoint for monitoring tools or load balancers.
    Returns HTTP 200 with service status.
    """
    return {"status": "healthy", "service": "NexusIQ Enterprise Policy Assistant"}


@app.post("/query", response_model=QueryResponse, tags=["Policy Query"])
def handle_query(request: QueryRequest):
    """
    Primary endpoint for processing employee policy queries.
    
    Pipeline:
    1. Pydantic validates and sanitises the request body.
    2. The query is passed to the multi-agent orchestration layer (agents.py).
    3. The structured result is returned as a QueryResponse.
    
    Raises HTTP 500 if an unexpected server-side error occurs (e.g., LLM API failure).
    """
    logger.info(f"Received query: {request.query[:80]}...")  

    try:
        
        result = process_query(request.query)

       
        logger.info(f"Query routed to: {result['department']} | Flagged: {result['flagged']}")

        
        return QueryResponse(**result)

    except ValueError as ve:
        
        logger.error(f"Configuration error: {ve}")
        raise HTTPException(status_code=500, detail=str(ve))

    except Exception as e:
        
        logger.error(f"Unexpected error during query processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your query. Please try again.",
        )
