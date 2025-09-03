import logging
import json
from telegram import Update

logger = logging.getLogger(__name__)

def get_user_data_from_update(update: Update):
    """استخلاص بيانات المستخدم من كائن التحديث."""
    if update.callback_query:
        user = update.callback_query.from_user
    elif update.message:
        user = update.message.from_user
    else:
        return None

    return {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }

def clean_channel_id(channel_input: str) -> str:
    """
    تنظيف معرف القناة أو الرابط المدخل من قبل المستخدم.
    يحول t.me/channelname أو @channelname إلى channelname.
    """
    if not channel_input:
        return ""

    if "t.me/" in channel_input:
        channel_input = channel_input.split("t.me/")[1]

    if channel_input.startswith("@"):
        return channel_input

    return f"@{channel_input}"


def parse_schedule_from_db(schedule_json: str):
    """
    تحويل سلسلة JSON الخاصة بالجدولة من قاعدة البيانات إلى كائن Python.
    """
    try:
        return json.loads(schedule_json)
    except (json.JSONDecodeError, TypeError):
        # إرجاع قيمة افتراضية في حالة الخطأ أو إذا كانت القيمة فارغة
        return {"days": [], "times": []}
