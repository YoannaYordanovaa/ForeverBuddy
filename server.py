import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Tuple

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# 1. Зареждане на ключове
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    print("Липсва API ключ.")
    exit()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. База данни
DB_PATH = "chroma_db"
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
retriever = vector_db.as_retriever(search_kwargs={"k": 6})

# 3. LLM Модел
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.3)

# Помощни функции
def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

def format_chat_history(history: List[List[str]]):
    buffer = []
    for human, ai in history:
        buffer.append(f"Human: {human}")
        buffer.append(f"AI: {ai}")
    return "\n".join(buffer)

condense_q_system = """Given a chat history and the latest user question \
which might reference context in the chat history, formulate a standalone question \
which can be understood without the chat history. Do NOT answer the question, \
just reformulate it if needed and otherwise return it as is. Return ONLY the question."""

condense_q_prompt = ChatPromptTemplate.from_messages([
    ("system", condense_q_system),
    ("human", "History: {chat_history}\nQuestion: {question}"),
])

condense_q_chain = condense_q_prompt | llm | StrOutputParser()

qa_system = """Ти си "Forever Buddy" – опитен, приятелски настроен AI ментор за Forever Living Products.
Днешната дата е: {date}.

ИЗТОЧНИК НА ИНФОРМАЦИЯ:
Използвай ЕДИНСТВЕНО предоставения по-долу контекст, за да отговориш.
Ако не намираш отговора в контекста, кажи: "Нямам тази информация в моите документи."

ПРАВИЛА:
1. Не прави медицински твърдения (не казвай "лекува", а "подкрепя").
2. Бъди позитивен и използвай емотикони (🌿, ✨).
3. Използвай Markdown за форматиране.

Контекст:
{context}
"""

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", qa_system),
    ("human", "{question}"),
])

# Тази верига приема: context, question, date
answer_chain = qa_prompt | llm | StrOutputParser()


# --- API ENDPOINTS ---

class ChatRequest(BaseModel):
    question: str
    history: List[Tuple[str, str]] = [] 

class LearnRequest(BaseModel):
    text: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # 1. Подготовка на данните
        formatted_history = format_chat_history(request.history)
        today_str = datetime.now().strftime("%d.%m.%Y г.")
        
        # 2. Определяне на истинския въпрос (Standalone Question)
        if request.history:
            print("Преформулиране на въпроса...")
            standalone_question = await condense_q_chain.ainvoke({
                "chat_history": formatted_history,
                "question": request.question
            })
            print(f"   -> Новият въпрос е: {standalone_question}")
        else:
            standalone_question = request.question

        # 3. Търсене в базата с НОВИЯ въпрос 
        docs = retriever.invoke(standalone_question)
        context_text = format_docs(docs)

        # 4. Стрийминг на отговора
        async def generate():
            # Подаваме на финалната верига вече намерените документи и преформулирания въпрос
            async for chunk in answer_chain.astream({
                "context": context_text,
                "question": standalone_question, 
                "date": today_str
            }):
                yield chunk

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        print(f"КРИТИЧНА ГРЕШКА: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# УЧЕНЕ
@app.post("/learn")
async def learn_endpoint(request: LearnRequest):
    print(f"Опит за запаметяване: {request.text}")
    try:
        vector_db.add_texts(texts=[request.text])
        return {"message": "Успешно запомних новата информация!"}
    except Exception as e:
        print(f"Грешка при запис: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ЗАБРАВЯНЕ
@app.post("/forget")
async def forget_endpoint(request: LearnRequest):
    print(f"Опит за изтриване на: {request.text}")
    try:
        results = vector_db.similarity_search_with_score(request.text, k=1)
        if not results:
            return {"message": "Не намерих нищо подобно."}

        document, score = results[0]
        found_text = document.page_content
        
        if score > 0.35: 
            return {"message": f"Намерих нещо, но не съм сигурен. Най-близкото е: '{found_text[:100]}...'"}

        collection = vector_db._collection
        db_data = collection.get(where_document={"$contains": found_text})
        
        if not db_data['ids']:
            return {"message": "Грешка при намирането на ID."}
            
        ids_to_delete = db_data['ids']
        collection.delete(ids=ids_to_delete)
        
        return {"message": f"Успешно изтрих: '{found_text[:50]}...'"}

    except Exception as e:
        print(f"Грешка в /forget: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Сървърът стартира...")
    uvicorn.run(app, host="0.0.0.0", port=8000)