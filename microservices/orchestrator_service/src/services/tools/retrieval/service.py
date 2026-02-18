"""
Retrieval Service Orchestrator.
Application Layer.
Coordinators domain logic, infrastructure, and fallback strategies.
"""

import httpx

from microservices.orchestrator_service.src.core.logging import get_logger
from . import local_store, parsing, remote_client

logger = get_logger("tool-retrieval-service")


def _calculate_year_penalty(payload_year: str | int | None, requested_year: str | None) -> int:
    """
    Calculates penalty for year mismatch.
    0: Exact Match
    1: Missing Year (Soft Penalty)
    3: Explicit Mismatch (Hard Penalty)
    """
    if not requested_year:
        return 0

    if payload_year is None or str(payload_year).strip() == "":
        return 1

    if str(payload_year) == str(requested_year):
        return 0

    return 3


async def search_educational_content(
    query: str,
    year: str | None = None,
    subject: str | None = None,
    branch: str | None = None,
    exam_ref: str | None = None,
    exercise_id: str | None = None,
) -> str:
    """
    يبحث في قاعدة المعرفة التعليمية عن محتوى محدد.

    يستخدم نظام التصفية بالوسوم للوصول إلى دقة عالية جدًا (مثلاً: التمرين الأول، الموضوع الأول، سنة 2024).

    Args:
        query (str): نص البحث العام (مثلاً "الاحتمالات" أو "التمرين الأول").
        year (str | None): السنة الدراسية (مثلاً "2024").
        subject (str | None): المادة (مثلاً "Mathematics" أو "رياضيات").
        branch (str | None): الشعبة (مثلاً "Science", "Experimental Sciences", "علوم تجريبية").
        exam_ref (str | None): مرجع الامتحان (مثلاً "Subject 1" أو "الموضوع الأول").
        exercise_id (str | None): رقم التمرين (مثلاً "1" أو "Exercise 1").

    Returns:
        str: نص المحتوى المسترجع أو رسالة بعدم العثور على نتائج.
    """

    # 1. تكوين الوسوم المطلوبة للتصفية
    base_tags = ["ingested"]
    if subject:
        base_tags.append(f"subject:{subject}")
    if branch:
        base_tags.append(f"branch:{branch}")
    if exam_ref:
        base_tags.append(f"exam_ref:{exam_ref}")

    # If explicit exercise ID is requested, add it to query to boost relevance
    full_query = query
    if exercise_id:
        full_query = f"{query} {exercise_id}"

    semantic_query = parsing.expand_query_semantics(full_query, year, subject, branch, exam_ref)

    try:
        results = []
        strict_mode = True
        min_results = 5  # Desired minimum results

        # Attempt 1: Strict Search (with year)
        strict_tags = list(base_tags)
        if year:
            strict_tags.append(f"year:{year}")

        results = await remote_client.fetch_from_memory_agent(semantic_query, strict_tags)

        # Attempt 2: Relaxed Search (Progressive Relaxation)
        # If strict search yielded insufficient results, try without the year constraint
        if year and len(results) < min_results:
            relaxed_results = await remote_client.fetch_from_memory_agent(semantic_query, base_tags)

            # Merge results (avoiding duplicates)
            # We use the raw content as a simple unique key for now
            existing_contents = {r.get("content", "") for r in results}

            added_relaxed = 0
            for item in relaxed_results:
                content = item.get("content", "")
                if content and content not in existing_contents:
                    results.append(item)
                    existing_contents.add(content)
                    added_relaxed += 1

            # If we added relaxed results, we are no longer in strict mode
            if added_relaxed > 0:
                strict_mode = False

        if not results:
            logger.info("Memory Agent returned no results. Attempting local fallback.")
            return local_store.search_local_knowledge_base(
                semantic_query, year, subject, branch, exam_ref
            )

        # Process and filter results
        candidates = []
        is_specific = parsing.is_specific_request(semantic_query)

        for item in results:
            content = item.get("content", "")
            if not content:
                continue

            # --- SOFT METADATA VERIFICATION ---
            payload = item.get("payload") or item.get("metadata") or {}

            # 1. Calculate Year Penalty (Ranking Signal instead of Filter)
            penalty = _calculate_year_penalty(payload.get("year"), year)

            # 2. Check Subject (Keep as Strict Filter for now)
            if subject:
                item_subject = str(payload.get("subject", "")).lower()
                if subject.lower() not in item_subject and item_subject not in subject.lower():
                    continue

            # 3. Check Exam Ref (Keep as Strict Filter for now)
            if exam_ref:
                item_ref = str(payload.get("exam_ref", "")).lower()
                if exam_ref.lower() not in item_ref and item_ref not in exam_ref.lower():
                    continue

            # Try granular extraction
            extracted = parsing.extract_specific_exercise(content, semantic_query)

            final_content = ""
            if extracted:
                final_content = extracted
            elif not is_specific:
                # Only include full content if the user didn't ask for a specific exercise/topic
                final_content = content

            if final_content:
                # Extract score for secondary ranking
                try:
                    score = float(payload.get("score", 0))
                except (ValueError, TypeError):
                    score = 0.0

                candidates.append(
                    {
                        "content": final_content,
                        "payload": payload,
                        "penalty": penalty,
                        "score": score,
                    }
                )

        if not candidates and is_specific:
            return "عذراً، لم أتمكن من العثور على التمرين المحدد في السياق المطلوب."

        # Sort candidates: Primary = Penalty (ASC), Secondary = Score (DESC)
        candidates.sort(key=lambda x: (x["penalty"], -x["score"]))

        # Format output and deduplicate (preserving order)
        final_contents = []
        seen_cores = set()

        for c in candidates:
            # Use core content for deduplication to handle overlaps
            core = parsing.get_core_content(c["content"])
            if core in seen_cores:
                continue
            seen_cores.add(core)

            # Add Source Header for Clarity
            source_label = f"--- Source: {c['payload'].get('year', 'Unknown')} {c['payload'].get('exam_ref', '')} ---"
            final_contents.append(f"{source_label}\n\n{c['content']}")

        final_output = "\n\n".join(final_contents).strip()

        # Add Explanation Note if needed (Relaxed Mode + Year Requested + Results Exist)
        if not strict_mode and year and final_output:
            note = f"\n\nملاحظة: لم أجد نتائج كافية مفهرسة بسنة {year} بدقة، فتم عرض أقرب النتائج."
            final_output += note

        return final_output

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
        logger.warning(
            f"Memory Agent connection error: {e}. Switching to local knowledge base fallback."
        )
        return local_store.search_local_knowledge_base(
            semantic_query, year, subject, branch, exam_ref
        )
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return local_store.search_local_knowledge_base(
            semantic_query, year, subject, branch, exam_ref
        )
