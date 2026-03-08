# التشخيص الحرج الشامل: لماذا يفشل أدمن شات في إعطاء أرقام دقيقة (الملفات/الجداول/المستخدمين)

## 1) الملخص التنفيذي (Executive Summary)

المشكلة **ليست** في نموذج الذكاء بحد ذاته، بل في سلسلة توجيه (Routing) وأدوات (Tooling) غير متكاملة عبر حدود المايكروسيرفس. النتيجة: عندما يطلب الأدمن عدًّا دقيقًا (مثل عدد ملفات بايثون أو عدد جداول قاعدة البيانات)، النظام غالبًا لا يدخل مسار Admin Tools الحقيقي، أو يدخله ثم لا يجد الأدوات المطلوبة مسجلة، فيعود إلى إجابة لغوية عامة/اعتذارية بدلاً من تنفيذ قياس فعلي.

**الخلاصة الجذرية:**
1. كشف النية في خدمة orchestrator المصغّرة لا يلتقط صياغات عربية حساسة مثل "كم عدد ملفات بايثون" ضمن ADMIN_QUERY بشكل موثوق.
2. عند السقوط إلى مسار fallback، يتم حقن Prompt تعليمي (Customer Tutor) يقيّد النطاق، فينتج رد عام بدل تنفيذ أدوات النظام.
3. سجل أدوات المايكروسيرفس لا يسجّل أدوات الأدمن الحسابية (users/tables/files) أثناء الإقلاع، بينما Admin Agent يطلب أسماء أدوات غير موجودة فعليًا.
4. يوجد عدم تطابق بين أسماء الأدوات التي يطلبها AdminAgent وبين الأدوات المسجلة فعليًا في registry.
5. جانب من المسار يعتمد على function-calling عبر LLM دون طبقة ضمان deterministic tool execution مستقلة عن قرار النموذج.

---

## 2) الأعراض كما تظهر للمستخدم

- سؤال مباشر: "كم عدد ملفات بايثون في المشروع؟"
- النتيجة الفعلية: رد عام (لا أستطيع الوصول/غير معروف) بدل رقم حقيقي.
- السلوك يظهر خاصة في محادثة الأدمن، رغم أن المنصة تحتوي أصلًا على مكونات معرفة المشروع/DB.

هذا يثبت وجود انقطاع بين **وجود الأدوات** وبين **مسار استدعائها الفعلي وقت الطلب**.

---

## 3) تشريح المسار التشغيلي (StateGraph/Reasoning Path)

### المرحلة A: دخول الطلب من Admin WebSocket
الطلب يمر من Admin Router إلى ChatOrchestrator ثم قد يُفوّض إلى orchestrator-service عبر `/agent/chat` إذا تم تصنيفه كـ ADMIN_QUERY.

### المرحلة B: في orchestrator-service
الوكيل الداخلي يقرر intent:
- إن كانت ADMIN_QUERY → يذهب إلى AdminAgent (المفترض).
- إن لم تُكتشف كـ ADMIN_QUERY → يسقط إلى `_handle_chat_fallback`.

### المرحلة C (المشكلة الحرجة)
في fallback يتم استخدام Prompt تعليمي موجّه للدروس، لا Prompt إداري، فيتولد سلوك "مساعد تعليمي" بدل "منفذ أدوات إدارية".

### المرحلة D (المشكلة الحرجة الثانية)
حتى لو دخل AdminAgent:
- يحاول استدعاء أدوات مثل `get_user_count`, `list_all_tables`, `count_python_files`, `count_db_tables`.
- لكن registry في المايكروسيرفس عند startup يسجّل أساسًا أدوات تعليمية/محتوى، وليس أدوات admin stats.
- النتيجة: tool not found / None / fallback نصي.

---

## 4) الأسباب الجذرية (Root Causes) بدقة 100%

## RC-1: Intent Drift (انحراف كشف النية) في المايكروسيرفس
- أنماط ADMIN_QUERY في المايكروسيرفس لا تشمل صيغًا عربية مهمة مرتبطة بعدّ الملفات مثل: "عدد ملفات بايثون" أو "كم ملف".
- عندما لا تُطابق regex، intent يصبح DEFAULT، فيسقط المسار على fallback التوليدي.

**الأثر:** لا يتم استدعاء AdminAgent ولا أدوات القياس.

## RC-2: Fallback Prompt Contamination
- مسار fallback في orchestrator-service يستخدم `get_customer_system_prompt()` (تعليمي) بدل prompt إداري.
- هذا يفرض إطار "تعليمي" على سؤال إداري تشغيلي.

**الأثر:** إجابات عامة/اعتذارية حتى لو السؤال يتطلب أداة رقمية.

## RC-3: Registry Starvation (جوع سجل الأدوات)
- `register_all_tools()` في orchestrator-service لا يسجل أدوات admin الأساسية.
- المسجل فعليًا: أدوات محتوى/استرجاع تعليمية أساسًا.

**الأثر:** AdminAgent يستدعي أدوات غير موجودة → لا نتائج موثوقة.

## RC-4: Tool Name Contract Mismatch
- AdminAgent يطلب أسماء (مثل `list_all_tables`) بينما مسارات أخرى تعتمد تسميات مختلفة (`get_database_tables` إلخ).
- لا يوجد عقد API موحد صارم بين "الوكيل" و"الريجستري".

**الأثر:** فشل صامت/جزئي في التنفيذ.

## RC-5: Over-Reliance on LLM Tool Choice
- الوكيل يحاول فرض `tool_choice="required"`، لكنه ما يزال يعتمد أولًا على استجابة LLM لاختيار/تنسيق الاستدعاء.
- في أنظمة critical admin metrics، يجب وجود deterministic tool router rule-first قبل LLM.

**الأثر:** أي انحراف نمذجي ينتج رد لغوي بدل تنفيذ آلي.

---

## 5) لماذا المشكلة تبدو "كارثة" في بيئة 100% Microservices API-First

لأن التصميم الحالي يملك:
- microservice boundary صحيحة شكليًا،
- لكن control plane للأدوات غير موحّد contract-first.

في API-First الصحيح:
1. يجب أن تكون أدوات العدّ exposed كواجهات خدمة مستقلة موثقة.
2. التوجيه إلى هذه الأدوات يجب أن يكون policy-driven (deterministic) قبل الاستعانة بالإجابات التوليدية.
3. الفشل يجب أن يكون explicit ومرصود بمقاييس observability، لا سقوط صامت إلى "إجابة عامة".

---

## 6) العلاج الكامل المقترح (بدون تطبيق كود هنا) — خطة إصلاح إنتاجية

## Phase 0 — Emergency Guardrail (فوري)
1. أي سؤال يحتوي intents إحصائية (`count`, `عدد`, `كم`, `files`, `tables`, `users`) يجب أن يمر عبر **Tool-Only Path**.
2. منع fallback التعليمي لهذه الفئة نهائيًا.
3. إذا الأداة غير متاحة: إرجاع خطأ تشغيلي صريح مع `error_code=ADMIN_TOOL_UNAVAILABLE`.

## Phase 1 — Contract Unification
1. إنشاء عقد موحد `AdminMetricsToolContract` (JSON Schema + versioning).
2. تثبيت أسماء أدوات canonical:
   - `admin.get_user_count`
   - `admin.get_database_tables`
   - `admin.count_python_files`
   - `admin.count_database_tables`
3. منع أي اسم أداة خارج العقد عبر validation في startup.

## Phase 2 — Registry Completion
1. تسجيل أدوات admin metrics في orchestrator-service startup.
2. فحص health عند الإقلاع:
   - `tool_registry_integrity_check`
   - `required_tools_present == true`
3. منع Ready state إذا الأدوات الأساسية ناقصة.

## Phase 3 — Intent Hardening (Arabic + EN)
1. توسيع regex/semantic intent للعبارات العربية الواقعية:
   - "كم عدد ملفات بايثون"
   - "عدد جداول قاعدة البيانات"
   - "عدد المستخدمين"
2. إضافة fallback classifier صغير مخصص admin-metrics قبل DEFAULT.
3. إضافة اختبارات behavior-level لحالات الصياغة المتنوعة.

## Phase 4 — Admin Fallback Isolation
1. إنشاء `get_admin_system_prompt()` داخل المايكروسيرفس واستخدامه عند أي سياق إداري.
2. منع استخدام customer educational prompt في admin channel.
3. إضافة assert runtime: `chat_scope=admin => admin_prompt_only`.

## Phase 5 — Deterministic Execution Engine
1. تحويل admin metrics إلى stategraph بعقد:
   - DetectIntentNode
   - ValidateAccessNode
   - ResolveToolNode
   - ExecuteToolNode
   - RenderAnswerNode
2. تنفيذ rule-first, LLM-second.
3. إرفاق provenance في الرد:
   - tool_name
   - timestamp
   - source_service

## Phase 6 — Observability + SLO
1. مؤشرات إلزامية:
   - `admin_metric_query_success_rate`
   - `admin_metric_query_tool_miss_rate`
   - `fallback_on_admin_metric_rate`
2. إنذار فوري إذا `fallback_on_admin_metric_rate > 1%`.
3. لوحة مراقبة خاصة بالأدمن chat reliability.

---

## 7) توافق الخطة مع المنظومة المذكورة (LangGraph / LlamaIndex / DSPy / Reranker / Kagent / MCP / TLM)

- **LangGraph/StateGraph**: اعتماد مسار إداري حتمي deterministic nodes بدل free-form fallback.
- **MCP**: تحويل أدوات الإحصاء إلى MCP resources/tools موحدة بعقد صارم.
- **LlamaIndex/Reranker**: ليسا المسار الصحيح لحسابات رقمية حية؛ يستخدمان فقط عند الحاجة لمراجع وثائقية، وليس للعدّ التشغيلي.
- **DSPy/TLM**: لتحسين اختيار النية وصياغة الإجابة، لكن ليس بديلاً عن tool execution الحتمي.
- **Kagent/Multi-Agent**: توزيع المسؤوليات (Intent/Policy/Execution/Audit) مع قناة تنفيذ واحدة موثوقة للـ Admin metrics.

---

## 8) تعريف "النجاح" بعد الإصلاح (Acceptance Criteria)

1. سؤال: "كم عدد ملفات بايثون في المشروع؟" → رقم دقيق + مصدر الأداة + timestamp.
2. سؤال: "كم عدد جداول قاعدة البيانات؟" → رقم دقيق مباشر.
3. سؤال: "كم عدد المستخدمين؟" → رقم دقيق من service API.
4. ممنوع الرد العام في هذه الفئة إلا بخطأ تشغيلي صريح قابل للرصد.
5. Pass rate لا يقل عن 99.9% في اختبارات admin metrics regression.

---

## 9) الخلاصة النهائية

المشكلة **معمارية تشغيلية** وليست "ذكاء ضعيف":
- intent غير محصّن،
- fallback خاطئ السياق،
- registry ناقص،
- contract أسماء الأدوات غير موحّد.

لذلك يظهر للمسؤول أن النظام "لا يستطيع" رغم وجود قدرات متقدمة. الحل الكامل هو **تثبيت مسار Admin Metrics حتمي contract-first** مع عزل صارم عن المسار التعليمي، وتفعيل observability يكتشف أي رجوع إلى الإجابات العامة.

