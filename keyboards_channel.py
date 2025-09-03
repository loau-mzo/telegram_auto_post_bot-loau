from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config

def get_content_type_keyboard():
    """إنشاء لوحة مفاتيح لاختيار نوع المحتوى."""
    keyboard = []
    row = []
    for content_type in config.CONTENT_TYPES:
        row.append(InlineKeyboardButton(content_type.capitalize(), callback_data=f"type_{content_type}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=config.CALLBACK_CANCEL_SETUP)])
    return InlineKeyboardMarkup(keyboard)

def get_schedule_days_keyboard(selected_days=None):
    """إنشاء لوحة مفاتيح لاختيار أيام النشر. `selected_days` هو set."""
    if selected_days is None:
        selected_days = set()

    keyboard = []
    days = list(config.DAYS_OF_WEEK.keys())

    for i in range(0, len(days), 2):
        row = []
        for j in range(2):
            if i + j < len(days):
                day_en = days[i+j]
                day_ar = config.DAYS_OF_WEEK[day_en]
                text = f"✅ {day_ar}" if day_en in selected_days else day_ar
                row.append(InlineKeyboardButton(text, callback_data=f"day_{day_en}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("✅ تم (الانتقال لاختيار الوقت)", callback_data="days_done")])
    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=config.CALLBACK_CANCEL_SETUP)])
    return InlineKeyboardMarkup(keyboard)

def get_schedule_times_keyboard(selected_times=None):
    """إنشاء لوحة مفاتيح لاختيار أوقات النشر. `selected_times` هو set."""
    if selected_times is None:
        selected_times = set()

    predefined_times = ["08:00", "12:00", "16:00", "20:00"]
    keyboard = []
    row = []
    for time in predefined_times:
        text = f"✅ {time}" if time in selected_times else time
        row.append(InlineKeyboardButton(text, callback_data=f"time_{time}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⏰ إدخال وقت مخصص", callback_data="custom_time")])
    keyboard.append([InlineKeyboardButton("💾 حفظ القناة", callback_data=config.CALLBACK_SAVE_CHANNEL)])
    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=config.CALLBACK_CANCEL_SETUP)])
    return InlineKeyboardMarkup(keyboard)

def get_channel_saved_keyboard():
    """إنشاء لوحة مفاتيح بعد حفظ القناة بنجاح."""
    keyboard = [
        [InlineKeyboardButton("✨ إنشاء منشور الآن", callback_data="create_post_now")],
        [InlineKeyboardButton("➕ إضافة قناة أخرى", callback_data=config.CALLBACK_ADD_CHANNEL)],
        [InlineKeyboardButton("📺 عرض قنواتي", callback_data=config.CALLBACK_MY_CHANNELS)],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_my_channels_keyboard(channels):
    """إنشاء لوحة مفاتيح تعرض قنوات المستخدم."""
    keyboard = []
    if not channels:
        keyboard.append([InlineKeyboardButton("➕ لم تقم بإضافة أي قناة بعد، إضغط هنا للإضافة", callback_data=config.CALLBACK_ADD_CHANNEL)])
    else:
        for channel in channels:
            # channel is a sqlite3.Row object
            channel_name = channel['channel_username'] or f"ID: {channel['channel_id']}"
            status = "🟢" if channel['active'] else "🔴"
            keyboard.append([InlineKeyboardButton(f"{status} {channel_name}", callback_data=f"{config.CALLBACK_EDIT_CHANNEL}{channel['channel_id']}")])
        keyboard.append([InlineKeyboardButton("➕ إضافة قناة جديدة", callback_data=config.CALLBACK_ADD_CHANNEL)])

    keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data=config.CALLBACK_BACK_TO_MAIN)])
    return InlineKeyboardMarkup(keyboard)

def get_edit_channel_keyboard(channel_id, is_active):
    """إنشاء لوحة مفاتيح لتعديل قناة."""
    status_text = "🔴 تعطيل النشر" if is_active else "🟢 تفعيل النشر"
    status_callback = f"{config.CALLBACK_TOGGLE_ACTIVE}{channel_id}"

    keyboard = [
        [InlineKeyboardButton("📝 تعديل نوع المحتوى", callback_data=f"{config.CALLBACK_EDIT_TYPE}{channel_id}")],
        [InlineKeyboardButton("⏰ تعديل جدول النشر", callback_data=f"{config.CALLBACK_EDIT_SCHEDULE}{channel_id}")],
        [InlineKeyboardButton(status_text, callback_data=status_callback)],
        [InlineKeyboardButton("🗑️ حذف القناة", callback_data=f"{config.CALLBACK_DELETE_CHANNEL}{channel_id}")],
        [InlineKeyboardButton("🔙 العودة لقائمة قنواتي", callback_data=config.CALLBACK_BACK_TO_CHANNELS)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirm_delete_keyboard(channel_id):
    """إنشاء لوحة مفاتيح لتأكيد حذف القناة."""
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، متأكد", callback_data=f"{config.CALLBACK_CONFIRM_DELETE_CHANNEL}{channel_id}"),
            InlineKeyboardButton("❌ لا، تراجعت", callback_data=f"{config.CALLBACK_EDIT_CHANNEL}{channel_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_select_channel_keyboard(channels, callback_prefix: str):
    """إنشاء لوحة مفاتيح لاختيار قناة من قائمة."""
    keyboard = []
    if not channels:
        # This case should be handled before calling the keyboard function
        return None

    for channel in channels:
        channel_name = channel['channel_username'] or f"ID: {channel['channel_id']}"
        keyboard.append([InlineKeyboardButton(channel_name, callback_data=f"{callback_prefix}{channel['channel_id']}")])

    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_action")])
    return InlineKeyboardMarkup(keyboard)

def get_confirm_post_keyboard():
    """إنشاء لوحة مفاتيح لتأكيد نشر المنشور."""
    keyboard = [
        [
            InlineKeyboardButton("✅ نشر الآن", callback_data="post_confirm"),
            InlineKeyboardButton("✏️ تعديل الموضوع", callback_data="post_edit"),
            InlineKeyboardButton("❌ إلغاء", callback_data="post_cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
