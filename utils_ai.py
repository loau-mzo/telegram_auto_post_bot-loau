import logging
import google.generativeai as genai
import config

logger = logging.getLogger(__name__)

# التحقق من وجود مفتاح API
if not config.GEMINI_API_KEY:
    logger.error("مفتاح Google Gemini API غير موجود في ملف الإعدادات.")
    # يمكنك اختيار رفع استثناء هنا لإيقاف البوت إذا كان المفتاح ضرورياً
    # raise ValueError("Missing Google Gemini API Key")
else:
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إعداد Google Gemini API: {e}")

async def generate_content(content_type: str, topic: str) -> str:
    """
    توليد محتوى باستخدام Google Gemini API.

    Args:
        content_type: نوع المحتوى (e.g., 'technology', 'news').
        topic: الموضوع الذي سيتم الكتابة عنه.

    Returns:
        النص الذي تم توليده أو رسالة خطأ.
    """
    if not config.GEMINI_API_KEY:
        return "خطأ: مفتاح API للذكاء الاصطناعي غير مهيأ."

    prompt_template = config.CONTENT_PROMPTS.get(content_type)
    if not prompt_template:
        logger.error(f"لم يتم العثور على قالب للمحتوى من نوع '{content_type}'")
        return f"خطأ: نوع المحتوى '{content_type}' غير مدعوم."

    try:
        # إعداد النموذج
        generation_config = genai.types.GenerationConfig(
            temperature=config.TEXT_GEN_PARAMS.get('temperature', 0.7),
            top_p=config.TEXT_GEN_PARAMS.get('top_p', 0.8),
            top_k=config.TEXT_GEN_PARAMS.get('top_k', 40),
            max_output_tokens=config.TEXT_GEN_PARAMS.get('max_output_tokens', 500)
        )
        model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL_NAME,
            generation_config=generation_config
        )

        # تكوين الطلب
        final_prompt = prompt_template.format(topic=topic)

        logger.info(f"إرسال طلب إلى Gemini API لنوع المحتوى: {content_type}, الموضوع: {topic}")

        # إرسال الطلب
        response = await model.generate_content_async(final_prompt)

        generated_text = response.text
        logger.info(f"تم استلام الرد من Gemini API بنجاح.")

        return generated_text

    except Exception as e:
        logger.error(f"حدث خطأ أثناء استدعاء Google Gemini API: {e}")
        return f"عذراً، حدث خطأ أثناء توليد المحتوى. يرجى المحاولة مرة أخرى لاحقاً. ({e})"
