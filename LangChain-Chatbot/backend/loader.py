# backend/loader.py
import os
import pickle
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss

INDEX_FAISS_PATH = "faiss_index.faiss"
INDEX_TEXTS_PATH = "texts.pkl"
EMB_MODEL_NAME = "all-MiniLM-L6-v2"  # local name for sentence-transformers hub

def read_pdf_pages(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for p in reader.pages:
        text = p.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(text)
    return pages

def build_index_from_pdf(pdf_path="data/company_faq.pdf"):
    print("Building FAISS index from PDF:", pdf_path)
    pages = read_pdf_pages(pdf_path)
    if not pages:
        raise RuntimeError("No text extracted from PDF. Check PDF path or contents.")

    model = SentenceTransformer(f"sentence-transformers/{EMB_MODEL_NAME}")
    # encode in batches (convert_to_numpy True)
    embeddings = model.encode(pages, convert_to_numpy=True, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # persist
    faiss.write_index(index, INDEX_FAISS_PATH)
    with open(INDEX_TEXTS_PATH, "wb") as f:
        pickle.dump(pages, f)

    print("Index built and saved.")
    return index, pages, model

def load_index():
    if os.path.exists(INDEX_FAISS_PATH) and os.path.exists(INDEX_TEXTS_PATH):
        print("Loading existing FAISS index...")
        index = faiss.read_index(INDEX_FAISS_PATH)
        with open(INDEX_TEXTS_PATH, "rb") as f:
            pages = pickle.load(f)
        model = SentenceTransformer(f"sentence-transformers/{EMB_MODEL_NAME}")
        return index, pages, model
    else:
        return None, None, None

def build_or_load_index(pdf_path="data/company_faq.pdf"):
    index, pages, model = load_index()
    if index is not None:
        return index, pages, model
    return build_index_from_pdf(pdf_path)

def similarity_search(index, pages, model, query, top_k=3):
    q_emb = model.encode([query], convert_to_numpy=True)[0].astype("float32")
    D, I = index.search(np.array([q_emb]), top_k)
    results = []
    for idx in I[0]:
        if idx < len(pages):
            results.append(pages[idx])
    return results
