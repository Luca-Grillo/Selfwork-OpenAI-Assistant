from dataclasses import dataclass
from typing import List, Optional
import json
import resend
from openai import OpenAI


MODEL = "gpt-4.1-mini"


INSTRUCTIONS = """
Il tuo nome è Sofia.
Sei un'assistente dell'Orto Botanico di Roma e aiuti i visitatori con le loro richieste.
Utilizza il contesto fornito nei file per rispondere alle domande in modo pertinente.
Quando un visitatore condivide il proprio INDIRIZZO EMAIL, INVIA loro un'email.
RICORDA DI INVIARE EMAIL SOLO QUANDO HAI IL LORO INDIRIZZO EMAIL.
"""


TOOLS = [
    {
        "type": "function",
        "name": "send_email",
        "description": "Invia al visitatore un'email quando fornisce il proprio indirizzo email",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "nome del visitatore",
                },
                "email": {
                    "type": "string",
                    "description": "email del visitatore",
                },
            },
            "required": ["name", "email"],
        },
    },
]


@dataclass
class Message:
    """
    Classe di supporto per rappresentare un messaggio nella chat.
    Contiene il ruolo (utente o assistente) e il contenuto del messaggio.
    """

    role: str
    content: str


class ChatLogic:
    """
    Classe principale che gestisce la logica della chat con l'assistente AI.
    Si occupa di:
    - Gestire le conversazioni
    - Processare i messaggi
    - Inviare email
    - Gestire le chiamate a funzioni
    """

    def __init__(self, openai_key: str, resend_key: str, vector_store_id: str):
        """
        Inizializza la classe con le chiavi API necessarie.

        Parametri:
        - openai_key: Chiave API per OpenAI
        - resend_key: Chiave API per il servizio email Resend
        - vector_store_id: ID del vector store con la knowledge base
        """

        self.client = OpenAI(api_key=openai_key)
        resend.api_key = resend_key
        self.vector_store_id = vector_store_id
        self.conversation_id = None

        # Tool della richiesta: la funzione send_email + file_search sul nostro vector store
        self.tools = TOOLS + [
            {"type": "file_search", "vector_store_ids": [vector_store_id]}
        ]

    def initialize_conversation(self):
        """
        Crea una nuova conversazione se non ne esiste già una.
        Una conversazione rappresenta una sessione di chat completa.

        Ritorna:
        - L'ID della conversazione creata o esistente
        """

        if not self.conversation_id:
            conversation = self.client.conversations.create()
            self.conversation_id = conversation.id
        return self.conversation_id

    def send_email(self, name: str, email: str) -> str:
        """
        Invia un'email di benvenuto all'utente utilizzando il servizio Resend.

        Parametri:
        - name: Nome dell'utente
        - email: Indirizzo email dell'utente

        Ritorna:
        - Messaggio di successo o errore dell'invio
        """

        try:
            r = resend.Emails.send(
                {
                    "from": "onboarding@resend.dev",
                    "to": email,
                    "subject": "Ciao, benvenuto all'Orto Botanico di Roma",
                    "html": f"""
                <p>Ciao, {name},<br/>
                Benvenuto all'Orto Botanico di Roma, ecco le informazioni per la tua visita.<br/>
                </p>
                Cordiali saluti, <br/>
                Orto Botanico di Roma
                """,
                }
            )
            return "Email sent successfully"
        except Exception as e:
            return f"Failed to send email: {str(e)}"

    def handle_function_calls(self, response):
        """
        Gestisce le chiamate a funzioni richieste dall'assistente AI.
        Attualmente supporta solo la funzione di invio email.

        Parametri:
        - response: risposta corrente del modello, con le chiamate da eseguire

        Ritorna:
        - La nuova risposta del modello dopo aver rimandato gli esiti, o None in caso di errore
        """

        tool_outputs = []

        for item in response.output:
            if item.type != "function_call":
                continue

            function_name = item.name
            function_args = json.loads(item.arguments)

            if function_name == "send_email":
                output = self.send_email(**function_args)
            else:
                output = f"Unknown function: {function_name}"

            tool_outputs.append(
                {"type": "function_call_output", "call_id": item.call_id, "output": output}
            )

        print("*" * 80)
        print("DEBUG")
        print("*" * 80)
        print(tool_outputs)
        print("*" * 80)

        if tool_outputs:
            try:
                return self.client.responses.create(
                    model=MODEL,
                    instructions=INSTRUCTIONS,
                    input=tool_outputs,
                    conversation=self.conversation_id,
                    tools=self.tools,
                )
            except Exception as e:
                print(f"Failed to submit tool outputs: {e}")
                return None

    def process_message(self, user_message: str) -> Optional[str]:
        """
        Elabora un messaggio dell'utente e restituisce la risposta dell'assistente.

        Il processo include:
        1. Inizializzazione della conversazione se necessario
        2. Invio del messaggio al modello (istruzioni e tool a ogni richiesta)
        3. Gestione di eventuali chiamate a funzioni
        4. Recupero della risposta

        Parametri:
        - user_message: Il messaggio dell'utente da processare

        Ritorna:
        - La risposta dell'assistente o None in caso di errore
        """

        conversation_id = self.initialize_conversation()

        response = self.client.responses.create(
            model=MODEL,
            instructions=INSTRUCTIONS,
            input=user_message,
            conversation=conversation_id,
            tools=self.tools,
        )

    
        while any(item.type == "function_call" for item in response.output):
            response = self.handle_function_calls(response)
            if not response:
                return None

      
        return response.output_text

    def fetch_messages(self, conversation_id: str):
        """
        Recupera tutti gli elementi (messaggi, chiamate a funzioni) di una conversazione.

        Parametri:
        - conversation_id: ID della conversazione

        Ritorna:
        - Lista degli elementi della conversazione
        """

        return self.client.conversations.items.list(conversation_id=conversation_id)