from utils import Search, GenerationGroq
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv 
from sentence_transformers import SentenceTransformer
import json



# Load environment variables from .env file
load_dotenv()

token = os.getenv("HUGGINGFACE_TOKEN")
groq_key = os.getenv("groq_api")
# login(token)


client = QdrantClient(host= 'localhost', port = 6333)
collection_name = "ENSA_chatbot"
embedding_model = SentenceTransformer("dangvantuan/sentence-camembert-base")


if __name__ == "__main__":
    query = "parlez moi de l'emploi du temps du filiere mecatronique 2 eme annee"
    results, source = Search(query, client, collection_name, embedding_model, top_k=1) # results, source are lists

    # Ensure compatibility with Windows paths
    source = source[0].replace("\\", "/") 
    data = None  # Initialize data
    if source.endswith(".json"):
        with open(source, 'r', encoding='utf-8') as f:
            data = json.load(f)
    elif source.endswith(".txt"):
        with open(source, "r", encoding="utf-8") as f:
            data = f.read()

    GenerationGroq(query, data, groq_key, temperature=0.6, max_tokens=650)

'''
    for result in results:
        metadata = result.payload
        print(f'metadata : {metadata["chunk"]}')
        print(f'source : {result.payload["source"]}')
        
'''