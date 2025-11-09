from django.apps import AppConfig
from django.conf import settings
import os


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat_app'
    
    def ready(self):
        """Initialize chatbot components when Django starts"""
        # Import here to avoid circular imports
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
        from .utils import chunk_Embedd
        
        # Initialize components
        self.embedding_model = SentenceTransformer("dangvantuan/sentence-camembert-base")
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = settings.COLLECTION_NAME
        
        # Create collection if it doesn't exist
        try:
            collection_info = self.client.get_collection(self.collection_name)
            print(f"Collection exists: {collection_info}")
        except Exception as e:
            print(f"Creating new collection: {self.collection_name}")
            data_path = os.path.join(settings.BASE_DIR, 'data', 'data_final')
            chunk_Embedd(self.client, self.collection_name, self.embedding_model, data_path)