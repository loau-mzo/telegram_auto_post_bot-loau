import schedule
import time
import threading
import logging
import json
import asyncio
from telegram.ext import Application
from telegram.error import TelegramError

import database as db
import config
from utils_ai import generate_content

logger = logging.getLogger(__name__)

async def post_scheduled_content(bot, channel_id: str, content_type: str, custom_signature: str):
    """
    مهمة متكاملة لتوليد ونشر المحتوى لجدولة معينة.
    """
    logger.info(f"بدء مهمة مجدولة للقناة {channel_id} من نوع {content_type}")
    try:
        # 1. توليد المحتوى
        # الموضوع هنا يمكن تطويره ليكون ديناميكياً في المستقبل
        # حالياً، سنستخدم نوع المحتوى كموضوع مبدئي
        topic = f"آخر التطورات في مجال {content_type}"
        content = await generate_content(content_type, topic)

        if "خطأ:" in content:
            logger.error(f"فشل توليد المحتوى للقناة {channel_id}: {content}")
            return

        # 2. إضافة التوقيع
        signature = custom_signature or config.DEFAULT_POST_SIGNATURE
        full_post = f"{content}\n\n{signature}"

        # 3. إرسال المنشور
        await bot.send_message(chat_id=channel_id, text=full_post)
        logger.info(f"تم نشر محتوى مجدول بنجاح في القناة {channel_id}")

        # 4. تسجيل المنشور في قاعدة البيانات
        db.log_published_post(channel_id, content)

    except TelegramError as e:
        logger.error(f"خطأ Telegram أثناء النشر في القناة {channel_id}: {e}")
        # قد نحتاج إلى التعامل مع الأخطاء مثل عدم وجود البوت في القناة
        if "bot is not a member" in str(e):
            logger.warning(f"البوت ليس عضواً في القناة {channel_id}. سيتم تعطيل القناة.")
            db.update_channel_active_status(channel_id, False)
            # يجب إعادة تحميل الجدولة لإزالة هذه القناة
            return "reload_schedule"

    except Exception as e:
        logger.error(f"خطأ غير متوقع في المهمة المجدولة للقناة {channel_id}: {e}")


def job_wrapper(bot, channel_id, content_type, signature):
    """
    غلاف لتشغيل الدالة غير المتزامنة في حلقة حدث جديدة
    """
    asyncio.run(post_scheduled_content(bot, channel_id, content_type, signature))


def setup_scheduler(bot):
    """
    إعداد جميع المهام المجدولة بناءً على القنوات النشطة في قاعدة البيانات.
    """
    schedule.clear() # مسح الجدولة القديمة قبل إضافة الجديدة
    logger.info("بدء إعداد جدولة النشر...")

    active_channels = db.get_all_active_channels()
    if not active_channels:
        logger.info("لا توجد قنوات نشطة لجدولتها.")
        return

    for channel in active_channels:
        channel_id = channel['channel_id']
        content_type = channel['content_type']
        signature = channel['custom_signature']

        try:
            schedule_data = json.loads(channel['posting_schedule'])
            days = schedule_data.get('days', [])
            times = schedule_data.get('times', [])
        except (json.JSONDecodeError, TypeError):
            logger.error(f"فشل في تحليل جدول النشر للقناة {channel_id}. تم التجاوز.")
            continue

        for day in days:
            for post_time in times:
                job = schedule.every()

                # ربط اليوم بالدالة المناسبة في مكتبة schedule
                day_attr = day.lower()
                if hasattr(job, day_attr):
                    job = getattr(job, day_attr)
                else:
                    logger.error(f"اسم يوم غير صالح '{day}' للقناة {channel_id}")
                    continue

                # إعداد المهمة
                job.at(post_time).do(job_wrapper, bot, channel_id, content_type, signature)
                logger.info(f"تمت جدولة مهمة للقناة {channel_id} في يوم {day} الساعة {post_time}")

    logger.info(f"تم الانتهاء من إعداد الجدولة. إجمالي المهام المجدولة: {len(schedule.get_jobs())}")


def run_pending_jobs():
    """
    تشغيل المهام المعلقة في حلقة لا نهائية.
    يجب تشغيل هذه الدالة في thread منفصل.
    """
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler_thread(application: Application):
    """
    إعداد وبدء thread الجدولة.
    """
    bot = application.bot
    setup_scheduler(bot)

    scheduler_thread = threading.Thread(target=run_pending_jobs, daemon=True)
    scheduler_thread.start()
    logger.info("تم بدء thread الجدولة في الخلفية.")
