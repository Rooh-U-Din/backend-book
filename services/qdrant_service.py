"""
Qdrant client wrapper for vector search operations (Cloud-compatible)
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Optional
import os
import uuid

# Disable local Qdrant usage (important for cloud deployments like Railway)
os.environ["QDRANT_DISABLE_LOCAL"] = "true"


class QdrantService:
    """Manages Qdrant vector database operations"""

    def __init__(self):
        self.url = os.getenv("QDRANT_URL")
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = "book-embeddings"

        if not self.url or not self.api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set")

        # Initialize remote Qdrant client
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=30
        )

    def create_collection(self, vector_size: int = 1536):
        """Create the book embeddings collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"Created collection: {self.collection_name}")
            else:
                print(f"Collection {self.collection_name} already exists")
        except Exception as e:
            print(f"Error creating collection: {e}")
            raise

    def upsert_chunks(self, chunks: List[dict]):
        """Upsert book chunks into Qdrant"""
        points = [
            PointStruct(
                id=chunk.get("id", str(uuid.uuid4())),
                vector=chunk["vector"],
                payload=chunk["payload"]
            )
            for chunk in chunks
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        chapter_filter: Optional[str] = None
    ) -> List[dict]:
        """Search for similar chunks"""
        query_filter = None
        if chapter_filter:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="chapter_id",
                        match=MatchValue(value=chapter_filter)
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter
        )

        return [
            {
                "id": str(result.id),
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]

    async def health_check(self) -> bool:
        """Check Qdrant connectivity"""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            print(f"Qdrant health check failed: {e}")
            return False

    def close(self):
        """Close Qdrant client connection"""
        self.client.close()


# Global Qdrant service instance
qdrant_service: QdrantService | None = None


def get_qdrant_service() -> QdrantService:
    """Get or create the global Qdrant service instance"""
    global qdrant_service
    if qdrant_service is None:
        qdrant_service = QdrantService()
    return qdrant_service
