from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from loguru import logger
from ..config import config
from ..llm.client import llm_client
from ..utils.subjects import detect_subject, get_subject_emoji

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


def build_subscription_keyboard() -> InlineKeyboardMarkup:
    pay_url = config.subscription_pay_url.strip()
    buttons = []
    if pay_url:
        buttons.append([InlineKeyboardButton(text="💳 Оплатить 299 ₽", url=pay_url)])
    buttons.append([InlineKeyboardButton(text="✖️ Пока без подписки", callback_data="sub_skip")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Короткое приветствие + inline-кнопки подписки + основное меню."""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""

    logger.info(f"Пользователь {user_id} запустил бота")

    welcome_text = (
        f"🤖 Привет, {first_name}!\n\n"
        "Я помогу быстро решить школьные задания.\n"
        "Выберите как удобнее начать:"
    )

    await message.answer(welcome_text, reply_markup=WELCOME_KEYBOARD)

    # Отправляем блок с подпиской отдельным сообщением, чтобы inline-кнопки были сразу
    sub_text = (
        "✨ Доступна подписка за 299 ₽ в месяц: быстрее ответы и приоритетная очередь.\n"
        "Можно продолжить и без подписки."
    )
    await message.answer(sub_text, reply_markup=build_subscription_keyboard())


@router.callback_query(F.data == "sub_skip")
async def subscription_skip(callback: CallbackQuery):
    await callback.answer("Продолжаем без подписки", show_alert=False)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Не удалось убрать inline-кнопки: {e}")
    
    await callback.message.answer(
        "Окей! Выберите режим ниже или отправьте задание.",
        reply_markup=WELCOME_KEYBOARD,
    )


# Обработчик для всех остальных callback-запросов
@router.callback_query()
async def handle_unknown_callback(callback: CallbackQuery):
    await callback.answer("Неизвестная команда", show_alert=False)


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


# Обработчик фото с реальным LLM
@router.message(F.photo)
async def handle_photo(message: Message):
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("📸 Фото получено. Обрабатываю задание…")
    
    try:
        # Получаем фото
        photo = message.photo[-1]  # Берем самое большое фото
        file = await message.bot.get_file(photo.file_id)
        image_bytes = await message.bot.download_file(file.file_path)
        
        # Определяем предмет (пока без подсказки)
        subject, confidence = detect_subject(message.caption or "")
        subject_emoji = get_subject_emoji(subject)
        
        # Решаем задачу
        result = await llm_client.solve_image(image_bytes.read(), subject)
        
        # Формируем ответ
        response = f"{subject_emoji} **{result['subject'].title()}**\n\n"
        
        if result['short_answer']:
            response += f"**Короткий ответ:** {result['short_answer']}\n\n"
        
        # Очищаем объяснение от уже извлеченных частей
        import re
        explanation = result['explanation']
        if result['short_answer']:
            explanation = re.sub(r'\*\*Короткий ответ:\*\*\s*.*?(?=\n\n|\*\*|$)', '', explanation, flags=re.IGNORECASE | re.DOTALL)
        
        response += f"**Решение:**\n{explanation.strip()}"
        
        if result['latex_formulas']:
            response += "\n\n**🔢 Формулы:**\n"
            for formula in result['latex_formulas']:
                response += f"```math\n{formula}\n```\n"
        
        if result['quiz']:
            response += "\n\n**🧠 Проверка себя:**\n"
            for i, question in enumerate(result['quiz'][:3], 1):
                response += f"{i}. {question}\n"
        
        # Удаляем сообщение о обработке и отправляем результат
        await processing_msg.delete()
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await processing_msg.edit_text("❌ Ошибка при обработке фото. Попробуйте еще раз.")


# Обработчик текста с реальным LLM
@router.message(F.text)
async def handle_text(message: Message):
    # Проверяем, что text не None
    if not message.text:
        return
    
    text = message.text.strip()
    if not text:
        await message.answer("Пожалуйста, отправьте текст задания или фото.")
        return

    if text in {"📝 Решить текстом", "📸 Решить по фото"}:
        return  # уже обработано соответствующими хендлерами

    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("📝 Обрабатываю задание…")
    
    try:
        # Определяем предмет
        subject, confidence = detect_subject(text)
        subject_emoji = get_subject_emoji(subject)
        
        # Решаем задачу
        result = await llm_client.solve_text(text, subject)
        
        # Формируем ответ
        response = f"{subject_emoji} **{result['subject'].title()}**\n\n"
        
        if result['short_answer']:
            response += f"**Короткий ответ:** {result['short_answer']}\n\n"
        
        # Очищаем объяснение от уже извлеченных частей
        import re
        explanation = result['explanation']
        if result['short_answer']:
            explanation = re.sub(r'\*\*Короткий ответ:\*\*\s*.*?(?=\n\n|\*\*|$)', '', explanation, flags=re.IGNORECASE | re.DOTALL)
        
        response += f"**Решение:**\n{explanation.strip()}"
        
        if result['latex_formulas']:
            response += "\n\n**🔢 Формулы:**\n"
            for formula in result['latex_formulas']:
                response += f"```math\n{formula}\n```\n"
        
        if result['quiz']:
            response += "\n\n**🧠 Проверка себя:**\n"
            for i, question in enumerate(result['quiz'][:3], 1):
                response += f"{i}. {question}\n"
        
        # Удаляем сообщение о обработке и отправляем результат
        await processing_msg.delete()
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка обработки текста: {e}")
        await processing_msg.edit_text("❌ Ошибка при обработке задания. Попробуйте еще раз.")
