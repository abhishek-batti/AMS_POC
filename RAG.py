from pathlib import Path
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ---------- Settings ----------
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
TOP_K = 5

class RAGRetriever:
    def __init__(self, embed_model_name=EMBED_MODEL_NAME):
        self.model = SentenceTransformer(embed_model_name)
        self.index = None
        self.chunks = []
        self.metadatas = []
        self._build_from_folder("D:\\AMS_POC\\AMS_POC\\Sops")

    def _build_from_folder(self, folder: str):
        """Extract text from PDFs, chunk it, and build FAISS index."""
        folder = Path(folder)
        assert folder.exists(), f"Folder not found: {folder}"

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", " ", ""]
        )

        for pdf in folder.glob("*.pdf"):
            doc = fitz.open(str(pdf))
            for i in range(len(doc)):
                text = doc.load_page(i).get_text("text").strip()
                if text:
                    page_chunks = splitter.split_text(text)
                    for idx, chunk in enumerate(page_chunks):
                        self.chunks.append(chunk)
                        self.metadatas.append({
                            "source_file": pdf.name,
                            "page": i + 1,
                            "chunk_index_in_page": idx
                        })
            doc.close()

        if not self.chunks:
            raise ValueError("No text chunks found in PDFs.")

        embeddings = self.model.encode(self.chunks, show_progress_bar=True, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

    def query(self, query: str, top_k=TOP_K):
        """Query the index and return top_k relevant chunks with metadata."""
        q_emb = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(q_emb)
        D, I = self.index.search(q_emb, top_k)

        # Select relevant neighbors based on largest gap in distances
        distances, indices = np.array(D[0]), np.array(I[0])
        mask = distances >= 0.2  # Keep all for gap-based selection
        filtered_indices = indices[mask]
        filtered_distances = distances[mask]

        if len(filtered_indices) <= 1:
            selected_indices = filtered_indices.tolist()
        else:
            gaps = np.diff(filtered_distances)
            cutoff_pos = np.argmax(gaps) + 1
            selected_indices = filtered_indices[:cutoff_pos].tolist()

        return [{
            "text": self.chunks[idx],
            "metadata": self.metadatas[idx],
            "score": float(D[0][np.where(I[0] == idx)][0])
        } for idx in selected_indices]

    def get_prompt_text(self, results, max_chars=3000):
        """Concatenate results into prompt-ready text, merging consecutive chunks."""
        pieces, cur_len, merged_text, prev_meta = [], 0, [], None
        for r in results:
            meta = (r["metadata"]["source_file"], r["metadata"]["page"])
            text = r["text"].strip()
            if prev_meta and meta == prev_meta:
                # Merge overlapping text
                prev_text = merged_text[-1]["text"]
                max_overlap = min(len(prev_text), len(text))
                overlap_len = 0
                for i in range(max_overlap, 10, -1):
                    if prev_text.endswith(text[:i]):
                        overlap_len = i
                        break
                merged_text[-1]["text"] = prev_text + text[overlap_len:]
            else:
                merged_text.append({"meta": meta, "text": text})
            prev_meta = meta

        for item in merged_text:
            src, page = item["meta"]
            part = f"Source: {src} | Page: {page}\n{item['text']}\n---\n"
            if cur_len + len(part) > max_chars:
                remaining = max_chars - cur_len
                if remaining > 0:
                    pieces.append(part[:remaining])
                break
            pieces.append(part)
            cur_len += len(part)
        return "\n".join(pieces)

# ---------- Usage ----------
if __name__ == "__main__":
    # pdf_folder = "D:\\AMS_POC\\AMS_POC\\Sops"
    # query = "Data Source connection to IBP failed"
    # query = "Unable to access S4 HANA Fiori development public URI"
    query = "All accounts not working S4 and BW"
    