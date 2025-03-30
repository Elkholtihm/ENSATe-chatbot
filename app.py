from flask import Flask, render_template, request, jsonify
import os
from utils import Search, GenerationGroq, chunk_Embedd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv 
from sentence_transformers import SentenceTransformer
import json

# Load environment variables
load_dotenv()

# Initialize Flask with explicit template folder
app = Flask(__name__, template_folder='templates')

# Initialize components
token = os.getenv("HUGGINGFACE_TOKEN")
groq_key = os.getenv("groq_api")
embedding_model = SentenceTransformer("dangvantuan/sentence-camembert-base")
collection_name = "ENSA_chatbot"

# Initialize Qdrant client and create collection if needed
client = QdrantClient(host='localhost', port=6333)

# Create collection if it doesn't exist
try:
    collection_info = client.get_collection(collection_name)
    print(f"Collection exists: {collection_info}")
except Exception as e:
    print(f"Creating new collection: {collection_name}")
    chunk_Embedd(client, collection_name, embedding_model)


@app.route('/')
def index():
    return render_template('base.html')

@app.route('/query', methods=['POST'])
def handle_query():
    try:
        query = request.json.get('query')
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        # Perform search
        results, sources = Search(query, client, collection_name, embedding_model, top_k=1)
        print("Found sources:", sources)
        
        # Process sources
        source_data = []
        for source in sources:
            source = source.replace("\\", "/")
            try:
                if source.endswith(".json"):
                    with open(source, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                elif source.endswith(".txt"):
                    with open(source, "r", encoding="utf-8") as f:
                        data = f.read()
                source_data.append(data)
            except Exception as e:
                print(f"Error loading source {source}: {str(e)}")
                continue
        
        print("Source data:", source_data)
        
        # Generate response
        if source_data:
            response = GenerationGroq(query, source_data[0], groq_key, temperature=0.6, max_tokens=650)
            print("Generated response:", response)
            
            if response is None:
                raise ValueError("GenerationGroq returned None response")
                
            formatted_response = f"{response}\n\nSources: {', '.join(sources)}"
            return jsonify({
                "response": formatted_response,
                "sources": sources
            })
        else:
            return jsonify({
                "response": "Désolé, je n'ai pas trouvé d'informations pertinentes pour répondre à votre question.",
                "sources": []
            })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    app.run(debug=True)