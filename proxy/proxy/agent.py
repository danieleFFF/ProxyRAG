from langchain.agents import create_agent
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import InMemorySaver
from fastapi import FastAPI
from langserve import add_routes
import uvicorn
import argparse
import os
from langchain_core.runnables import chain
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# read from env var so Docker containers and colleagues don't need to change the code
pathChromaDB = os.getenv("CHROMA_PATH", r"C:\Users\danie\Desktop\Scripts\ProxyRAG\embeddings\db_gemma")
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

def split_text(documents: list[Document]):
    """splits documents into chunks of 200 characters, with 5 shared characters between each chunk"""
    chunks = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=5).split_documents(documents)
    
    return chunks

vectorDB = Chroma(
    persist_directory=pathChromaDB,
    embedding_function=OllamaEmbeddings(model="embeddinggemma:300m", base_url=ollama_base_url),
    collection_name="medicina"
)

@tool
def search_info(query: str) -> str:
    """Use this tool to search the vector database for information about documents loaded by the user."""
    results = vectorDB.similarity_search(query, k=15)

    if not results:
        return "no information found."

    return "\n".join([r.page_content for r in results])

memory_checkpointer = InMemorySaver() # outside "agentRunnable" so that the model can change dynamically/maintain the conversation

class AgentInput(BaseModel):
    input: str = Field(description="User message")
    model: str = Field(default="qwen3.5:2b", description="llm model")
    thread_id: str = Field(default="session_1", description="Session ID")

@chain  # the function is now a runnable; plain functions are not accepted by langserve
async def agentRunnable(inputs: dict):
    userInput = inputs.get("input", "")
    model = inputs.get("model", "qwen3.5:2b")
    thread_id = inputs.get("thread_id", "session_1")

    llm = ChatOllama(model=model, base_url=ollama_base_url)
    
    # the agent dynamically uses the correct model while keeping the shared memory (checkpointer) across messages
    agent = create_agent(
        model=llm,
        tools=[search_info],
        checkpointer=memory_checkpointer,
        system_prompt = (
            "You are a specialized medical assistant. "
            "You have access to a vector database containing medical articles, clinical documents, and guidelines via the 'search_info' tool. "
            "For any questions regarding medical topics, health, pathology, or documents loaded by the user, you MUST search the database first using 'search_info'. "
            "If the tool returns 'no information found', inform the user honestly, and if appropriate, answer using your general knowledge but clearly state that the information was not found in the local database."
            )
        )

    # streaming tokens are intercepted (async for langserve and fastapi)
    async for event in agent.astream_events(
        {"messages": [("user", userInput)]},
        config={"configurable": {"thread_id": thread_id}},
        version="v2"
    ):
        # when the model generates text (token) it sends it
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"].content
            # ensures only actual text is extracted and sent
            if isinstance(chunk, str) and chunk:
                yield chunk

app = FastAPI(
    title="ProxyRAG agent server",
    version="1.0",
    description="API server with Langserve"
)

# endpoints
agentRunnable_typed = agentRunnable.with_types(input_type=AgentInput)

add_routes(
    app, agentRunnable_typed, path="/agent"
)

if __name__ == "__main__":
    # Each agent instance runs as a background service on its own port.
    # Launches one process per model: the model itself is read from the
    # request payload at runtime, so the same codebase serves all models.
    parser = argparse.ArgumentParser(description="ProxyRAG agent server")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    args = parser.parse_args()

    # host 0.0.0.0 makes the server reachable from other Docker containers
    uvicorn.run(app, host="0.0.0.0", port=args.port)
