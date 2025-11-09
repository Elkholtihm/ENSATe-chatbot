import os
import json
from transformers import CamembertTokenizer
import numpy as np
from groq import Groq
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, HnswConfigDiff
import uuid

os.environ["HF_HUB_TIMEOUT"] = "300"

tokenizer = CamembertTokenizer.from_pretrained("dangvantuan/sentence-camembert-base")


def chunking_json_files(folder_path):
    """Create chunks from JSON schedule files"""
    chunks = []
    metadata = []
    
    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            file_path = os.path.join(folder_path, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunk = f'{file} : '
            for day, schedule in data.items():
                chunk += f' | {day} : '
                
                for entry in schedule:
                    entry_text = " | ".join([f"{k}: {v}" for k, v in entry.items()])
                    chunk += f' {entry_text} ;'
            
            tokens = tokenizer.encode(chunk)
            counter = 1
            if len(tokens) <= 512:
                chunks.append(tokenizer.decode(tokens))
                metadata.append({'name': file, 'categorie': 'emploie du temps', 'source': file_path})
            else:
                while len(tokens) > 512:
                    context = f"c'est le reste du document {file} (partie {counter}) :"
                    context_tokens = tokenizer.encode(context)
                    tokens_split = tokens[:512 - len(context_tokens)]
                    chunks.append(f"{context}" + tokenizer.decode(tokens_split))
                    tokens = tokens[512 - len(context_tokens):]
                    counter += 1
                    metadata.append({'name': f"{file} (partie {counter})", 'categorie': 'emploie du temps', 'source': file_path})
                
                if tokens:
                    context = f"c'est le reste du document {file} (partie {counter}) :"
                    context_tokens = tokenizer.encode(context)
                    if len(tokens) + len(context_tokens) <= 512:
                        chunks.append(f"{context}" + tokenizer.decode(tokens))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': 'emploie du temps', 'source': file_path})
                    else:
                        tokens_split = tokens[:512 - len(context_tokens)]
                        chunks.append(f"{context}" + tokenizer.decode(tokens_split))
                        tokens = tokens[512 - len(context_tokens):]
                        counter += 1
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': 'emploie du temps', 'source': file_path})
                        context = f"c'est le reste du document {file} (partie {counter}) :"
                        chunks.append(f"{context}" + tokenizer.decode(tokens))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': 'emploie du temps', 'source': file_path})
    
    return chunks, metadata


def chunking_txt_files(folder_path):
    """Chunking TXT files"""
    chunks = []
    metadata = []
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.txt'):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as infile:
                    data = infile.read()
                
                chunk = data.strip()
                category = os.path.basename(root)
            
                tokens = tokenizer.encode(chunk)
                counter = 1
                while len(tokens) > 512:
                    context = f"c'est le reste du document {file} (partie {counter}) :"
                    context_tokens = tokenizer.encode(context)
                    tokens_split = tokens[:512 - len(context_tokens)]
                    chunks.append(f"{context}" + tokenizer.decode(tokens_split))
                    metadata.append({'name': f"{file} (partie {counter})", 'categorie': f'{category}', 'source': file_path})
                    tokens = tokens[512 - len(context_tokens):]
                    counter += 1
                
                if tokens:
                    context = f"c'est le reste du document {file} (partie {counter}) :"
                    context_tokens = tokenizer.encode(context)
                    if len(tokens) + len(context_tokens) <= 512:
                        chunks.append(f"{context}" + tokenizer.decode(tokens))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': f'{category}', 'source': file_path})
                    else:
                        tokens_split = tokens[:512 - len(context_tokens)]
                        chunks.append(f"{context}" + tokenizer.decode(tokens_split))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': f'{category}', 'source': file_path})
                        tokens = tokens[512 - len(context_tokens):]
                        counter += 1
                        context = f"c'est le reste du document {file} (partie {counter}) :"
                        chunks.append(f"{context}" + tokenizer.decode(tokens))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': f'{category}', 'source': file_path})
    
    return chunks, metadata


def normalize(vector):
    """Normalize embeddings"""
    return vector / np.linalg.norm(vector)


def Search(query, client, collection_name, embedding_model, top_k=1):
    """Retrieve data from Qdrant"""
    query_embedding = normalize(embedding_model.encode(query))

    results = client.search(
        collection_name=collection_name,
        query_vector=("default", query_embedding), 
        limit=top_k
    )
    chunks = []
    document_path = []
    for result in results:
        metadata = result.payload
        chunks.append(metadata["chunk"])
        document_path.append(result.payload["source"])

    if top_k == 1:
        return results, document_path
    else:
        return results


def GenerationGroq(query, search_results, groq_key, temperature=0.6, max_tokens=650):
    """Generate response using Groq API"""
    client = Groq(api_key=groq_key)

    prompt = f"""
    Vous êtes un assistant utile. Utilisez le contexte suivant pour répondre à la question de l'utilisateur (reponse en francais). Si vous ne connaissez pas la réponse, dites simplement que vous ne savez pas.
    si le context ne coresspond pas au question dit a l'utlisateur de donner plus de contexte.

    Contexte:
    {search_results}

    Question:
    {query}

    Réponse:
    """

    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{'role': 'user', 'content': f'''{prompt}'''}],
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=1,
        stream=True,
        stop=None,
    )
    
    generations = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            generations += chunk.choices[0].delta.content
    
    return generations


def chunk_Embedd(client, collection_name, embedding_model, data_path):
    """Chunk and embed data, then store in Qdrant"""
    # Chunk json files
    json_folder = os.path.join(data_path, "emploi-temps")
    chunks_json, metadata_json = chunking_json_files(json_folder)

    # Chunk txt files
    chunks_txt, metadata_txt = chunking_txt_files(data_path)

    chunks = chunks_json + chunks_txt
    metadata = metadata_json + metadata_txt

    print(f"Number of chunks: {len(chunks)}")
    print(f"Number of metadata: {len(metadata)}")

    # Embedding
    embeddings = embedding_model.encode(chunks, convert_to_numpy=True)
    embeddings = np.array([normalize(vec) for vec in embeddings])

    # Create Qdrant points
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector={"default": embeddings[i].tolist()},
            payload={"chunk": chunks[i], **metadata[i]}
        )
        for i in range(len(chunks))
    ]

    # Create collection
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "default": VectorParams(size=embedding_model.get_sentence_embedding_dimension(), distance=Distance.DOT)
        },
        hnsw_config=HnswConfigDiff(ef_construct=300)
    )

    # Upsert points
    client.upsert(collection_name=collection_name, points=points)
    print("Data indexed successfully!")