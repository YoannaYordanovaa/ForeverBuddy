import os
import shutil
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("Грешка: Липсва API ключ в .env")
    exit()

# Конфигурация
DATA_PATH = "output_md"   # Чете
DB_PATH = "chroma_db"     # Записва

def create_vector_db():
    print("Създаване на базата данни...")

    # --- А. Проверка на данните 
    if not os.path.exists(DATA_PATH):
        print(f"Грешка: Папката '{DATA_PATH}' липсва.")
        return

    # --- Б. Зареждане на файловете 
    print("Зареждане на Markdown файлове...")
    loader = DirectoryLoader(
        DATA_PATH, 
        glob="*.md", 
        loader_cls=TextLoader, 
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
    
    if not documents:
        print("Не намерих .md файлове.")
        return
        
    print(f"Открити са {len(documents)} документа.")

    # --- В. Нарязване на текста (Chunking) 
    print("Нарязване на текста...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,    # Размер 
        chunk_overlap=200,  # Застъпване за запазване на контекста
        separators=["\n## ", "\n# ", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"   -> Създадени са {len(chunks)} парчета текст.")

    # --- Г. Записване в ChromaDB 
    print("Записване във векторен формат...")
    
    # Изтриваме стара база, ако има такава.
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)

    # Използваме 'text-embedding-3-small' 
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=DB_PATH
    )
    
    print(f"Готово! '{DB_PATH}'.")

if __name__ == "__main__":
    create_vector_db()