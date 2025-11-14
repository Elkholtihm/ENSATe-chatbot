import os
import json
from torch import chunk
from transformers import CamembertTokenizer
import numpy as np
from groq import Groq
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, HnswConfigDiff
import uuid

os.environ["HF_HUB_TIMEOUT"] = "300"

tokenizer = CamembertTokenizer.from_pretrained("dangvantuan/sentence-camembert-base")

# --- helper utilities ---
def _clean_text(text: str) -> str:
    """Basic text normalization: collapse whitespace, strip."""
    return " ".join(text.split()).strip()

def _token_windows_from_text(text: str, tokenizer, chunk_size=512, overlap=50):
    """
    Encode text to token ids and yield token windows (list of id lists).
    Returns generator of (token_window, start_idx).
    """
    tokens = tokenizer.encode(text)
    if len(tokens) == 0:
        return

    step = max(1, chunk_size - overlap)
    for start in range(0, len(tokens), step):
        window = tokens[start:start + chunk_size]
        yield window, start

def chunking_json_files(folder_path, tokenizer=tokenizer, chunk_size=512, overlap=50):
    """
    Read JSON schedule files and produce token-based sliding-window chunks.
    Returns: (chunks:list[str], metadata:list[dict])
    """
    chunks = []
    metadata = []

    for file in os.listdir(folder_path):
        if not file.endswith(".json"):
            continue
        file_path = os.path.join(folder_path, file)
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                # skip or log invalid JSON
                print(f"Skipping {file_path}: JSON error {e}")
                continue

        # Build a clean, structured, human-friendly text for the schedule
        lines = [f"Document: {file}"]
        for day, schedule in data.items():
            if not schedule:
                continue
            for entry in schedule:
                # format nicely: "Jour: Lundi | Matière: X | Prof: Y | Salle: Z | Heure: 08:00-10:00"
                entry_parts = [f"{k}: {v}" for k, v in entry.items()]
                lines.append(f"{day} | " + " | ".join(entry_parts))

        text = _clean_text("\n".join(lines))

        # Produce token windows and decode each window back to text
        part = 1
        for token_window, start in _token_windows_from_text(text, tokenizer, chunk_size=chunk_size, overlap=overlap):
            chunk_text = tokenizer.decode(token_window, skip_special_tokens=True).strip()
            # Store chunk text and metadata (part numbering starts at 1)
            chunks.append(chunk_text)
            metadata.append({
                "name": f"{file} (partie {part})",
                "categorie": "emploi du temps",
                "source": file_path,
                "part": part,
                "token_start": int(start)
            })
            part += 1

        # if file was empty we might want one empty chunk? skip.

    return chunks, metadata

def chunking_txt_files(folder_path, tokenizer=tokenizer, chunk_size=512, overlap=50):
    """
    Chunk plain .txt files using token-level sliding windows.
    Returns: (chunks:list[str], metadata:list[dict])
    """
    chunks = []
    metadata = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if not file.endswith(".txt"):
                continue
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                raw = f.read()

            text = _clean_text(raw)
            category = os.path.basename(root) or "txt"

            part = 1
            for token_window, start in _token_windows_from_text(text, tokenizer, chunk_size=chunk_size, overlap=overlap):
                chunk_text = tokenizer.decode(token_window, skip_special_tokens=True).strip()
                chunks.append(chunk_text)
                metadata.append({
                    "name": f"{file} (partie {part})",
                    "categorie": category,
                    "source": file_path,
                    "part": part,
                    "token_start": int(start)
                })
                part += 1

    return chunks, metadata


def normalize(vector):
    """Normalize embeddings"""
    return vector / np.linalg.norm(vector)

def Search(query, client, collection_name, embedding_model, top_k=3):
    """Retrieve top_k relevant chunks from Qdrant"""
    query_embedding = normalize(embedding_model.encode(query))

    results = client.search(
        collection_name=collection_name,
        query_vector=("default", query_embedding),
        limit=top_k
    )

    # Extract only the text chunks
    chunks = [r.payload["chunk"] for r in results]

    # Merge chunks into a readable context
    context_text = "\n---\n".join(chunks)

    # Also extract sources (optional)
    documents_path = [r.payload["source"] for r in results]

    return context_text, documents_path


def GenerationGroq(query, search_results, groq_key, temperature=0.6, max_tokens=2000):
    """Generate response using Groq API"""
    client = Groq(api_key=groq_key)

    prompt = f"""
    Vous êtes un assistant utile. Utilisez le contexte suivant pour répondre à la question de l'utilisateur de manière COMPLÈTE et DÉTAILLÉE en français.
    
    IMPORTANT - FORMAT DE RÉPONSE:
    - Utilisez le format Markdown pour structurer votre réponse
    - Utilisez des titres (##, ###) pour organiser les sections
    - Utilisez des listes à puces ou numérotées pour les énumérations
    - Utilisez des tableaux Markdown pour présenter des données structurées
    - Mettez en **gras** les informations importantes
    - Utilisez des `backticks` pour le code ou les termes techniques
    - Assurez-vous de terminer complètement vos phrases et tableaux
    
    Contexte:
    {search_results}
    
    Question:
    {query}
    
    Réponse complète en Markdown:
    """

    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{'role': 'user', 'content': prompt}],
        temperature=temperature,
        max_completion_tokens=max_tokens,
        top_p=1,
        stream=True,
        stop=None,
    )
    
    generations = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            generations += chunk.choices[0].delta.content
    
    return generations.strip()

def chunk_Embedd(client: QdrantClient, collection_name: str, embedding_model: SentenceTransformer,
                 data_path: str, tokenizer=tokenizer, chunk_size=512, overlap=50, batch_size=64):
    """
    Full pipeline: chunk files, deduplicate, embed in batches, create collection and upsert in batches.
    Returns number of indexed points.
    """
    # chunk
    json_folder = os.path.join(data_path, "emploi-temps")
    chunks_json, metadata_json = chunking_json_files(json_folder, tokenizer=tokenizer, chunk_size=chunk_size, overlap=overlap)
    chunks_txt, metadata_txt = chunking_txt_files(data_path, tokenizer=tokenizer, chunk_size=chunk_size, overlap=overlap)

    chunks = chunks_json + chunks_txt
    metadata = metadata_json + metadata_txt

    # deduplicate while preserving metadata correspondence
    seen = {}
    clean_chunks = []
    clean_metadata = []
    for c, m in zip(chunks, metadata):
        key = c.strip()
        if not key:
            continue
        if key in seen:
            # optionally merge metadata (keep first)
            continue
        seen[key] = True
        clean_chunks.append(key)
        clean_metadata.append(m)

    chunks = clean_chunks
    metadata = clean_metadata

    if len(chunks) == 0:
        print("No chunks to index.")
        return 0

    print(f"Number of chunks to embed: {len(chunks)}")

    # create collection (delete if exists)
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "default": VectorParams(size=embedding_model.get_sentence_embedding_dimension(), distance=Distance.COSINE)
        },
        hnsw_config=HnswConfigDiff(ef_construct=300)
    )

    # batch encode + upsert
    points = []
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_meta = metadata[i:i+batch_size]

        embs = embedding_model.encode(batch_chunks, convert_to_numpy=True, show_progress_bar=False)
        # normalize
        embs = np.array([v / np.linalg.norm(v) if np.linalg.norm(v) > 0 else v for v in embs])

        for j, emb in enumerate(embs):
            idx = i + j
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector={"default": emb.tolist()},
                    payload={"chunk": chunks[idx], **metadata[idx]}
                )
            )

        # upsert in smaller batches to avoid huge payloads
        client.upsert(collection_name=collection_name, points=points)
        points = []  # clear for next batch

    print("Data indexed successfully!")
    return len(chunks)
