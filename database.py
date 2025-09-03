import sqlite3
import json
import logging
from datetime import datetime

# إعداد اللوجر
logger = logging.getLogger(__name__)

DB_FILE = "bot_database.db"

def get_db_connection():
    """إنشاء وإرجاع اتصال بقاعدة البيانات."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    # تفعيل مفاتيح الربط الخارجية
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """تهيئة قاعدة البيانات وإنشاء الجداول إذا لم تكن موجودة."""
    schema_query = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        is_approved BOOLEAN DEFAULT FALSE,
        approval_date TIMESTAMP,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS channels (
        channel_id TEXT PRIMARY KEY,
        channel_username TEXT,
        owner_id INTEGER,
        content_type TEXT,
        posting_schedule TEXT,
        custom_signature TEXT,
        active BOOLEAN DEFAULT TRUE,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS approval_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        response_date TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS published_content (
        content_id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT,
        content_text TEXT,
        post_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (channel_id) REFERENCES channels (channel_id) ON DELETE SET NULL
    );
    """
    try:
        with get_db_connection() as conn:
            conn.executescript(schema_query)
            logger.info("تم تهيئة قاعدة البيانات بنجاح.")
    except sqlite3.Error as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")


# --- دوال إدارة المستخدمين (Users) ---

def add_or_update_user(user_id, username, first_name, last_name):
    """إضافة مستخدم جديد أو تحديث بياناته إذا كان موجوداً."""
    sql = """
    INSERT INTO users (user_id, username, first_name, last_name, created_date)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        username=excluded.username,
        first_name=excluded.first_name,
        last_name=excluded.last_name;
    """
    try:
        with get_db_connection() as conn:
            conn.execute(sql, (user_id, username, first_name, last_name, datetime.now()))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"خطأ في إضافة/تحديث المستخدم {user_id}: {e}")

def get_user(user_id):
    """الحصول على بيانات مستخدم معين."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"خطأ في الحصول على بيانات المستخدم {user_id}: {e}")
        return None

def is_user_approved(user_id):
    """التحقق مما إذا كان المستخدم قد تمت الموافقة عليه."""
    user = get_user(user_id)
    return user['is_approved'] if user else False

def approve_user(user_id):
    """الموافقة على مستخدم وتحديث حالة طلبه."""
    try:
        with get_db_connection() as conn:
            conn.execute("UPDATE users SET is_approved = TRUE, approval_date = ? WHERE user_id = ?", (datetime.now(), user_id))
            conn.execute("UPDATE approval_requests SET status = 'approved', response_date = ? WHERE user_id = ?", (datetime.now(), user_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"خطأ في الموافقة على المستخدم {user_id}: {e}")
        return False

def reject_user_request(user_id):
    """رفض طلب مستخدم."""
    try:
        with get_db_connection() as conn:
            conn.execute("UPDATE approval_requests SET status = 'rejected', response_date = ? WHERE user_id = ?", (datetime.now(), user_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"خطأ في رفض طلب المستخدم {user_id}: {e}")
        return False

def get_user_stats():
    """الحصول على إحصائيات المستخدمين."""
    try:
        with get_db_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            approved = conn.execute("SELECT COUNT(*) FROM users WHERE is_approved = TRUE").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM approval_requests WHERE status = 'pending'").fetchone()[0]
            return {"total": total, "approved": approved, "pending": pending}
    except sqlite3.Error as e:
        logger.error(f"خطأ في الحصول على إحصائيات المستخدمين: {e}")
        return {"total": 0, "approved": 0, "pending": 0}

# --- دوال إدارة طلبات الموافقة (Approval Requests) ---

def create_approval_request(user_id):
    """إنشاء طلب موافقة جديد."""
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO approval_requests (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"المستخدم {user_id} لديه طلب موافقة موجود بالفعل.")
        return False
    except sqlite3.Error as e:
        logger.error(f"خطأ في إنشاء طلب موافقة للمستخدم {user_id}: {e}")
        return False

def has_pending_request(user_id):
    """التحقق مما إذا كان لدى المستخدم طلب موافقة معلق."""
    try:
        with get_db_connection() as conn:
            res = conn.execute("SELECT 1 FROM approval_requests WHERE user_id = ? AND status = 'pending'", (user_id,)).fetchone()
            return res is not None
    except sqlite3.Error as e:
        logger.error(f"خطأ في التحقق من طلبات المستخدم {user_id}: {e}")
        return False

def get_pending_requests():
    """الحصول على جميع طلبات الموافقة المعلقة مع بيانات المستخدم."""
    sql = """
    SELECT u.user_id, u.first_name, u.username
    FROM users u
    JOIN approval_requests ar ON u.user_id = ar.user_id
    WHERE ar.status = 'pending'
    """
    try:
        with get_db_connection() as conn:
            return conn.execute(sql).fetchall()
    except sqlite3.Error as e:
        logger.error(f"خطأ في الحصول على الطلبات المعلقة: {e}")
        return []

# --- دوال إدارة القنوات (Channels) ---

def add_channel(channel_id, channel_username, owner_id, content_type, posting_schedule, custom_signature):
    """إضافة قناة جديدة."""
    try:
        with get_db_connection() as conn:
            schedule_str = json.dumps(posting_schedule)
            sql = "INSERT INTO channels (channel_id, channel_username, owner_id, content_type, posting_schedule, custom_signature) VALUES (?, ?, ?, ?, ?, ?)"
            conn.execute(sql, (channel_id, channel_username, owner_id, content_type, schedule_str, custom_signature))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"خطأ في إضافة القناة {channel_id}: {e}")
        return False

def get_user_channels(user_id):
    """الحصول على جميع قنوات مستخدم معين."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM channels WHERE owner_id = ?", (user_id,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"خطأ في الحصول على قنوات المستخدم {user_id}: {e}")
        return []

def get_channel_count(user_id):
    """الحصول على عدد قنوات مستخدم معين."""
    try:
        with get_db_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM channels WHERE owner_id = ?", (user_id,)).fetchone()[0]
    except sqlite3.Error as e:
        logger.error(f"خطأ في حساب عدد قنوات المستخدم {user_id}: {e}")
        return 0

def get_all_active_channels():
    """الحصول على جميع القنوات النشطة لجدولة النشر."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM channels WHERE active = TRUE")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"خطأ في الحصول على القنوات النشطة: {e}")
        return []

def update_channel_active_status(channel_id, active):
    """تحديث حالة تفعيل القناة."""
    try:
        with get_db_connection() as conn:
            conn.execute("UPDATE channels SET active = ? WHERE channel_id = ?", (active, channel_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"خطأ في تحديث حالة القناة {channel_id}: {e}")
        return False

def update_channel_content_type(channel_id, new_type):
    """تحديث نوع محتوى القناة."""
    try:
        with get_db_connection() as conn:
            conn.execute("UPDATE channels SET content_type = ? WHERE channel_id = ?", (new_type, channel_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"خطأ في تحديث نوع محتوى القناة {channel_id}: {e}")
        return False

def update_channel_schedule(channel_id, new_schedule):
    """تحديث جدول نشر القناة."""
    try:
        with get_db_connection() as conn:
            schedule_str = json.dumps(new_schedule)
            conn.execute("UPDATE channels SET posting_schedule = ? WHERE channel_id = ?", (schedule_str, channel_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"خطأ في تحديث جدول نشر القناة {channel_id}: {e}")
        return False

def update_channel_signature(channel_id, new_signature):
    """تحديث التوقيع المخصص للقناة."""
    try:
        with get_db_connection() as conn:
            conn.execute("UPDATE channels SET custom_signature = ? WHERE channel_id = ?", (new_signature, channel_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"خطأ في تحديث توقيع القناة {channel_id}: {e}")
        return False

def get_channel(channel_id):
    """الحصول على بيانات قناة معينة."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"خطأ في الحصول على بيانات القناة {channel_id}: {e}")
        return None

def delete_channel(channel_id):
    """حذف قناة من قاعدة البيانات."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
            conn.commit()
            logger.info(f"تم حذف القناة {channel_id} بنجاح.")
            return True
    except sqlite3.Error as e:
        logger.error(f"خطأ في حذف القناة {channel_id}: {e}")
        return False

# --- دوال إدارة المحتوى المنشور ---

def log_published_post(channel_id, content_text):
    """تسجيل منشور تم نشره بنجاح."""
    try:
        with get_db_connection() as conn:
            sql = "INSERT INTO published_content (channel_id, content_text, post_date) VALUES (?, ?, ?)"
            conn.execute(sql, (channel_id, content_text, datetime.now()))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"خطأ في تسجيل المنشور للقناة {channel_id}: {e}")
