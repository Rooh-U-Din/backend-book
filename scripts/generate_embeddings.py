#!/usr/bin/env python3
"""
Embedding Generation Script for Book Content

Reads MDX/MD files from docs directory, chunks them with section-awareness,
generates embeddings using Gemini API, and uploads to Qdrant.

Author: Physical AI & Humanoid Robotics Course
License: MIT
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import List, Dict, Tuple
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

load_dotenv()


class BookEmbeddingGenerator:
    """Generates embeddings for book content and uploads to Qdrant"""

    def __init__(self, docs_dir: str, collection_name: str = "book-embeddings"):
        self.docs_dir = Path(docs_dir)
        self.collection_name = collection_name

        # Initialize Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")

        genai.configure(api_key=api_key)
        self.embedding_model = 'models/embedding-001'

        # Initialize Qdrant client
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if not qdrant_url or not qdrant_api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set")

        self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

        # Create collection if not exists (768 dimensions for Gemini embeddings)
        self._ensure_collection()

    def _ensure_collection(self):
        """Create Qdrant collection if it doesn't exist"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                print(f"Creating collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Gemini embedding-001 dimensions
                        distance=Distance.COSINE
                    )
                )
                print("✓ Collection created")
            else:
                print(f"✓ Collection '{self.collection_name}' already exists")
        except Exception as e:
            print(f"Error creating collection: {e}")
            raise

    def extract_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """Extract YAML frontmatter from MDX file"""
        frontmatter = {}
        body = content

        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                # Parse simple YAML (just key: value)
                fm_text = parts[1].strip()
                for line in fm_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip().strip('"\'')
                body = parts[2].strip()

        return frontmatter, body

    def chunk_content(
        self,
        content: str,
        chapter_id: str,
        chapter_title: str,
        url_path: str,
        chunk_size: int = 800,
        overlap: int = 100
    ) -> List[Dict]:
        """
        Chunk content with section-awareness

        Args:
            content: Markdown/MDX content
            chapter_id: Chapter identifier
            chapter_title: Human-readable title
            url_path: URL path to chapter
            chunk_size: Target chunk size in characters (~500-1000 tokens)
            overlap: Overlap between chunks

        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []

        # Split by headings (## or ###)
        sections = re.split(r'\n(#{2,3})\s+(.+)\n', content)

        current_section = "Introduction"
        current_text = ""
        chunk_index = 0

        for i, part in enumerate(sections):
            # Check if this is a heading marker
            if part.startswith('##'):
                # Save previous section if it has content
                if current_text.strip():
                    section_chunks = self._split_text(
                        current_text,
                        chunk_size,
                        overlap
                    )

                    for chunk_text in section_chunks:
                        chunks.append({
                            "text": chunk_text,
                            "metadata": {
                                "chapter_id": chapter_id,
                                "chapter_title": chapter_title,
                                "section_title": current_section,
                                "url_path": url_path,
                                "chunk_index": chunk_index,
                                "token_count": len(chunk_text.split()),  # Rough estimate
                                "created_at": datetime.utcnow().isoformat()
                            }
                        })
                        chunk_index += 1

                # Start new section
                if i + 1 < len(sections):
                    current_section = sections[i + 1].strip()
                    current_text = ""
            else:
                current_text += part

        # Process last section
        if current_text.strip():
            section_chunks = self._split_text(current_text, chunk_size, overlap)
            for chunk_text in section_chunks:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "chapter_id": chapter_id,
                        "chapter_title": chapter_title,
                        "section_title": current_section,
                        "url_path": url_path,
                        "chunk_index": chunk_index,
                        "token_count": len(chunk_text.split()),
                        "created_at": datetime.utcnow().isoformat()
                    }
                })
                chunk_index += 1

        return chunks

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('. ')
                if last_period > chunk_size // 2:
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if len(c.strip()) > 50]  # Filter very small chunks

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini API"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise

    def process_file(self, file_path: Path) -> int:
        """Process a single MDX/MD file"""
        print(f"\nProcessing: {file_path}")

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter
        frontmatter, body = self.extract_frontmatter(content)

        # Determine chapter info
        relative_path = file_path.relative_to(self.docs_dir)
        chapter_id = str(relative_path).replace('\\', '/').replace('.mdx', '').replace('.md', '')
        chapter_title = frontmatter.get('title', file_path.stem.replace('-', ' ').title())
        url_path = f"/docs/{chapter_id}"

        # Chunk content
        chunks = self.chunk_content(body, chapter_id, chapter_title, url_path)
        print(f"  Created {len(chunks)} chunks")

        # Generate embeddings and upload
        points = []
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = self.generate_embedding(chunk['text'])

            # Create Qdrant point
            point = PointStruct(
                id=f"{chapter_id}-{i}",
                vector=embedding,
                payload={
                    **chunk['metadata'],
                    'chunk_text': chunk['text']
                }
            )
            points.append(point)

            # Rate limiting (Gemini API has limits)
            if i > 0 and i % 10 == 0:
                print(f"  Processed {i}/{len(chunks)} chunks...")
                time.sleep(1)  # Avoid rate limits

        # Upload to Qdrant in batch
        print(f"  Uploading {len(points)} points to Qdrant...")
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"✓ Completed: {file_path.name} ({len(chunks)} chunks)")
        return len(chunks)

    def process_directory(self, batch_size: int = 100) -> Dict:
        """Process all MDX/MD files in docs directory"""
        print(f"Scanning directory: {self.docs_dir}")

        # Find all .mdx and .md files
        md_files = list(self.docs_dir.rglob("*.md"))
        mdx_files = list(self.docs_dir.rglob("*.mdx"))
        all_files = md_files + mdx_files

        print(f"Found {len(all_files)} files to process\n")

        total_chunks = 0
        processed_files = 0

        for file_path in all_files:
            try:
                chunks = self.process_file(file_path)
                total_chunks += chunks
                processed_files += 1
            except Exception as e:
                print(f"✗ Error processing {file_path}: {e}")

        return {
            "total_files": len(all_files),
            "processed_files": processed_files,
            "total_chunks": total_chunks,
            "collection_name": self.collection_name
        }


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for book content")
    parser.add_argument(
        '--docs-dir',
        type=str,
        default='../../docs',
        help='Path to docs directory'
    )
    parser.add_argument(
        '--collection-name',
        type=str,
        default='book-embeddings',
        help='Qdrant collection name'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for Qdrant uploads'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Book Embedding Generation Script")
    print("=" * 60)

    try:
        generator = BookEmbeddingGenerator(
            docs_dir=args.docs_dir,
            collection_name=args.collection_name
        )

        result = generator.process_directory(batch_size=args.batch_size)

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total files found:     {result['total_files']}")
        print(f"Files processed:       {result['processed_files']}")
        print(f"Total chunks created:  {result['total_chunks']}")
        print(f"Collection:            {result['collection_name']}")
        print("=" * 60)
        print("✓ Embedding generation complete!")

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
