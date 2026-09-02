# ╔══════════════════════════════════════════════════════════════╗
# ║          КОНФИГУРАЦИОНЕН ФАЙЛ НА АСИСТЕНТА                  ║
# ║  Сменете само тези стойности за адаптация към нова компания  ║
# ╚══════════════════════════════════════════════════════════════╝

# ── ИДЕНТИЧНОСТ НА КОМПАНИЯТА ────────────────────────────────
COMPANY_NAME    = "Forever Living Products"
COMPANY_SHORT   = "Forever"
COMPANY_WEBSITE = "https://foreverlivingbg.com"

# ── ИДЕНТИЧНОСТ НА АСИСТЕНТА ─────────────────────────────────
ASSISTANT_NAME       = "ForeverBuddy"
ASSISTANT_NAME_PART1 = "Forever"   # Първата част (цвят: BRAND_COLOR)
ASSISTANT_NAME_PART2 = "Buddy"     # Втората част (цвят: ACCENT_COLOR)

# ── ВИЗИЯ ────────────────────────────────────────────────────
BRAND_COLOR  = "#6A0DAD"   # Основен цвят (лилав)
ACCENT_COLOR = "#FFC300"   # Акцентен цвят (жълт)
HEADER_BG    = "#2e0a47"   # Фон на хедъра и сайдбара

# ── ПЕРСОНА НА БОТА ──────────────────────────────────────────
BOT_EXPERTISE = """специализиран в областта на нутрициологията, хранителните добавки
и продуктите на Forever Living Products"""

BOT_DOMAINS = [
    "продукти: хранителни добавки, козметика, уелнес",
    "фирмена политика, процедури и бизнес структура",
    "маркетинг съдържание за социални мрежи и блог",
]

# ── ПРИВЕТСТВЕНО СЪОБЩЕНИЕ ───────────────────────────────────
WELCOME_MESSAGE = "Попитай ме за продукти, цени или бизнес възможности!"

# ── БЪРЗИ ДЕЙСТВИЯ ───────────────────────────────────────────
QUICK_ACTIONS = [
    {
        "icon": "🔍",
        "label": "Намери продукт",
        "desc": "Цена, съставки и ползи",
        "prompt": "Помогни ми да намеря продукт. Какви са наличните продукти и техните цени?",
    },
    {
        "icon": "📱",
        "label": "Напиши пост",
        "desc": "За Instagram, Facebook и др.",
        "prompt": "Искам да напишеш маркетингов пост за социални мрежи. За кой продукт и каква платформа да е?",
    },
    {
        "icon": "📋",
        "label": "Фирмена политика",
        "desc": "Правила, процедури, условия",
        "prompt": f"Обясни ми фирмената политика на {COMPANY_NAME}.",
    },
    {
        "icon": "✍️",
        "label": "Напиши статия",
        "desc": "Блог съдържание с SEO",
        "prompt": "Искам да напишеш блог статия. За кой продукт или тема да е?",
    },
]

# ── ДИСКЛЕЙМЪР ───────────────────────────────────────────────
DISCLAIMER = (
    f"Това приложение е разработено с академична цел. "
    f"Не е официален продукт на {COMPANY_NAME}. "
    f"Всички търговски марки принадлежат на съответните им собственици."
)

# ── ПРОДУКТОВИ СИНОНИМИ БГ → EN ──────────────────────────────
# Използват се от промпта за по-добро семантично търсене
# ── АДМИНИСТРАТОРСКА ПАРОЛА ──────────────────────────────────
# Паролата се задава в .env (ADMIN_PASSWORD=...), не тук — за да не
# се качва в git хранилището.
import os as _os
from dotenv import load_dotenv as _load_dotenv
_load_dotenv()
ADMIN_PASSWORD = _os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("Липсва ADMIN_PASSWORD в .env файла.")

PRODUCT_SYNONYMS = {
    "суха кожа":          "Hydrating Serum, Replenishing Skin Oil, Deep Moisturizing Cream, Aloe Vera Gelly",
    "бръчки / стареене":  "Infinite Firming Serum, Infinite Restoring Crème, Forever Bakuchiol",
    "хидратация":         "Hydrating Serum, Aloe Moisturizing Lotion, Protecting Day Lotion",
    "коса":               "Aloe-Jojoba Shampoo, Aloe-Jojoba Conditioner, Nourishing Hair Oil",
    "имунитет":           "Aloe Vera Gel, Forever ImmuStart, Forever Arctic Sea",
    "енергия / умора":    "Forever Energy, Forever B12 Plus, Forever Therm, FAB",
    "отслабване":         "Forever Therm, Forever Garcinia Plus, Forever Fiber, C9, F15",
    "стави / болки":      "Forever Active HA, Forever Marine Collagen, Forever Arctic Sea",
    "храносмилане":       "Aloe Vera Gel, Forever Fiber, Aloe Digestive Formula",
}