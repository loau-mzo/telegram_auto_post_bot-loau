from functools import wraps
import config
import logging

logger = logging.getLogger(__name__)

def is_admin(func):
    """
    Decorator للتحقق مما إذا كان المستخدم هو الأدمن.
    يجب استخدامه على معالجات الأوامر التي تتطلب صلاحيات الأدمن.
    """
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != config.ADMIN_ID:
            logger.warning(f"محاولة وصول غير مصرح بها إلى أمر أدمن من قبل المستخدم {user_id}.")
            await update.message.reply_text("ليس لديك الصلاحية لاستخدام هذا الأمر.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped
