import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

import config
import database as db
from keyboards_main import get_main_keyboard, get_request_approval_keyboard
from keyboards_admin import get_admin_panel_keyboard
from keyboards_channel import get_my_channels_keyboard, get_content_type_keyboard
from utils_helpers import get_user_data_from_update
from utils_validators import is_admin

logger = logging.getLogger(__name__)

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    يبدأ المحادثة عند إرسال /start.
    يسجل المستخدم، ويتحقق من صلاحيته، ويعرض الرسالة المناسبة.
    """
    user_data = get_user_data_from_update(update)
    if not user_data:
        return ConversationHandler.END

    user_id = user_data['user_id']

    # إضافة أو تحديث المستخدم في قاعدة البيانات
    db.add_or_update_user(user_id, user_data['username'], user_data['first_name'], user_data['last_name'])

    # التحقق إذا كان الأدمن
    if user_id == config.ADMIN_ID:
        if not db.is_user_approved(user_id):
            db.approve_user(user_id) # الموافقة التلقائية على الأدمن
        logger.info(f"Admin {user_id} started the bot.")
        await update.message.reply_text("أهلاً بك أيها الأدمن!", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    # التحقق من نظام الموافقة
    if config.APPROVAL_REQUIRED:
        if not db.is_user_approved(user_id):
            logger.info(f"New user {user_id} requires approval.")
            if db.has_pending_request(user_id):
                await update.message.reply_text(config.UI_MESSAGES['approval_sent_message'])
            else:
                await update.message.reply_text(
                    config.UI_MESSAGES['approval_request_message'],
                    reply_markup=get_request_approval_keyboard()
                )
            return ConversationHandler.END

    # إذا تمت الموافقة على المستخدم
    logger.info(f"Approved user {user_id} started the bot.")
    await update.message.reply_text(config.WELCOME_MESSAGE, reply_markup=get_main_keyboard())
    return ConversationHandler.END


@is_admin
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض لوحة تحكم الأدمن."""
    await update.message.reply_text("لوحة تحكم الأدمن:", reply_markup=get_admin_panel_keyboard())


async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض قنوات المستخدم."""
    user_id = update.effective_user.id
    channels = db.get_user_channels(user_id)
    await update.message.reply_text(
        "قنواتك المضافة:",
        reply_markup=get_my_channels_keyboard(channels)
    )

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يبدأ عملية إضافة قناة جديدة عبر أمر."""
    user_id = update.effective_user.id

    # التحقق من الحد الأقصى للقنوات
    if db.get_channel_count(user_id) >= config.MAX_CHANNELS_PER_USER:
        await update.message.reply_text(f"لقد وصلت إلى الحد الأقصى لعدد القنوات المسموح به وهو {config.MAX_CHANNELS_PER_USER} قنوات.")
        return ConversationHandler.END

    # بدء محادثة جديدة لإضافة القناة
    context.user_data['new_channel'] = {}
    await update.message.reply_text(
        "حسناً، لنبدأ بإضافة قناة جديدة.\n"
        "الخطوة 1 من 3: أرسل معرف القناة (username) الآن (مثال: @mychannel).\n\n"
        "يجب أن يكون البوت مشرفاً في القناة ولديه صلاحية إرسال الرسائل.",
        reply_markup=ReplyKeyboardRemove()
    )
    return config.WAITING_FOR_CHANNEL_USERNAME


async def add_channel_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يبدأ عملية إضافة قناة جديدة عبر كولباك."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if db.get_channel_count(user_id) >= config.MAX_CHANNELS_PER_USER:
        await query.edit_message_text(f"لقد وصلت إلى الحد الأقصى لعدد القنوات المسموح به وهو {config.MAX_CHANNELS_PER_USER} قنوات.")
        return ConversationHandler.END

    context.user_data['new_channel'] = {}
    await query.edit_message_text(
        "حسناً، لنبدأ بإضافة قناة جديدة.\n"
        "الخطوة 1 من 3: أرسل معرف القناة (username) الآن (مثال: @mychannel).\n\n"
        "يجب أن يكون البوت مشرفاً في القناة ولديه صلاحية إرسال الرسائل."
    )
    return config.WAITING_FOR_CHANNEL_USERNAME


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يلغي العملية الحالية ويعود للقائمة الرئيسية."""
    user_data = context.user_data
    if 'new_channel' in user_data:
        user_data.clear()

    await update.message.reply_text(
        "تم إلغاء العملية.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض رسالة المساعدة."""
    help_text = """
    قائمة الأوامر المتاحة:
    /start - بدء استخدام البوت
    /my_channels - عرض وإدارة قنواتك
    /add_channel - إضافة قناة جديدة
    /admin - (للأدمن فقط) عرض لوحة التحكم
    /cancel - إلغاء أي عملية جارية
    /help - عرض هذه الرسالة
    """
    await update.message.reply_text(help_text)
