import logging
import json
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import config
import database as db
from keyboards_main import get_main_keyboard
from keyboards_admin import get_admin_panel_keyboard
from keyboards_channel import (
    get_my_channels_keyboard, get_edit_channel_keyboard, get_content_type_keyboard,
    get_schedule_days_keyboard, get_schedule_times_keyboard, get_channel_saved_keyboard,
    get_confirm_delete_keyboard
)
from handlers_admin import show_stats, show_pending_requests
from utils_helpers import get_user_data_from_update

logger = logging.getLogger(__name__)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """المعالج الرئيسي لجميع استعلامات الكولباك."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    logger.info(f"Received callback query from user {user_id} with data: {data}")

    # --- معالجة طلبات الموافقة ---
    if data == config.CALLBACK_REQUEST_APPROVAL:
        await handle_request_approval(update, context)
    elif data.startswith(config.CALLBACK_APPROVE_USER):
        await handle_approve_user(update, context)
    elif data.startswith(config.CALLBACK_REJECT_USER):
        await handle_reject_user(update, context)

    # --- لوحة تحكم الأدمن ---
    elif data == config.CALLBACK_ADMIN_STATS:
        await show_stats(update, context)
    elif data == config.CALLBACK_PENDING_REQUESTS:
        await show_pending_requests(update, context)

    # --- إدارة القنوات ---
    elif data == config.CALLBACK_MY_CHANNELS:
        channels = db.get_user_channels(user_id)
        await query.edit_message_text("قنواتك المضافة:", reply_markup=get_my_channels_keyboard(channels))
    elif data.startswith(config.CALLBACK_EDIT_CHANNEL):
        channel_id = data.replace(config.CALLBACK_EDIT_CHANNEL, "")
        channel = db.get_channel(channel_id)
        if channel:
            await query.edit_message_text(f"إدارة القناة: {channel['channel_username']}", reply_markup=get_edit_channel_keyboard(channel_id, channel['active']))
    elif data.startswith(config.CALLBACK_TOGGLE_ACTIVE):
        channel_id = data.replace(config.CALLBACK_TOGGLE_ACTIVE, "")
        channel = db.get_channel(channel_id)
        if channel:
            new_status = not channel['active']
            db.update_channel_active_status(channel_id, new_status)
            await query.edit_message_text(f"تم تغيير حالة القناة {channel['channel_username']} إلى {'نشطة' if new_status else 'غير نشطة'}.", reply_markup=get_edit_channel_keyboard(channel_id, new_status))
    elif data.startswith(config.CALLBACK_DELETE_CHANNEL):
        channel_id = data.replace(config.CALLBACK_DELETE_CHANNEL, "")
        channel = db.get_channel(channel_id)
        if channel:
            await query.edit_message_text(
                f"⚠️ هل أنت متأكد من أنك تريد حذف القناة {channel['channel_username']}؟\n"
                "سيتم حذف جميع البيانات المتعلقة بها ولا يمكن التراجع عن هذا الإجراء.",
                reply_markup=get_confirm_delete_keyboard(channel_id)
            )
    elif data.startswith(config.CALLBACK_CONFIRM_DELETE_CHANNEL):
        channel_id = data.replace(config.CALLBACK_CONFIRM_DELETE_CHANNEL, "")
        channel = db.get_channel(channel_id)
        if channel:
            if db.delete_channel(channel_id):
                # Reload scheduler after deleting a channel
                from utils_schedule import setup_scheduler
                setup_scheduler(context.bot)
                await query.edit_message_text(f"🗑️ تم حذف القناة {channel['channel_username']} بنجاح.")
                # Go back to channels list
                channels = db.get_user_channels(user_id)
                await query.message.reply_text("قنواتك المضافة:", reply_markup=get_my_channels_keyboard(channels))
            else:
                await query.edit_message_text("حدث خطأ أثناء حذف القناة.", reply_markup=get_edit_channel_keyboard(channel_id, channel['active']))

    elif data == config.CALLBACK_BACK_TO_CHANNELS:
        channels = db.get_user_channels(user_id)
        await query.edit_message_text("قنواتك المضافة:", reply_markup=get_my_channels_keyboard(channels))
    elif data == config.CALLBACK_BACK_TO_MAIN:
         await query.edit_message_text("تم العودة للقائمة الرئيسية. استخدم الأزرار بالأسفل.", reply_markup=None)
         await context.bot.send_message(chat_id=user_id, text="القائمة الرئيسية:", reply_markup=get_main_keyboard())


    # --- أزرار ما بعد حفظ القناة ---
    # The CALLBACK_ADD_CHANNEL is now handled as a ConversationHandler entry point

    # --- إلغاء الإعداد ---
    elif data == config.CALLBACK_CANCEL_SETUP:
        await query.edit_message_text("تم إلغاء عملية الإعداد.")
        context.user_data.clear()
        # No return state needed as this is not in a conversation

# --- دوال مساعدة للكولباك ---

async def handle_request_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب المستخدم للموافقة."""
    query = update.callback_query
    user_data = get_user_data_from_update(update)
    user_id = user_data['user_id']

    if db.has_pending_request(user_id):
        await query.edit_message_text(config.UI_MESSAGES['approval_sent_message'])
        return

    if db.create_approval_request(user_id):
        await query.edit_message_text(config.UI_MESSAGES['approval_sent_message'])
        # إرسال إشعار للأدمن
        admin_message = config.UI_MESSAGES['admin_notification_message'].format(
            user_id=user_id,
            user_name=user_data['first_name']
        )
        from keyboards_admin import get_approval_keyboard
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=admin_message,
            reply_markup=get_approval_keyboard(user_id)
        )
    else:
        await query.edit_message_text("حدث خطأ ما أثناء إرسال طلبك. يرجى المحاولة مرة أخرى.")

async def handle_approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة موافقة الأدمن على مستخدم."""
    query = update.callback_query
    user_id_to_approve = int(query.data.replace(config.CALLBACK_APPROVE_USER, ""))

    if db.approve_user(user_id_to_approve):
        await query.edit_message_text(f"✅ تمت الموافقة على المستخدم {user_id_to_approve}.")
        # إرسال إشعار للمستخدم
        await context.bot.send_message(
            chat_id=user_id_to_approve,
            text=config.UI_MESSAGES['user_approved_message'],
            reply_markup=get_main_keyboard()
        )
    else:
        await query.edit_message_text(f"حدث خطأ أثناء الموافقة على المستخدم {user_id_to_approve}.")

async def handle_reject_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفض الأدمن لطلب مستخدم."""
    query = update.callback_query
    user_id_to_reject = int(query.data.replace(config.CALLBACK_REJECT_USER, ""))

    if db.reject_user_request(user_id_to_reject):
        await query.edit_message_text(f"❌ تم رفض طلب المستخدم {user_id_to_reject}.")
        # إرسال إشعار للمستخدم
        await context.bot.send_message(
            chat_id=user_id_to_reject,
            text=config.UI_MESSAGES['user_rejected_message']
        )
    else:
        await query.edit_message_text(f"حدث خطأ أثناء رفض طلب المستخدم {user_id_to_reject}.")
