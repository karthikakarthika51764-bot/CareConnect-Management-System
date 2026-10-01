# Knowledge Retrieval

Owners and staff can create approved FAQ, policy, clinic, pricing, and service information with `POST /api/v1/knowledge/documents`. Uploads are split into overlapping text chunks and stored with business/document IDs. Search is business-scoped; the answer is returned from the selected saved chunk, not generated prose. Missing matches use the staff-handoff fallback.

An optional embedding vector field and `EmbeddingProvider` protocol establish a replacement boundary, but there is no embedding implementation, vector index, pgvector extension, file extraction, or semantic search configured. Current retrieval is lexical matching and should be treated as a development feature. Before production, select a vector store, add document lifecycle/indexing jobs, enforce source metadata, evaluate retrieval quality, and keep the no-evidence fallback.
