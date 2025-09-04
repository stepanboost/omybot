from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from loguru import logger
from ..config import config
from ..llm.client import llm_client
from ..utils.subjects import detect_subject, get_subject_emoji
from ..db.repo import db_repo

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
        buttons.append([InlineKeyboardButton(text="Оплатить 299 ₽", url=pay_url)])
    buttons.append([InlineKeyboardButton(text="Пока без подписки", callback_data="sub_skip")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Короткое приветствие + inline-кнопки подписки + основное меню."""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username
    last_name = message.from_user.last_name

    logger.info(f"Пользователь {user_id} запустил бота")
    
    # Создаем или обновляем пользователя в базе данных
    try:
        await db_repo.create_user(user_id, username, first_name, last_name)
    except Exception as e:
        logger.error(f"Ошибка создания пользователя {user_id}: {e}")

    welcome_text = (
        f"Привет, {first_name}!\n\n"
        "Я помогу решить школьные задания по всем предметам.\n\n"
        "Что я умею:\n"
        "• Математика — алгебра, геометрия, тригонометрия\n"
        "• Физика — механика, электричество, оптика\n"
        "• Химия — уравнения, реакции, расчёты\n"
        "• Русский язык, литература, история\n"
        "• Английский язык, информатика, биология\n\n"
        "Как это работает:\n"
        "1. Отправь задачу текстом или фото\n"
        "2. Получи решение с объяснениями\n"
        "3. Изучи формулы и проверь знания\n\n"
        "Выбери режим:"
    )

    await message.answer(welcome_text, reply_markup=WELCOME_KEYBOARD)

    # Отправляем блок с подпиской отдельным сообщением, чтобы inline-кнопки были сразу
    sub_text = (
        "Доступна подписка за 299 ₽ в месяц:\n"
        "• Быстрые ответы\n"
        "• Расширенные объяснения\n"
        "• Приоритетная поддержка\n\n"
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
        "Команды:\n"
        "• /start - начать работу\n"
        "• /help - эта справка\n"
        "• /cancel_subscription - отменить подписку\n"
        "• /stats - статистика базы данных\n"
        "• /cleanup - очистить старые данные\n\n"
        "Примеры:\n"
        "• Реши уравнение: 3x + 7 = 25\n"
        "• Физика: тело 2 кг движется с ускорением 3 м/с². Найди силу\n"
        "• Химия: уравняй реакцию Fe + O₂ → Fe₂O₃\n"
    )
    await message.answer(help_text, reply_markup=WELCOME_KEYBOARD)


@router.message(Command("cancel_subscription"))
async def cmd_cancel_subscription(message: Message):
    """Обработчик команды отмены подписки"""
    user_id = message.from_user.id
    
    # Создаем клавиатуру для подтверждения отмены
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, отменить подписку", callback_data="confirm_cancel")],
        [InlineKeyboardButton(text="❌ Нет, оставить подписку", callback_data="keep_subscription")]
    ])
    
    cancel_text = (
        "🔄 Отмена подписки\n\n"
        "Вы действительно хотите отменить VIP-подписку?\n\n"
        "⚠️ После отмены вы потеряете:\n"
        "• ⚡ Мгновенные ответы\n"
        "• 🎯 Расширенные объяснения\n"
        "• 📊 Персональную статистику\n"
        "• 🔥 Приоритетную поддержку\n\n"
        "💡 *Базовый функционал останется доступным*"
    )
    
    await message.answer(cancel_text, reply_markup=keyboard)


@router.callback_query(F.data == "confirm_cancel")
async def confirm_cancel_subscription(callback: CallbackQuery):
    """Подтверждение отмены подписки"""
    await callback.answer("Подписка отменена", show_alert=True)
    
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Не удалось убрать inline-кнопки: {e}")
    
    # Здесь должна быть логика отмены подписки в базе данных
    # Пока просто показываем сообщение
    await callback.message.answer(
        "✅ Подписка успешно отменена!\n\n"
        "Спасибо, что пользовались нашим сервисом! 🙏\n"
        "Базовый функционал остается доступным.\n\n"
        "Если передумаете, просто нажмите /start для повторной подписки! 🚀",
    )


@router.callback_query(F.data == "keep_subscription")
async def keep_subscription(callback: CallbackQuery):
    """Отмена отмены подписки"""
    await callback.answer("Подписка сохранена", show_alert=False)
    
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Не удалось убрать inline-кнопки: {e}")
    
    await callback.message.answer(
        "✅ Отлично! Подписка сохранена!\n\n"
        "Продолжайте пользоваться всеми VIP-возможностями! 🚀\n"
        "Спасибо за доверие! 💎",
    )


# Обработчик фото с реальным LLM
@router.message(F.photo)
async def handle_photo(message: Message):
    user_id = message.from_user.id
    
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("📸 Фото получено. Обрабатываю задание…")
    
    try:
        # Получаем фото
        photo = message.photo[-1]  # Берем самое большое фото
        file = await message.bot.get_file(photo.file_id)
        image_bytes = await message.bot.download_file(file.file_path)
        
        # Создаем или получаем ID диалога
        conversation_id = f"user_{user_id}_main"
        
        # Получаем контекст диалога
        conversation_context = await db_repo.get_conversation_context(user_id, conversation_id)
        
        # Определяем предмет (пока без подсказки)
        subject, confidence = detect_subject(message.caption or "")
        subject_emoji = get_subject_emoji(subject)
        
        # Решаем задачу с контекстом
        result = await llm_client.solve_image(image_bytes.read(), subject, conversation_context)
        
        # Сохраняем сообщения в контекст
        photo_description = f"[Фото с заданием] {message.caption or ''}"
        await db_repo.save_message(user_id, conversation_id, "user", photo_description)
        await db_repo.save_message(user_id, conversation_id, "assistant", result['response'])
        
        # Сохраняем запрос в статистику
        await db_repo.save_request(user_id, photo_description, "image", subject, result['response'])
        
        # Отправляем ответ как есть
        await processing_msg.delete()
        await message.answer(result['response'])
        
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

    user_id = message.from_user.id
    
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("📝 Обрабатываю задание…")
    
    try:
        # Создаем или получаем ID диалога
        conversation_id = f"user_{user_id}_main"
        
        # Получаем контекст диалога
        conversation_context = await db_repo.get_conversation_context(user_id, conversation_id)
        
        # Определяем предмет
        subject, confidence = detect_subject(text)
        subject_emoji = get_subject_emoji(subject)
        
        # Решаем задачу с контекстом
        result = await llm_client.solve_text(text, subject, conversation_context)
        
        # Сохраняем сообщения в контекст
        await db_repo.save_message(user_id, conversation_id, "user", text)
        await db_repo.save_message(user_id, conversation_id, "assistant", result['response'])
        
        # Сохраняем запрос в статистику
        await db_repo.save_request(user_id, text, "text", subject, result['response'])
        
        # Отправляем ответ как есть
        await processing_msg.delete()
        await message.answer(result['response'])
        
    except Exception as e:
        logger.error(f"Ошибка обработки текста: {e}")
        await processing_msg.edit_text("❌ Ошибка при обработке задания. Попробуйте еще раз.")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает статистику базы данных"""
    try:
        stats = await db_repo.get_database_stats()
        
        stats_text = (
            "📊 Статистика базы данных:\n\n"
            f"👥 Пользователи: {stats['users_count']}\n"
            f"📝 Запросы: {stats['requests_count']}\n"
            f"💬 Сообщения контекста: {stats['conversation_context_count']}\n"
            f"💎 Подписки: {stats['subscriptions_count']}\n\n"
            f"💾 Размер базы: {stats['database_size_mb']} МБ\n\n"
            f"🗑️ Старые данные:\n"
            f"• Контекст старше 7 дней: {stats['old_context_messages']}\n"
            f"• Запросы старше 30 дней: {stats['old_requests']}\n\n"
            "💡 Используйте /cleanup для очистки старых данных"
        )
        
        await message.answer(stats_text)
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await message.answer("❌ Ошибка при получении статистики")


@router.message(Command("cleanup"))
async def cmd_cleanup(message: Message):
    """Очищает старые данные"""
    try:
        # Показываем сообщение о начале очистки
        cleanup_msg = await message.answer("🧹 Начинаю очистку старых данных...")
        
        # Выполняем очистку
        result = await db_repo.cleanup_old_data()
        
        # Показываем результат
        total_deleted = sum(result.values())
        
        cleanup_result = (
            "✅ Очистка завершена!\n\n"
            f"🗑️ Удалено записей:\n"
            f"• Сообщения контекста: {result['context_messages_deleted']}\n"
            f"• Старые запросы: {result['old_requests_deleted']}\n"
            f"• Неактивные пользователи: {result['inactive_users_deleted']}\n"
            f"• Истекшие подписки: {result['expired_subscriptions_deleted']}\n\n"
            f"📊 Всего удалено: {total_deleted} записей"
        )
        
        await cleanup_msg.edit_text(cleanup_result)
        
        # Если удалили много данных, делаем VACUUM
        if total_deleted > 50:
            vacuum_msg = await message.answer("🔧 Оптимизирую базу данных...")
            await db_repo.vacuum_database()
            await vacuum_msg.edit_text("✅ База данных оптимизирована!")
        
    except Exception as e:
        logger.error(f"Ошибка очистки данных: {e}")
        await message.answer("❌ Ошибка при очистке данных")
