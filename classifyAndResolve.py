import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from groq import Groq
import json
load_dotenv()

class TicketClassification(BaseModel):
    category: str
    subcategory: str
    assignment_group: str
    confidence: float
    signals: List[str]
    priority: str

class TicketResolution(BaseModel):
    level: str
    solutions: list[str]

api_key = os.environ.get("GROQ_TOKEN")
MODEL_NAME = "openai/gpt-oss-20b"

# Initialize your client
client = Groq(api_key=api_key)

CLASSIFIER_PROMPT = """
You are a hierarchical ticket classifier for SAP S/4HANA incidents. 
Your job: map a free-text “Short description” to a JSON with fields:
- category (string)
- subcategory (string)
- assignment_group (string)
- confidence (0-1 float with two decimals)
- signals (array of short strings: key words/phrases you matched)
- priority (Low, Medium, High, Critical)

### CONTEXT
Follow this taxonomy strictly:
- category = "Record to Report" (default in current knowledge).
- subcategory = "CO" (unless future taxonomy expands).
- assignment_group:
  * TwO CG Record to Report (default for FI/CO issues)
  * TwO CG SAP Integration (interfaces/SFTP, BluePlanner/IBP, I03x codes)
  * TwO CG SAP Security (roles/Fiori/authorization issues)
  * TwO CG Order to Cash (billing, SD, customer hierarchy, FPS)
  * TwO GMDM (BOM, master recipe, production version, valuation, net weight, PP1)
  * TwO D&A Support (reports, Analyzer, variance reporting)
  * TwO HYPERCARE Make to Deliver (execution/maintenance orders not purely FI/CO)
  * TwO Triaging & Support (explicit test/triage tickets)

Regional overrides:
- If description contains "<TNA>", replace “CG” with “TNA_{Domain} HYPERCARE”.
- If "<FI France>", use “WER_{Domain} HYPERCARE”.
- If “hypercare” context is explicit, choose the hypercare variant if available.
- Otherwise default to CG flavor.

Tie-breakers:
- If both Integration and R2R: interface/SFTP issues → Integration; posting/accounting logic → R2R.
- If both GMDM and R2R: master data root cause → GMDM; accounting logic → R2R.
- Maintenance/production orders: accounting settlement → R2R; execution → M2D; master data setup → GMDM.

### FEW-SHOT EXAMPLES
Input: "<Switzerland> CoA table"
Output: {"category":"Record to Report","subcategory":"CO","assignment_group":"TwO CG Record to Report","confidence":0.88,"signals":["CoA","GL/Chart of Accounts"], "priority":"Medium"}

Input: "<UK> Monthly Inbound Accruals file from BluePlanner did not process - file on SFTP"
Output: {"category":"Record to Report","subcategory":"CO","assignment_group":"TwO CG SAP Integration","confidence":0.92,"signals":["BluePlanner","SFTP","inbound file"], "priority":"High"}

Input: "<FI France> Customer Hierarchy Not Assigned"
Output: {"category":"Record to Report","subcategory":"CO","assignment_group":"TwO WER_Order to Cash HYPERCARE","confidence":0.86,"signals":["customer hierarchy","O2C","<FI France>"], "priority":"High"}

Input: "OB52 - period incorrectly opened for 1100 and 1200 company codes"
Output: {"category":"Record to Report","subcategory":"CO","assignment_group":"TwO CG Record to Report","confidence":0.90,"signals":["OB52","period open"], "priority":"High"}

Input: "<TNA> FX Reval is booking to the wrong profit center"
Output: {"category":"Record to Report","subcategory":"CO","assignment_group":"TwO TNA_Record to Report HYPERCARE","confidence":0.93,"signals":["FX revaluation","profit center","<TNA>"], "priority":"Critical"}

Input: "Edit option needs to be enabled in Manage Cost Element Groups Fiori app"
Output: {"category":"Record to Report","subcategory":"CO","assignment_group":"TwO CG SAP Security","confidence":0.89,"signals":["Fiori","authorization","enable edit"], "priority":"Medium"}

---
NOW CLASSIFY the new short description strictly in the JSON schema above.
"""

def classify_ticket(issue_text: str):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": CLASSIFIER_PROMPT},
                  {"role": "user", "content": issue_text}],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content
    # print("Raw result:\n", raw_content)

    try:
        # Try direct parse first
        ticket = TicketClassification.model_validate_json(raw_content)
        return ticket.model_dump()
    except Exception:
        # Fallback: try to slice out JSON portion
        try:
            start = raw_content.find("{")
            end = raw_content.rfind("}")
            if start != -1 and end != -1:
                json_str = raw_content[start:end+1]
                ticket = TicketClassification.model_validate_json(json_str)
                return ticket.model_dump()
        except Exception as e:
            print("Fallback parsing failed:", e)

def resolve_ticket_specific(issue_text: str):
    SPECIFIC_SOLVER_PROMPT="""
You are an expert SAP ERP support specialist with deep knowledge of finance (FI), controlling (CO), materials management (MM), production planning (PP), and integration modules. Analyze the following list of recorded issues from various regions and departments. For each issue, first classify it into one of the following IT support levels based on complexity:

L1 (Low Level): Simple problems requiring basic knowledge, such as user errors, simple configuration checks, or standard transactions that can be resolved quickly without system changes (e.g., verifying settings, running reports, or basic troubleshooting).
L2 (Medium Level): Operational problems requiring moderate expertise, such as making changes in the system via standard customizing (e.g., updating master data, configuring in SPRO, adjusting OKB9/OB52, or scheduling batch jobs).
L3 (High Level): Complex problems requiring advanced steps, custom code changes, ABAP development, or deep system modifications (e.g., debugging programs, enhancing user exits, or fixing core system bugs).

After classifying the issue, provide a step-by-step solution tailored to that level.
Then, provide a numbered step-by-step solution guide, assuming access to SAP GUI/Fiori apps where relevant. 
Include transaction codes (e.g., T-codes like CK11N for costing, OB52 for period opening), safety precautions (e.g., test in a sandbox first), and any prerequisites (e.g., required roles/authorizations).

Ensure solutions are practical, safe, and based on standard SAP best practices. Do not invent details; base on common SAP resolutions.

Provide result strictly in JSON format with fields and no other commentaries:
- level: L1, L2, or L3
- solutions: List of step-by-step instructions
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": SPECIFIC_SOLVER_PROMPT},
                  {"role": "user", "content": issue_text}],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content
    # print("Raw result:\n", raw_content)

    try:
        # Try direct parse first
        result = TicketResolution.model_validate_json(raw_content)
        return result.model_dump()
    except Exception:
        # Fallback: try to slice out JSON portion
        try:
            start = raw_content.find("{")
            end = raw_content.rfind("}")
            if start != -1 and end != -1:
                json_str = raw_content[start:end+1]
                result = TicketResolution.model_validate_json(json_str)
                return result.model_dump()
        except Exception as e:
            print("Fallback parsing failed:", e)
            raise ValueError("Unable to parse raw content into TicketResolution")

def resolve_ticket_general(issue_text: str):
    GENERAL_SOLVER_PROMPT="""
You are an expert IT support specialist with deep knowledge of ERP systems (e.g., SAP S/4HANA) and other IT systems. I will provide a single IT-related issue from a specific region or department. Your task is to:

Classify the issue into one of the following IT support levels based on its complexity:

L1 (Low Level): Simple issue requiring basic knowledge, such as user errors, standard transaction usage, or basic troubleshooting (e.g., checking settings, running reports, or guiding users through standard processes).
L2 (Medium Level): Operational issue requiring moderate expertise, such as system configuration changes via standard customizing (e.g., updating master data, adjusting settings in SPRO, or scheduling batch jobs).
L3 (High Level): Complex issue requiring advanced steps, such as custom code changes, ABAP development, debugging, or significant system modifications (e.g., enhancing user exits, fixing core system bugs, or addressing deep integration issues).

Provide a step-by-step solution for the issue, tailored to its classified support level.
If the issue references a specific incident number, note that historical context may need review but provide a general solution based on common practices.
Ensure the solution is practical, follows best practices, and prioritizes system stability. Do not invent details; base the solution on standard processes and configurations. If clarification is needed for the issue, note it and provide a generalized approach.

Provide result strictly in JSON format with fields and no other commentaries:
- level: L1, L2, or L3
- solutions: List of step-by-step instructions
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": GENERAL_SOLVER_PROMPT},
                  {"role": "user", "content": issue_text}],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content
    # print("Raw result:\n", raw_content)

    try:
        # Try direct parse first
        result = TicketResolution.model_validate_json(raw_content)
        return result.model_dump()
    except Exception:
        # Fallback: try to slice out JSON portion
        try:
            start = raw_content.find("{")
            end = raw_content.rfind("}")
            if start != -1 and end != -1:
                json_str = raw_content[start:end+1]
                result = TicketResolution.model_validate_json(json_str)
                return result.model_dump()
        except Exception as e:
            print("Fallback parsing failed:", e)
            raise ValueError("Unable to parse raw content into TicketResolution")


def resolve_ticket_general(issue_text: str):
    GENERAL_SOLVER_PROMPT="""
You are an expert IT support specialist with deep knowledge of ERP systems (e.g., SAP S/4HANA) and other IT systems. I will provide a single IT-related issue from a specific region or department. Your task is to:

Classify the issue into one of the following IT support levels based on its complexity:

L1 (Low Level): Simple issue requiring basic knowledge, such as user errors, standard transaction usage, or basic troubleshooting (e.g., checking settings, running reports, or guiding users through standard processes).
L2 (Medium Level): Operational issue requiring moderate expertise, such as system configuration changes via standard customizing (e.g., updating master data, adjusting settings in SPRO, or scheduling batch jobs).
L3 (High Level): Complex issue requiring advanced steps, such as custom code changes, ABAP development, debugging, or significant system modifications (e.g., enhancing user exits, fixing core system bugs, or addressing deep integration issues).

Provide a step-by-step solution for the issue, tailored to its classified support level.
If the issue references a specific incident number, note that historical context may need review but provide a general solution based on common practices.
Ensure the solution is practical, follows best practices, and prioritizes system stability. Do not invent details; base the solution on standard processes and configurations. If clarification is needed for the issue, note it and provide a generalized approach.

Provide result strictly in JSON format with fields and no other commentaries:
- level: L1, L2, or L3
- solutions: List of step-by-step instructions
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": GENERAL_SOLVER_PROMPT},
                  {"role": "user", "content": issue_text}],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content
    # print("Raw result:\n", raw_content)

    try:
        # Try direct parse first
        result = TicketResolution.model_validate_json(raw_content)
        return result.model_dump()
    except Exception:
        # Fallback: try to slice out JSON portion
        try:
            start = raw_content.find("{")
            end = raw_content.rfind("}")
            if start != -1 and end != -1:
                json_str = raw_content[start:end+1]
                result = TicketResolution.model_validate_json(json_str)
                return result.model_dump()
        except Exception as e:
            print("Fallback parsing failed:", e)
            raise ValueError("Unable to parse raw content into TicketResolution")


def resolve_ticket(issue_text: str, context_text: str):
    GENERAL_SOLVER_PROMPT = """
You are an expert IT support specialist with access to the organization's SOPs and knowledge base.

Your task is to:
1. Use the provided SOP context to suggest a resolution for the given IT issue.
2. Classify the issue resolution into one of the following categories:
   - "automated": Fully solvable with automation steps.
   - "partially automated": Some steps can be automated, but final step requires human decision/action.
   - "unsolvable": Too complex or not covered by SOPs, should be escalated to human staff.

3. If the resolution is "automated", return all automation steps.
   If it is "partially automated", return the automation steps and the last step should be "Escalate to human staff".
   If it is "unsolvable", return no steps.

Strictly return the result in JSON format:
{
  "Solvability": "automated" | "partially automated" | "unsolvable",
  "steps": [ "step1", "step2", ... ]
}
"""

    full_prompt = f"""
Context (SOPs / Knowledge Base):
{context_text}

Issue:
{issue_text}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": GENERAL_SOLVER_PROMPT},
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content

    try:
        # Try parsing directly
        result = json.loads(raw_content)
        return result
    except Exception:
        # Fallback: extract JSON manually
        try:
            start = raw_content.find("{")
            end = raw_content.rfind("}")
            if start != -1 and end != -1:
                json_str = raw_content[start:end+1]
                result = json.loads(json_str)
                return result
        except Exception as e:
            print("Fallback parsing failed:", e)
            raise ValueError("Unable to parse raw content into resolution JSON")
