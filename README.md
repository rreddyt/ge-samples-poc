# Google Cloud Gemini Enterprise Samples

Welcome to the **`ge-samples`** repository! This repository is a curated catalog of reference implementations,  integrations, and AI agent samples designed for Google Cloud customers.

These assets demonstrate best practices in architecting AI agents and systems using Google's **Gemini Enterprise** portfolio (Agent Platform and Gemini Enterprise App), **Model Context Protocol (MCP)**, **Agent-to-Agent (A2A)** protocol, **Integration Connectors**, and rich client interfaces such as **Agent-to-UI (A2UI)**.

---

## 📂 Catalog & Sub-Projects

Each directory in this repository is a self-contained sample. Click on the links below to view their dedicated architecture diagrams, setup configurations, and deployment guides:

| Project Name & Directory Link | Key Technologies | Use Case & Description |
| :--- | :--- | :--- |
| 🇬🇧 [**`ukg-mock-api-mcp/`**](ukg-mock-api-mcp/README.md) | FastMCP, FastAPI, BigQuery, Cloud Run | **Retail HR/Payroll MCP Integration:** Exposes secure employee payroll profiles, compensation metrics, and pay grade threshold queries to AI agents in real-time. |
| 🏢 [**`msft-mock-api-mcp/`**](msft-mock-api-mcp/README.md) | FastMCP, FastAPI, BigQuery, Cloud Run | **Microsoft Graph (Entra ID) MCP Directory:** Simulates a secure corporate directory lookup using standard Graph API v1.0 user properties. |
| 🤖 [**`sample-hr-change-intake-agent/hr-intake/`**](sample-hr-change-intake-agent/hr-intake/README.md) | ADK Python, A2UI, A2A, Stdio MCP, Dotenv | **AI-Assisted HR Personnel Change Intake:** An interactive agent enabling Store Leaders to process promotions, transfers, and terminations. Renders forms via A2UI, audits policy thresholds, and dispatches review tickets. |
| 🗓️ [**`gtasks-mcp/`**](gtasks-mcp/README.md) | FastMCP, googleapiclient, Cloud Run | **Google Tasks API MCP Integration:** Secure, read-write integration enabling Gemini Enterprise AI agents to manage task lists and task items utilizing dynamic end-user OAuth tokens. |
| 🖼️ [**`product-media-agent/`**](product-media-agent/README.md) | ADK Python, Gemini 3.1, Veo 3.1, BigQuery, GCS, Dotenv | **Multi-Agent Product Lifestyle Content (Image & Video) Generator:** A premium ADK multi-agent routing architecture consisting of a parent director delegating to specialized image (Gemini 3.1 Flash Image) and video (Veo 3.1 Fast Generate) sub-agents to automatically generate and upload stunning product marketing content to GCS. |
| 💻 [**`image-video-gen-script/`**](image-video-gen-script/README.md) | Python 3, Vertex AI SDK, BigQuery, GCS, Dotenv | **Interactive Lifestyle Media CLI Script:** A portable, single-file interactive CLI utility utilizing Vertex AI SDK, BigQuery, and GCS to generate professional product lifestyle images and videos directly from a terminal. |

---

## 🚀 Quick Start Guide

To set up or run any PoC in this repository:
1.  Navigate to the target sub-project directory (e.g., `sample-hr-change-intake-agent/hr-intake/`).
2.  Follow the **Local Development & Setup** guide inside that folder's dedicated `README.md` to configure virtual environments (`.venv`), manage environment variables, and run local playgrounds.
3.  Follow the **Cloud Run & Deployment Blueprint** inside the same directory to host the services on Google Cloud and integrate them with Gemini Enterprise.

---

## 📢 Access Notice
Access to this repository is temporary (30 days). Ensure you have cloned the content before **2026-06-19**.
