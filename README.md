# Content-Flow
Multi-agent content factory powered by LangGraph, GPT-4o, and pgvector. Features a Glassmorphism UI, async processing, and semantic caching.
ContentFlow: Enterprise-Grade AI Content Factory
ContentFlow is a production-ready AI orchestration platform that transforms long-form video (YouTube/Vimeo) and articles into a viral social media ecosystem. It leverages LangGraph multi-agent workflows and a modern Glassmorphism stack to deliver high-quality, platform-specific content at scale.

✨ Core Pillars
🤖 Agentic Orchestration: Uses LangGraph to manage specialized agents (Extraction, Research, Generation, Optimization) with stateful memory and feedback loops.

⚡ Real-Time Feedback: Persistent WebSocket connections provide a live "thinking" stream as agents process your content, reflected through a high-fidelity UI.

🧠 Semantic Intelligence: Integrated pgvector and ChromaDB provide a semantic cache, preventing redundant LLM calls and reducing operational costs.

🎨 High-Fidelity UX: A React 19 frontend utilizing Tailwind 4 and Framer Motion for a premium, tactile user experience.

🛠 Tech Stack
Backend
Engine: Python 3.12+ / FastAPI

Orchestration: LangGraph (Stateful Multi-Agent Workflows)

Intelligence: OpenAI GPT-4o & Claude 3.5 Sonnet

Database: PostgreSQL with pgvector (Content & Metadata)

Vector Cache: ChromaDB (Semantic Deduplication)

Frontend
Framework: React 19 / TypeScript

Build Tool: Vite

Styling: Tailwind CSS 4 (Glassmorphism / Design System)

Motion: Framer Motion (State-driven animations)

🤖 AI Agent Workflow
The "Brain" of ContentFlow is a cyclic graph that ensures quality through specialized nodes:

Extraction Agent: Scrapes transcripts/metadata; cleans and normalizes raw data.

Summarization Agent: Condenses core themes and stores semantic embeddings.

Generation Agent: Executes a "fan-out" process to create LinkedIn Carousels, X Threads, and Newsletters simultaneously.

Optimization Agent: Acts as the "Editor-in-Chief" to refine tone, inject CTAs, and ensure platform-fit.

📦 Project Structure
Plaintext

contentflow/
├── backend/                # FastAPI + LangGraph Agents
│   ├── app/
│   │   ├── agents/         # Agent logic & Graph definitions
│   │   ├── services/       # AI Orchestrator & Video Processing
│   │   └── api/            # REST & WebSocket Endpoints
├── frontend/               # React 19 + Tailwind 4
│   ├── src/
│   │   ├── components/     # Framer Motion UI Components
│   │   └── hooks/          # Custom WS & Generation hooks
└── docker-compose.yml      # Full-stack orchestration
🚦 Quick Start
1. Backend Setup
Bash

cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add OpenAI/Anthropic API Keys
alembic upgrade head
uvicorn app.main:app --reload
2. Frontend Setup
Bash

cd frontend
npm install
npm run dev
📡 API Architecture (v1)
Content Generation
POST /api/v1/generate

JSON

{
  "source_url": "https://youtube.com/watch?v=...",
  "content_types": ["linkedin_carousel", "twitter_thread"],
  "tone": "professional"
}
Returns 202 Accepted with a session_id for tracking.

Live Progress
WS /ws/process/{session_id} Streams real-time state updates (e.g., { "step": "summarizing", "progress": 45 }).

📊 Performance & Scaling
Semantic Deduplication: Before hitting the LLM, ContentFlow queries ChromaDB. If identical content was processed recently, it serves from the cache.

Async-First: Utilizes asyncio and asyncpg for non-blocking database and API operations.

Production Guardrails: Structured JSON logging, Sentry integration, and Pydantic v2 validation.

📄 License
This project is licensed under the MIT License.
