# ProxyRAG

A Django proxy that sits between [Open WebUI](https://github.com/open-webui/open-webui) and multiple LLM agents, adding **role-based access control** via Keycloak and **RAG** (Retrieval-Augmented Generation) over a medical document database powered by ChromaDB.

## Architecture

```
Open WebUI  -->  Django Proxy  -->  LangServe Agents  -->  Ollama
   :3000          :8000            :8001‒8004              :11434
                    |
                Keycloak (:8080)
```

- **Django Proxy** - authenticates requests using Keycloak, checks the user's roles, and routes each chat to the correct agent.
- **LangServe Agents** - one FastAPI server per model, each with access to a shared ChromaDB vector store for RAG.
- **Keycloak** - manages users, roles, and SSO. A user can only chat with the models matching their assigned roles.
- **Open WebUI** - the chat frontend; authenticates via Keycloak OIDC.

## Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- [Ollama](https://ollama.com/) running on the host with the required models pulled:
  ```
  ollama pull qwen3.5:2b
  ollama pull qwen3.5:4b
  ollama pull llama3.2:3b
  ollama pull llama3.2:1b-instruct-q5_K_M
  ollama pull embeddinggemma:300m
  ```

## Quick Start

1. **Clone the repo**
   ```bash
   git clone https://github.com/danieleFFF/LangChain.git
   cd LangChain
   ```

2. **Create the `.env` file**
   ```bash
   cp .env.example .env
   ```
   Fill in the required values:
   | Variable | Description |
   |---|---|
   | `OLLAMA_BASE_URL` | Ollama URL reachable from Docker (`http://host.docker.internal:11434` on Windows/Mac) |
   | `DJANGO_SECRET_KEY` | Django secret key (generate at [djecrety.ir](https://djecrety.ir)) |
   | `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin password |

3. **Create the Open WebUI Docker volume** (first time only)
   ```bash
   docker volume create open-webui
   ```

4. **Start all services**
   ```bash
   docker compose up --build
   ```

5. **Configure Keycloak** (first time only)
   - Go to `http://localhost:8080` and log in with `admin` / your password.
   - Create a realm named `openwebui-realm`.
   - Create a client named `open-webui` (Client authentication: ON, redirect URI: `http://localhost:3000/*`).
   - Copy the client secret into `.env` as `OAUTH_CLIENT_SECRET` and restart.
   - Create realm roles matching each model name (e.g. `qwen3.5:2b`).
   - Create users and assign them the appropriate model roles.

6. **Open the UI** at `http://localhost:3000` and log in via Keycloak.

## Adding a New Model

1. Pull the model in Ollama: `ollama pull <model-name>`
2. Add a new agent service in `docker-compose.yml` with a dedicated port.
3. Register the model in Django — either via the admin panel (`/admin/`) or by creating a new migration under `proxy/proxy/migrations/`.
4. Create a Keycloak role with the same name as the model and assign it to the users who need access.

## API Endpoints

The proxy exposes an OpenAI-compatible API:

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/models` | Lists models available to the authenticated user |
| `POST` | `/v1/chat/completions` | Chat (supports streaming) |

## Project Structure

```
├── proxy/                  # Django project
│   ├── config/             #   Django settings, urls, wsgi
│   └── proxy/              #   App: views, models, auth, agent, migrations
├── embeddings/             # ChromaDB vector databases
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```
