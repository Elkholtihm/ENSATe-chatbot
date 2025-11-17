import os
from torch import chunk
from transformers import CamembertTokenizer
import numpy as np
from groq import Groq
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, HnswConfigDiff
import uuid

from langchain_core.language_models import LLM
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.chains.query_constructor.schema import AttributeInfo

from typing import Optional, List
from groq import Groq
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.document_loaders.json_loader import JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq


from langchain.llms import HuggingFaceHub


def load_and_split_json(folder_path, chunk_size=800, overlap=100):
    """
    Load .json schedules using LangChain JSONLoader and split with RecursiveCharacterTextSplitter.
    Returns: chunks list[str], metadata list[dict]
    """

    docs = []

    # Load all JSON files inside folder using DirectoryLoader
    loader = DirectoryLoader(
        folder_path,
        glob="*.json",
        loader_cls=JSONLoader,
        loader_kwargs={
            "jq_schema": ".",   # load all JSON
            "text_content": False
        }
    )

    loaded_docs = loader.load()

    # Convert JSON to readable schedule text
    converted_docs = []
    for doc in loaded_docs:
        file_name = os.path.basename(doc.metadata["source"])
        json_data = doc.page_content

        lines = []

        if isinstance(json_data, dict):
            for day, schedule in json_data.items():
                if schedule:
                    for entry in schedule:
                        entry_text = " | ".join(f"{k}: {v}" for k, v in entry.items())
                        lines.append(f"{day} | {entry_text}")

        text = "\n".join(lines).strip()

        converted_docs.append({
            "text": text,
            "metadata": {
                "name": file_name,
                "categorie": "emploi du temps",
                "source": doc.metadata["source"]
            }
        })


    # Split using LangChain splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap
    )

    chunks = []
    metadatas = []

    for d in converted_docs:
        texts = splitter.split_text(d["text"])
        for i, t in enumerate(texts, start=1):
            chunks.append(t)
            meta = d["metadata"].copy()
            meta["part"] = i
            metadatas.append(meta)

    return chunks, metadatas

def load_and_split_txt(folder_path, chunk_size=800, overlap=100):
    """
    Load all .txt files recursively with LangChain DirectoryLoader and split them.
    """

    loader = DirectoryLoader(
        folder_path,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )

    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap
    )

    chunks = []
    metadatas = []

    for doc in docs:
        texts = splitter.split_text(doc.page_content)

        category = os.path.basename(os.path.dirname(doc.metadata["source"])) or "txt"

        for i, t in enumerate(texts, start=1):
            chunks.append(t)
            metadatas.append({
                "name": f"{os.path.basename(doc.metadata['source'])} (part {i})",
                "categorie": category,
                "source": doc.metadata["source"],
                "part": i
            })

    return chunks, metadatas



os.environ["HF_HUB_TIMEOUT"] = "300"

tokenizer = CamembertTokenizer.from_pretrained("dangvantuan/sentence-camembert-base")

def normalize(vector):
    """Normalize embeddings"""
    return vector / np.linalg.norm(vector)


# -------------------------
#   Main unified search()
# -------------------------
def Search(
    query,
    client,
    collection_name,
    embedding_model,
    groq_key=None,
    mode="default",
    top_k=3
):
    """
    mode='default'  → cosine search (your current method)
    mode='self'     → Self-Query Retriever (LLM reasons over metadata)
    mode='multi'    → Multi-Query Retriever (LLM generates multiple queries)
    """

    # -------------------------
    # DEFAULT MODE (your old search)
    # -------------------------
    if mode == "default":
        query_embedding = normalize(embedding_model.encode(query))

        results = client.search(
            collection_name=collection_name,
            query_vector=("default", query_embedding),
            limit=top_k
        )

        chunks = [r.payload["chunk"] for r in results]
        context = "\n---\n".join(chunks)
        sources = [r.payload["source"] for r in results]

        return context, sources

    # -------------------------
    # LLM is required for self/multi retrievers
    # -------------------------
    if groq_key is None:
        raise ValueError("groq_key is required when using mode='self' or 'multi'")

    # Build LangChain VectorStore wrapper for Qdrant
    embedding = HuggingFaceEmbeddings(model_name="dangvantuan/sentence-camembert-base")
    vectorstore = QdrantVectorStore(
        client=client,
        embedding=embedding,
        collection_name=collection_name,
        vector_name="default",
        content_payload_key="chunk"
    )

    llm = ChatGroq(
        groq_api_key=groq_key,
        model_name="openai/gpt-oss-20b",
        temperature=0
        )

    # ------------------------------------------
    # SELF-QUERY RETRIEVER (LLM filters metadata)
    # ------------------------------------------
    if mode == "self":
        metadata_fields = [
            AttributeInfo(name="name", description="Document name", type="string"),
            AttributeInfo(name="categorie", description="Document category", type="string"),
            AttributeInfo(name="source", description="Original file path", type="string"),
            AttributeInfo(name="part", description="Chunk part number", type="integer"),
            ]
    
        self_retriever = SelfQueryRetriever.from_llm(
            llm=llm,
            vectorstore=vectorstore,
            document_contents="ENSA documents",
            metadata_field_info=metadata_fields,
            verbose=True
        )

        docs = self_retriever.invoke(query)


        chunks = [d.page_content for d in docs]
        sources = [d.metadata.get("source") for d in docs if d.metadata.get("source")]

        context = "\n---\n".join(chunks)
        return context, sources

    # ------------------------------------------
    # MULTI-QUERY RETRIEVER (LLM expands queries)
    # ------------------------------------------
    if mode == "multi":
        base_ret = vectorstore.as_retriever(search_kwargs={"k": top_k})

        multi = MultiQueryRetriever.from_llm(
            retriever=base_ret,
            llm=llm,
            include_original=True
        )
                
        docs = multi.invoke(query)

        chunks = [d.page_content for d in docs]
        sources = [d.metadata.get("source") for d in docs if d.metadata.get("source")]

        context = "\n---\n".join(chunks)
        print(f"----------------------- Multi-Query retrieved {context}")
        return context, sources

    raise ValueError("mode must be 'default', 'self', or 'multi'")


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
        model="openai/gpt-oss-safeguard-20b",
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
    chunks_json, metadata_json = load_and_split_json(json_folder)
    chunks_txt, metadata_txt = load_and_split_txt(data_path)


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
