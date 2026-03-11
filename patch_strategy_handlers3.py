import re

file_path = "app/services/chat/handlers/strategy_handlers.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's fix the MissionComplexHandler. Since the legacy endpoints MUST NOT be deleted but we need to stop the split-brain error.
# The `execute` method was generating a "Dispatch Failed" error because `start_mission` calls `orchestrator_client.create_mission` via HTTP bridge which is broken.
# What if we just bypass the HTTP bridge and run the DefaultChatHandler?
# Oh wait! In my previous attempt, I introduced a `NameError` because I deleted the `import DefaultChatHandler`!
# Let's cleanly implement the bypass by instantiating `DefaultChatHandler()` safely, because `DefaultChatHandler` is defined further down the file, so we can just refer to it! But `MissionComplexHandler` is defined BEFORE `DefaultChatHandler`, so `DefaultChatHandler` doesn't exist yet!

# Let's rewrite `execute` to use `DefaultChatHandler` safely by fetching it from the class dict or putting the import inside the method.

new_execute = """    async def execute(self, context: ChatContext) -> AsyncGenerator[str | dict, None]:
        \"\"\"
        Execute complex mission gracefully disabled in legacy monolith.
        Forwarding to DefaultChatHandler to prevent 'Dispatch Failed' split-brain errors.
        \"\"\"
        from app.services.chat.handlers.strategy_handlers import DefaultChatHandler
        handler = DefaultChatHandler()
        async for chunk in handler.execute(context):
            yield chunk
"""

pattern = re.compile(r'    async def execute\(self, context: ChatContext\) -> AsyncGenerator\[str \| dict, None\]:.*?    def _check_provider_config\(self\) -> str \| None:', re.DOTALL)
content = re.sub(pattern, new_execute + "\n    def _check_provider_config(self) -> str | None:", content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
