import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from groq import Groq

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


if __name__ == "__main__":
    test_issue = "<UK> Strand postings for billing and material movements are all wrong"
    classification = classify_ticket(test_issue)
    print("Classification result:\n", classification)

    specific_solution = resolve_ticket_specific(test_issue)
    print("\nSpecific solution result:\n", specific_solution)

    general_solution = resolve_ticket_general(test_issue)
    print("\nGeneral solution result:\n", general_solution)

    # Sample output:

    # Classification result:
    # {'category': 'Record to Report', 'subcategory': 'CO', 'assignment_group': 'TwO CG Record to Report', 'confidence': 0.92, 'signals': ['Strand postings', 'billing', 'material movements', '<UK>'], 'priority': 'High'}

    # Specific solution result:
    # {'level': 'L2', 'solutions': ['1. Verify the posting keys used for billing and material movements – open transaction **OBYC** and check the posting key assignments for the relevant document types (e.g., 01 for billing, 01/02 for material movements). Ensure the keys are correctly mapped to the appropriate G/L accounts and posting types.', '2. Check the posting period settings – run transaction **OB52** and confirm that the posting periods for the fiscal year are open for the periods in which the incorrect postings were made. If closed, open the period or use a period open/close exception if business‑justified.', '3. Review the document type configuration – navigate to **SPRO → Materials Management → Material Master → Accounting → Define Document Types** and confirm that the document type used for the postings is correctly linked to the posting keys and G/L accounts. Adjust if necessary.', '4. Inspect the G/L account assignments – use transaction **OBYC** or **OBYC** (for posting keys) and **OBYC** (for account groups) to ensure the G/L accounts used in the postings are correctly assigned to the posting keys and document types. Correct any mismatches.', '5. Validate integration settings – in **SPRO → Sales and Distribution → Billing → Billing Documents → Define Billing Document Types** and **SPRO → Materials Management → Material Master → Accounting → Define Posting Keys for Material Movements**, confirm that the integration between SD and MM is correctly configured for the posting keys in use.', '6. Test the corrected configuration in a sandbox or development system – create a test billing document and a test material movement using the same posting keys and verify that the postings now reflect the correct amounts and G/L accounts.', '7. If the test is successful, transport the configuration changes to the quality and production systems using the standard transport request process. Ensure that all affected roles have the necessary authorizations (e.g., **S_TCODE** for OBYC, OB52, and SPRO).', '8. After transport, clear the SAP cache (transaction **SM12** for locks, **SM58** for background jobs) and restart any relevant background processes if necessary. Monitor the next few postings to confirm the issue is resolved.']}

    # General solution result:
    # {'level': 'L2', 'solutions': ['1. Identify the posting keys used for the billing and material movement transactions that are producing incorrect postings.', '2. In SPRO, navigate to Accounting > Financial Accounting > Financial Accounting Global Settings > Document > Posting > Posting Keys. Verify that the posting keys for the affected transaction types are correctly assigned to the appropriate GL accounts and posting periods.', '3. Check the document type configuration (SPRO > Accounting > Financial Accounting > Financial Accounting Global Settings > Document > Document Types) to ensure the document type used for these postings has the correct posting key and account determination settings.', '4. Review the account determination settings for the relevant posting keys (SPRO > Accounting > Financial Accounting > Financial Accounting Global Settings > Document > Account Determination > Posting Key). Confirm that the correct G/L account groups and account groups are assigned.', '5. Examine the posting period control (SPRO > Accounting > Financial Accounting > Financial Accounting Global Settings > Posting Periods > Posting Period Control) to ensure the posting period is open for the transaction dates and that the period control settings are correct for the document type.', '6. Verify that no user exits or BADI (e.g., USEREXIT_BADI_POSTING) is active that could be overriding standard posting logic. If active, review the custom code for potential errors.', '7. Perform a test posting in a sandbox or test system using the same transaction and posting key. Capture the resulting accounting document and compare it to the expected outcome.', '8. If discrepancies are found, adjust the configuration in SPRO accordingly (e.g., correct posting key assignment, update account determination, or modify posting period control).', '9. After configuration changes, repeat the test posting to confirm that the postings are now correct.', '10. Document the changes made, including the rationale, the configuration paths, and any test results, and communicate the update to relevant users and stakeholders.']}
