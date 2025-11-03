"""
Document processing service with optimized batching for TEI and Qdrant.

This service handles embedding generation and vector storage for all document sources
(scrape, search, extract, crawl) with intelligent batching based on TEI limits.
"""

import hashlib
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import VectorDBService

embeddings_service = EmbeddingsService()
vector_db_service = VectorDBService()

# TEI Configuration Limits (from docker-compose.yaml)
# --max-batch-requests: 80
# --max-batch-tokens: 163840
# --max-client-batch-size: 128
MAX_BATCH_SIZE = 80  # Optimal batch size matching TEI max-batch-requests
MAX_CONCURRENT_BATCHES = 10  # Limit parallel batch processing


async def process_and_store_documents_batch(documents: List[Dict[str, Any]]):
    """
    Process and store multiple documents in optimized batches.

    Automatically splits large document sets into TEI-optimized batches of 80.
    Processes multiple batches in parallel for maximum throughput.

    Performance:
    - Single document: ~100ms
    - 10 documents (1 batch): ~150ms
    - 200 documents (3 batches in parallel): ~2-3s

    Args:
        documents: List of dicts with keys:
            - content: str (text content to embed)
            - source_url: str (source URL of document)
            - metadata: dict (additional metadata)
            - source_type: str (scrape/search/extract/crawl)
    """
    if not documents:
        return

    try:
        # Filter out empty documents
        valid_docs = [doc for doc in documents if doc.get("content") and doc.get("source_url")]

        if not valid_docs:
            print("No valid documents to process")
            return

        print(f"Processing {len(valid_docs)} document(s)...")

        # Add doc IDs and metadata
        for doc in valid_docs:
            doc["doc_id"] = hashlib.md5(doc["source_url"].encode()).hexdigest()
            if "metadata" not in doc:
                doc["metadata"] = {}
            doc["metadata"]["source_type"] = doc["source_type"]
            doc["metadata"]["indexed_at"] = datetime.utcnow().isoformat()

        # Split into batches of 80 documents (TEI max-batch-requests)
        batches = [
            valid_docs[i : i + MAX_BATCH_SIZE] for i in range(0, len(valid_docs), MAX_BATCH_SIZE)
        ]

        if len(batches) > 1:
            print(f"Split into {len(batches)} batch(es) of up to {MAX_BATCH_SIZE} documents")

        # Process batches in parallel (with concurrency limit)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

        async def process_batch(batch: List[Dict[str, Any]], batch_num: int):
            async with semaphore:
                batch_size = len(batch)
                if len(batches) > 1:
                    print(
                        f"Processing batch {batch_num + 1}/{len(batches)} ({batch_size} documents)..."
                    )

                # Generate embeddings for this batch (ONE TEI API call)
                contents = [doc["content"] for doc in batch]
                embeddings = await embeddings_service.generate_embeddings(contents)

                # Add embeddings to documents
                for doc, embedding in zip(batch, embeddings):
                    doc["embedding"] = embedding

                # Upsert batch to Qdrant (ONE Qdrant API call)
                await vector_db_service.upsert_documents(batch)

                if len(batches) > 1:
                    print(f"✓ Batch {batch_num + 1}/{len(batches)} stored ({batch_size} documents)")

        # Process all batches in parallel
        await asyncio.gather(*[process_batch(batch, i) for i, batch in enumerate(batches)])

        print(f"✓ Successfully stored {len(valid_docs)} document(s)")

    except Exception as e:
        print(f"✗ Failed to batch store documents: {str(e)}")
        import traceback

        traceback.print_exc()


async def process_and_store_document(
    content: str, source_url: str, metadata: Dict[str, Any], source_type: str
):
    """
    Process and store a single document.

    Delegates to batch processor for consistency and code reuse.

    Args:
        content: Text content to embed and store
        source_url: Source URL of the document
        metadata: Additional metadata to store with the document
        source_type: Type of operation (scrape/search/extract/crawl)
    """
    await process_and_store_documents_batch(
        [
            {
                "content": content,
                "source_url": source_url,
                "metadata": metadata,
                "source_type": source_type,
            }
        ]
    )
