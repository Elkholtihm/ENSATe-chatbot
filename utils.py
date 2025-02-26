import os
import json
from transformers import AutoTokenizer, pipeline, CamembertTokenizer
import numpy as np
from groq import Groq

os.environ["HF_HUB_TIMEOUT"] = "300"  # Increase to 5 minutes

tokenizer = CamembertTokenizer.from_pretrained("dangvantuan/sentence-camembert-base")

# ------------------------------------------------chunking the data------------------------------------------------
# Create chunks from JSON schedule files
def chunking_json_files(folder_path):
    chunks = []
    metadata = []
    
    for file in os.listdir(folder_path):
        if file.endswith(".json"):  # Ensure only JSON files are processed
            file_path = os.path.join(folder_path, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunk = f'{file} : '  # Store file name as metadata
            for day, schedule in data.items():
                chunk += f' | {day} : '  # Add day to chunk
                
                for entry in schedule:
                    entry_text = " | ".join([f"{k}: {v}" for k, v in entry.items()])
                    chunk += f' {entry_text} ;'  # Append schedule details
            
             # split the chunk into smaller chunks of 512 tokens if it exceeds the limit
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
                
                # Add the remaining tokens as the last chunk if they fit within 512 tokens with context
                if tokens:
                    context = f"c'est le reste du document {file} (partie {counter}) :"
                    context_tokens = tokenizer.encode(context)
                    if len(tokens) + len(context_tokens) <= 512:
                        chunks.append(f"{context}" + tokenizer.decode(tokens))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': 'emploie du temps', 'source': file_path})
                    else:
                        # Split the remaining tokens if they don't fit within 512 tokens with context
                        tokens_split = tokens[:512 - len(context_tokens)]
                        chunks.append(f"{context}" + tokenizer.decode(tokens_split))
                        tokens = tokens[512 - len(context_tokens):]
                        counter += 1
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': 'emploie du temps', 'source': file_path})
                        context = f"c'est le reste du document {file} (partie {counter}) :"
                        chunks.append(f"{context}" + tokenizer.decode(tokens))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': 'emploie du temps', 'source': file_path})
    
    return chunks, metadata


# Chunking TXT files
def chunking_txt_files(folder_path):
    chunks = []
    metadata = []
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.txt'):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as infile:
                    data = infile.read()  # Read entire file
                
                # Store the full text as a single chunk
                chunk = data.strip()

                # Extract category from parent directory name
                category = os.path.basename(root)  
            
                # Split the chunk into smaller chunks of 512 tokens if it exceeds the limit
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
                
                # Add the remaining tokens as the last chunk if they fit within 512 tokens with context
                if tokens:
                    context = f"c'est le reste du document {file} (partie {counter}) :"
                    context_tokens = tokenizer.encode(context)
                    if len(tokens) + len(context_tokens) <= 512:
                        chunks.append(f"{context}" + tokenizer.decode(tokens))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': f'{category}', 'source': file_path})
                    else:
                        # Split the remaining tokens if they don't fit within 512 tokens with context
                        tokens_split = tokens[:512 - len(context_tokens)]
                        chunks.append(f"{context}" + tokenizer.decode(tokens_split))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': f'{category}', 'source': file_path})
                        tokens = tokens[512 - len(context_tokens):]
                        counter += 1
                        context = f"c'est le reste du document {file} (partie {counter}) :"
                        chunks.append(f"{context}" + tokenizer.decode(tokens))
                        metadata.append({'name': f"{file} (partie {counter})", 'categorie': f'{category}', 'source': file_path})
    
    return chunks, metadata



# Normalize embeddings
def normalize(vector):
    return vector / np.linalg.norm(vector)

# this function is used for retriving data from Qdrant
def Search(query, client, collection_name, embedding_model, top_k=1):
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
#-----------------generation--------------------------
# using a generation model-----
def Generation(query, serch_results, model_name= 'HuggingFaceH4/zephyr-7b-alpha', max_new_tokens= 150, num_return_sequences = 1, temperature=0.7):
    generator = pipeline('text-generation', model=model_name, device_map="auto")

    if serch_results:
        context = serch_results[0].payload["chunk"]
        prompt = f"Contexte: {context}\nQuestion: {query}\nRéponse:"

        response = generator(prompt, max_new_tokens=max_new_tokens, num_return_sequences=num_return_sequences, temperature=temperature)
        print(f"Réponse générée : {response[0]['generated_text'].split('Réponse:')[-1].strip()}")
    else:
        print("Aucun résultat trouvé.")


# using groq API-----
def GenerationGroq(query, serch_results, groq_key, temperature=0.6,max_tokens=650 ):
    client = Groq(api_key=groq_key)

    prompt = f"""
    Vous êtes un assistant utile. Utilisez le contexte suivant pour répondre à la question de l'utilisateur (reponse en francais). Si vous ne connaissez pas la réponse, dites simplement que vous ne savez pas.

    Contexte:
    {serch_results}

    Question:
    {query}

    Réponse:
    """

    # Get the email content
    completion = client.chat.completions.create(
        model="gemma2-9b-it",
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
    print(f"Réponse générée : {generations}")