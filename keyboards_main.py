from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import config

def get_main_keyboard():
    """إنشاء لوحة المفاتيح الرئيسية للمستخدمين الموافق عليهم."""
    keyboard = [
        [config.UI_BUTTONS['generate_post'], config.UI_BUTTONS['schedule_post']],
        [config.UI_BUTTONS['configure_channel'], config.UI_BUTTONS['set_signature']],
        [config.UI_BUTTONS['official_channel']]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_request_approval_keyboard():
    """إنشاء زر مضمن لطلب الموافقة."""
    keyboard = [
        [InlineKeyboardButton(config.UI_BUTTONS['request_approval'], callback_data=config.CALLBACK_REQUEST_APPROVAL)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_main_keyboard():
    """إنشاء لوحة مفاتيح للعودة إلى القائمة الرئيسية."""
    keyboard = [
        ["🏠 الرئيسية"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
