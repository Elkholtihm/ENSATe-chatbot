from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct ,VectorParams, Distance, HnswConfigDiff
import numpy as np
import uuid
from utils import chunking_json_files, chunking_txt_files, normalize


# chunk json files
folder_path = r"data\data_final\emploi-temps"
chunks_json, metadata_json = chunking_json_files(folder_path)

# chunk txt files
folder_path = r"data\data_final"
chunks_txt, metadata_txt = chunking_txt_files(folder_path)  

chunks = chunks_json + chunks_txt
metadata = metadata_json + metadata_txt

print(f"Number of chunks: {len(chunks)}")
print(f"Number of metadata: {len(metadata)}")



# -----------------Embedding-----------------
embedding_model = SentenceTransformer("dangvantuan/sentence-camembert-base")
embeddings = embedding_model.encode(chunks, convert_to_numpy=True)
embeddings = np.array([normalize(vec) for vec in embeddings])

# -----------------Qdrant-----------------
client = QdrantClient(host= 'localhost', port = 6333)
points = [
    PointStruct(
        id=str(uuid.uuid4()),
        vector={"default": embeddings[i].tolist()},
        payload={"chunk": chunks[i], **metadata[i]}
    )
    for i in range(len(chunks))
]

# Create collection (if not exists)
collection_name = "ENSA_chatbot"
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


#-----------------Search--------------------------
query = "parlez moi de l'emploi du temps du filiere mecatronique 2 eme annee"
query_embedding = normalize(embedding_model.encode(query))

results = client.search(
    collection_name=collection_name,
    query_vector=("default", query_embedding), 
    limit=1
)

for result in results:
    metadata = result.payload
    print(f'metadata : {metadata["chunk"]}')
    print(f'source : {result.payload["source"]}')
