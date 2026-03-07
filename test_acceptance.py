import asyncio

from langchain_core.messages import HumanMessage

from microservices.orchestrator_service.src.services.overmind.graph.main import create_unified_graph


async def main():
    app = create_unified_graph()

    print("=== TEST_CLIENT ===")
    q1 = "اعطني تمرين الاحتمالات بكالوريا شعبة علوم تجريبية الموضوع الاول التمرين الأول لسنة 2024"
    res1 = await app.ainvoke(
        {"query": q1, "messages": [HumanMessage(content=q1)]},
        config={"configurable": {"thread_id": "1"}},
    )
    print("Result:")
    print(res1.get("final_response"))
    print("\n")

    print("=== TEST_ADMIN_1 ===")
    q2 = "كم عدد ملفات بايثون في المشروع"
    res2 = await app.ainvoke(
        {"query": q2, "messages": [HumanMessage(content=q2)]},
        config={"configurable": {"thread_id": "2"}},
    )
    print("Result:")
    print(res2.get("final_response"))
    print("\n")

    print("=== TEST_ADMIN_2 ===")
    q3 = "كم عدد جداول قاعدة البيانات"
    res3 = await app.ainvoke(
        {"query": q3, "messages": [HumanMessage(content=q3)]},
        config={"configurable": {"thread_id": "3"}},
    )
    print("Result:")
    print(res3.get("final_response"))
    print("\n")

    print("=== TEST_ADMIN_3 ===")
    q4 = "اعطني إحصائيات المشروع الكاملة"
    res4 = await app.ainvoke(
        {"query": q4, "messages": [HumanMessage(content=q4)]},
        config={"configurable": {"thread_id": "4"}},
    )
    print("Result:")
    print(res4.get("final_response"))
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
