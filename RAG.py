from pathlib import Path
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

# ---------- Settings ----------
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 3
DISTANCE_THRESHOLD = 0.2  # Minimum similarity threshold


class RAGRetriever:
    def __init__(self, folder: str = "D:\\AMS_POC\\AMS_POC\\Sops", embed_model_name=EMBED_MODEL_NAME):
        self.model = SentenceTransformer(embed_model_name)
        self.pdf_texts = []       # Full text of each PDF
        self.metadatas = []       # Metadata for each PDF
        self.index = None
        self._build_from_folder(folder)

    def _extract_pdf_text(self, pdf_file):
        """Extract all text from a PDF (no OCR)"""
        full_text = []
        with fitz.open(pdf_file) as doc:
            for page_num, page in enumerate(doc, start=1):
                blocks = page.get_text("blocks")
                if not blocks:
                    continue
                # Sort blocks top-to-bottom, left-to-right
                blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
                page_text = "\n".join([b[4].strip() for b in blocks if b[4].strip()])
                if page_text:
                    full_text.append(f"Page {page_num}:\n{page_text}")
        return "\n\n".join(full_text)

    def _build_from_folder(self, folder: str):
        """Extract text from PDFs and build FAISS index at PDF-level"""
        folder = Path(folder)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")

        for pdf_file in folder.glob("*.pdf"):
            text = self._extract_pdf_text(pdf_file)
            if not text:
                continue
            self.pdf_texts.append(text)
            self.metadatas.append({"source_file": pdf_file.name})

        if not self.pdf_texts:
            raise ValueError("No text found in PDFs.")

        # Encode embeddings for full PDFs
        embeddings = self.model.encode(
            self.pdf_texts, batch_size=8, show_progress_bar=True, convert_to_numpy=True
        )
        faiss.normalize_L2(embeddings)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

    def query(self, query: str, top_k=TOP_K):
        """Query FAISS and return top PDFs whose content matches the query"""
        q_emb = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(q_emb)
        distances, indices = self.index.search(q_emb, top_k)

        results = []
        for idx, score in zip(indices[0], distances[0]):
            if score >= DISTANCE_THRESHOLD:
                results.append({
                    "text": self.pdf_texts[idx],
                    "metadata": self.metadatas[idx],
                    "score": float(score)
                })
        return results

    def get_prompt_text(self, results, max_chars=3000):
        """Concatenate results into prompt-ready text"""
        pieces, cur_len = [], 0
        for r in results:
            src = r["metadata"]["source_file"]
            part = f"Source: {src}\n{r['text']}\n---\n"
            if cur_len + len(part) > max_chars:
                remaining = max_chars - cur_len
                if remaining > 0:
                    pieces.append(part[:remaining])
                break
            pieces.append(part)
            cur_len += len(part)
        return "\n".join(pieces)


# ---------- Usage ----------
# if __name__ == "__main__":
#     retriever = RAGRetriever(folder="D:\\AMS_POC\\AMS_POC\\Sops")
#     query = "All accounts not working S4 and BW"
#     results = retriever.query(query)
#     prompt_text = retriever.get_prompt_text(results)
#     print(prompt_text[:2000], "\n... [truncated]\n")  # Print first 2000 chars
