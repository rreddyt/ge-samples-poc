# Google Cloud GenAI Customer Proof of Concepts (PoCs)

Welcome to the **`ge-customer-pocs`** repository! This repository is a curated catalog of reference implementations, custom integrations, and Proof of Concepts (PoCs) designed for Google Cloud customers.

These assets demonstrate best practices in architecting advanced generative AI systems using **Gemini Enterprise (Vertex AI Agent Builder)**, **Model Context Protocol (MCP)**, and rich client interfaces such as **Agent-to-UI (A2UI)** and **Agent-to-Agent (A2A)**.

---

## 📂 Catalog & Sub-Projects

Each directory in this repository is a self-contained PoC project. Click on the links below to view their dedicated architecture diagrams, setup configurations, and deployment guides:

| Project Name & Directory Link | Key Technologies | Use Case & Description |
| :--- | :--- | :--- |
| 🇬🇧 [**`ukg-mock-api-mcp/`**](ukg-mock-api-mcp/README.md) | FastMCP, FastAPI, BigQuery, Cloud Run | **Retail HR/Payroll MCP Integration:** Exposes secure employee payroll profiles, compensation metrics, and pay grade threshold queries to AI agents in real-time. |
| 🏢 [**`msft-mock-api-mcp/`**](msft-mock-api-mcp/README.md) | FastMCP, FastAPI, BigQuery, Cloud Run | **Microsoft Graph (Entra ID) MCP Directory:** Simulates a secure corporate directory lookup using standard Graph API v1.0 user properties. |
| 🤖 [**`sample-hr-change-intake-agent/hr-intake/`**](sample-hr-change-intake-agent/hr-intake/README.md) | ADK Python, A2UI, A2A, Stdio MCP, Dotenv | **AI-Assisted HR Personnel Change Intake:** An interactive agent enabling Store Leaders to process promotions, transfers, and terminations. Renders forms via A2UI, audits policy thresholds, and dispatches review tickets. |

---

## 🚀 Quick Start Guide

To set up or run any PoC in this repository:
1.  Navigate to the target sub-project directory (e.g., `sample-hr-change-intake-agent/hr-intake/`).
2.  Follow the **Local Development & Setup** guide inside that folder's dedicated `README.md` to configure virtual environments (`.venv`), manage environment variables, and run local playgrounds.
3.  Follow the **Cloud Run & Deployment Blueprint** inside the same directory to host the services on Google Cloud and integrate them with Gemini Enterprise.

---

## 📢 Access Notice
Access to this repository is temporary (30 days). Ensure you have cloned the content before **2026-06-19**.
