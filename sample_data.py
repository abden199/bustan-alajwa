#!/usr/bin/env python3
"""إدراج 30 فاتورة عينة بأنواع مختلفة"""

sample_invoices = [
    {"advId": 1, "amount": 1500, "taxableAmount": 1304, "taxAmount": 196, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-001", "costCenter": "مزرعة عرعر", "desc": "شراء أسمدة", "date": "2026-07-01", "notes": ""},
    {"advId": 1, "amount": 2300, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "إيصال عادي", "invoiceNo": "REC-001", "costCenter": "مزرعة عرعر", "desc": "مصاريف نقل", "date": "2026-07-02", "notes": ""},
    {"advId": 2, "amount": 3500, "taxableAmount": 3043, "taxAmount": 457, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-002", "costCenter": "مزرعة الاكحل", "desc": "علف حيواني", "date": "2026-07-03", "notes": ""},
    {"advId": 2, "amount": 1200, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "مذكرة دخول", "invoiceNo": "MEM-001", "costCenter": "مزرعة الاكحل", "desc": "خدمات بيطرية", "date": "2026-07-04", "notes": ""},
    {"advId": 3, "amount": 4500, "taxableAmount": 3913, "taxAmount": 587, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-003", "costCenter": "معمل البستان", "desc": "قطع غيار", "date": "2026-07-05", "notes": ""},
    {"advId": 3, "amount": 800, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "إيصال عادي", "invoiceNo": "REC-002", "costCenter": "معمل البستان", "desc": "وقود", "date": "2026-07-06", "notes": ""},
    {"advId": 4, "amount": 2800, "taxableAmount": 2435, "taxAmount": 365, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-004", "costCenter": "سكن العمال", "desc": "مواد بناء", "date": "2026-07-07", "notes": ""},
    {"advId": 4, "amount": 1500, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "مذكرة دخول", "invoiceNo": "MEM-002", "costCenter": "سكن العمال", "desc": "أثاث", "date": "2026-07-08", "notes": ""},
    {"advId": 5, "amount": 3200, "taxableAmount": 2783, "taxAmount": 417, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-005", "costCenter": "المحمية", "desc": "معدات صيانة", "date": "2026-07-09", "notes": ""},
    {"advId": 5, "amount": 950, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "إيصال عادي", "invoiceNo": "REC-003", "costCenter": "المحمية", "desc": "مستلزمات", "date": "2026-07-10", "notes": ""},
    {"advId": 1, "amount": 5000, "taxableAmount": 4348, "taxAmount": 652, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-006", "costCenter": "مزرعة عرعر", "desc": "بذور محسنة", "date": "2026-07-11", "notes": ""},
    {"advId": 2, "amount": 2200, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "إيصال عادي", "invoiceNo": "REC-004", "costCenter": "مزرعة الاكحل", "desc": "خدمات استشارية", "date": "2026-07-12", "notes": ""},
    {"advId": 3, "amount": 6500, "taxableAmount": 5652, "taxAmount": 848, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-007", "costCenter": "معمل البستان", "desc": "آلات صناعية", "date": "2026-07-13", "notes": ""},
    {"advId": 4, "amount": 3300, "taxableAmount": 2870, "taxAmount": 430, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-008", "costCenter": "سكن البستان", "desc": "تصليحات", "date": "2026-07-14", "notes": ""},
    {"advId": 5, "amount": 1800, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "مذكرة دخول", "invoiceNo": "MEM-003", "costCenter": "المكتب", "desc": "متطلبات إدارية", "date": "2026-07-15", "notes": ""},
    {"advId": 1, "amount": 2700, "taxableAmount": 2348, "taxAmount": 352, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-009", "costCenter": "الصيانة", "desc": "أجهزة مراقبة", "date": "2026-07-16", "notes": ""},
    {"advId": 2, "amount": 4100, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "إيصال عادي", "invoiceNo": "REC-005", "costCenter": "مزرعة الابل", "desc": "علاجات بيطرية", "date": "2026-07-17", "notes": ""},
    {"advId": 3, "amount": 3600, "taxableAmount": 3130, "taxAmount": 470, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-010", "costCenter": "مزرعة الغنم", "desc": "مستحضرات عناية", "date": "2026-07-18", "notes": ""},
    {"advId": 4, "amount": 2500, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "مذكرة دخول", "invoiceNo": "MEM-004", "costCenter": "خاص", "desc": "خدمات نقل", "date": "2026-07-19", "notes": ""},
    {"advId": 5, "amount": 4800, "taxableAmount": 4174, "taxAmount": 626, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-011", "costCenter": "مركز التوزيع", "desc": "تغليف ومواد", "date": "2026-07-20", "notes": ""},
    {"advId": 1, "amount": 3400, "taxableAmount": 2957, "taxAmount": 443, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-012", "costCenter": "مزرعة عرعر", "desc": "معدات زراعية", "date": "2026-07-21", "notes": ""},
    {"advId": 2, "amount": 1900, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "إيصال عادي", "invoiceNo": "REC-006", "costCenter": "مزرعة الاكحل", "desc": "استشارات فنية", "date": "2026-07-22", "notes": ""},
    {"advId": 3, "amount": 5200, "taxableAmount": 4522, "taxAmount": 678, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-013", "costCenter": "معمل البستان", "desc": "خام الإنتاج", "date": "2026-07-23", "notes": ""},
    {"advId": 4, "amount": 2100, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "مذكرة دخول", "invoiceNo": "MEM-005", "costCenter": "الديرة", "desc": "أدوات يدوية", "date": "2026-07-24", "notes": ""},
    {"advId": 5, "amount": 3900, "taxableAmount": 3391, "taxAmount": 509, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-014", "costCenter": "المحمية", "desc": "تجهيزات", "date": "2026-07-25", "notes": ""},
    {"advId": 1, "amount": 2600, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "إيصال عادي", "invoiceNo": "REC-007", "costCenter": "مزرعة عرعر", "desc": "خدمات توصيل", "date": "2026-07-26", "notes": ""},
    {"advId": 2, "amount": 4400, "taxableAmount": 3826, "taxAmount": 574, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-015", "costCenter": "مزرعة الاكحل", "desc": "مستلزمات الإنتاج", "date": "2026-07-27", "notes": ""},
    {"advId": 3, "amount": 3100, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "مذكرة دخول", "invoiceNo": "MEM-006", "costCenter": "معمل البستان", "desc": "تدريب وتطوير", "date": "2026-07-28", "notes": ""},
    {"advId": 4, "amount": 5500, "taxableAmount": 4783, "taxAmount": 717, "invoiceType": "فاتورة ضريبية", "invoiceNo": "INV-016", "costCenter": "سكن البستان", "desc": "تطوير البنية", "date": "2026-07-29", "notes": ""},
    {"advId": 5, "amount": 2400, "taxableAmount": 0, "taxAmount": 0, "invoiceType": "إيصال عادي", "invoiceNo": "REC-008", "costCenter": "المكتب", "desc": "أدوات مكتبية", "date": "2026-07-30", "notes": ""}
]

print(f"عدد الفواتير العينة: {len(sample_invoices)}")
for inv in sample_invoices:
    print(f"#{inv['invoiceNo']} - {inv['invoiceType']} - {inv['amount']} ر.س")
