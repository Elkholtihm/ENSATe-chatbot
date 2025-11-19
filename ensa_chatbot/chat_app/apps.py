from django.apps import AppConfig
from django.conf import settings
import os


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat_app'
    
    def ready(self):
        """Initialize chatbot components when Django starts"""
        # Import signals to register them
        from . import models
        
        # Import here to avoid circular imports
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
        from qdrant_client.http.exceptions import ResponseHandlingException
        from .utils import chunk_Embedd
        
        try:
            print("Initializing ENSA Chatbot...")
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer("dangvantuan/sentence-camembert-base")
            print("Embedding model loaded")
            
            # Initialize Qdrant client (Cloud or Local)
            if settings.QDRANT_USE_CLOUD:
                print("Connecting to Qdrant Cloud...")
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=60
                )
                print(f"Connected to Qdrant Cloud: {settings.QDRANT_URL}")
            else:
                print("Connecting to Local Qdrant...")
                self.client = QdrantClient(
                    host=settings.QDRANT_HOST, 
                    port=settings.QDRANT_PORT
                )
                print(f"Connected to Local Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
            
            self.collection_name = settings.COLLECTION_NAME
            
            # Create or verify collection
            try:
                collection_info = self.client.get_collection(self.collection_name)
                print(f"Collection '{self.collection_name}' exists with {collection_info.points_count} points")
            except Exception as e:
                print(f"Collection not found. Creating new collection: {self.collection_name}")
                data_path = settings.DATA_DIR
                chunk_Embedd(self.client, self.collection_name, self.embedding_model, data_path)
                print("Collection created and data indexed successfully!")
        
        except ResponseHandlingException as e:
            print("=" * 70)
            print("ERROR: Cannot connect to Qdrant!")
            print("=" * 70)
            if settings.QDRANT_USE_CLOUD:
                print("Qdrant Cloud connection failed.")
                print("Check your QDRANT_URL and QDRANT_API_KEY in .env file")
            else:
                print("Local Qdrant is not running. Start it with:")
                print("  docker run -d -p 6333:6333 --name qdrant qdrant/qdrant")
            print("=" * 70)
            
            # Set to None so views can check
            self.client = None
            self.embedding_model = None
            self.collection_name = None
            
        except Exception as e:
            print(f"Error initializing chatbot: {str(e)}")
            import traceback
            traceback.print_exc()
            
            self.client = None
            self.embedding_model = None
            self.collection_name = None