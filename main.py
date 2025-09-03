import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
import database as db
from handlers_commands import start, admin_panel, my_channels, add_channel_start, add_channel_start_callback, cancel, help_command
from handlers_callbacks import handle_callback_query
from handlers_messages import (
    handle_text_buttons,
    handle_channel_username,
    handle_content_type,
    handle_schedule_days,
    handle_schedule_time,
    save_channel,
    edit_content_type_start,
    edit_content_type_select,
    edit_schedule_start,
    edit_schedule_days,
    edit_schedule_times,
    signature_start,
    signature_channel_selected,
    signature_receive,
    cancel_action,
    post_start,
    post_select_channel,
    post_receive_topic,
    post_confirm_action,
)
from utils_schedule import start_scheduler_thread

# إعداد اللوجر
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """بدء تشغيل البوت."""
    # التحقق من وجود التوكن
    if not config.BOT_TOKEN:
        logger.critical("خطأ فادح: توكن البوت غير موجود. يرجى إضافته إلى config.json")
        return

    # تهيئة قاعدة البيانات
    db.init_db()

    # إنشاء التطبيق
    application = Application.builder().token(config.BOT_TOKEN).build()

    # --- إعداد محادثة إضافة القناة ---
    add_channel_conv = ConversationHandler(
        entry_points=[
            CommandHandler("add_channel", add_channel_start),
            CallbackQueryHandler(add_channel_start_callback, pattern=f"^{config.CALLBACK_ADD_CHANNEL}$")
        ],
        states={
            config.WAITING_FOR_CHANNEL_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_username)
            ],
            config.SETTING_CONTENT_TYPE: [
                CallbackQueryHandler(handle_content_type, pattern="^type_")
            ],
            config.SETTING_SCHEDULE_DAYS: [
                CallbackQueryHandler(handle_schedule_days, pattern="^day_"),
                CallbackQueryHandler(handle_schedule_days, pattern="^days_done$")
            ],
            config.SETTING_SCHEDULE_TIME: [
                CallbackQueryHandler(handle_schedule_time, pattern="^time_"),
                CallbackQueryHandler(save_channel, pattern=f"^{config.CALLBACK_SAVE_CHANNEL}$")
                # Note: custom_time handler would need another state if we were to implement it fully
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        # Allow re-entry into the conversation
        allow_reentry=True
    )

    # --- إعداد محادثة تعديل نوع المحتوى ---
    edit_type_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_content_type_start, pattern=f"^{config.CALLBACK_EDIT_TYPE}")],
        states={
            config.EDITING_CHANNEL_TYPE: [
                CallbackQueryHandler(edit_content_type_select, pattern="^type_")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        # A conversation can be started again at any time
        allow_reentry=True
    )

    # --- إعداد محادثة تعديل جدول النشر ---
    edit_schedule_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_schedule_start, pattern=f"^{config.CALLBACK_EDIT_SCHEDULE}")],
        states={
            config.EDITING_SCHEDULE_DAYS: [
                CallbackQueryHandler(edit_schedule_days, pattern="^day_"),
                CallbackQueryHandler(edit_schedule_days, pattern="^days_done$")
            ],
            config.EDITING_SCHEDULE_TIME: [
                CallbackQueryHandler(edit_schedule_times, pattern="^time_"),
                CallbackQueryHandler(edit_schedule_times, pattern=f"^{config.CALLBACK_SAVE_CHANNEL}$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    # --- إعداد محادثة تعديل التوقيع ---
    edit_sig_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{config.UI_BUTTONS['set_signature']}$"), signature_start)],
        states={
            config.SELECTING_CHANNEL_FOR_SIGNATURE: [
                CallbackQueryHandler(signature_channel_selected, pattern="^sig_channel_")
            ],
            config.WAITING_FOR_SIGNATURE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, signature_receive)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$")
        ],
        allow_reentry=True
    )

    # --- إعداد محادثة إنشاء منشور فوري ---
    post_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{config.UI_BUTTONS['generate_post']}$"), post_start)],
        states={
            config.SELECTING_CHANNEL_FOR_POST: [
                CallbackQueryHandler(post_select_channel, pattern="^post_channel_")
            ],
            config.WAITING_FOR_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, post_receive_topic)
            ],
            config.CONFIRMING_POST: [
                CallbackQueryHandler(post_confirm_action, pattern="^post_")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$")
        ],
        allow_reentry=True
    )

    # --- تسجيل المعالجات ---
    application.add_handler(add_channel_conv)
    application.add_handler(edit_type_conv)
    application.add_handler(edit_schedule_conv)
    application.add_handler(edit_sig_conv)
    application.add_handler(post_conv)

    # الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("my_channels", my_channels))

    # الكولباكات (التي ليست جزءاً من المحادثة)
    # This handler will catch all callbacks that are not handled by the ConversationHandler
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # معالج الرسائل النصية (لأزرار القائمة الرئيسية)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))

    # بدء thread الجدولة
    logger.info("Starting scheduler thread...")
    start_scheduler_thread(application)

    # بدء تشغيل البوت
    logger.info("Starting bot polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
