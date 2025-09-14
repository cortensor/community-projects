import logging
import asyncio
import aiohttp
import os
import uuid
import pickle
import json
import time
import re
import html
import numpy as np
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from aiogram.utils.exceptions import Throttled, CantParseEntities
from aiogram.utils.markdown import escape_md
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")

# Configuration
class Config:
    MAX_RETRIES = 3
    RETRY_DELAY = 1.5
    TIMEOUT_SEC = 60
    PROMPT_CACHE_FILE = "prompt_cache.pkl"
    USER_HISTORY_FILE = "user_history.pkl" 
    KNOWLEDGE_BASE_FILE = "knowledge_base.json"
    THROTTLE_RATE = 0.5
    MESSAGE_CHUNK_SIZE = 3800
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    SIMILARITY_THRESHOLD = 0.7
    TOP_K = 3

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Bot initialization
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Initialize embedding model
try:
    embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
except Exception as e:
    logger.error(f"Failed to load embedding model: {e}")
    raise

# Data storage classes
class PersistentDict:
    def __init__(self, filename: str):
        self.filename = Path(filename)
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        if self.filename.exists():
            try:
                with open(self.filename, "rb") as f:
                    return pickle.load(f)
            except (pickle.PickleError, EOFError):
                logger.warning("Failed to load data, creating new storage")
        return {}
    
    def _save_data(self):
        with open(self.filename, "wb") as f:
            pickle.dump(self.data, f)
    
    def __getitem__(self, key):
        return self.data[key]
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __setitem__(self, key, value):
        self.data[key] = value
        self._save_data()
    
    def __delitem__(self, key):
        del self.data[key]
        self._save_data()
    
    def pop(self, key, default=None):
        value = self.data.pop(key, default)
        if key in self.data:
            self._save_data()
        return value

class PromptCache(PersistentDict):
    pass

class UserHistory(PersistentDict):
    def add_entry(self, user_id: int, prompt_key: str):
        if user_id not in self.data:
            self.data[user_id] = []
        self.data[user_id].append(prompt_key)
        self._save_data()
    
    def get_user_history(self, user_id: int, limit: int = 5) -> list:
        return self.data.get(user_id, [])[-limit:]

class KnowledgeBase:
    def __init__(self):
        self.kb_file = Path(Config.KNOWLEDGE_BASE_FILE)
        self.knowledge = self._load_knowledge()
        self.embeddings = self._generate_embeddings()
    
    def _load_knowledge(self) -> List[dict]:
        if not self.kb_file.exists():
            return []
        
        try:
            with open(self.kb_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("Failed to load knowledge base, creating new one")
            return []
    
    def _generate_embeddings(self) -> np.ndarray:
        if not self.knowledge:
            return np.array([])
        
        texts = [item["content"] for item in self.knowledge]
        return embedding_model.encode(texts, convert_to_numpy=True)
    
    def search(self, query: str) -> List[Tuple[dict, float]]:
        if not self.knowledge:
            return []
        
        query_embedding = embedding_model.encode(query, convert_to_numpy=True)
        query_embedding = query_embedding.reshape(1, -1)
        
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        results = zip(self.knowledge, similarities)
        results = sorted(results, key=lambda x: x[1], reverse=True)
        
        filtered = [r for r in results if r[1] >= Config.SIMILARITY_THRESHOLD]
        return filtered[:Config.TOP_K]
    
    def add_document(self, title: str, content: str):
        new_doc = {
            "title": title,
            "content": content,
            "timestamp": time.time()
        }
        self.knowledge.append(new_doc)
        
        new_embedding = embedding_model.encode(content, convert_to_numpy=True)
        if len(self.embeddings) == 0:
            self.embeddings = new_embedding.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, new_embedding])
        
        with open(self.kb_file, "w", encoding="utf-8") as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)

# Initialize storage
prompt_cache = PromptCache(Config.PROMPT_CACHE_FILE)
user_history = UserHistory(Config.USER_HISTORY_FILE)
knowledge_base = KnowledgeBase()

# Middleware for rate limiting
class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self):
        self.user_last_message = {}
        super().__init__()

    async def on_process_message(self, message: types.Message, data: dict):
        user_id = message.from_user.id
        current_time = time.time()
        
        last_message_time = self.user_last_message.get(user_id, 0)
        time_since_last = current_time - last_message_time
        
        if time_since_last < Config.THROTTLE_RATE:
            wait_time = Config.THROTTLE_RATE - time_since_last
            await message.reply(f"⚠️ Please wait {wait_time:.1f} seconds before sending another message.")
            raise CancelHandler()
        
        self.user_last_message[user_id] = current_time

dp.middleware.setup(ThrottlingMiddleware())

# Prompt improvement engine
class PromptImprover:
    TEMPLATES = [
        {
            "name": "Structured Points", 
            "template": "Create a structured answer with key points for: {prompt}",
            "suggestion": "Add practical examples if relevant."
        },
        {
            "name": "Comprehensive Explanation",
            "template": "Explain comprehensively and provide examples: {prompt}",
            "suggestion": "Include analogies for easier understanding."
        },
        {
            "name": "Step-by-Step Guide",
            "template": "Provide step-by-step explanation for: {prompt}",
            "suggestion": "Add tips and warnings about common mistakes."
        },
        {
            "name": "In-Depth Analysis",
            "template": "Create in-depth analysis about: {prompt}",
            "suggestion": "Include different perspectives if possible."
        }
    ]

    @classmethod
    def get_all_improvements(cls, prompt: str) -> List[dict]:
        """Generate all possible improved versions"""
        return [
            {
                "name": template["name"],
                "improved_prompt": template["template"].format(prompt=prompt.strip()),
                "suggestion": template["suggestion"],
                "full_prompt": f"{template['template'].format(prompt=prompt.strip())}\n\n{template['suggestion']}"
            }
            for template in cls.TEMPLATES
        ]

# API client
class CortensorAPI:
    @staticmethod
    def clean_response(text: str) -> str:
        """Clean API response from special tokens and formatting"""
        if not text:
            return text
            
        text = text.replace('</s>', '').replace('<s>', '').strip()
        text = text.replace('\\n', '\n').replace('\\"', '"')
        return text[:Config.MESSAGE_CHUNK_SIZE*10]

    @staticmethod
    async def query(
        prompt: str,
        session_id: str = CORTENSOR_SESSION_ID,
        max_retries: int = Config.MAX_RETRIES
    ) -> str:
        headers = {
            "Authorization": f"Bearer {CORTENSOR_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "session_id": session_id,
            "prompt": prompt,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        CORTENSOR_API_URL,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=Config.TIMEOUT_SEC)
                    ) as resp:
                        
                        raw_response = await resp.text()
                        logger.info(f"Raw API response (status {resp.status}): {raw_response[:500]}...")
                        
                        if resp.status != 200:
                            return f"⚠️ API Error (HTTP {resp.status}): {raw_response[:300]}"
                        
                        try:
                            data = json.loads(raw_response)
                            if isinstance(data, str):
                                return CortensorAPI.clean_response(data)
                            elif isinstance(data, dict):
                                if "text" in data:
                                    return CortensorAPI.clean_response(data["text"])
                                elif "choices" in data and isinstance(data["choices"], list):
                                    if data["choices"] and isinstance(data["choices"][0], dict):
                                        return CortensorAPI.clean_response(data["choices"][0].get("text", raw_response))
                                    return CortensorAPI.clean_response(str(data["choices"][0]) if data["choices"] else raw_response)
                                elif "response" in data:
                                    return CortensorAPI.clean_response(data["response"])
                            
                            return CortensorAPI.clean_response(raw_response)
                            
                        except json.JSONDecodeError:
                            return CortensorAPI.clean_response(raw_response)
                            
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    return "⚠️ Timeout: Could not connect to Cortensor API"
                await asyncio.sleep(Config.RETRY_DELAY * (attempt + 1))
                
            except Exception as e:
                logger.error(f"API request failed: {str(e)}")
                if attempt == max_retries - 1:
                    return f"⚠️ Error: {str(e)}"
                await asyncio.sleep(Config.RETRY_DELAY * (attempt + 1))
        
        return "⚠️ Failed to process request after several attempts"
    
    @staticmethod
    async def query_with_rag(prompt: str) -> str:
        try:
            relevant_docs = knowledge_base.search(prompt)
            
            context_parts = []
            if relevant_docs:
                context_parts.append("Context:\n" + "\n".join(
                    f"- {doc['title']}: {doc['content'][:300]}..."
                    for doc, score in relevant_docs
                ))
            
            full_prompt = "\n\n".join([
                f"Question: {prompt}",
                *context_parts,
                "Based on your knowledge, provide an answer that:",
                "- Gets straight to the point",
                "- Is deep and comprehensive",
                "- Without disclaimers about limitations", 
                "- In proper English"
            ])
            
            return await CortensorAPI.query(full_prompt)
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return await CortensorAPI.query(prompt)

# Utility functions
def chunks(text: str, limit: int = Config.MESSAGE_CHUNK_SIZE) -> List[str]:
    """Split text into chunks safe for Telegram messages"""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

async def show_processing_message(chat_id: int, prompt_type: str):
    """Show processing message that won't be deleted"""
    return await bot.send_message(
        chat_id,
        f"⏳ Executing prompt ({prompt_type}) to Cortensor...",
        parse_mode="HTML"
    )

async def safe_send_message(chat_id: int, text: str, parse_mode: str = None, **kwargs):
    """Safely send message with error handling"""
    try:
        return await bot.send_message(chat_id, text, parse_mode=parse_mode, **kwargs)
    except CantParseEntities:
        return await bot.send_message(chat_id, text, parse_mode=None, **kwargs)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise

# Command handlers
@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    welcome_text = """
Welcome to the Decentralized Prompting Helper Bot By Cortensor Network 🤖

How to use:
1. Send your question/prompt
2. Choose improvement style
3. View prompt preview
4. Execute your chosen prompt
5. Get answers from Cortensor AI

Send your question now!
"""
    await safe_send_message(message.chat.id, welcome_text)

@dp.message_handler(commands=["history"])
async def cmd_history(message: types.Message):
    """Show user's recent prompts"""
    history = user_history.get_user_history(message.from_user.id)
    if not history:
        return await safe_send_message(message.chat.id, "No history found.")
    
    items = []
    for key in reversed(history):
        item = prompt_cache.get(key)
        if item:
            items.append(f"• {item['prompt'][:50]}... ({item['type']})")
    
    text = "📚 Your Prompt History:\n\n" + "\n".join(items[:5])
    await safe_send_message(message.chat.id, text)

# Message handler
@dp.message_handler()
async def handle_message(message: types.Message):
    """Main handler for user prompts"""
    user_prompt = message.text.strip()
    if not user_prompt:
        return await safe_send_message(message.chat.id, "Please provide a prompt.")
    
    try:
        improvements = PromptImprover.get_all_improvements(user_prompt)
        
        original_key = f"orig_{uuid.uuid4().hex[:8]}"
        prompt_cache[original_key] = {
            "type": "original",
            "prompt": user_prompt,
            "timestamp": time.time()
        }
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton(
            "🔵 Original", 
            callback_data=f"view|{original_key}"
        ))
        
        buttons = []
        for imp in improvements:
            imp_key = f"imp_{uuid.uuid4().hex[:8]}"
            prompt_cache[imp_key] = {
                "type": "improved",
                "name": imp["name"],
                "prompt": imp["full_prompt"],
                "original_key": original_key,
                "timestamp": time.time()
            }
            buttons.append(types.InlineKeyboardButton(
                f"🟢 {imp['name']}", 
                callback_data=f"view|{imp_key}"
            ))
        
        kb.add(*buttons)
        
        response = [
            "📋 <b>Choose Prompt Type:</b>",
            "",
            f"🔹 <b>Original</b>:",
            f"<i>{escape_md(user_prompt[:100])}...</i>",
            "",
            "🔹 <b>Improvement Options:</b>"
        ]
        
        for imp in improvements:
            response.append(
                f"• <b>{imp['name']}</b>:\n"
                f"<i>{escape_md(imp['improved_prompt'][:100])}...</i>"
            )
        
        await safe_send_message(
            message.chat.id,
            "\n".join(response),
            parse_mode="HTML",
            reply_markup=kb
        )
        
        user_history.add_entry(message.from_user.id, original_key)
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await safe_send_message(message.chat.id, "⚠️ An error occurred. Please try again.")

# Callback handlers
@dp.callback_query_handler(lambda c: c.data.startswith("view|"))
async def handle_view_prompt(callback: types.CallbackQuery):
    """Show full prompt before execution"""
    try:
        _, key = callback.data.split("|", 1)
        prompt_data = prompt_cache.get(key)
        
        if not prompt_data:
            await callback.answer("Prompt not found")
            return
            
        if prompt_data["type"] == "original":
            text = "📋 <b>Original Prompt</b>\n\n" + prompt_data["prompt"]
        else:
            text = f"✨ <b>{prompt_data['name']}</b>\n\n{prompt_data['prompt']}"
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            "🚀 Use This Prompt",
            callback_data=f"use|{key}"
        ))
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=kb
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"View prompt error: {e}")
        await callback.answer("Error showing prompt")

@dp.callback_query_handler(lambda c: c.data.startswith("use|"))
async def handle_prompt_execution(callback: types.CallbackQuery):
    """Execute the selected prompt"""
    try:
        _, key = callback.data.split("|", 1)
        prompt_data = prompt_cache.get(key)
        
        if not prompt_data:
            await callback.answer("Invalid prompt")
            return
            
        await callback.message.edit_reply_markup()
        
        # Show processing message
        processing_msg = await show_processing_message(
            callback.message.chat.id,
            "Improved" if prompt_data["type"] == "improved" else "Original"
        )
        
        # Execute prompt
        response = await CortensorAPI.query_with_rag(
            prompt_data["prompt"] if prompt_data["type"] == "original" 
            else prompt_data["prompt"].split("\n\n")[0]
        )
        
        # Send response (processing message remains)
        for chunk in chunks(response):
            await safe_send_message(
                callback.message.chat.id,
                chunk,
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Execution error: {e}")
        await safe_send_message(
            callback.message.chat.id,
            "⚠️ Failed to process prompt. Please try again."
        )

# Error handler
@dp.errors_handler()
async def errors_handler(update: types.Update, exception: Exception):
    logger.error(f"Update {update} caused error: {exception}", exc_info=True)
    return True

# Main execution
if __name__ == "__main__":
    logger.info("Starting bot...")
    try:
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        logger.info("Bot stopped")
