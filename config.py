import json
import logging

# إعداد اللوجر
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_config(filename="config.json"):
    """تحميل الإعدادات من ملف JSON."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"ملف الإعدادات '{filename}' غير موجود.")
        return None
    except json.JSONDecodeError:
        logger.error(f"خطأ في تحليل ملف JSON '{filename}'.")
        return None

# تحميل الإعدادات عند بدء تشغيل الوحدة
config_data = load_config()

if config_data:
    # --- الإعدادات العامة ---
    BOT_TOKEN = config_data.get('configuration', {}).get('bot_token')
    BOT_USERNAME = config_data.get('configuration', {}).get('bot_username')
    ADMIN_ID = config_data.get('configuration', {}).get('admin_id')
    OFFICIAL_CHANNEL = config_data.get('configuration', {}).get('official_channel')
    WELCOME_MESSAGE = config_data.get('configuration', {}).get('welcome_message')
    APPROVAL_REQUIRED = config_data.get('configuration', {}).get('approval_required', True)
    MAX_CHANNELS_PER_USER = config_data.get('configuration', {}).get('max_channels_per_user', 3)
    DEFAULT_POST_SIGNATURE = config_data.get('configuration', {}).get('default_post_signature')

    # --- إعدادات الذكاء الاصطناعي ---
    AI_PROVIDER = config_data.get('ai_settings', {}).get('provider')
    GEMINI_API_KEY = config_data.get('ai_settings', {}).get('api_key')
    GEMINI_MODEL_NAME = config_data.get('ai_settings', {}).get('model_name', 'gemini-pro')
    TEXT_GEN_PARAMS = config_data.get('ai_settings', {}).get('text_generation_parameters', {})
    CONTENT_PROMPTS = config_data.get('ai_settings', {}).get('content_types_and_prompts', {})

    # --- رسائل واجهة المستخدم ---
    UI_MESSAGES = config_data.get('user_management_and_approval', {}).get('ui_messages', {})

    # --- أزرار واجهة المستخدم ---
    UI_BUTTONS = config_data.get('ui_elements', {}).get('buttons', {})

    # --- أنواع المحتوى ---
    CONTENT_TYPES = list(CONTENT_PROMPTS.keys())

    # --- بنية البيانات (للاستخدام في أماكن أخرى إذا لزم الأمر) ---
    DATABASE_SCHEMA = config_data.get('database_schema', {})

else:
    # قيم افتراضية في حالة فشل تحميل الإعدادات
    logger.critical("فشل تحميل ملف الإعدادات. سيتم استخدام قيم فارغة، وقد لا يعمل البوت بشكل صحيح.")
    BOT_TOKEN = None
    ADMIN_ID = None
    GEMINI_API_KEY = None
    # ... يمكن إضافة المزيد من القيم الافتراضية هنا
    # ... This is a fallback, but the bot will likely fail to start without a token.

# --- ثوابت المحادثة ---
(SELECTING_ACTION, ADDING_CHANNEL, SETTING_CONTENT_TYPE,
 SETTING_SCHEDULE_DAYS, SETTING_SCHEDULE_TIME,
 WAITING_FOR_CHANNEL_USERNAME, WAITING_FOR_CUSTOM_TIME,
 POST_TOPIC, POST_CONFIRM, EDITING_CHANNEL_TYPE,
 EDITING_SCHEDULE_DAYS, EDITING_SCHEDULE_TIME,
 SELECTING_CHANNEL_FOR_SIGNATURE, WAITING_FOR_SIGNATURE,
 SELECTING_CHANNEL_FOR_POST, WAITING_FOR_TOPIC, CONFIRMING_POST) = range(17)

# --- تعريفات الكولباك (لتجنب الأخطاء الإملائية) ---
CALLBACK_REQUEST_APPROVAL = "request_approval"
CALLBACK_APPROVE_USER = "approve_"
CALLBACK_REJECT_USER = "reject_"
CALLBACK_ADMIN_PANEL = "admin_panel"
CALLBACK_PENDING_REQUESTS = "pending_requests"
CALLBACK_ADMIN_STATS = "admin_stats"
CALLBACK_ADD_CHANNEL = "add_channel"
CALLBACK_MY_CHANNELS = "my_channels"
CALLBACK_VIEW_CHANNEL = "view_channel_"
CALLBACK_EDIT_CHANNEL = "edit_"
CALLBACK_DELETE_CHANNEL = "delete_"
CALLBACK_CONFIRM_DELETE_CHANNEL = "confirm_delete_"
CALLBACK_TOGGLE_ACTIVE = "toggle_active_"
CALLBACK_EDIT_TYPE = "edit_type_"
CALLBACK_SAVE_TYPE = "save_type_"
CALLBACK_EDIT_SCHEDULE = "edit_schedule_"
CALLBACK_BACK_TO_CHANNELS = "back_to_channels"
CALLBACK_BACK_TO_MAIN = "back_to_main"
CALLBACK_CANCEL_SETUP = "cancel_setup"
CALLBACK_SAVE_CHANNEL = "save_channel"

# --- أيام الأسبوع للجدولة ---
DAYS_OF_WEEK = {
    "Monday": "الاثنين",
    "Tuesday": "الثلاثاء",
    "Wednesday": "الأربعاء",
    "Thursday": "الخميس",
    "Friday": "الجمعة",
    "Saturday": "السبت",
    "Sunday": "الأحد"
}
