"""
Query API Routes for RAG Chatbot

Handles query requests for full-book and selection modes.

Author: Physical AI & Humanoid Robotics Course
License: MIT
"""

from fastapi import APIRouter, HTTPException, Request
from models.query import QueryRequest, SelectionQueryRequest, QueryResponse, Citation
from services.retrieval_service import get_retrieval_service
from services.response_service import get_response_service
import time
from datetime import datetime

router = APIRouter(prefix="/api", tags=["query"])

# Get service instances
retrieval_service = get_retrieval_service()
response_service = get_response_service()


@router.post("/query", response_model=QueryResponse)
async def query_chatbot(request_data: QueryRequest, request: Request):
    """
    Query chatbot in full-book mode

    Args:
        request_data: QueryRequest with query and session_id

    Returns:
        QueryResponse with answer, citations, and metadata
    """
    start_time = time.time()

    try:
        # Validate query
        if not request_data.query or len(request_data.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        # Retrieve similar chunks
        search_results = retrieval_service.query_similar_chunks(
            query=request_data.query,
            top_k=5
        )

        if not search_results:
            # No results found
            return QueryResponse(
                answer="I couldn't find relevant information in the book to answer your question. Please try rephrasing or ask about topics covered in the course.",
                citations=[],
                mode="full-book",
                latency_ms=int((time.time() - start_time) * 1000),
                session_id=request_data.session_id,
                timestamp=datetime.utcnow()
            )

        # Generate answer with citations
        answer, citations, gen_latency = response_service.generate_answer(
            query=request_data.query,
            search_results=search_results
        )

        total_latency = int((time.time() - start_time) * 1000)

        return QueryResponse(
            answer=answer,
            citations=citations,
            mode="full-book",
            latency_ms=total_latency,
            session_id=request_data.session_id,
            timestamp=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log error (in production, use proper logging)
        print(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/query-selection", response_model=QueryResponse)
async def query_selection(request_data: SelectionQueryRequest, request: Request):
    """
    Query chatbot in selection mode

    Args:
        request_data: SelectionQueryRequest with selected_text, query, chapter_context

    Returns:
        QueryResponse with answer constrained to selection
    """
    start_time = time.time()

    try:
        # Validate inputs
        if not request_data.query or len(request_data.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        if not request_data.selected_text or len(request_data.selected_text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Selected text cannot be empty")

        # Validate selection length
        word_count = len(request_data.selected_text.split())
        if word_count > 1000:
            raise HTTPException(
                status_code=400,
                detail=f"Selection too long ({word_count} words). Maximum 1000 words."
            )

        # Retrieve chunks from same chapter
        search_results = retrieval_service.query_with_selection(
            query=request_data.query,
            selected_text=request_data.selected_text,
            chapter_id=request_data.chapter_context,
            top_k=3
        )

        # Generate answer with selection context
        answer, citations, gen_latency = response_service.generate_answer(
            query=request_data.query,
            search_results=search_results,
            selected_text=request_data.selected_text
        )

        total_latency = int((time.time() - start_time) * 1000)

        return QueryResponse(
            answer=answer,
            citations=citations,
            mode="selection",
            latency_ms=total_latency,
            session_id=request_data.session_id,
            timestamp=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing selection query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
