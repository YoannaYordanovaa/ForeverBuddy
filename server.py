import os
import sys
import shutil
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Tuple
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. Зареждане на конфигурацията и ключовете
from config import (
    COMPANY_NAME, COMPANY_SHORT, COMPANY_WEBSITE,
    ASSISTANT_NAME, BOT_EXPERTISE, BOT_DOMAINS,
    PRODUCT_SYNONYMS, DISCLAIMER,
)
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
retriever = vector_db.as_retriever(search_kwargs={"k": 10})

def reload_vector_db():
    """Презарежда retriever-а след rebuild."""
    global vector_db, retriever
    import gc
    vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    retriever = vector_db.as_retriever(search_kwargs={"k": 10})
    gc.collect()
    print("ChromaDB презаредена успешно.")

# 3. LLM Модели
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.3)
# По-висок лимит за маркетинг съдържание
llm_marketing = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7, max_tokens=4000)

# Помощни функции
def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

def format_chat_history(history: List[List[str]]):
    buffer = []
    for human, ai in history:
        buffer.append(f"Клиент: {human}")
        buffer.append(f"Асистент: {ai}")
    return "\n".join(buffer)

condense_q_system = """Given a chat history and the latest user question, \
formulate a standalone question that preserves the INTENT from the chat history.

CRITICAL RULE 1: If the chat history shows the user asked to write a post, article, blog or \
any marketing content — the standalone question MUST include that intent.

CRITICAL RULE 2: Always expand short/informal product names to FULL official names:
- "aloe berry" / "алое бери" → "Forever Aloe Berry Nectar"
- "aloe vera" / "алое вера" / "алое гел" → "Forever Aloe Vera Gel"
- "алое манго" → "Forever Aloe Mango"
- "алое праскова" → "Forever Aloe Peaches"
- "арктик си" / "омега" → "Forever Arctic Sea"
- "арги" → "Forever ARGI+"
- "therm" / "термо" → "Forever Therm"
- "гарциния" → "Forever Garcinia Plus"
- "дейли" → "Forever Daily"
- "колаген" → "Forever Marine Collagen"
- "прополис" → "Forever Bee Propolis"
- "гел за зъби" / "паста" → "Forever Bright Toothgel"
- "с9" / "c9" → "C9 Clean 9"
- "ф15" / "f15" → "F15"
- "fab" / "фаб" → "FAB Forever Active Boost"
If the product is not in this list — keep the user's wording but add "Forever Living" before it.

Examples:
- History: "write a blog article" → User: "aloe berry" → Output: "Write a blog article about Forever Aloe Berry Nectar"
- History: "напиши пост" → User: "алое бери" → Output: "Напиши пост за Forever Aloe Berry Nectar"
- History: "напиши блог статия" → User: "гел за зъби" → Output: "Напиши блог статия за Forever Bright Toothgel"
- User: "арктик си цена" → Output: "Каква е цената на Forever Arctic Sea?"

Do NOT answer the question. Return ONLY the reformulated standalone question."""

condense_q_prompt = ChatPromptTemplate.from_messages([
    ("system", condense_q_system),
    ("human", "History: {chat_history}\nQuestion: {question}"),
])

condense_q_chain = condense_q_prompt | llm | StrOutputParser()

# ── ДЕТЕКЦИЯ НА НАМЕРЕНИЕТО ─────────────────────────────────
intent_system = """You are classifying messages for a Forever Living Products assistant.
Classify the user's message into exactly ONE category:

- PRODUCT   — health concern, symptom, body issue, energy, weight, immunity,
              asking about a specific product, price, ingredients, benefits, usage.
              Examples: "суха кожа", "липса на енергия", "алое", "колко струва"

- POLICY    — business structure, ranks, bonuses, points, manager, registration,
              company rules, procedures, HR, returns, contracts, onboarding,
              how to become a manager/distributor, bonus points, marketing plan levels.
              Examples: "как да стана мениджър", "колко бонусни точки", "фирмена политика",
              "как се регистрирам", "какви са нивата", "супервайзор", "сениор"

- MARKETING — ONLY when explicitly asked to WRITE/CREATE content:
              post, article, blog, caption, статия, пост, блог, напиши, създай съдържание.
              CRITICAL: "как да стана мениджър" is POLICY, NOT marketing.
              CRITICAL: Questions about business/career are POLICY, NOT marketing.
              Examples: "напиши пост", "създай статия", "блог за алое"

- GENERAL   — greeting, unclear, completely off-topic

PRIORITY RULES (apply in order):
1. If message asks to WRITE/CREATE content → MARKETING
2. If message is about business ranks, points, bonuses, career → POLICY
3. If message is about health, products, prices → PRODUCT
4. Otherwise → GENERAL

Reply with ONLY the category word in uppercase. No explanation."""

intent_prompt = ChatPromptTemplate.from_messages([
    ("system", intent_system),
    ("human", "Chat history (last exchange):\n{history_hint}\n\nCurrent question: {question}"),
])
intent_chain = intent_prompt | llm | StrOutputParser()

# ── СПЕЦИАЛИЗИРАНИ ПРОМПТОВЕ ПО НАМЕРЕНИЕ ───────────────────
# BASE_IDENTITY се генерира динамично от config.py
BASE_IDENTITY = (
    f'Ти си "{ASSISTANT_NAME}" – топъл и компетентен AI ментор за служителите на {COMPANY_NAME}.\n'
    f'Ти си {BOT_EXPERTISE}.\n'
    'Днешната дата е: {date}.\n'
    'Пиши ВИНАГИ на български. Използвай Markdown, кратки параграфи и емотикони (🌿, ✨, 💛) там където е уместно.\n'
    'Не правиш медицински диагнози. При здравословни въпроси насочвай към лекар.\n'
    'Коректни формулировки: не "лекува", а "подкрепя", "допринася за", "помага при".\n'
    '\n'
    '{dynamic_rule}\n'
    '\n'
    'Контекст от базата данни:\n'
    '{context}'
)

PRODUCT_SYSTEM = BASE_IDENTITY + """

РЕЖИМ: ПРОДУКТИ — ЗАДЪЛЖИТЕЛНИ ПРАВИЛА:
1. НИКОГА не давай общи здравни съвети (спи повече, яж балансирано и т.н.) — това не е твоята роля.
2. ВЕДНАГА препоръчай 1-3 конкретни продукта от базата данни с пълно форматиране:
   - **Име на продукта**
   - 💰 Цена: XX.XX EUR
   - ✅ Основна полза: ...
   - 📋 Употреба: ...
3. Ако имаш няколко подходящи продукта — сравни ги с 1 изречение всеки.
4. Завърши ВИНАГИ с конкретна следваща стъпка: как да поръча или с какво да комбинира.
5. Ако в базата няма подходящ продукт — кажи го честно с 1 изречение и предложи алтернатива.

ВАЖНО — ЕЗИКОВА ВРЪЗКА:
Продуктите в базата имат английски имена. При търсене използвай пълното официално наименование.
Примери за разширяване на кратки имена:
- "aloe berry" / "алое бери" → "Forever Aloe Berry Nectar"
- "aloe vera" / "алое вера" / "алое гел" → "Forever Aloe Vera Gel"
- "алое манго" / "aloe mango" → "Forever Aloe Mango"
- "алое праскова" / "aloe peach" → "Forever Aloe Peaches"
- "арктик си" / "омега" → "Forever Arctic Sea"
- "арги" / "аргинин" → "Forever ARGI+"
- "термо" / "therm" / "метаболизъм" → "Forever Therm"
- "гарциния" → "Forever Garcinia Plus"
- "фибри" / "fiber" → "Forever Fiber"
- "лийн" / "lean" → "Forever Lean"
- "имустарт" / "имунитет деца" → "Forever ImmuStart"
- "имублeнд" → "Forever ImmuBlend"
- "дейли" / "мултивитамини" → "Forever Daily"
- "кидс" / "витамини деца" → "Forever Kids"
- "калций" → "Forever Calcium"
- "витамин С" / "absorbent" → "Forever Absorbent-C"
- "колаген" / "marine collagen" → "Forever Marine Collagen"
- "хиалуронова" / "active ha" → "Forever Active HA"
- "пробиотик" / "pro-b" → "Forever Active Pro-B"
- "гинко" → "Forever Ginkgo Plus"
- "ликиум" → "Forever Lycium Plus"
- "помистийн" / "pomesteen" → "Forever Pomesteen Power"
- "пчелен мед" → "Forever Bee Honey"
- "пчелен прашец" → "Forever Bee Pollen"
- "прополис" → "Forever Bee Propolis"
- "пчелно млечице" / "royal jelly" → "Forever Royal Jelly"
- "алое фърст" / "aloe first" → "Aloe First"
- "алое хийт" / "мускули" / "топлинен" → "Aloe Heat Lotion"
- "гел за зъби" / "паста" / "bright" → "Forever Bright Toothgel"
- "дезодорант" / "ever-shield" → "Aloe Ever-Shield"
- "шампоан" → "Aloe-Jojoba Shampoo"
- "балсам" / "conditioner" → "Aloe-Jojoba Conditioner"
- "С9" / "c9" / "9-дневна програма" → "C9"
- "Ф15" / "f15" / "15-дневна програма" → "F15"
- "протеин бар" / "fastbreak" → "FastBreak"
- "ФАБ" / "fab" / "енергийна напитка" → "FAB Forever Active Boost"
- "фокус" / "концентрация" → "Forever Focus"
- "слънцезащитен" → "Aloe Sunscreen"
- "суха кожа" → "Hydrating Serum, Replenishing Skin Oil, Deep Moisturizing Cream"
- "бръчки / стареене" → "Infinite Firming Serum, Infinite Restoring Crème, Forever Bakuchiol"
- "хидратация лице" → "Hydrating Serum, Aloe Moisturizing Lotion, Protecting Day Lotion"
- "коса" → "Aloe-Jojoba Shampoo, Aloe-Jojoba Conditioner, Nourishing Hair Oil"
- "енергия / умора" → "Forever Energy, Forever B12 Plus, Forever Therm, FAB"
- "отслабване / тегло" → "Forever Therm, Forever Garcinia Plus, Forever Fiber, C9, F15"
- "стави / болки" → "Forever Active HA, Forever Marine Collagen, Forever Arctic Sea"
- "храносмилане" → "Forever Aloe Vera Gel, Forever Fiber"""  

POLICY_SYSTEM = BASE_IDENTITY + """

РЕЖИМ: ФИРМЕНА ПОЛИТИКА — ЗАДЪЛЖИТЕЛНИ ПРАВИЛА:
1. НИКОГА не пиши блог статии, постове или маркетинг съдържание — това е информационен режим.
2. НИКОГА не добавяй хаштагове или дисклеймър за образователни цели.
3. Отговори директно и конкретно — като опитен колега, не като автор на статия.
4. Използвай САМО информация от контекста — не измисляй числа, нива или правила.
5. Ако в базата има конкретни числа (точки, нива, проценти) — цитирай ги точно.
6. Ако информацията липсва — кажи го честно и насочи към официалния сайт.
7. Структура: кратко въведение → конкретни стъпки/правила → следваща стъпка."""

MARKETING_SYSTEM = BASE_IDENTITY + """

РЕЖИМ: МАРКЕТИНГ СЪДЪРЖАНИЕ
- Потребителят иска готово съдържание — не обяснявай, ПИШИ директно.
- Дори ако въпросът е непълен — довърши идеята и напиши съдържанието веднага.
- Адаптирай тона: Instagram=топъл/личен, Facebook=информативен, LinkedIn=професионален.
- Ако не е уточнена платформа — избери Instagram по подразбиране и напиши.

КРИТИЧНО — САМО РЕАЛНА ИНФОРМАЦИЯ ОТ КОНТЕКСТА:
- Използвай САМО данните от контекста по-долу — не измисляй нищо.
- Ако продуктът не е в контекста: кажи "Не намерих данни за този продукт. Уточни точното наименование."
- ТОЧНИ ЧИСЛА: процентното съдържание (напр. "90.7% алое"), дозировката и цената трябва да са ДОСЛОВНО от контекста.
- УПОТРЕБА: пиши САМО инструкциите от полето "НАЧИН НА УПОТРЕБА" в контекста — не измисляй дози или начини.
- НИКОГА не добавяй информация която не е в контекста — дори да звучи логично.
- НИКОГА не пиши за козметични ефекти на хранителна напитка или обратното.
- Ако в контекста няма информация за употреба — напиши "Вижте инструкциите на опаковката."

БЛОГ СТАТИЯ — ЗАДЪЛЖИТЕЛНИ ИЗИСКВАНИЯ:
!!!ВАЖНО: Статията трябва да е МИНИМУМ 1500 думи. НЕ СПИРАЙ преди да си написал всички секции!!!

1. СТРУКТУРА — пиши ВСИЧКИ секции без изключение:
   ## [Заглавие с ключова дума]
   [Въведение — 3-4 изречения]

   ## Какво представлява [продуктът]?
   [Минимум 3 параграфа по 3 изречения]

   ## Ключови съставки и техните ползи
   [Минимум 3 параграфа — описвай всяка съставка подробно]

   ## Научно доказани ползи за здравето
   [Минимум 3 параграфа с конкретни факти от контекста]

   ## Как да използвате [продукта] правилно
   [Минимум 2 параграфа с конкретни инструкции]

   ## За кого е подходящ?
   [Минимум 2 параграфа]

   ## Цена и как да поръчате
   [Цена от контекста + линк към сайта]

   ## Заключение
   [2-3 изречения + призив за действие]

   ---
   *Дисклеймър: Този продукт не е лекарствено средство и не е предназначен за диагностика, лечение или предотвратяване на заболявания. За индивидуални въпроси консултирайте се с квалифициран специалист.*

   #хаштаг1 #хаштаг2 #хаштаг3 #хаштаг4 #хаштаг5

2. SEO ПРАВИЛА:
   - Ключовата дума: в заглавието, въведението и поне 3 подзаглавия
   - Конкретни съставки и факти от базата данни — не измисляй
   - Цената на продукта задължително ако е налична

3. ТОН: топъл, убедителен, автентичен — като препоръка от приятел
4. ЛИНК И ЦЕНА:
   - Винаги включвай цената от контекста ако е налична
   - Вместо "[вашия сайт]" използвай линка от config.py (COMPANY_WEBSITE)"""

GENERAL_SYSTEM = BASE_IDENTITY + """

РЕЖИМ: ОБЩИ ВЪПРОСИ
- Отговори топло и полезно.
- Ако темата е здравословна или за продукт — насочи веднага към конкретна препоръка.
- Ако въпросът е наистина неясен — задай 1 уточняващ въпрос."""

INTENT_PROMPTS = {
    "PRODUCT":   PRODUCT_SYSTEM,
    "POLICY":    POLICY_SYSTEM,
    "MARKETING": MARKETING_SYSTEM,
    "GENERAL":   GENERAL_SYSTEM,
}

def get_answer_chain(intent: str):
    system_prompt = INTENT_PROMPTS.get(intent, GENERAL_SYSTEM)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "История на разговора:\n{chat_history}\n\nСегашен въпрос: {question}"),
    ])
    # Маркетинг съдържание изисква повече токени
    model = llm_marketing if intent == "MARKETING" else llm
    return prompt | model | StrOutputParser()


# --- API ENDPOINTS ---

class ChatRequest(BaseModel):
    question: str
    history: List[Tuple[str, str]] = []

class LearnRequest(BaseModel):
    text: str

@app.get("/config")
async def get_config():
    """Връща публичната конфигурация към фронтенда."""
    from config import (
        COMPANY_NAME, COMPANY_SHORT, COMPANY_WEBSITE,
        ASSISTANT_NAME, ASSISTANT_NAME_PART1, ASSISTANT_NAME_PART2,
        BRAND_COLOR, ACCENT_COLOR, HEADER_BG,
        WELCOME_MESSAGE, QUICK_ACTIONS, DISCLAIMER,
    )
    return {
        "companyName":       COMPANY_NAME,
        "companyShort":      COMPANY_SHORT,
        "companyWebsite":    COMPANY_WEBSITE,
        "assistantName":     ASSISTANT_NAME,
        "namePart1":         ASSISTANT_NAME_PART1,
        "namePart2":         ASSISTANT_NAME_PART2,
        "brandColor":        BRAND_COLOR,
        "accentColor":       ACCENT_COLOR,
        "headerBg":          HEADER_BG,
        "welcomeMessage":    WELCOME_MESSAGE,
        "quickActions":      QUICK_ACTIONS,
        "disclaimer":        DISCLAIMER,
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        formatted_history = format_chat_history(request.history)
        today_str = datetime.now().strftime("%d.%m.%Y г.")

        # 1. Преформулиране на въпроса ако има история
        if request.history:
            print("Преформулиране на въпроса...")
            standalone_question = await condense_q_chain.ainvoke({
                "chat_history": formatted_history,
                "question": request.question
            })
            print(f"   -> Самостоятелен въпрос: {standalone_question}")
        else:
            standalone_question = request.question

        # 2. Детекция на намерението (с контекст от историята)
        # Вземаме последния обмен от историята като подсказка
        history_hint = ""
        if request.history:
            last_human, last_ai = request.history[-1]
            history_hint = f"User: {last_human}\nAssistant: {last_ai[:100]}"

        raw_intent = await intent_chain.ainvoke({
            "question": standalone_question,
            "history_hint": history_hint,
        })
        intent = raw_intent.strip().upper()
        if intent not in INTENT_PROMPTS:
            intent = "GENERAL"
        print(f"   -> Намерение: {intent}")

        # 3. Динамично правило според контекста
        if not request.history:
            dynamic_rule = "ПЪРВО СЪОБЩЕНИЕ: Отговори директно с конкретна информация. Ако въпросът е неясен, задай САМО 1 уточняващ въпрос."
        else:
            dynamic_rule = "ПРОДЪЛЖЕНИЕ: Потребителят е дал контекст — дай конкретен отговор ВЕДНАГА. Не разпитвай повече."

        # 4. Търсене в базата
        docs = retriever.invoke(standalone_question)
        context_text = format_docs(docs)

        # 5. Избор на верига според намерението и стрийминг
        answer_chain = get_answer_chain(intent)

        async def generate():
            async for chunk in answer_chain.astream({
                "context": context_text,
                "chat_history": formatted_history,
                "question": standalone_question,
                "date": today_str,
                "dynamic_rule": dynamic_rule,
            }):
                yield chunk

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        print(f"КРИТИЧНА ГРЕШКА: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# УЧЕНЕ
@app.get("/debug/search")
async def debug_search(q: str, password: str):
    """Диагностика — показва какво точно намира търсачката."""
    if password != _ADMIN_PWD:
        raise HTTPException(status_code=401, detail="Неоторизиран достъп.")
    docs = retriever.invoke(q)
    results = []
    for i, doc in enumerate(docs):
        results.append({
            "rank": i + 1,
            "source": doc.metadata.get("source", "неизвестен"),
            "preview": doc.page_content[:300],
            "length": len(doc.page_content),
        })
    return {"query": q, "total": len(results), "results": results}

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

# ── АДМИНИСТРАТОРСКИ ENDPOINTS ───────────────────────────────

from config import ADMIN_PASSWORD as _ADMIN_PWD

class AdminLoginRequest(BaseModel):
    password: str

class AdminActionRequest(BaseModel):
    password: str

@app.post("/admin/login")
async def admin_login(request: AdminLoginRequest):
    """Проверка на администраторска парола."""
    if request.password == _ADMIN_PWD:
        return {"success": True, "message": "Добре дошъл, администратор!"}
    raise HTTPException(status_code=401, detail="Грешна парола.")

@app.get("/admin/files")
async def admin_list_files(password: str):
    """Списък с файловете в input_files/."""
    if password != _ADMIN_PWD:
        raise HTTPException(status_code=401, detail="Неоторизиран достъп.")
    try:
        files = []
        if os.path.exists("input_files"):
            for f in os.listdir("input_files"):
                path = os.path.join("input_files", f)
                if os.path.isfile(path) and not f.startswith("."):
                    files.append({
                        "name": f,
                        "size": os.path.getsize(path),
                        "modified": datetime.fromtimestamp(
                            os.path.getmtime(path)
                        ).strftime("%d.%m.%Y %H:%M"),
                    })
        return {"files": sorted(files, key=lambda x: x["name"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/upload")
async def admin_upload_file(
    password: str = Form(...),
    file: UploadFile = File(...)
):
    """Качване на файл в input_files/."""
    if password != _ADMIN_PWD:
        raise HTTPException(status_code=401, detail="Неоторизиран достъп.")
    allowed = {".pdf", ".docx", ".xlsx", ".xls", ".json", ".txt", ".md"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдържан формат. Разрешени: {', '.join(allowed)}"
        )
    os.makedirs("input_files", exist_ok=True)
    dest = os.path.join("input_files", file.filename)
    try:
        content_bytes = await file.read()
        with open(dest, "wb") as f:
            f.write(content_bytes)
        return {"success": True, "message": f"Файлът '{file.filename}' е качен успешно."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/files/{filename:path}/download")
async def admin_download_file(filename: str, password: str = None, token: str = None):
    """Сваляне/преглед на файл от input_files/.
    Паролата се подава като header X-Admin-Password или query param token (base64).
    """
    from fastapi import Header
    from fastapi.responses import FileResponse
    import mimetypes, base64

    # Приемаме парола или като token (base64) или директно — никога plain password в URL
    provided = None
    if token:
        try:
            provided = base64.b64decode(token.encode()).decode()
        except Exception:
            provided = None
    elif password:
        provided = password

    if provided != _ADMIN_PWD:
        raise HTTPException(status_code=401, detail="Неоторизиран достъп.")

    # Предпазваме от path traversal
    safe_name = os.path.basename(filename)
    path = os.path.join("input_files", safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Файлът не е намерен: {safe_name}")

    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    inline_types = {"application/pdf", "text/plain", "text/markdown", "text/csv"}
    disposition = "inline" if mime in inline_types else "attachment"

    return FileResponse(
        path,
        media_type=mime,
        headers={"Content-Disposition": f'{disposition}; filename="{safe_name}"'}
    )

@app.delete("/admin/files/{filename}")
async def admin_delete_file(filename: str, password: str):
    """Изтриване на файл от input_files/."""
    if password != _ADMIN_PWD:
        raise HTTPException(status_code=401, detail="Неоторизиран достъп.")
    path = os.path.join("input_files", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файлът не е намерен.")
    try:
        os.remove(path)
        return {"success": True, "message": f"'{filename}' е изтрит."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

_rebuild_log: List[str] = []
_rebuild_running = False

@app.post("/admin/rebuild")
async def admin_rebuild_db(request: AdminActionRequest):
    """Стартира rebuild на векторната база данни."""
    global _rebuild_running, _rebuild_log
    if request.password != _ADMIN_PWD:
        raise HTTPException(status_code=401, detail="Неоторизиран достъп.")
    if _rebuild_running:
        raise HTTPException(status_code=409, detail="Rebuild вече е в ход.")
    import asyncio
    _rebuild_running = True
    _rebuild_log = ["⏳ Стартиране на rebuild..."]

    async def run_rebuild():
        global _rebuild_running, _rebuild_log
        import shutil as _shutil, time as _time, gc as _gc
        REBUILD_PATH = "chroma_db_rebuild"

        try:
            # Стъпка 1: fix_products.py
            _rebuild_log.append("📦 Обработка на продукти...")
            r = subprocess.run([sys.executable, "fix_products.py"],
                capture_output=True, text=True, timeout=300, encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
            if r.returncode != 0:
                _rebuild_log.append("❌ Грешка в fix_products.py:")
                for line in (r.stderr or r.stdout or "").strip().splitlines()[-10:]:
                    if line.strip(): _rebuild_log.append(f"   {line}")
                return
            _rebuild_log.append("✅ fix_products.py завърши успешно.")

            # Стъпка 2: converter.py
            _rebuild_log.append("🔄 Конвертиране на файлове...")
            r = subprocess.run([sys.executable, "converter.py"],
                capture_output=True, text=True, timeout=300, encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
            if r.returncode != 0:
                _rebuild_log.append("❌ Грешка в converter.py:")
                for line in (r.stderr or r.stdout or "").strip().splitlines()[-10:]:
                    if line.strip(): _rebuild_log.append(f"   {line}")
                return
            _rebuild_log.append("✅ converter.py завърши успешно.")

            # Стъпка 3: create_db.py — пише в REBUILD_PATH, не в активната база
            _rebuild_log.append("🧠 Изграждане на нова векторна база...")
            if os.path.exists(REBUILD_PATH):
                _shutil.rmtree(REBUILD_PATH, ignore_errors=True)

            r = subprocess.run([sys.executable, "create_db.py"],
                capture_output=True, text=True, timeout=300, encoding="utf-8",
                env={**os.environ,
                     "PYTHONIOENCODING": "utf-8",
                     "PYTHONUTF8": "1",
                     "CHROMA_DB_PATH": REBUILD_PATH})
            if r.returncode != 0:
                _rebuild_log.append("❌ Грешка в create_db.py:")
                for line in (r.stderr or r.stdout or "").strip().splitlines()[-10:]:
                    if line.strip(): _rebuild_log.append(f"   {line}")
                _shutil.rmtree(REBUILD_PATH, ignore_errors=True)
                return
            _rebuild_log.append("✅ Новата база е изградена успешно.")

            # Стъпка 4: рестарт — сървърът ще зареди REBUILD_PATH при старт
            # Преименуваме преди рестарт: chroma_db → chroma_db_old, rebuild → chroma_db
            _rebuild_log.append("🔄 Подготовка за рестарт...")
            _time.sleep(0.5)

            old_bak = "chroma_db_old"
            if os.path.exists(old_bak):
                _shutil.rmtree(old_bak, ignore_errors=True)

            # Заменяме старата база с новата
            # На Windows os.rename се проваля ако папката е заключена
            # Затова копираме файл по файл вместо rename
            try:
                import shutil as _shutil2
                # Изтриваме старата база файл по файл (по-безопасно от rmtree)
                if os.path.exists("chroma_db"):
                    for root, dirs, files in os.walk("chroma_db", topdown=False):
                        for name in files:
                            fpath = os.path.join(root, name)
                            try:
                                os.remove(fpath)
                            except Exception:
                                pass
                        for name in dirs:
                            dpath = os.path.join(root, name)
                            try:
                                os.rmdir(dpath)
                            except Exception:
                                pass
                    try:
                        os.rmdir("chroma_db")
                    except Exception:
                        pass

                # Копираме новата база върху старата
                _shutil2.copytree(REBUILD_PATH, "chroma_db", dirs_exist_ok=True)
                _shutil2.rmtree(REBUILD_PATH, ignore_errors=True)
                _rebuild_log.append("✅ Базата е подменена успешно.")
            except Exception as e:
                _rebuild_log.append(f"⚠️ Неуспешна замяна ({e}) — рестартирай сървъра ръчно.")

            _rebuild_log.append("🎉 Rebuild завърши! Рестарт след 3 секунди...")
            import asyncio as _asyncio

            async def _do_restart():
                    await _asyncio.sleep(2)
                    import os as _os
                    _os._exit(0)

            _asyncio.create_task(_do_restart())

        except Exception as e:
            _rebuild_log.append(f"❌ Критична грешка: {e}")
        finally:
            _rebuild_running = False
    asyncio.create_task(run_rebuild())
    return {"success": True, "message": "Rebuild стартиран."}

@app.get("/admin/rebuild/status")
async def admin_rebuild_status(password: str):
    """Статус на текущия rebuild."""
    if password != _ADMIN_PWD:
        raise HTTPException(status_code=401, detail="Неоторизиран достъп.")
    return {
        "running": _rebuild_running,
        "log": _rebuild_log,
    }

if __name__ == "__main__":
    import uvicorn
    print("Сървърът стартира...")
    uvicorn.run(app, host="0.0.0.0", port=8000)