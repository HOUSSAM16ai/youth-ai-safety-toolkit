import asyncio
import os

from langchain_core.messages import HumanMessage

from microservices.orchestrator_service.src.services.overmind.graph.main import create_unified_graph


async def main():
    # Provide a dummy key just to let LLM auth fail quickly if it reaches it,
    # but the client query should hit retriever/synthesizer primarily.
    os.environ["OPENAI_API_KEY"] = "dummy-key"
    app = create_unified_graph()

    print("=== FINAL CLIENT E2E ===")
    q1 = "اعطني تمرين الاحتمالات بكالوريا شعبة علوم تجريبية 2024 التمرين الأول"
    try:
        res1 = await app.ainvoke(
            {"query": q1, "messages": [HumanMessage(content=q1)]},
            config={"configurable": {"thread_id": "client-1"}},
        )
        print("Result:")
        print(res1.get("final_response"))
    except Exception as e:
        print("Client Error:", e)
    print("\n")

    print("=== FINAL ADMIN E2E ===")
    q2 = "كم عدد ملفات بايثون في المشروع"
    try:
        res2 = await app.ainvoke(
            {"query": q2, "messages": [HumanMessage(content=q2)]},
            config={"configurable": {"thread_id": "admin-1"}},
        )
        print("Result:")
        print(res2.get("final_response"))
    except Exception as e:
        print("Admin Error:", e)


if __name__ == "__main__":
    asyncio.run(main())
