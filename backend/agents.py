# agents.py
# Core multi-agent orchestration logic for NexusIQ.
# Contains: policy loading, guardrails, supervisor routing, and department agent calls.

import os                          
import re                          
from functools import lru_cache    
from langchain_openai import ChatOpenAI         
from langchain_core.messages import HumanMessage, SystemMessage 
from dotenv import load_dotenv     


load_dotenv()

# ─── CONSTANTS ──────────────────────────────────────────────────────────────


POLICY_DIR = os.path.join(os.path.dirname(__file__), "..", "policies")


MODEL_NAME = "gpt-4o-mini"


VALID_DEPARTMENTS = {"HR", "IT", "Finance"}

# ─── GUARDRAILS ──────────────────────────────────────────────────────────────


INJECTION_PATTERNS = [
    r"ignore (all |previous |above |prior )?instructions",  
    r"you are now",                
    r"act as (a |an )?(?!HR|IT|Finance)",  
    r"disregard (your |the )?system",      
    r"forget (everything|your instructions)", 
    r"jailbreak",               
    r"DAN mode",                 
    r"developer mode",             
    r"override (safety|policy|guidelines)",  
    r"reveal (your |the )?(system |internal )?prompt", 
    r"translate (this|the following) to (base64|hex|binary)", 
]

def check_guardrails(query: str) -> tuple[bool, str]:
    """
    Scans the user query for known prompt injection and abuse patterns.
    Returns (is_safe: bool, reason: str).
    If is_safe is False, the query must be rejected before LLM invocation.
    """
    query_lower = query.lower()  

    
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query_lower):
            return False, f"Query flagged by security guardrail: matched pattern '{pattern}'."

   
    if len(query) > 2000:
        return False, "Query exceeds maximum allowed length of 2000 characters."

    
    if not query.strip():
        return False, "Query is empty. Please enter a valid question."

    return True, "OK"  


# ─── POLICY LOADER ───────────────────────────────────────────────────────────

@lru_cache(maxsize=3)  
def load_policy(department: str) -> str:
    """
    Reads the plain-text policy file for the given department.
    Filenames: hr_policy.txt, it_policy.txt, finance_policy.txt
    Uses lru_cache so each file is only read once per server lifetime.
    """
    filename_map = {
        "HR": "hr_policy.txt",
        "IT": "it_policy.txt",
        "Finance": "finance_policy.txt",
    }
    filepath = os.path.join(POLICY_DIR, filename_map[department])

    
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# ─── LLM INITIALISATION ──────────────────────────────────────────────────────

def get_llm() -> ChatOpenAI:
    """
    Initialises and returns the ChatOpenAI LLM instance.
    temperature=0 ensures deterministic, consistent answers (no creativity drift).
    Called fresh per request so API key changes in .env take effect without restart.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Please add it to your .env file.")
    return ChatOpenAI(model=MODEL_NAME, temperature=0, openai_api_key=api_key)


# ─── SUPERVISOR AGENT ────────────────────────────────────────────────────────

def supervisor_route(query: str, llm: ChatOpenAI) -> str:
    """
    Supervisor Agent: decides which department (HR, IT, Finance) should handle the query.
    Uses a tightly constrained prompt to ensure it only returns one of three department names.
    This is the orchestration layer — it does NOT answer the question itself.
    """
    routing_prompt = f"""
You are an enterprise routing supervisor for a company policy assistant.
Your ONLY task is to classify the user query into exactly one department.

Rules:
- Respond with EXACTLY ONE WORD from: HR, IT, Finance
- Do NOT explain your choice
- Do NOT answer the question
- If the query is ambiguous, choose the most likely department

Query: {query}
"""
    
    response = llm([HumanMessage(content=routing_prompt)])
    department = response.content.strip()

  
    if department not in VALID_DEPARTMENTS:
        
        return "HR"

    return department


# ─── DEPARTMENT AGENTS ───────────────────────────────────────────────────────

def department_agent(department: str, query: str, llm: ChatOpenAI) -> str:
    """
    Department Agent: answers the user query strictly based on the department's policy document.
    Each department has its own system prompt constructed from its policy text.
    The agent is instructed NOT to hallucinate or answer outside the provided context.
    """
    
    policy_text = load_policy(department)

  
    system_prompt = f"""
You are a professional {department} Policy Assistant for an enterprise organisation.
Your role is to answer employee queries accurately, clearly, and politely.

STRICT RULES:
1. Answer ONLY based on the policy information provided below.
2. Do NOT make up, infer, or assume any information not present in the policy.
3. If the answer is not found in the policy, respond with:
   "This specific query is not covered in the current {department} policy document. 
    Please contact the {department} department directly for assistance."
4. Always maintain a professional and respectful tone.
5. Structure your answer in clear, readable paragraphs or bullet points when listing multiple points.
6. Begin your response by briefly confirming which policy area you are addressing.

--- {department} POLICY DOCUMENT ---
{policy_text}
--- END OF POLICY DOCUMENT ---
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=query),
    ]

  
    response = llm(messages)
    return response.content.strip()


# ─── GOVERNANCE LAYER ────────────────────────────────────────────────────────

def governance_check_response(response: str, department: str) -> str:
    """
    Post-generation governance layer.
    Ensures the LLM response does not inadvertently contain sensitive metadata,
    internal prompts, or system-level information before returning to the user.
    This acts as an output filter on top of the agent response.
    """
   
    disallowed_output_patterns = [
        r"system prompt",           
        r"openai_api_key",          
        r"sk-[a-zA-Z0-9]{20,}",    
        r"POLICY DOCUMENT",         
    ]

    response_lower = response.lower()
    for pattern in disallowed_output_patterns:
        if re.search(pattern, response_lower):
            
            return (
                f"The {department} department response could not be delivered due to a "
                "content policy check. Please rephrase your query or contact the department directly."
            )

    return response  


# ─── MAIN ORCHESTRATION FUNCTION ─────────────────────────────────────────────

def process_query(user_query: str) -> dict:
    """
    End-to-end orchestration function called by the FastAPI route.
    Pipeline:
      1. Guardrail check (input validation & injection detection)
      2. Supervisor routing (which department handles this?)
      3. Department agent invocation (generate policy-grounded answer)
      4. Governance output check (sanitise the response)
    Returns a dict with keys: department, answer, flagged (bool), flag_reason.
    """

   
    is_safe, reason = check_guardrails(user_query)
    if not is_safe:
        return {
            "department": "Security",
            "answer": f"Your query could not be processed. {reason}",
            "flagged": True,
            "flag_reason": reason,
        }

   
    llm = get_llm()

    
    department = supervisor_route(user_query, llm)

    
    raw_answer = department_agent(department, user_query, llm)

    
    final_answer = governance_check_response(raw_answer, department)

    return {
        "department": department,
        "answer": final_answer,
        "flagged": False,
        "flag_reason": None,
    }
