import logging
from telegram import Update
from telegram.ext import ContextTypes

import database as db
from keyboards_admin import get_approval_keyboard, get_admin_panel_keyboard

logger = logging.getLogger(__name__)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    يعرض إحصائيات البوت للأدمن.
    يتم استدعاؤه عبر callback.
    """
    query = update.callback_query
    await query.answer()

    stats = db.get_user_stats()

    message = (
        "📊 إحصائيات البوت\n\n"
        f"إجمالي المستخدمين: {stats['total']}\n"
        f"المستخدمون الموافق عليهم: {stats['approved']}\n"
        f"الطلبات المعلقة: {stats['pending']}"
    )

    await query.edit_message_text(text=message, reply_markup=get_admin_panel_keyboard())


async def show_pending_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    يعرض طلبات الموافقة المعلقة للأدمن.
    يتم استدعاؤه عبر callback.
    """
    query = update.callback_query
    await query.answer()

    pending_list = db.get_pending_requests()

    if not pending_list:
        await query.edit_message_text(
            text="لا توجد طلبات موافقة معلقة حالياً.",
            reply_markup=get_admin_panel_keyboard()
        )
        return

    await query.edit_message_text(text="الطلبات المعلقة:")

    for user in pending_list:
        user_id = user['user_id']
        first_name = user['first_name']
        username = f"@{user['username']}" if user['username'] else "لا يوجد"

        message = (
            f"👤 طلب جديد:\n"
            f"الاسم: {first_name}\n"
            f"المعرف: `{user_id}`\n"
            f"اسم المستخدم: {username}"
        )

        # إرسال كل طلب في رسالة منفصلة مع أزرار الموافقة/الرفض
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=get_approval_keyboard(user_id),
            parse_mode='Markdown'
        )
