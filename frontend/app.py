# app.py
# NexusIQ Streamlit frontend — Professional enterprise policy assistant UI.
# Communicates with the FastAPI backend via HTTP POST to /query.

import streamlit as st      
import requests             
from datetime import datetime  
from io import BytesIO      
from reportlab.lib.pagesizes import A4          
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  
from reportlab.lib.units import inch            
from reportlab.lib import colors                
from reportlab.platypus import (                
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT 

# ─── PAGE CONFIGURATION ──────────────────────────────────────────────────────


st.set_page_config(
    page_title="NexusIQ | Enterprise Policy Assistant",  
    page_icon="🔷",              
    layout="wide",               
    initial_sidebar_state="collapsed",  
)

# ─── CONSTANTS ───────────────────────────────────────────────────────────────


BACKEND_URL = "http://localhost:8000/query"


DEPT_COLORS = {
    "HR": "#0d6efd",      
    "IT": "#198754",      
    "Finance": "#fd7e14",  
    "Security": "#dc3545", 
}


# ─── CUSTOM CSS ──────────────────────────────────────────────────────────────

def inject_css():
    """
    Injects custom CSS to give NexusIQ a polished, enterprise-grade appearance.
    Overrides Streamlit defaults for typography, colours, and component styling.
    """
    st.markdown("""
    <style>
    /* Import professional fonts from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@700&display=swap');

    /* ── Global Reset ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #f8f9fc;
    }

    /* ── Main content area ── */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 900px;
    }

    /* ── Header banner ── */
    .nexus-header {
        background: linear-gradient(135deg, #0a1628 0%, #1a3a6b 50%, #0f2d5e 100%);
        border-radius: 16px;
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
        color: white;
        position: relative;
        overflow: hidden;
    }
    .nexus-header::before {
        content: '';
        position: absolute;
        top: -40px; right: -40px;
        width: 200px; height: 200px;
        background: rgba(255,255,255,0.04);
        border-radius: 50%;
    }
    .nexus-header h1 {
        font-family: 'Playfair Display', serif;
        font-size: 2.4rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin: 0 0 0.4rem 0;
        color: white !important;
    }
    .nexus-header .subtitle {
        font-size: 1rem;
        color: rgba(255,255,255,0.72);
        font-weight: 300;
        letter-spacing: 0.3px;
        margin: 0;
    }
    .nexus-badge {
        display: inline-block;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: rgba(255,255,255,0.85);
        margin-bottom: 1rem;
    }

    /* ── Input card ── */
    .input-card {
        background: white;
        border-radius: 14px;
        padding: 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid #e8ecf4;
        margin-bottom: 1.5rem;
    }
    .input-card h3 {
        font-size: 1rem;
        font-weight: 600;
        color: #1a2540;
        margin: 0 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ── Streamlit textarea override ── */
    .stTextArea textarea {
        border: 1.5px solid #d1d9e6 !important;
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.95rem !important;
        color: #1a2540 !important;
        padding: 0.8rem 1rem !important;
        transition: border-color 0.2s;
        background: #fafbfd !important;
    }
    .stTextArea textarea:focus {
        border-color: #1a3a6b !important;
        box-shadow: 0 0 0 3px rgba(26,58,107,0.08) !important;
    }

    /* ── Submit button ── */
    .stButton button {
        background: linear-gradient(135deg, #0a1628, #1a3a6b) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.65rem 2rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.3px !important;
        transition: all 0.2s !important;
        cursor: pointer !important;
    }
    .stButton button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(26,58,107,0.3) !important;
    }

    /* ── Response card ── */
    .response-card {
        background: white;
        border-radius: 14px;
        padding: 2rem 2.5rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.07);
        border: 1px solid #e8ecf4;
        margin-bottom: 1.5rem;
    }
    .dept-badge {
        display: inline-block;
        border-radius: 8px;
        padding: 5px 16px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: white;
        margin-bottom: 1rem;
    }
    .response-text {
        font-size: 0.97rem;
        line-height: 1.8;
        color: #2c3e60;
    }
    .response-divider {
        border: none;
        border-top: 1px solid #e8ecf4;
        margin: 1.5rem 0;
    }

    /* ── Warning / flagged message ── */
    .flag-card {
        background: #fff5f5;
        border: 1.5px solid #fcc;
        border-radius: 12px;
        padding: 1.2rem 1.6rem;
        color: #8b1a1a;
        font-size: 0.92rem;
    }

    /* ── Dept info chips at top ── */
    .dept-chips {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        margin-bottom: 1.5rem;
    }
    .chip {
        background: white;
        border: 1px solid #d1d9e6;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.8rem;
        color: #4a5568;
        font-weight: 500;
    }

    /* ── Footer ── */
    .nexus-footer {
        text-align: center;
        color: #9aa5be;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e8ecf4;
    }

    /* ── Hide Streamlit branding ── */
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


# ─── PDF GENERATION ──────────────────────────────────────────────────────────

def generate_pdf(query: str, department: str, answer: str) -> bytes:
    """
    Generates a formatted PDF report of the query and response.
    Uses ReportLab to build an A4 document with NexusIQ branding.
    Returns the PDF as a bytes object for download.
    """
    buffer = BytesIO()  

   
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.2 * inch,
        leftMargin=1.2 * inch,
        topMargin=1.2 * inch,
        bottomMargin=1.2 * inch,
    )

    
    styles = getSampleStyleSheet()

    
    title_style = ParagraphStyle(
        "NexusTitle",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#0a1628"),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )

  
    subtitle_style = ParagraphStyle(
        "NexusSub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#8a96a8"),
        alignment=TA_CENTER,
        spaceAfter=20,
    )

  
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6b7280"),
        fontName="Helvetica-Bold",
        spaceAfter=4,
        letterSpacing=1,
    )

    
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10.5,
        textColor=colors.HexColor("#1e2d4d"),
        leading=16,  
        spaceAfter=6,
    )

    
    dept_color = DEPT_COLORS.get(department, "#1a3a6b")

   
    timestamp = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # ── Build the content story (ReportLab flowable list) ──
    story = []

    
    story.append(Paragraph("NexusIQ", title_style))
    story.append(Paragraph("Enterprise Policy Assistant — Response Report", subtitle_style))

    
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e8ecf4")))
    story.append(Spacer(1, 0.2 * inch))

   
    meta_data = [
        ["Department:", department],
        ["Report Date:", timestamp],
    ]
    meta_table = Table(meta_data, colWidths=[1.5 * inch, 4 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#4a5568")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.25 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e8ecf4")))
    story.append(Spacer(1, 0.2 * inch))

    
    story.append(Paragraph("EMPLOYEE QUERY", label_style))
    story.append(Paragraph(query, body_style))
    story.append(Spacer(1, 0.2 * inch))

    
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e8ecf4")))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"{department.upper()} POLICY RESPONSE", label_style))

    
    for line in answer.split("\n"):
        if line.strip():  
            story.append(Paragraph(line.strip(), body_style))

    story.append(Spacer(1, 0.4 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e8ecf4")))
    story.append(Spacer(1, 0.15 * inch))

    
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#9aa5be"),
        alignment=TA_CENTER,
        leading=12,
    )
    story.append(Paragraph(
        "This report is generated by NexusIQ and is based solely on published company policies. "
        "For policy clarifications, contact the respective department directly. "
        "This document is intended for internal use only.",
        disclaimer_style,
    ))

    
    doc.build(story)

   
    return buffer.getvalue()


# ─── MAIN APP ────────────────────────────────────────────────────────────────

def main():
    """
    Main Streamlit application function.
    Renders the full UI: header, query input, API call, response display, PDF download.
    """
    inject_css() 

 
    st.markdown("""
    <div class="nexus-header">
        <div class="nexus-badge">Enterprise Intelligence Platform</div>
        <h1>🔷 NexusIQ</h1>
        <p class="subtitle">
            Your intelligent enterprise policy assistant — get accurate, instant answers 
            on HR, IT, and Finance policies.
        </p>
    </div>
    """, unsafe_allow_html=True)

    
    st.markdown("""
    <div class="dept-chips">
        <span class="chip">👥 Human Resources</span>
        <span class="chip">💻 Information Technology</span>
        <span class="chip">💼 Finance</span>
    </div>
    """, unsafe_allow_html=True)

   
    st.markdown('<div class="input-card"><h3>🗂️ Submit Your Policy Query</h3>', unsafe_allow_html=True)

   
    user_query = st.text_area(
        label="",                             
        placeholder="e.g. How many days of annual leave am I entitled to?\n"
                    "e.g. What is the password policy for company systems?\n"
                    "e.g. How do I submit an expense reimbursement claim?",
        height=130,                            
        key="query_input",                     
        label_visibility="collapsed",         
    )

 
    submit = st.button("🔍 Get Policy Answer", use_container_width=False)

    st.markdown("</div>", unsafe_allow_html=True) 

   
    if submit:
       
        if not user_query or len(user_query.strip()) < 3:
            st.warning("Please enter a valid query of at least 3 characters.")
        else:
          
            with st.spinner("NexusIQ is analysing your query..."):
                try:
                    
                    response = requests.post(
                        BACKEND_URL,
                        json={"query": user_query.strip()},
                        timeout=60,  
                    )
                    response.raise_for_status()  
                    data = response.json()      

                except requests.exceptions.ConnectionError:
                   
                    st.error(
                        "⚠️ Unable to connect to the NexusIQ backend. "
                        "Please ensure the FastAPI server is running on port 8000."
                    )
                    return

                except requests.exceptions.Timeout:
                
                    st.error("⚠️ The request timed out. Please try again.")
                    return

                except requests.exceptions.HTTPError as e:
                    
                    st.error(f"⚠️ Backend error: {e.response.status_code} — {e.response.text}")
                    return

            
            department = data.get("department", "Unknown")
            answer = data.get("answer", "No response received.")
            flagged = data.get("flagged", False)

            if flagged:
                
                st.markdown(f"""
                <div class="flag-card">
                    🚨 <strong>Query Flagged by Security Guardrail</strong><br><br>
                    {answer}
                </div>
                """, unsafe_allow_html=True)
            else:
             
                dept_color = DEPT_COLORS.get(department, "#1a3a6b")

             
                st.markdown(f"""
                <div class="response-card">
                    <span class="dept-badge" style="background:{dept_color};">
                        {department} Department
                    </span>
                    <hr class="response-divider">
                    <div class="response-text">{answer.replace(chr(10), "<br>")}</div>
                </div>
                """, unsafe_allow_html=True)

             
                st.markdown("**📥 Download Response as PDF**")

            
                pdf_bytes = generate_pdf(user_query, department, answer)

             
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"NexusIQ_{department}_Response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",    
                    use_container_width=False,
                )

  
    st.markdown("""
    <div class="nexus-footer">
        NexusIQ · Enterprise Policy Assistant · For internal use only · 
        Responses are based on published company policies.
    </div>
    """, unsafe_allow_html=True)



if __name__ == "__main__":
    main()  
