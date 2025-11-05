"""
Tests for document_processor service.

TDD: These tests are written FIRST to verify proper dependency injection
and error handling in the document processing pipeline.

RED: These tests will FAIL with the current implementation because:
1. document_processor uses module-level services (not initialized)
2. document_processor uses print() instead of logger
3. document_processor swallows exceptions with bare except

GREEN: After fixing, these tests will PASS.
"""

import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch, call
from typing import List, Dict, Any

from app.services.document_processor import (
    process_and_store_document,
    process_and_store_documents_batch,
)


class TestDocumentProcessorInitialization:
    """Test that document_processor uses properly initialized services."""

    @pytest.mark.asyncio
    async def test_uses_dependency_injection_for_embeddings(self):
        """
        RED TEST: Verify document_processor uses get_embeddings_service().
        
        Current code FAILS: Uses module-level embeddings_service
        Expected: Should call get_embeddings_service() to get initialized singleton
        """
        # Mock the dependency injection function
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [[0.1] * 1024]
        
        mock_vector_db_service = AsyncMock()
        
        with patch('app.services.document_processor.get_embeddings_service', 
                   return_value=mock_embeddings_service) as mock_get_embeddings:
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service):
                
                # Process a document
                await process_and_store_document(
                    content="test content",
                    source_url="https://example.com/test",
                    metadata={},
                    source_type="test"
                )
                
                # VERIFY: Should have called get_embeddings_service() to get the singleton
                mock_get_embeddings.assert_called_once()
                
                # VERIFY: Should have used the injected service
                mock_embeddings_service.generate_embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_dependency_injection_for_vector_db(self):
        """
        RED TEST: Verify document_processor uses get_vector_db_service().
        
        Current code FAILS: Uses module-level vector_db_service
        Expected: Should call get_vector_db_service() to get initialized singleton
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [[0.1] * 1024]
        
        mock_vector_db_service = AsyncMock()
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service) as mock_get_vector_db:
                
                # Process a document
                await process_and_store_document(
                    content="test content",
                    source_url="https://example.com/test",
                    metadata={},
                    source_type="test"
                )
                
                # VERIFY: Should have called get_vector_db_service() to get the singleton
                mock_get_vector_db.assert_called_once()
                
                # VERIFY: Should have used the injected service
                mock_vector_db_service.upsert_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_processing_uses_dependency_injection(self):
        """
        RED TEST: Verify batch processor uses dependency injection.
        
        Current code FAILS: Uses module-level services
        Expected: Should get services via dependency injection
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [
            [0.1] * 1024,
            [0.2] * 1024,
        ]
        
        mock_vector_db_service = AsyncMock()
        
        documents = [
            {
                "content": "doc 1",
                "source_url": "https://example.com/1",
                "metadata": {},
                "source_type": "test",
            },
            {
                "content": "doc 2",
                "source_url": "https://example.com/2",
                "metadata": {},
                "source_type": "test",
            },
        ]
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service) as mock_get_embeddings:
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service) as mock_get_vector_db:
                
                await process_and_store_documents_batch(documents)
                
                # VERIFY: Both services obtained via dependency injection
                mock_get_embeddings.assert_called_once()
                mock_get_vector_db.assert_called_once()


class TestDocumentProcessorLogging:
    """Test that document_processor uses proper logging instead of print()."""

    @pytest.mark.asyncio
    async def test_uses_logger_not_print_for_info(self, caplog):
        """
        RED TEST: Verify logger.info() is used instead of print().
        
        Current code FAILS: Uses print(f"Processing {len(valid_docs)} document(s)...")
        Expected: Should use logger.info()
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [[0.1] * 1024]
        
        mock_vector_db_service = AsyncMock()
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service):
                
                with caplog.at_level(logging.INFO):
                    await process_and_store_document(
                        content="test",
                        source_url="https://example.com",
                        metadata={},
                        source_type="test",
                    )
                
                # VERIFY: Should have logged via logger, not print()
                assert any("Processing 1 document" in record.message 
                          for record in caplog.records), \
                    "Expected logger.info() for processing message"
                assert any("Successfully stored 1 document" in record.message 
                          for record in caplog.records), \
                    "Expected logger.info() for success message"

    @pytest.mark.asyncio
    async def test_uses_logger_for_errors_with_exc_info(self, caplog):
        """
        RED TEST: Verify logger.error() with exc_info=True is used.
        
        Current code FAILS: Uses print() and traceback.print_exc()
        Expected: Should use logger.error(..., exc_info=True)
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.side_effect = Exception("TEI failure")
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=AsyncMock()):
                
                with caplog.at_level(logging.ERROR):
                    # Should NOT swallow the exception
                    with pytest.raises(Exception, match="TEI failure"):
                        await process_and_store_document(
                            content="test",
                            source_url="https://example.com",
                            metadata={},
                            source_type="test",
                        )
                
                # VERIFY: Error was logged with traceback
                assert any("Failed to process document" in record.message 
                          for record in caplog.records), \
                    "Expected logger.error() for failure"
                
                # VERIFY: Stack trace was logged (exc_info=True)
                assert any(record.exc_info is not None 
                          for record in caplog.records), \
                    "Expected exc_info=True in logger.error()"

    @pytest.mark.asyncio
    async def test_no_print_statements_in_processing(self, capsys):
        """
        RED TEST: Verify NO print() statements are used.
        
        Current code FAILS: Uses print() for all output
        Expected: Should use logger only, no print()
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [[0.1] * 1024]
        
        mock_vector_db_service = AsyncMock()
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service):
                
                await process_and_store_document(
                    content="test",
                    source_url="https://example.com",
                    metadata={},
                    source_type="test",
                )
                
                # VERIFY: No print() output
                captured = capsys.readouterr()
                assert captured.out == "", \
                    f"Expected no print() output, but got: {captured.out}"


class TestDocumentProcessorErrorHandling:
    """Test that document_processor fails fast and doesn't swallow errors."""

    @pytest.mark.asyncio
    async def test_raises_exception_on_embedding_failure(self):
        """
        RED TEST: Verify exceptions are raised, not swallowed.
        
        Current code FAILS: Uses except Exception: print() - swallows errors
        Expected: Should raise exceptions to fail fast
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.side_effect = \
            RuntimeError("TEI service unavailable")
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=AsyncMock()):
                
                # VERIFY: Exception should be raised, not swallowed
                with pytest.raises(RuntimeError, match="TEI service unavailable"):
                    await process_and_store_document(
                        content="test",
                        source_url="https://example.com",
                        metadata={},
                        source_type="test",
                    )

    @pytest.mark.asyncio
    async def test_raises_exception_on_vector_db_failure(self):
        """
        RED TEST: Verify vector DB errors are raised.
        
        Current code FAILS: Swallows exceptions
        Expected: Should raise to fail fast
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [[0.1] * 1024]
        
        mock_vector_db_service = AsyncMock()
        mock_vector_db_service.upsert_documents.side_effect = \
            RuntimeError("Qdrant connection failed")
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service):
                
                # VERIFY: Exception should be raised
                with pytest.raises(RuntimeError, match="Qdrant connection failed"):
                    await process_and_store_document(
                        content="test",
                        source_url="https://example.com",
                        metadata={},
                        source_type="test",
                    )

    @pytest.mark.asyncio
    async def test_raises_exception_for_uninitialized_services(self):
        """
        RED TEST: Verify clear error when services not initialized.
        
        Current code FAILS: Would raise AttributeError on None.upsert_documents()
        Expected: Should raise RuntimeError with clear message
        """
        # Mock get_vector_db_service to return uninitialized service
        mock_vector_db = Mock()
        mock_vector_db.client = None  # Not initialized
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=AsyncMock()):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db):
                
                # VERIFY: Should get clear error about uninitialized service
                with pytest.raises(RuntimeError, match="not initialized"):
                    await process_and_store_document(
                        content="test",
                        source_url="https://example.com",
                        metadata={},
                        source_type="test",
                    )


class TestDocumentProcessorBatchOptimization:
    """Test batch processing optimization with proper service injection."""

    @pytest.mark.asyncio
    async def test_batch_uses_single_embedding_call(self):
        """
        Verify batch processing uses single TEI call for multiple documents.
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [
            [0.1] * 1024,
            [0.2] * 1024,
            [0.3] * 1024,
        ]
        
        mock_vector_db_service = AsyncMock()
        
        documents = [
            {"content": f"doc {i}", "source_url": f"https://example.com/{i}",
             "metadata": {}, "source_type": "test"}
            for i in range(3)
        ]
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service):
                
                await process_and_store_documents_batch(documents)
                
                # VERIFY: Single call to generate_embeddings with all 3 docs
                assert mock_embeddings_service.generate_embeddings.call_count == 1
                call_args = mock_embeddings_service.generate_embeddings.call_args
                assert len(call_args[0][0]) == 3  # 3 documents in single call

    @pytest.mark.asyncio
    async def test_batch_uses_single_qdrant_upsert(self):
        """
        Verify batch processing uses single Qdrant upsert for all documents.
        """
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [
            [0.1] * 1024,
            [0.2] * 1024,
        ]
        
        mock_vector_db_service = AsyncMock()
        
        documents = [
            {"content": f"doc {i}", "source_url": f"https://example.com/{i}",
             "metadata": {}, "source_type": "test"}
            for i in range(2)
        ]
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service):
                
                await process_and_store_documents_batch(documents)
                
                # VERIFY: Single call to upsert_documents with both docs
                assert mock_vector_db_service.upsert_documents.call_count == 1
                call_args = mock_vector_db_service.upsert_documents.call_args
                assert len(call_args[0][0]) == 2  # 2 documents in single upsert


class TestDocumentProcessorEdgeCases:
    """Test edge cases and validation."""

    @pytest.mark.asyncio
    async def test_handles_empty_documents_list(self):
        """Verify graceful handling of empty document list."""
        # Empty list should return early without errors
        # No services needed since it returns immediately
        await process_and_store_documents_batch([])
        # If we get here without exception, test passes

    @pytest.mark.asyncio
    async def test_filters_documents_without_content(self, caplog):
        """Verify documents with empty content are skipped."""
        mock_embeddings_service = AsyncMock()
        mock_vector_db_service = AsyncMock()
        
        documents = [
            {"content": "", "source_url": "https://example.com/1",
             "metadata": {}, "source_type": "test"},
            {"content": "valid content", "source_url": "https://example.com/2",
             "metadata": {}, "source_type": "test"},
        ]
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service):
                
                mock_embeddings_service.generate_embeddings.return_value = [[0.1] * 1024]
                
                with caplog.at_level(logging.INFO):
                    await process_and_store_documents_batch(documents)
                
                # VERIFY: Only 1 document processed (the valid one)
                assert mock_embeddings_service.generate_embeddings.call_count == 1
                call_args = mock_embeddings_service.generate_embeddings.call_args
                assert len(call_args[0][0]) == 1  # Only 1 valid document

    @pytest.mark.asyncio
    async def test_filters_documents_without_source_url(self):
        """Verify documents without source_url are skipped."""
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [[0.1] * 1024]
        
        mock_vector_db_service = AsyncMock()
        
        documents = [
            {"content": "test", "source_url": "",
             "metadata": {}, "source_type": "test"},
            {"content": "test", "source_url": "https://example.com",
             "metadata": {}, "source_type": "test"},
        ]
        
        with patch('app.services.document_processor.get_embeddings_service',
                   return_value=mock_embeddings_service):
            with patch('app.services.document_processor.get_vector_db_service',
                       return_value=mock_vector_db_service):
                
                await process_and_store_documents_batch(documents)
                
                # VERIFY: Only 1 document processed
                call_args = mock_embeddings_service.generate_embeddings.call_args
                assert len(call_args[0][0]) == 1
