# 🎯 Agent War Room — Multi-Agent Job Application Assistant

A multi-agent AI system that analyses job postings using 5 specialised agents working in parallel. Watch agents coordinate, debate, and produce a tailored application package — with full observability into every handoff, retry, and decision.

**Status: 🔄 In Development**

## 🚀 What It Does

Applying to competitive roles takes hours of manual research per job. This system uses multiple AI agents that divide and conquer — one analyses the job description, one finds resume gaps, one researches the company, one plays devil's advocate, and one writes a tailored cover letter. An orchestrator coordinates them all.

**You provide a job description + your resume → 5 agents analyse in parallel → You get a match report, risk assessment, and tailored cover letter.**

---

## ✨ Features

- **Multi-Agent Orchestration** — 5 specialised agents coordinated by a state machine orchestrator
- **Parallel Execution** — Independent agents run concurrently via asyncio for faster results
- **Devil's Advocate Agent** — Challenges other agents' conclusions and flags risks
- **Live Trace Dashboard** — Watch agents work in real-time via WebSocket-powered UI
- **Typed Contracts** — Pydantic v2 models enforce typed communication between all agents
- **Failure Handling** — Automatic retries with backoff, graceful degradation, and short-circuit on dealbreakers
- **Full Observability** — Every agent call traced with token counts, latency, cost estimates, and status

---

## 🏗️ How It Works

1. User provides a job description (file or paste) and resume
2. Orchestrator dispatches `Job Analyzer` to parse the JD into structured data
3. Orchestrator checks for dealbreakers (security clearance, visa, etc.) — short-circuits if found
4. `Gap Analyzer` + `Company Researcher` run in parallel (independent tasks)
5. `Devil's Advocate` challenges the match assessment and flags risks
6. `Letter Writer` produces a tailored cover letter addressing strengths and preempting gaps
7. Orchestrator compiles the final `ApplicationPackage` with match report, strategy, and trace

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                       │
│  ANALYZE → CHECK → GAPS+RESEARCH → ADVOCATE → WRITE │
└──────┬──────────┬──────────┬──────────┬────────┬────┘
       │          │          │          │        │
  ┌────▼────┐ ┌──▼───┐ ┌───▼────┐ ┌──▼────┐ ┌─▼─────┐
  │  Job    │ │ Gap  │ │Company │ │Devil's│ │Letter │
  │Analyzer │ │Analyz│ │Research│ │Advoc. │ │Writer │
  └─────────┘ └──────┘ └────────┘ └───────┘ └───────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| AI | Anthropic Claude API |
| Contracts | Pydantic v2 |
| Async | asyncio |
| Web | FastAPI + WebSocket |
| Frontend | Single HTML + Vanilla JS |
| Traces | SQLite |
| CLI | Typer |
| Testing | pytest + pytest-asyncio |

---

## 🤖 Agent Roster

| Agent | Role | Model Tier |
|---|---|---|
| Job Analyzer | Parses JD into structured skills, requirements, red flags | Haiku (fast, cheap) |
| Gap Analyzer | Compares resume against JD, identifies matches and gaps with severity | Sonnet (reasoning) |
| Company Researcher | Researches company culture, values, and interview tips | Sonnet |
| Devil's Advocate | Challenges match assessment, flags risks, suggests rebuttals | Sonnet (adversarial) |
| Letter Writer | Generates tailored cover letter addressing strengths and preempting gaps | Sonnet (writing) |

---

## ⚙️ Getting Started

### Prerequisites
- Python 3.12+
- Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com)

### Installation

Clone the repository and install dependencies:

    git clone https://github.com/manasa-shivananda/ai-sub-agents.git
    cd ai-sub-agents
    pip install -e .

### Configuration

Create a .env file and add your API key:

    ANTHROPIC_API_KEY=your_api_key_here

### Run

Analyse a job posting:

    python main.py analyze --job data/sample_jobs/first_real_job.md --resume data/sample_resume.md

Launch the live trace dashboard:

    python main.py dashboard

View a trace from a previous run:

    python main.py trace --last

Or use the Makefile:

    make run          # Run analysis with sample data
    make dashboard    # Launch live dashboard
    make test         # Run test suite
    make trace        # View last execution trace

---

## 📸 Demo

**CLI Trace Output:**
```
[00.0s] ORCHESTRATOR → job_analyzer (1,247 tokens in)
[02.1s] job_analyzer → ORCHESTRATOR (832 tokens out, SUCCESS)
[02.1s] ORCHESTRATOR → gap_analyzer (2,079 tokens in)
[02.1s] ORCHESTRATOR → company_researcher (412 tokens in) [PARALLEL]
[03.8s] company_researcher → ORCHESTRATOR (FAILED, retrying 1/3)
[04.9s] company_researcher → ORCHESTRATOR (623 tokens out, SUCCESS)
[05.2s] gap_analyzer → ORCHESTRATOR (1,104 tokens out, SUCCESS)
[05.2s] ORCHESTRATOR → devils_advocate (2,559 tokens in)
[07.1s] devils_advocate → ORCHESTRATOR (891 tokens out, SUCCESS)
[07.1s] ORCHESTRATOR → letter_writer (3,806 tokens in)
[09.8s] letter_writer → ORCHESTRATOR (1,847 tokens out, SUCCESS)
[09.8s] COMPLETE — 6 agent calls, 1 retry, 9.8s total, $0.04 estimated cost
```

*Live dashboard screenshot coming soon.*

---

## 🧠 What I Learned

- **Multi-agent orchestration** — designing state machines that coordinate parallel agent execution with typed handoffs
- **Failure handling patterns** — retry with backoff, graceful degradation, short-circuit on dealbreakers
- **Typed inter-agent contracts** — Pydantic v2 models as enforceable interfaces between agents
- **Observability** — tracing every agent call with token counts, latency, cost, and status
- **Model tiering** — using cheap models for simple tasks and capable models for reasoning to optimise cost
- **Adversarial agents** — designing agents that challenge other agents' conclusions for better output quality

---

## 📐 Architecture

For the full architecture, agent specifications, Pydantic contracts, orchestrator state machine, and design decisions, see [DESIGN.md](DESIGN.md).

---

## 🗺️ Roadmap

- [ ] Core orchestrator with state machine
- [ ] All 5 agents with typed Pydantic contracts
- [ ] CLI trace output with token counts and cost estimates
- [ ] Parallel execution for independent agents
- [ ] Retry with backoff and graceful degradation
- [ ] Devil's Advocate agent challenging match assessments
- [ ] Live trace dashboard (FastAPI + WebSocket)
- [ ] Comprehensive test suite
- [ ] URL scraping for Seek.com.au job postings
- [ ] Brave Search API integration for company research

---

## 👩‍💻 About

Built by [Manasa Shivananda](https://github.com/manasa-shivananda) — Full-Stack Developer specialising in AI-powered tooling.

**AI Portfolio Series:**
- ✅ Project 1: [AI Code Reviewer](https://github.com/manasa-shivananda/ai-code-reviewer)
- ✅ Project 2: [AI Document Q&A Tool](https://github.com/manasa-shivananda/ai-document-qa)
- ✅ Project 3: [AI Job Application Assistant](https://github.com/manasa-shivananda/ai-job-assistant)
- 🔄 Project 4: Agent War Room — Multi-Agent Job Application Assistant (this project)

---

## 📄 License

MIT License
