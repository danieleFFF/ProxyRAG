from langchain.agents import create_agent
from langchain_ollama import ChatOllama #senò non trova qwen

def meteo(citta: str) -> str:
    """meteo per la citta"""
    return f"A {citta} c'è: pioggia, 15°C."

#oggetto per comunicare con il provider tramite l'app
llm = ChatOllama(model="qwen3.5:2b")

agent = create_agent(
    model=llm,
    tools=[meteo],
    system_prompt="Sei un assistente che fornisce informazioni sul meteo",
)

storico = []

while True:
    inputUtente = str(input("UTENTE: "))
    storico.append({"role": "user", "content": inputUtente})

    #'invoke' esegue l'agente e ritorna 'messages' aggiornata.
    #'messages' è una lista di dizionari (ognuno con ruolo e contenuto) ed è 
    #la cronologia della conversazione.
    print("LLM: ", end="")
    response = agent.invoke({"messages": storico}, 
                            {"configurable": {"thread_id": "chat_1"}},) #identifica la "chat singola"
    storico.append(response["messages"][-1])

    #stampa la risposta 
    print(response["messages"][-1].content)

#provare llama3.2/qwen3.5_q8
