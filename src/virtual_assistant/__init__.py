import os  # Per la gestione delle variabili d'ambiente
import chainlit as cl  # Framework per la creazione di chatbot
from dotenv import load_dotenv  # Per caricare le variabili da file .env
from virtual_assistant.chat_logic import ChatLogic  # Import assoluto della logica di chat

# Caricamento delle variabili d'ambiente dal file .env
load_dotenv()

# Configurazione delle chiavi API e degli ID necessari
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Chiave API di OpenAI
RESEND_API_KEY = os.getenv("RESEND_API_KEY")  # Chiave per il servizio Resend
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")  # ID del vector store con la knowledge base


# Eseguito all'avvio di una nuova sessione di chat
@cl.on_chat_start
def on_chat_start():
    """
    Inizializza una nuova sessione di chat:
    crea l'oggetto ChatLogic con le chiavi necessarie e lo salva nella sessione.
    """

    cl.user_session.set(
        "chat_logic",
        ChatLogic(
            openai_key=OPENAI_API_KEY,
            resend_key=RESEND_API_KEY,
            vector_store_id=VECTOR_STORE_ID,
        ),
    )


# Eseguito a ogni nuovo messaggio dell'utente
@cl.on_message
async def main(message: cl.Message):
    """
    Gestisce ogni nuovo messaggio ricevuto nella chat:
    1. Estrae il contenuto del messaggio
    2. Lo processa tramite ChatLogic
    3. Invia la risposta all'utente
    """

    user_message = message.content

    # Recupera l'istanza di ChatLogic della sessione e processa il messaggio.
    # process_message è sincrona (bloccante): make_async la esegue senza bloccare Chainlit.
    chat_logic = cl.user_session.get("chat_logic")
    response = await cl.make_async(chat_logic.process_message)(user_message)

    # Invia la risposta finale (con un messaggio di ripiego se qualcosa è andato storto)
    await cl.Message(
        author="assistant",
        content=response or "Mi dispiace, c'è stato un problema. Riprova.",
    ).send()