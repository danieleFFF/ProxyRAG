from langchain.agents import create_agent
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import InMemorySaver

pathChromaDB = "./embeddings/help-embedding-chromadb/"

def meteo(citta: str) -> str:
    """meteo per la citta"""
    return f"A {citta} c'è pioggia e 15°C."


def split_testo(documenti: list[Document]):
    """divide i documenti in chunk da 10 caratteri, considerando 5 caratteri condivisi tra ogni chunk"""
    chunks = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=5).split_documents(documenti)
    
    return chunks


modello_embedding = OllamaEmbeddings(model="embeddinggemma:300m")

documenti = [
        Document(page_content="Daniele Filice ha 21 anni."),
        Document(page_content="Daniele Filice è uno studente dell'Unical."),
    ]

chunks = split_testo(documenti)

vectorDB = Chroma.from_documents(
    documents=chunks,
    embedding=modello_embedding,
    persist_directory=pathChromaDB,
)


def cerca_info(domanda: str) -> str:
    """cerca informazioni nel db"""
    risultati = vectorDB.similarity_search(domanda, k=3)

    if not risultati:
        return "Nessuna informazione trovata."

    return "\n".join([r.page_content for r in risultati])


llm = ChatOllama(model="qwen3.5:2b")

agent = create_agent(
    model=llm,
    tools=[meteo, cerca_info],
    checkpointer=InMemorySaver(),
    system_prompt="Sei un assistente utile. Usa 'meteo' per il tempo e 'cerca_info' per domande su Daniele e il ChromaDB.",
)

while True:
    inputUtente = str(input("UTENTE: "))

    print("LLM: ", end="")
    response = agent.invoke(
        {"messages": [("user", inputUtente)]},
        {"configurable": {"thread_id": "sessione_1"}},
    )

    print(response["messages"][-1].content)

#modelli per embeddings open-weights: Gemma 300M, nomic-embed-text
