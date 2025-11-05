"""
Document processing service with optimized batching for TEI and Qdrant.

This service handles embedding generation and vector storage for all document sources
(scrape, search, extract, crawl) with intelligent batching based on TEI limits.
"""

import hashlib
import asyncio
import logging
from datetime import datetime, UTC
from typing import Dict, Any, List
from app.dependencies import get_embeddings_service, get_vector_db_service

logger = logging.getLogger(__name__)

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
            
    Raises:
        RuntimeError: If services not initialized or embedding/storage fails
    """
    if not documents:
        return

    # Get initialized singleton services via dependency injection
    embeddings_service = get_embeddings_service()
    vector_db_service = get_vector_db_service()
    
    # Validate services are initialized
    if vector_db_service.client is None:
        raise RuntimeError(
            "VectorDBService not initialized. Call initialize() first or ensure app is started."
        )

    # Filter out empty documents
    valid_docs = [doc for doc in documents if doc.get("content") and doc.get("source_url")]

    if not valid_docs:
        logger.info("No valid documents to process")
        return

    logger.info(f"Processing {len(valid_docs)} document(s)...")

    try:
        # Add doc IDs and metadata
        for doc in valid_docs:
            doc["doc_id"] = hashlib.md5(doc["source_url"].encode()).hexdigest()
            if "metadata" not in doc:
                doc["metadata"] = {}
            doc["metadata"]["source_type"] = doc["source_type"]
            doc["metadata"]["indexed_at"] = datetime.now(UTC).isoformat()

        # Split into batches of 80 documents (TEI max-batch-requests)
        batches = [
            valid_docs[i : i + MAX_BATCH_SIZE] for i in range(0, len(valid_docs), MAX_BATCH_SIZE)
        ]

        if len(batches) > 1:
            logger.info(f"Split into {len(batches)} batch(es) of up to {MAX_BATCH_SIZE} documents")

        # Process batches in parallel (with concurrency limit)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

        async def process_batch(batch: List[Dict[str, Any]], batch_num: int):
            async with semaphore:
                batch_size = len(batch)
                if len(batches) > 1:
                    logger.info(
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
                    logger.info(f"✓ Batch {batch_num + 1}/{len(batches)} stored ({batch_size} documents)")

        # Process all batches in parallel
        await asyncio.gather(*[process_batch(batch, i) for i, batch in enumerate(batches)])

        logger.info(f"✓ Successfully stored {len(valid_docs)} document(s)")

    except RuntimeError as e:
        # Service initialization errors - fail fast
        logger.error(
            f"Failed to process documents batch: Service initialization error: {str(e)}",
            exc_info=True,
            extra={"document_count": len(documents)},
        )
        raise
    except Exception as e:
        # All other errors - log and fail fast
        logger.error(
            f"Failed to process documents batch: {str(e)}",
            exc_info=True,
            extra={"document_count": len(documents), "valid_document_count": len(valid_docs)},
        )
        raise


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
