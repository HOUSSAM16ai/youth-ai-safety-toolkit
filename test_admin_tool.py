import asyncio

from microservices.orchestrator_service.src.services.overmind.graph.admin import count_python_files


async def main():
    print("Testing count_python_files kagent tool directly")
    res = count_python_files.invoke({})
    print(res)


if __name__ == "__main__":
    asyncio.run(main())
