import sys
try:
    from app.services.chat.handlers.strategy_handlers import MissionComplexHandler
    print("Syntax OK")
except Exception as e:
    print(f"Error: {e}")
