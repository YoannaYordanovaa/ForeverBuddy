import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "chroma_db"
EXPORT_FILE = "database_dump.txt"
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def export_db_to_text():
    print("Зареждане на базата данни...")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    collection = db._collection
    
    # Взимаме всички документи (текстови парчета)
    data = collection.get()
    documents = data.get('documents', [])
    metadatas = data.get('metadatas', [])
    ids = data.get('ids', [])

    print(f"Намерени {len(documents)} записа. Експортиране в {EXPORT_FILE}...")

    with open(EXPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"--- БАЗА ДАННИ: {DB_PATH} | Общ брой записи: {len(documents)} ---\n\n")
        
        for i in range(len(documents)):
            f.write(f"ID: {ids[i]}\n")
            f.write(f"МЕТАДАТА: {metadatas[i]}\n")
            f.write(f"ТЕКСТ:\n{documents[i]}\n")
            f.write("-" * 50 + "\n\n")

    print(f"Готово! Отвори файла '{EXPORT_FILE}', за да разгледаш съдържанието.")

if __name__ == "__main__":
    export_db_to_text()