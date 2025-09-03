from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from loguru import logger

router = Router()


WELCOME_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📝 Решить текстом"),
            KeyboardButton(text="📸 Решить по фото"),
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите режим или отправьте задание текстом/фото",
)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Короткое приветствие + клавиатура."""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""

    logger.info(f"Пользователь {user_id} запустил бота")

    welcome_text = (
        f"🤖 Привет, {first_name}!\n\n"
        "Я помогу быстро решить школьные задания.\n"
        "Выберите как удобнее начать:"
    )

    await message.answer(welcome_text, reply_markup=WELCOME_KEYBOARD)


@router.message(F.text == "📝 Решить текстом")
async def handle_choose_text(message: Message):
    await message.answer(
        "Отправьте текст задания одним сообщением.\n\n"
        "Например: \"Реши уравнение: 3x + 7 = 25\""
    )


@router.message(F.text == "📸 Решить по фото")
async def handle_choose_photo(message: Message):
    await message.answer(
        "Пришлите фото с заданием (чёткое, без бликов)."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Короткая справка без упоминаний лимитов/форматов."""
    help_text = (
        "📖 Как пользоваться:\n\n"
        "1) Отправьте текст задания — я определю предмет и предложу решение.\n"
        "2) Или пришлите фото задания — выделю условие и решу.\n\n"
        "Примеры:\n"
        "• Реши уравнение: 3x + 7 = 25\n"
        "• Физика: тело 2 кг движется с ускорением 3 м/с². Найди силу\n"
        "• Химия: уравняй реакцию Fe + O₂ → Fe₂O₃\n"
    )
    await message.answer(help_text, reply_markup=WELCOME_KEYBOARD)


# Базовый обработчик фото (демо)
@router.message(F.photo)
async def handle_photo(message: Message):
    await message.answer(
        "Фото получено. Обрабатываю задание… (демо-ответ)"
    )


# Базовый обработчик текста (демо)
@router.message(F.text)
async def handle_text(message: Message):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, отправьте текст задания или фото.")
        return

    if text in {"📝 Решить текстом", "📸 Решить по фото"}:
        return  # уже обработано соответствующими хендлерами

    response = (
        "📝 Задание получено. (демо-ответ)\n\n"
        "В полной версии здесь будет:\n"
        "• Определение предмета\n"
        "• Пошаговое решение\n"
        "• Формулы в LaTeX\n"
        "• Небольшой квиз для самопроверки"
    )
    await message.answer(response)
