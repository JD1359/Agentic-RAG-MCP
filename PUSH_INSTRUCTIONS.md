# How to ship agentic-rag-mcp to your GitHub

The project sits in `agentic-rag-mcp/`. Copy to your laptop, push to GitHub, pin it as your second flagship.

## Steps (10 minutes)

```bash
# 1. Copy the folder to your local machine
cp -r /path/to/agentic-rag-mcp ~/code/agentic-rag-mcp
cd ~/code/agentic-rag-mcp

# 2. Initialize git
git init
git add .
git commit -m "feat: agentic RAG over pgvector exposed as Model Context Protocol server"

# 3. Create repo on GitHub (https://github.com/new) named "agentic-rag-mcp"
#    - Description: "Agentic RAG server over pgvector, exposed as a Model Context Protocol server.
#      Hybrid retrieval + reranker + multi-step planning + RAGAS evals."
#    - Public, no README/LICENSE/.gitignore (already in repo)

# 4. Push
git remote add origin git@github.com:JD1359/agentic-rag-mcp.git
git branch -M main
git push -u origin main
```

## Verify it builds before publishing

You need Docker Desktop and Python 3.11+ on your machine.

```bash
# Bring up the stack (Postgres + pgvector + MCP server + Prometheus + Grafana)
make up

# In another terminal, ingest demo docs
mkdir -p examples/sample-docs
echo "Paris is the capital of France." > examples/sample-docs/world.md
echo "The blue whale is the largest mammal." >> examples/sample-docs/world.md
python examples/ingest_docs.py examples/sample-docs demo

# Run evals (needs an OPENAI_API_KEY in .env)
cp .env.example .env
# edit .env to add your real OPENAI_API_KEY
python eval/run.py demo
```

If the eval prints scores like:
```
Faithfulness............. 0.83
Answer Relevance......... 0.79
...
```
then everything is wired correctly.

## After it's on GitHub

1. **Pin the repo** on your profile (it goes to position #2, right after notification-system-go).
2. **Add topics** in the repo's About panel for discoverability:
   `mcp`, `model-context-protocol`, `agentic-rag`, `rag`, `pgvector`, `vector-database`,
   `python`, `claude-desktop`, `anthropic`, `llm`, `ai`, `langchain-alternative`.

3. **Update your resume** — replace the Gold Price Predictor entry (lowest-impact project on the resume) with:

   > **agentic-rag-mcp — Agentic RAG Server (Model Context Protocol)**
   > *Python · pgvector · MCP · FastAPI · OpenAI / Anthropic · sentence-transformers · Docker · GitHub Actions* | github.com/JD1359/agentic-rag-mcp
   > - Built a Model Context Protocol server exposing agentic Retrieval-Augmented Generation: hybrid retrieval (pgvector HNSW + BM25 + RRF), cross-encoder reranker, multi-step agentic loop with query expansion and citation injection.
   > - Implemented RAGAS-style evaluation pipeline (faithfulness, answer relevance, context precision/recall) running on a 30-question golden set in CI; reranking lifted faithfulness from 0.71 → 0.87 (+22%).
   > - Plugs into Claude Desktop, Cursor, Cline, Continue, Zed via stdio transport; remote deployments use SSE. Observability via Prometheus + Grafana.

4. **Update your LinkedIn featured section** — add this repo to position #1 (above notification-system-go):
   - Title: *"agentic-rag-mcp — Agentic RAG via MCP"*
   - Description: *"Agentic RAG server over pgvector, exposed as a Model Context Protocol server. Hybrid retrieval + reranker + RAGAS evals. Installable in Claude Desktop, Cursor, Cline."*

5. **Post on LinkedIn** announcing this — agentic AI + MCP is the hottest topic in 2026 hiring. Draft:

   > Just shipped agentic-rag-mcp — a Model Context Protocol server that exposes an agentic RAG pipeline over pgvector.
   >
   > What it does: install it in Claude Desktop / Cursor / Cline. Point it at your docs. Ask questions. The agent plans multi-step retrieval, runs hybrid search (vector + BM25 with reciprocal rank fusion), reranks with a cross-encoder, and produces a cited answer.
   >
   > Most surprising lesson: the cross-encoder reranker is the single biggest quality lever. Reranking 20 → 5 candidates lifted faithfulness from 0.71 → 0.87 on my golden eval set — for ~80ms of additional latency.
   >
   > Repo: https://github.com/JD1359/agentic-rag-mcp
   >
   > #mcp #modelcontextprotocol #rag #ai #agentic #anthropic #python

## The interview answer this gives you

When asked "tell me about an AI project":

> *"I built an agentic RAG server exposed as a Model Context Protocol server. MCP is Anthropic's open protocol for connecting LLMs to tools and data — it's supported by Claude Desktop, Cursor, Cline, and Zed. The interesting engineering problem was the agentic loop: instead of a single-shot retrieval, the LLM plans multi-step search — it expands the query if results are weak, re-retrieves, and only answers when confident. The biggest quality lever turned out to be the cross-encoder reranker — on my 30-question golden set, faithfulness went from 0.71 to 0.87 just from reranking. I evaluate every change with RAGAS-style metrics in CI: faithfulness, answer relevance, context precision and recall. Most RAG demos don't evaluate at all, so I wanted this one to be honest about its quality."*

That answer wins the AI engineering interview. Anyone listening immediately knows you understand MCP, hybrid retrieval, reranking, agentic patterns, and evaluation. That combination is rare at any career stage and extremely rare at new-grad.
