from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import config

def get_admin_panel_keyboard():
    """إنشاء لوحة مفاتيح لوحة تحكم الأدمن."""
    keyboard = [
        [
            InlineKeyboardButton("📊 الإحصائيات", callback_data=config.CALLBACK_ADMIN_STATS),
            InlineKeyboardButton("👤 الطلبات المعلقة", callback_data=config.CALLBACK_PENDING_REQUESTS)
        ],
        [
            InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data=config.CALLBACK_BACK_TO_MAIN)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_approval_keyboard(user_id):
    """إنشاء أزرار الموافقة والرفض لطلب مستخدم."""
    keyboard = [
        [
            InlineKeyboardButton(config.UI_BUTTONS['admin_approve'], callback_data=f"{config.CALLBACK_APPROVE_USER}{user_id}"),
            InlineKeyboardButton(config.UI_BUTTONS['admin_reject'], callback_data=f"{config.CALLBACK_REJECT_USER}{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
