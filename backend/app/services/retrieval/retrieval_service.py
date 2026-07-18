from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.models.models import Document, DocumentMetadata, Chunk
from app.repositories.document_repo import document_repo
from app.services.embeddings.embedding_service import embedding_service
from app.services.retrieval.query_analyzer import query_analyzer, QueryAnalysisResult

class RetrievalService:
    def __init__(self):
        # Local ML models are bypassed to fit free cloud tiers (512MB RAM)
        pass

    def _apply_metadata_filters(self, db: Session, visitor_id: str, analysis: QueryAnalysisResult) -> Optional[List[int]]:
        """
        Query DB to find document IDs matching structured metadata filters.
        Returns a list of matching document IDs, or None if no filters were applied.
        """
        filter_applied = False
        query = db.query(Document.id).filter(Document.visitor_id == visitor_id)
        
        # Filter by document type
        if analysis.doc_type_filter:
            filter_applied = True
            query = query.join(DocumentMetadata).filter(DocumentMetadata.doc_type == analysis.doc_type_filter)
            
        # Compile lists of matching IDs based on JSONB metadata filters
        # 1. Vendor filter
        if getattr(analysis, "vendor", None):
            filter_applied = True
            query = query.join(DocumentMetadata).filter(
                text("document_metadata.extracted_data->>'vendor' ILIKE :vendor")
            ).params(vendor=f"%{analysis.vendor}%")
            
        # 2. Parties filter
        if getattr(analysis, "parties", None):
            filter_applied = True
            query = query.join(DocumentMetadata).filter(
                text("document_metadata.extracted_data->>'parties' ILIKE :parties")
            ).params(parties=f"%{analysis.parties}%")
            
        # 3. Amount threshold & operator
        if getattr(analysis, "amount_threshold", None) is not None and getattr(analysis, "amount_operator", None):
            op = getattr(analysis, "amount_operator")
            if op in [">", "<", "=", ">=", "<="]:
                filter_applied = True
                query = query.join(DocumentMetadata).filter(
                    text(f"CAST(document_metadata.extracted_data->>'amount' AS NUMERIC) {op} :amount")
                ).params(amount=analysis.amount_threshold)
                
        # 4. Expiry date threshold & operator
        if getattr(analysis, "expiry_date_threshold", None) and getattr(analysis, "expiry_date_operator", None):
            op = getattr(analysis, "expiry_date_operator")
            if op in [">", "<", "=", ">=", "<="]:
                filter_applied = True
                query = query.join(DocumentMetadata).filter(
                    text(f"document_metadata.extracted_data->>'expiry_date' {op} :expiry_date")
                ).params(expiry_date=analysis.expiry_date_threshold)
                
        # 5. GST query filter
        if getattr(analysis, "gst_mentioned", None):
            filter_applied = True
            query = query.join(DocumentMetadata).filter(
                text("document_metadata.extracted_data->>'gst' IS NOT NULL AND document_metadata.extracted_data->>'gst' != ''")
            )
                        
        if filter_applied:
            results = query.all()
            return [r[0] for r in results]
        return None

    def retrieve_relevant_chunks(
        self, 
        db: Session, 
        visitor_id: str, 
        query: str, 
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search pipeline:
        Metadata filtering -> Vector + BM25 -> RRF -> Return top hits.
        """
        # 1. Analyze user query
        analysis = query_analyzer.analyze_query(query)
        
        # 2. Resolve document IDs matching metadata filters
        filtered_doc_ids = self._apply_metadata_filters(db, visitor_id, analysis)
        
        # Intersect manual document scope and metadata filtered document scope
        final_doc_ids = document_ids
        if filtered_doc_ids is not None:
            if final_doc_ids is None:
                final_doc_ids = filtered_doc_ids
            else:
                final_doc_ids = list(set(final_doc_ids).intersection(set(filtered_doc_ids)))
                # If intersection is empty, we immediately return nothing
                if not final_doc_ids:
                    return []

        # 3. Perform Vector Search (pgvector)
        query_emb = embedding_service.get_embedding(analysis.search_query, is_query=True)
        vector_results = document_repo.search_vector(
            db, 
            embedding_vector=query_emb, 
            visitor_id=visitor_id, 
            limit=50, 
            document_ids=final_doc_ids
        )
        
        # 4. Perform BM25 Keyword Search
        all_chunks = document_repo.get_all_chunks_for_bm25(db, visitor_id, final_doc_ids)
        if not all_chunks:
            return []
            
        def tokenize(text_str: str) -> List[str]:
            # Simple lowercase whitespace + alphanumeric tokenization
            clean_str = re.sub(r'[^\w\s]', '', text_str.lower())
            return clean_str.split()
            
        import re
        corpus = [c.content for c in all_chunks]
        tokenized_corpus = [tokenize(doc) for doc in corpus]
        
        # Initialize BM25 and score all chunks
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = tokenize(analysis.search_query)
        
        # Get scores
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Zip chunks with scores and sort to get top BM25
        chunk_bm25_pairs = list(zip(all_chunks, bm25_scores))
        chunk_bm25_pairs.sort(key=lambda x: x[1], reverse=True)
        bm25_results = [chunk for chunk, score in chunk_bm25_pairs[:50] if score > 0]

        # 5. Merge results using Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        for rank, chunk in enumerate(vector_results):
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (1.0 / (60.0 + rank))
            
        for rank, chunk in enumerate(bm25_results):
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (1.0 / (60.0 + rank))

        # Sort candidate chunks by RRF score
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:20]
        
        # Retrieve actual chunk objects in sorted order
        candidate_chunks_map = {c.id: c for c in vector_results + bm25_results}
        candidate_chunks = [candidate_chunks_map[cid] for cid in sorted_chunk_ids if cid in candidate_chunks_map]
        
        if not candidate_chunks:
            return []

        # 6. Settle RRF candidates as search outputs directly (removes high-memory local model reranker dependencies)
        return [
            {
                "chunk": chunk,
                "score": 1.0,
                "document_name": chunk.document.filename if chunk.document else "Unknown Document",
                "page_number": chunk.page_number
            }
            for chunk in candidate_chunks[:7]
        ]

retrieval_service = RetrievalService()
