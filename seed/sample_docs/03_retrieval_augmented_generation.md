# Retrieval-Augmented Generation (RAG)

## The basic RAG pattern

RAG augments a language model's prompt with relevant context retrieved from an
external knowledge base. The simplest version: embed the question, retrieve the
top-k most similar chunks from a vector database, concatenate those chunks into
the prompt as "context", and let the LLM generate an answer conditioned on it.

## Chunking strategies

Documents must be split into chunks before embedding because most embedding
models have a maximum token limit (typically 512 or 8192 tokens). Fixed-size
chunking with overlap preserves context across boundaries. Typical values are
512 tokens per chunk with 50 tokens of overlap.

For code or structured documents, semantic chunking (at function boundaries or
section headers) typically outperforms token-based chunking.

## Hybrid retrieval

Semantic search using dense vector embeddings excels at conceptual matching but
sometimes misses exact keyword matches that traditional lexical search would
catch. The solution is hybrid retrieval: run both semantic search and a lexical
search (typically BM25) and combine the results.

The most robust combination strategy is Reciprocal Rank Fusion (RRF), which
combines ranked lists by summing the inverse of each item's rank in each list.
RRF beats linear weighted combinations because it requires no parameter tuning.

## Cross-encoder rerankers

A cross-encoder reranker takes a (query, candidate) pair and produces a single
relevance score by processing both jointly. This is more expensive than vector
similarity (10-100ms per pair) but dramatically improves ranking quality.

The standard production pattern is: retrieve top 20-50 candidates with hybrid
retrieval (cheap), then rerank to top 5 with a cross-encoder (expensive but
high quality). Empirically this lifts retrieval quality by 15-30%.

## RAGAS metrics

The four RAGAS metrics for RAG quality are:
- Faithfulness: does the generated answer follow from the retrieved context?
- Answer Relevance: does the answer address the user's question?
- Context Precision: how many of the retrieved chunks were useful?
- Context Recall: does the context contain all information needed for the
  ground-truth answer?

These metrics are typically computed via LLM-as-judge - a separate, capable LLM
scores each metric for each sample.
