import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import json
from keyboards_admin import get_admin_panel_keyboard
import config
import database as db
from keyboards_main import get_main_keyboard
from keyboards_channel import (
    get_my_channels_keyboard, get_edit_channel_keyboard, get_content_type_keyboard,
    get_schedule_days_keyboard, get_schedule_times_keyboard, get_channel_saved_keyboard,
    get_confirm_delete_keyboard, get_select_channel_keyboard, get_confirm_post_keyboard
)
from utils_helpers import clean_channel_id
from utils_ai import generate_content


logger = logging.getLogger(__name__)


# --- Main Message Handler for Keyboard Buttons ---

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالجة الرسائل النصية التي تطابق أزرار لوحة المفاتيح الرئيسية.
    """
    text = update.message.text
    user_id = update.effective_user.id

    # التأكد من أن المستخدم موافق عليه قبل تنفيذ أي إجراء
    if not db.is_user_approved(user_id) and user_id != config.ADMIN_ID:
        await update.message.reply_text("ليس لديك صلاحية بعد. يرجى طلب الموافقة أولاً.")
        return

    if text == config.UI_BUTTONS['configure_channel']:
        channels = db.get_user_channels(user_id)
        await update.message.reply_text(
            "قنواتك المضافة:",
            reply_markup=get_my_channels_keyboard(channels)
        )
    # The "generate_post" button is now an entry point to a conversation
    elif text == config.UI_BUTTONS['schedule_post']:
        await update.message.reply_text("ميزة جدولة منشور محدد قيد التطوير.")
    # The "set_signature" button is now an entry point to a conversation
    # so it does not need to be handled here.
    elif text == config.UI_BUTTONS['official_channel']:
        await update.message.reply_text(f"تابع قناتنا الرسمية: {config.OFFICIAL_CHANNEL}")
    elif text == "🏠 الرئيسية":
        await update.message.reply_text("القائمة الرئيسية:", reply_markup=get_main_keyboard())


# --- Conversation States for Adding a Channel ---

async def handle_channel_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    المرحلة الأولى في إضافة قناة: استقبال ومعالجة اسم القناة.
    """
    channel_username = update.message.text
    bot = context.bot

    # تنظيف المدخل
    cleaned_username = clean_channel_id(channel_username)

    # التحقق من أن البوت مشرف في القناة
    try:
        bot_member = await bot.get_chat_member(chat_id=cleaned_username, user_id=bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "❌ خطأ: البوت ليس مشرفاً في هذه القناة. يرجى رفع البوت كمشرف والمحاولة مرة أخرى.\n"
                "أرسل /cancel للإلغاء."
            )
            return config.WAITING_FOR_CHANNEL_USERNAME

        if not bot_member.can_post_messages:
            await update.message.reply_text(
                "❌ خطأ: البوت لا يملك صلاحية 'نشر الرسائل' في هذه القناة. يرجى منحه الصلاحية والمحاولة مرة أخرى.\n"
                "أرسل /cancel للإلغاء."
            )
            return config.WAITING_FOR_CHANNEL_USERNAME

        chat_info = await bot.get_chat(chat_id=cleaned_username)
        channel_id = str(chat_info.id) # تحويله لنص ليكون متوافقاً مع الاستخدام كـ PK

        context.user_data['new_channel']['id'] = channel_id
        context.user_data['new_channel']['username'] = cleaned_username

        await update.message.reply_text(
            "✅ تم التحقق من القناة بنجاح!\n"
            "الخطوة 2 من 3: اختر نوع المحتوى الذي تريد نشره في هذه القناة.",
            reply_markup=get_content_type_keyboard()
        )
        return config.SETTING_CONTENT_TYPE

    except Exception as e:
        logger.error(f"Failed to verify channel {cleaned_username}: {e}")
        await update.message.reply_text(
            "❌ لم أتمكن من العثور على القناة أو التحقق منها. تأكد من صحة اسم المستخدم وأن القناة عامة.\n"
            "أرسل /cancel للإلغاء."
        )
        return config.WAITING_FOR_CHANNEL_USERNAME


async def handle_content_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    المرحلة الثانية: استقبال نوع المحتوى والانتقال لجدولة الأيام.
    """
    query = update.callback_query
    await query.answer()
    content_type = query.data.split('_')[1]

    context.user_data['new_channel']['content_type'] = content_type

    # Initialize selected days as a set for easy add/remove
    context.user_data['new_channel']['schedule_days'] = set()

    await query.edit_message_text(
        "الخطوة 3 من 3: اختر أيام النشر.\n"
        "يمكنك اختيار أكثر من يوم.",
        reply_markup=get_schedule_days_keyboard()
    )
    return config.SETTING_SCHEDULE_DAYS


async def handle_schedule_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    معالجة اختيار أيام النشر.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "days_done":
        if not context.user_data['new_channel'].get('schedule_days'):
            await context.bot.answer_callback_query(query.id, "الرجاء اختيار يوم واحد على الأقل.", show_alert=True)
            return config.SETTING_SCHEDULE_DAYS

        # Initialize selected times
        context.user_data['new_channel']['schedule_times'] = set()
        await query.edit_message_text(
            "رائع! الآن اختر أوقات النشر.\n"
            "يمكنك اختيار أكثر من وقت.",
            reply_markup=get_schedule_times_keyboard()
        )
        return config.SETTING_SCHEDULE_TIME

    # Add/remove day from the set
    day = data.split('_')[1]
    selected_days = context.user_data['new_channel']['schedule_days']
    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.add(day)

    await query.edit_message_text(
        "اختر أيام النشر:",
        reply_markup=get_schedule_days_keyboard(selected_days)
    )
    return config.SETTING_SCHEDULE_DAYS


async def handle_schedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    معالجة اختيار أوقات النشر وحفظ القناة.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == config.CALLBACK_SAVE_CHANNEL:
        return await save_channel(update, context)

    selected_times = context.user_data['new_channel']['schedule_times']
    time = data.split('_')[1]

    if time in selected_times:
        selected_times.remove(time)
    else:
        selected_times.add(time)

    await query.edit_message_text(
        "اختر أوقات النشر:",
        reply_markup=get_schedule_times_keyboard(selected_times)
    )
    return config.SETTING_SCHEDULE_TIME


async def save_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    المرحلة النهائية: حفظ القناة في قاعدة البيانات وإنهاء المحادثة.
    """
    query = update.callback_query
    user_data = context.user_data['new_channel']
    user_id = query.from_user.id

    if not user_data.get('schedule_times'):
        await context.bot.answer_callback_query(query.id, "الرجاء اختيار وقت واحد على الأقل أو إدخال وقت مخصص.", show_alert=True)
        return config.SETTING_SCHEDULE_TIME

    schedule = {
        "days": list(user_data['schedule_days']),
        "times": list(user_data['schedule_times'])
    }

    # Here you can ask for custom signature, for now we use default
    custom_signature = ""

    db.add_channel(
        channel_id=user_data['id'],
        channel_username=user_data['username'],
        owner_id=user_id,
        content_type=user_data['content_type'],
        posting_schedule=schedule,
        custom_signature=custom_signature
    )

    # Reload scheduler to include the new channel
    from utils_schedule import setup_scheduler
    setup_scheduler(context.bot)

    await query.edit_message_text(
        "🎉 تم حفظ القناة بنجاح!\n"
        "سيبدأ النشر التلقائي حسب الجدول الذي حددته.",
        reply_markup=get_channel_saved_keyboard()
    )

    context.user_data.clear()
    return ConversationHandler.END


# --- Conversation States for Instant Post Generation ---

async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يبدأ محادثة إنشاء منشور فوري."""
    user_id = update.effective_user.id
    channels = db.get_user_channels(user_id)

    if not channels:
        await update.message.reply_text("ليس لديك أي قنوات مضافة للنشر فيها.")
        return ConversationHandler.END

    keyboard = get_select_channel_keyboard(channels, callback_prefix="post_channel_")
    await update.message.reply_text("اختر القناة التي تريد النشر فيها:", reply_markup=keyboard)

    return config.SELECTING_CHANNEL_FOR_POST


async def post_select_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يستقبل القناة المختارة ويطلب موضوع المنشور."""
    query = update.callback_query
    await query.answer()

    channel_id = query.data.replace("post_channel_", "")
    channel = db.get_channel(channel_id)
    if not channel:
        await query.edit_message_text("خطأ: لم يتم العثور على القناة.")
        return ConversationHandler.END

    context.user_data['post_channel_id'] = channel_id
    context.user_data['post_content_type'] = channel['content_type']

    await query.edit_message_text(f"القناة المختارة: {channel['channel_username']}.\n\n"
                                f"الآن، أرسل موضوع المنشور الذي تريد الكتابة عنه.")

    return config.WAITING_FOR_TOPIC


async def post_receive_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يستقبل الموضوع، يولد المحتوى، ويعرضه للمعاينة."""
    topic = update.message.text
    context.user_data['post_topic'] = topic

    await update.message.reply_text("⏳ جارٍ إنشاء المحتوى باستخدام الذكاء الاصطناعي، يرجى الانتظار...")

    content_type = context.user_data['post_content_type']
    generated_text = await generate_content(content_type, topic)

    if "خطأ:" in generated_text:
        await update.message.reply_text(f"❌ حدث خطأ أثناء إنشاء المحتوى:\n{generated_text}")
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data['post_generated_text'] = generated_text

    # إضافة التوقيع للمعاينة
    channel_id = context.user_data['post_channel_id']
    channel = db.get_channel(channel_id)
    signature = channel['custom_signature'] or config.DEFAULT_POST_SIGNATURE
    full_post_preview = f"{generated_text}\n\n{signature}"

    await update.message.reply_text("✨ تم إنشاء المحتوى بنجاح! ✨\n\n"
                                f"--- **معاينة المنشور** ---\n{full_post_preview}\n"
                                "---------------------\n\n"
                                "هل تريد نشره الآن؟",
                                reply_markup=get_confirm_post_keyboard())

    return config.CONFIRMING_POST


async def post_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة قرار المستخدم بخصوص المنشور الذي تم إنشاؤه."""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "post_edit":
        await query.edit_message_text("حسناً، أرسل الموضوع الجديد.")
        return config.WAITING_FOR_TOPIC

    elif action == "post_cancel":
        await query.edit_message_text("تم إلغاء النشر.")
        context.user_data.clear()
        return ConversationHandler.END

    elif action == "post_confirm":
        channel_id = context.user_data['post_channel_id']
        full_text = context.user_data['post_generated_text']

        channel = db.get_channel(channel_id)
        signature = channel['custom_signature'] or config.DEFAULT_POST_SIGNATURE
        full_post = f"{full_text}\n\n{signature}"

        try:
            await context.bot.send_message(chat_id=channel_id, text=full_post)
            await query.edit_message_text("✅ تم نشر المنشور بنجاح!")
            db.log_published_post(channel_id, full_text)
        except Exception as e:
            logger.error(f"Failed to post to channel {channel_id}: {e}")
            await query.edit_message_text(f"❌ حدث خطأ أثناء النشر: {e}")

        context.user_data.clear()
        return ConversationHandler.END


# --- Conversation States for Editing Signature ---

async def signature_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يبدأ محادثة تعديل التوقيع."""
    user_id = update.effective_user.id
    channels = db.get_user_channels(user_id)

    if not channels:
        await update.message.reply_text("ليس لديك أي قنوات مضافة لتعديل توقيعها.")
        return ConversationHandler.END

    # Add a new constant for this prefix
    keyboard = get_select_channel_keyboard(channels, callback_prefix="sig_channel_")
    await update.message.reply_text("اختر القناة التي تريد تعديل توقيعها:", reply_markup=keyboard)

    return config.SELECTING_CHANNEL_FOR_SIGNATURE


async def signature_channel_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يستقبل القناة المختارة ويطلب التوقيع الجديد."""
    query = update.callback_query
    await query.answer()

    channel_id = query.data.replace("sig_channel_", "")
    context.user_data['signature_channel_id'] = channel_id

    await query.edit_message_text("حسناً، أرسل الآن نص التوقيع الجديد. لإزالته، أرسل 'بدون'.")

    return config.WAITING_FOR_SIGNATURE


async def signature_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يستقبل التوقيع الجديد ويحفظه."""
    new_signature = update.message.text
    channel_id = context.user_data.get('signature_channel_id')

    if not channel_id:
        await update.message.reply_text("حدث خطأ، يرجى المحاولة مرة أخرى.")
        context.user_data.clear()
        return ConversationHandler.END

    # Handle signature removal
    if new_signature.strip() == 'بدون':
        new_signature = ""

    if db.update_channel_signature(channel_id, new_signature):
        await update.message.reply_text("✅ تم تحديث التوقيع بنجاح!")
    else:
        await update.message.reply_text("❌ حدث خطأ أثناء تحديث التوقيع.")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء أي محادثة بسيطة."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("تم إلغاء الإجراء.")
    context.user_data.clear()
    return ConversationHandler.END


# --- Conversation States for Editing Channel Schedule ---

async def edit_schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يبدأ محادثة تعديل جدول النشر."""
    query = update.callback_query
    await query.answer()
    channel_id = query.data.replace(config.CALLBACK_EDIT_SCHEDULE, "")

    channel = db.get_channel(channel_id)
    if not channel:
        await query.edit_message_text("لم يتم العثور على القناة.")
        return ConversationHandler.END

    context.user_data['editing_channel_id'] = channel_id

    try:
        schedule_data = json.loads(channel['posting_schedule'])
        selected_days = set(schedule_data.get('days', []))
    except (json.JSONDecodeError, TypeError):
        selected_days = set()

    context.user_data['edit_schedule_days'] = selected_days

    await query.edit_message_text(
        "اختر أيام النشر الجديدة:",
        reply_markup=get_schedule_days_keyboard(selected_days)
    )
    return config.EDITING_SCHEDULE_DAYS


async def edit_schedule_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار أيام النشر أثناء التعديل."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "days_done":
        if not context.user_data.get('edit_schedule_days'):
            await context.bot.answer_callback_query(query.id, "الرجاء اختيار يوم واحد على الأقل.", show_alert=True)
            return config.EDITING_SCHEDULE_DAYS

        channel_id = context.user_data['editing_channel_id']
        channel = db.get_channel(channel_id)
        try:
            schedule_data = json.loads(channel['posting_schedule'])
            selected_times = set(schedule_data.get('times', []))
        except (json.JSONDecodeError, TypeError):
            selected_times = set()

        context.user_data['edit_schedule_times'] = selected_times

        await query.edit_message_text(
            "الآن اختر أوقات النشر الجديدة:",
            reply_markup=get_schedule_times_keyboard(selected_times)
        )
        return config.EDITING_SCHEDULE_TIME

    day = data.split('_')[1]
    selected_days = context.user_data['edit_schedule_days']
    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.add(day)

    await query.edit_message_text(
        "اختر أيام النشر الجديدة:",
        reply_markup=get_schedule_days_keyboard(selected_days)
    )
    return config.EDITING_SCHEDULE_DAYS


async def edit_schedule_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار أوقات النشر وحفظ الجدول الجديد."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == config.CALLBACK_SAVE_CHANNEL:
        return await save_edited_schedule(update, context)

    selected_times = context.user_data['edit_schedule_times']
    time = data.split('_')[1]

    if time in selected_times:
        selected_times.remove(time)
    else:
        selected_times.add(time)

    await query.edit_message_text(
        "اختر أوقات النشر الجديدة:",
        reply_markup=get_schedule_times_keyboard(selected_times)
    )
    return config.EDITING_SCHEDULE_TIME


async def save_edited_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """حفظ جدول النشر المعدل."""
    query = update.callback_query
    channel_id = context.user_data.get('editing_channel_id')

    if not channel_id or not context.user_data.get('edit_schedule_times'):
        await context.bot.answer_callback_query(query.id, "الرجاء اختيار وقت واحد على الأقل.", show_alert=True)
        return config.EDITING_SCHEDULE_TIME

    new_schedule = {
        "days": list(context.user_data['edit_schedule_days']),
        "times": list(context.user_data['edit_schedule_times'])
    }

    if db.update_channel_schedule(channel_id, new_schedule):
        from utils_schedule import setup_scheduler
        setup_scheduler(context.bot)

        await query.edit_message_text("✅ تم تحديث جدول النشر بنجاح.")
        channel = db.get_channel(channel_id)
        await query.message.reply_text(
            f"إدارة القناة: {channel['channel_username']}",
            reply_markup=get_edit_channel_keyboard(channel_id, channel['active'])
        )
    else:
        await query.edit_message_text("حدث خطأ أثناء تحديث الجدول.")

    context.user_data.clear()
    return ConversationHandler.END


# --- Conversation States for Editing Channel Content Type ---

async def edit_content_type_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    يبدأ محادثة تعديل نوع المحتوى لقناة موجودة.
    """
    query = update.callback_query
    await query.answer()
    channel_id = query.data.replace(config.CALLBACK_EDIT_TYPE, "")

    # تخزين معرف القناة في بيانات المستخدم للمحادثة
    context.user_data['editing_channel_id'] = channel_id

    await query.edit_message_text(
        "اختر نوع المحتوى الجديد للقناة:",
        reply_markup=get_content_type_keyboard()
    )

    return config.EDITING_CHANNEL_TYPE


async def edit_content_type_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    يستقبل نوع المحتوى الجديد ويقوم بتحديثه في قاعدة البيانات.
    """
    query = update.callback_query
    await query.answer()

    new_type = query.data.split('_')[1]
    channel_id = context.user_data.get('editing_channel_id')

    if not channel_id:
        await query.edit_message_text("حدث خطأ ما، لم يتم العثور على القناة.")
        return ConversationHandler.END

    if db.update_channel_content_type(channel_id, new_type):
        # Reload scheduler to apply changes
        from utils_schedule import setup_scheduler
        setup_scheduler(context.bot)

        await query.edit_message_text(f"✅ تم تحديث نوع المحتوى إلى '{new_type}' بنجاح.")

        # عرض شاشة تعديل القناة مرة أخرى
        channel = db.get_channel(channel_id)
        await query.message.reply_text(
            f"إدارة القناة: {channel['channel_username']}",
            reply_markup=get_edit_channel_keyboard(channel_id, channel['active'])
        )
    else:
        await query.edit_message_text("حدث خطأ أثناء تحديث نوع المحتوى.")

    context.user_data.clear()
    return ConversationHandler.END
