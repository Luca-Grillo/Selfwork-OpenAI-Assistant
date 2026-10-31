import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def create_vector_store():
    """
    Crea il vector store con la knowledge base dell'Orto Botanico di Roma.

    Returns:
        vector_store: l'oggetto vector store creato
    """

    # Il vector store è un database per la ricerca semantica gestito da OpenAI
    vector_store = client.vector_stores.create(name="Orto Botanico Roma Infos")

    # File della knowledge base da caricare (percorsi dalla radice del progetto)
    file_paths = ["./kb/info.txt", "./kb/more_info.txt"]
    file_streams = [open(path, "rb") for path in file_paths]

    # Carica i file e li indicizza; aspetta che l'elaborazione sia finita
    client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
    )

    return vector_store


if __name__ == "__main__":
    vector_store = create_vector_store()
    print("\n\n\nVector Store ID:", vector_store.id, "\n\n\n")