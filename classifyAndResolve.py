import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import json
from pydantic import BaseModel
from groq import Groq
load_dotenv()

class TicketClassification(BaseModel):
    category: str
    subcategory: str
    assignment_group: str
    priority: str

api_key = os.environ.get("GROQ_TOKEN")
MODEL_NAME = "openai/gpt-oss-20b"

# Initialize your client
client = Groq(api_key=api_key)

# Define paths for saved files
DATA_PATH = "./historical_data/incident.xlsx"
EMBEDDINGS_PATH = "./index/embeddings.npy"
INDEX_PATH = "./index/faiss_index.index"
DF_PICKLE_PATH = "./index/df.pkl"

# 1. Load or create DataFrame
if os.path.exists(DF_PICKLE_PATH):
    df = pd.read_pickle(DF_PICKLE_PATH)
    print("Loaded DataFrame from pickle...")
else:
    df = pd.read_excel(DATA_PATH)
    df.to_pickle(DF_PICKLE_PATH)
    print("Loaded Excel and saved as pickle...")

# 2. Initialize embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# 3. Load or create embeddings
if os.path.exists(EMBEDDINGS_PATH):
    embeddings = np.load(EMBEDDINGS_PATH)
    print("Loaded embeddings from file...")
else:
    embeddings = model.encode(df["Short description"].astype(str).tolist(), convert_to_numpy=True, normalize_embeddings=True)
    np.save(EMBEDDINGS_PATH, embeddings)
    print("Encoded all short descriptions and saved to file...")

# 4. Load or build FAISS index
d = embeddings.shape[1]  # dimension
if os.path.exists(INDEX_PATH):
    index = faiss.read_index(INDEX_PATH)
    print("Loaded FAISS index from file...")
else:
    index = faiss.IndexFlatIP(d)
    index.add(embeddings)
    faiss.write_index(index, INDEX_PATH)
    print("Built FAISS index and saved to file...")

# 5. Function to get similar incidents
def get_similar_incidents(query, top_k=5):
    query_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    scores, idxs = index.search(query_emb, top_k)  # (1, top_k)
    idxs, scores = idxs[0], scores[0]

    # Retrieve top-k rows
    top_matches = df.iloc[idxs].copy()
    top_matches["similarity"] = scores

    return top_matches

def classify_ticket(issue_text: str):
    # Get similar incidents as context
    top_matches = get_similar_incidents(issue_text, top_k=5)
    
    SIMILAR_INC = "### SIMILAR INCIDENTS\n\n"
    for i, (_, row) in enumerate(top_matches.iterrows(), 1):
        SIMILAR_INC += f"{i}. Description: {row['Short description']}\n"
        SIMILAR_INC += f"   Category: {row['Category']}\n"
        SIMILAR_INC += f"   Subcategory: {row['Subcategory']}\n"
        SIMILAR_INC += f"   Assignment group: {row['Assignment group']}\n"
        SIMILAR_INC += f"   Priority: {row['Priority']}\n"
        SIMILAR_INC += f"   Similarity: {row['similarity']:.2f}\n\n"
    
    # Append similar incidents to the system prompt
    system_content = SIMILAR_INC + """\n---\nNOW Correctly choose the one that matches with the new short description user gives.\n
Give output strictly in the JSON schema as
    {
        category: str
        subcategory: str
        assignment_group: str
        priority: str
    }
"""

    print("Context: ")
    print(system_content)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": system_content},
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
