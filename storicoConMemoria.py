from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver  
 
def meteo(citta: str) -> str:
    """meteo per la citta"""
    return f"A {citta} c'è pioggia e 15°C."

llm = ChatOllama(model="qwen3.5:2b")

agent = create_agent(
    model=llm,
    tools=[meteo],
    checkpointer=InMemorySaver(),
    system_prompt="Sei un assistente che fornisce informazioni sul meteo",
)

while True:
    inputUtente = str(input("UTENTE: "))

    print("LLM: ", end="")
    response = agent.invoke({"messages": [("user", inputUtente)]}, 
                            {"configurable": {"thread_id": "chat_1"}},)

    print(response["messages"][-1].content)

#guardare 
