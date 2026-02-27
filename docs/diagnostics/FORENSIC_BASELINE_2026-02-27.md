# Forensic Baseline — 2026-02-27

## 1) ما هو المكسور الآن
- يوجد انفصال سلطة بين مسار الدردشة (`chat_http`) المملوك لـ `conversation-platform` ومسار المهام (`missions_root`) المملوك لـ `orchestrator-service`.
- `StateGraph` موجود ضمن خدمة المنسق، لكنه ليس مرجعية التنفيذ الوحيدة لكل رحلة مستخدم.
- قياس split-brain الحالي حسب لوحة القطع يثبت أن `single_brain_architecture=false`.

## 2) السبب الجذري الحقيقي
- ملكية المسارات في السجل الرسمي ما زالت متعددة الأدمغة في نطاق chat/mission.
- طبقة الحافة (conversation platform) تقوم بدور يتجاوز adapter خفيف، ما يخلق control-plane مزدوجًا.
- مؤشرات الصحة كانت تركز على منع legacy فقط، وليس على حسم «مالك الرحلة» كشرط صريح.

## 3) صورة الهدف المعماري
- سلطة تنظيم واحدة: orchestrator/stategraph كـ control-plane وحيد.
- chat + super-agent على نفس brain عبر عقود API صريحة.
- stategraph يصبح العمود الفقري التنفيذي الفعلي (وليس مسارًا جانبيًا).
- runtime الافتراضي يبقى microservices-only مع عدم الحاجة إلى monolith.

## 4) baseline رقمي (PR#1)
- legacy_routes_count: `0`
- legacy_ws_targets_count: `0`
- monolith_required_for_default_runtime: `false`
- normal_chat_owner: `conversation-platform`
- super_agent_owner: `orchestrator-service`
- single_brain_architecture: `false`
- app_import_count_in_microservices: `0`
- active_overmind_duplication_metric: `0`
- stategraph_is_runtime_backbone: `false`
- contract_gate: `true`
- tracing_gate: `false`
