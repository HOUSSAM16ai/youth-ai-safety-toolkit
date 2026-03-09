# تشريح جراحي لعطل عدّ ملفات بايثون في قناة الأدمن (بدون تعديل الشيفرة)

## 1) الملخص التنفيذي

العطل الظاهر في الواجهة (`All connection attempts failed` ثم `No response received from AI service`) ليس خللاً في سؤال الأدمن نفسه، بل **سلسلة انقطاع** في مسار التفويض من بوابة الأدمن إلى خدمة Orchestrator بعد الانتقال إلى نمط Microservices.

السبب الجذري الأرجح:
1. سؤال "كم عدد ملفات بايثون" يُصنَّف كـ `ADMIN_QUERY`.
2. هذا التصنيف يُحوِّل التنفيذ إجبارياً إلى `orchestrator-service` عبر HTTP.
3. عند فشل الاتصال بالشبكة/الاكتشاف الخدمي/المنفذ، يعود الخطأ: `All connection attempts failed`.
4. لا يوجد مسار fallback محلي يحسب العدد مباشرة كما كان ممكنًا عملياً في بنية Monolith.

النتيجة: النظام يفشل في **نقطة الربط بين الخدمات** لا في منطق العدّ ذاته.

---

## 2) الأعراض كما تظهر للمستخدم

- رسالة مباشرة: `Error connecting to agent: All connection attempts failed`.
- ثم في بعض الجلسات/إعادة التحميل: `Error: No response received from AI service.`

هذا النمط يتطابق مع سلوكين منفصلين:
- فشل اتصال العميل الداخلي بـ Orchestrator.
- ثم حفظ رد افتراضي لأن أي محتوى مساعد حقيقي لم يصل.

---

## 3) مسار التنفيذ الفعلي (Trace) من السؤال إلى الخطأ

### المرحلة A: تصنيف سؤال الأدمن

سؤال "كم عدد ملفات بايثون" يطابق صراحة قواعد `ADMIN_QUERY` لأن القاعدة تحتوي مفردات:
`count files` / `ملفات بايثون` / `python files`.

**النتيجة:** يدخل المسار الإداري بدل مسار أدوات محلية مباشرة.

### المرحلة B: التفويض الإجباري إلى Orchestrator Microservice

عند كون النية من نوع إداري/تحليلي، منسق الدردشة (`ChatOrchestrator`) يفعل `Delegating ... to OrchestratorAgent (Microservice)`، ثم يستدعي:

- `orchestrator_client.chat_with_agent(...)`
- endpoint الهدف: `POST {ORCHESTRATOR_SERVICE_URL}/agent/chat`

### المرحلة C: فشل الاتصال الشبكي

داخل `chat_with_agent` يوجد retry (3 محاولات) على `ConnectError/Timeout`.
عند فشل كل المحاولات يُولَّد حدث:

```json
{
  "type": "assistant_error",
  "payload": {"content": "Error connecting to agent: <exception>"}
}
```

ولذلك تظهر عبارة `All connection attempts failed`.

### المرحلة D: ظهور رسالة "No response received"

في طبقة `AdminChatStreamer`، التخزين النهائي يعتمد على تجميع نصوص delta.
إذا لم يصل نص فعلي (فقط أحداث خطأ/metadata)، يتم حفظ:

`Error: No response received from AI service.`

أي أن هذه الرسالة **ثانوية** ناتجة عن غياب chunks نصية ناجحة.

---

## 4) لماذا كان يعمل سابقًا في المونوليث وأصبح هشًا الآن؟

في المونوليث، تنفيذ مهام مثل "عدّ ملفات بايثون" كان يمكن أن يتم داخل نفس العملية (local tool execution) دون قفزة شبكية بين خدمات.

بعد التحول إلى microservices:
- المسار أصبح: `Admin WS -> ChatOrchestrator -> OrchestratorClient -> Orchestrator Service`.
- أي تعطل DNS/منفذ/health/route في أي نقطة = فشل كامل للمهمة.
- لا يوجد "رجوع تلقائي" إلى عدّ محلي عندما تكون مهمة إحصائية بسيطة.

إذن الانتقال المعماري نقل نقطة الفشل من "منطق الأداة" إلى "بنية الاتصال بين الخدمات".

---

## 5) القرائن التقنية الأقوى (Root Cause Evidence)

### قرينة 1: التصنيف الإداري يلتقط استعلام عدّ الملفات مباشرة
نمط `ADMIN_QUERY` يشمل `count files` و`python files` و`ملفات بايثون`.
=> الاستعلام يذهب للمسار الميكروسيرفسي الإداري.

### قرينة 2: التفويض إلى Orchestrator يتم قبل أي fallback محلي
`ChatOrchestrator.process` عند `ADMIN_QUERY` يستدعي `orchestrator_client.chat_with_agent` ثم `return`.
=> لا استكمال للمعالجات التقليدية المحلية في هذا المسار.

### قرينة 3: رسالة الخطأ المعروضة مولّدة حرفياً من عميل Orchestrator
`orchestrator_client` يُنتج `Error connecting to agent: {e}` عند الاستثناء.
=> نص الخطأ الظاهر في الصورة متسق 1:1 مع الكود.

### قرينة 4: إعدادات URL تحمل مخاطرة بيئية (خصوصًا خارج docker-compose المتناسق)
الدالة `_resolve_service_url` تضبط:
`ORCHESTRATOR_SERVICE_URL -> ("8006", "localhost", "8006")`
بينما بقية الخدمات تستخدم أسماء خدمات Docker (`user-service`, `research-agent`, ...).

هذا يعني أن أي بيئة تتوقع service-discovery بالاسم قد تتلقى `localhost` غير صحيح داخل الحاوية/العقدة، وبالتالي `ConnectError`.

### قرينة 5: رسالة "No response received..." ناتجة عن empty assistant buffer
`AdminChatStreamer._persist_response` إذا كان الرد المجمّع فارغًا يكتب الرسالة الافتراضية.
=> يفسر الصورة الثانية بدون تناقض.

---

## 6) تحليل معماري وفق API-First + Microservices Constitution

**ما هو صحيح معماريًا:**
- فصل القرار الإداري إلى خدمة Orchestrator مستقلة ينسجم مع API-first.
- عدم الوصول المباشر لطبقات خارج الخدمة ينسجم مع الاستقلالية.

**ما الذي انكسر وظيفيًا (Operational gap):**
- غياب resilience pattern على مستوى المنتج (Fallback/Circuit Open UX).
- ربط استعلامات إدارية بسيطة بمسار شبكة إلزامي دون degraded mode.
- اتساع الفجوة بين `event contracts` (مثلاً `assistant_error`) وبين عرض الواجهة وطبقة التخزين النصي.

**الخلاصة:** الالتزام الشكلي بالميكروسيرفس موجود، لكن الاعتمادية التشغيلية لم تُغلق الحلقة end-to-end.

---

## 7) تشخيص احتمالي مرتب (من الأكثر إلى الأقل احتمالاً)

1. **عدم قابلية الوصول إلى orchestrator-service** (DNS/port/service down/network policy).
2. **قيمة `ORCHESTRATOR_SERVICE_URL` غير مناسبة لبيئة التشغيل** (خاصة default `localhost`).
3. **مشكلة health/startup ordering**: الطلب يصل قبل جاهزية orchestrator.
4. **انقطاع وسيط API Gateway/WebSocket proxy** إذا كان المسار يمر عبر طبقة وسيطة.
5. **أخطاء داخل endpoint `/agent/chat`** (أقل احتمالًا هنا لأن الرسالة تشير لفشل اتصال قبل استجابة HTTP).

---

## 8) لماذا الخلل يظهر تحديدًا في سؤال "كم عدد ملفات بايثون"؟

لأن هذا السؤال أصبح "إشارة توجيه" إلى intent إداري مع تفويض microservice، وليس مجرد استدعاء أداة shell محلية.

بعبارة دقيقة:
- سابقًا: `question -> local shell tool -> count`.
- الآن: `question -> intent=ADMIN_QUERY -> remote orchestrator -> (network fail) -> error`.

إذًا المشكلة ليست في عملية العدّ، بل في **توجيه السؤال إلى مسار بعيد غير متاح**.

---

## 9) خطة تحقق تشخيصية (بدون أي تعديل شيفرة)

1. التحقق من قيمة `ORCHESTRATOR_SERVICE_URL` الفعلية داخل حاوية/خدمة الـ backend وقت التشغيل.
2. اختبار اتصال مباشر من backend إلى `{ORCHESTRATOR_SERVICE_URL}/health`.
3. اختبار endpoint `{ORCHESTRATOR_SERVICE_URL}/agent/chat` بطلب تجريبي minimal.
4. مراجعة logs زمنياً:
   - `ChatOrchestrator` (لحظة التفويض).
   - `orchestrator-client` (تفاصيل connect error).
   - orchestrator-service (هل وصله أي طلب أصلًا).
5. مقارنة بيئة النجاح السابقة (monolith/dev) ببيئة الفشل الحالية (service discovery + ingress + container network).

---

## 10) الحكم النهائي (Final Surgical Verdict)

العطل ناتج عن **انقطاع في طبقة الربط بين الخدمات** بعد تحويل الأسئلة الإدارية إلى مسار Orchestrator إجباري، مع غياب fallback تشغيلي محلي لنفس المهمة البسيطة.

لذلك ظهر للمسؤول:
- أولاً: `Error connecting to agent: All connection attempts failed` (فشل transport).
- ثم: `No response received from AI service` (أثر جانبي لحفظ رد فارغ).

النظام لم يفقد قدرة "عدّ الملفات" منطقياً؛ بل فقد **المسار الموثوق للوصول إلى هذه القدرة** ضمن البنية الموزعة.
