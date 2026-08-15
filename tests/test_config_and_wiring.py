import unittest
from unittest.mock import AsyncMock
from aiogram.fsm.storage.memory import MemoryStorage
from banana_bot.app import build_dispatcher, configure_webhook
from banana_bot.config import load_config
from banana_bot.diary import SQLiteDiaryRepository
from banana_bot.memory import ConversationMemory
from banana_bot.observability import Metrics

class WiringTests(unittest.IsolatedAsyncioTestCase):
 async def test_health_middleware_webhook_and_routers_remain(self):
  config=load_config({"TELEGRAM_BOT_TOKEN":"t","AI_API_KEY":"k"},validate=True)
  service=type("S",(),{"diary":SQLiteDiaryRepository(":memory:"),"config":config})()
  dispatcher=build_dispatcher(config,service,ConversationMemory(),Metrics(),MemoryStorage())
  self.assertEqual({x.name for x in dispatcher.sub_routers},{"admin","common","text","media"})
  bot=AsyncMock(); updates=await configure_webhook(bot,dispatcher,"https://bot.example/","secret")
  self.assertIn("message",updates); self.assertIn("callback_query",updates)
