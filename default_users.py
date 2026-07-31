#!/usr/bin/env python3
"""إضافة مستخدم افتراضي وإصلاح مشاكل الدخول"""

# إضافة مستخدمين افتراضيين
default_users = [
    {
        "id": 1,
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "name": "مدير النظام",
        "active": True
    },
    {
        "id": 2,
        "username": "user",
        "password": "user123",
        "role": "user",
        "name": "مستخدم",
        "active": True
    }
]

# يجب إضافة هؤلاء المستخدمين إلى قاعدة البيانات
# أو تحديث app.py لإضافتهم تلقائياً عند التشغيل الأول

print("المستخدمون الافتراضيون:")
for user in default_users:
    print(f"  - {user['username']}: {user['password']} ({user['name']})")
