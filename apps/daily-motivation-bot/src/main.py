import os
import logging
import requests
import random
import re
import json
import threading
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler, CallbackQueryHandler
)
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from typing import Dict, Set, List, Optional, Tuple

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Thread-safe data access
data_lock = threading.RLock()

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")

# Conversation state
ASK_TIMEZONE, ASK_TONE, ASK_FEELING = range(3)

# Global user list and timezone map
user_ids = set()
user_timezones = {}
user_prompt_cache = {}
user_tones = {}
user_names = {}  # Untuk menyimpan nama pengguna
user_feedback = {}  # Untuk menyimpan feedback pengguna

# Daftar tone yang tersedia
AVAILABLE_TONES = {
    "Captain": "strict captain style - firm but caring commands, military terminology",
    "SteveHarvey": "motivational with humor - engaging stories, relatable, inspirational",
    "Motivational": "energetic and inspiring - uplifting, empowering, action-oriented",
    "Friendly": "warm and supportive - empathetic, compassionate, like a caring friend"
}

# Knowledge Base for RAG implementation - EXPANDED FOR VARIETY
KNOWLEDGE_BASE = {
    "motivation": [
        "The only way to do great work is to love what you do. - Steve Jobs",
        "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
        "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
        "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
        "It does not matter how slowly you go as long as you do not stop. - Confucius",
        "Believe you can and you're halfway there. - Theodore Roosevelt",
        "The only impossible journey is the one you never begin. - Tony Robbins",
        "Don't watch the clock; do what it does. Keep going. - Sam Levenson"
    ],
    "sad": [
        "This feeling is temporary. Brighter days will come.",
        "It's okay not to feel okay. What matters is that you keep moving forward.",
        "Every storm runs out of rain, just like every dark night turns into day.",
        "You're allowed to feel messed up and inside out. It doesn't mean you're defective, it means you're human.",
        "The sun will rise again, and so will you."
    ],
    "anxious": [
        "Take a breath. You are stronger than you think.",
        "You've already survived 100% of your worst days so far. You can get through this too.",
        "Anxiety is like a rocking chair. It gives you something to do, but it doesn't get you anywhere.",
        "This too shall pass. Everything is temporary.",
        "Focus on what you can control, let go of what you can't."
    ],
    "happy": [
        "Happiness is not something ready-made. It comes from your own actions. - Dalai Lama",
        "The more you praise and celebrate your life, the more there is in life to celebrate. - Oprah Winfrey",
        "Joy is not in things; it is in us. - Richard Wagner",
        "Happiness is a direction, not a place. - Sydney J. Harris",
        "The happiest people don't have the best of everything, they make the best of everything."
    ],
    "determined": [
        "Perseverance is not a long race; it is many short races one after the other. - Walter Elliot",
        "The difference between the impossible and the possible lies in a person's determination. - Tommy Lasorda",
        "When you feel like quitting, remember why you started.",
        "Determination today leads to success tomorrow.",
        "Strength doesn't come from what you can do. It comes from overcoming the things you once thought you couldn't."
    ],
    "focused": [
        "The successful warrior is the average man, with laser-like focus. - Bruce Lee",
        "Focus on being productive instead of busy.",
        "Concentrate all your thoughts upon the work at hand. The sun's rays do not burn until brought to a focus. - Alexander Graham Bell",
        "Where focus goes, energy flows. - Tony Robbins",
        "The ability to focus is the key to great work and great living."
    ],
    "grateful": [
        "Gratitude turns what we have into enough. - Anonymous",
        "The more grateful I am, the more beauty I see. - Mary Davis",
        "Gratitude is the healthiest of all human emotions. - Zig Ziglar",
        "Appreciate what you have before it becomes what you had.",
        "Count your blessings, not your problems."
    ],
    "energetic": [
        "Energy and persistence conquer all things. - Benjamin Franklin",
        "Your energy introduces you before you even speak.",
        "The only way to have energy is to create it.",
        "Act enthusiastic and you will be enthusiastic. - Dale Carnegie",
        "Positive energy attracts positive outcomes."
    ],
    "captain_style": [
        "Soldier, fall in! Your mission is not complete until you've given your all.",
        "Attention! Your potential is your greatest weapon - don't holster it.",
        "At ease, soldier. Even the strongest warriors need to recharge for the next battle.",
        "Steady your breathing, soldier. Anxiety is just the enemy trying to infiltrate your mind.",
        "Combat readiness includes mental preparedness. Face your fears head-on.",
        "Outstanding work, soldier! Celebrate this victory, but stay vigilant for the next mission.",
        "Soldier, your discipline today builds your freedom tomorrow.",
        "Stand tall! Confidence is your armor against doubt.",
        "Mission focus! Your goals are within reach - advance!",
        "Soldier, resilience is forged in adversity. Embrace the challenge!"
    ]
}

CACHE_FILE = "user_prompt_cache.json"
USER_DATA_FILE = "user_data.json"
KNOWLEDGE_FILE = "knowledge_base.json"
FEEDBACK_FILE = "user_feedback.json"  # File untuk menyimpan feedback
DAILY_CACHE_FILE = "daily_messages_cache.json"  # File untuk cache pesan harian

# Daily Motivation Manager untuk variasi dan anti-duplikasi
class DailyMotivationManager:
    def __init__(self):
        self.sent_messages_cache: Dict[int, List[str]] = {}  # user_id: list of sent messages
        self.max_cache_size = 20  # Keep last 20 messages to avoid duplicates
        
    def get_varied_mood(self, user_id: int, previous_moods: List[str]) -> str:
        """Get a varied mood for daily motivation, avoiding recent duplicates"""
        all_moods = ["motivation", "happy", "determined", "focused", "inspired", 
                    "productive", "confident", "grateful", "energetic", "optimistic"]
        
        # Remove moods that have been used recently
        recent_moods = self.sent_messages_cache.get(user_id, [])
        available_moods = [mood for mood in all_moods if mood not in recent_moods[-5:]]
        
        # If all moods exhausted, reset and use any
        if not available_moods:
            available_moods = all_moods
            
        return random.choice(available_moods)
    
    def get_varied_knowledge(self, mood: str, tone: str, count: int = 3) -> List[str]:
        """Get varied knowledge items with rotation"""
        relevant_items = []
        
        # Base knowledge for the mood
        if mood in KNOWLEDGE_BASE:
            mood_items = KNOWLEDGE_BASE[mood].copy()
            random.shuffle(mood_items)
            relevant_items.extend(mood_items[:2])
        
        # Add tone-specific knowledge with variety
        if tone == "Captain" and "captain_style" in KNOWLEDGE_BASE:
            captain_items = KNOWLEDGE_BASE["captain_style"].copy()
            random.shuffle(captain_items)
            relevant_items.extend(captain_items[:1])
        elif tone == "SteveHarvey" and "motivation" in KNOWLEDGE_BASE:
            steve_items = [item for item in KNOWLEDGE_BASE["motivation"] 
                          if "Steve" in item or "Harvey" in item or "story" in item.lower()]
            if steve_items:
                relevant_items.extend(random.sample(steve_items, min(1, len(steve_items))))
        
        # Fill with general motivation if needed
        if len(relevant_items) < count and "motivation" in KNOWLEDGE_BASE:
            general_items = KNOWLEDGE_BASE["motivation"].copy()
            random.shuffle(general_items)
            needed = count - len(relevant_items)
            relevant_items.extend(general_items[:needed])
            
        return relevant_items[:count]
    
    def track_sent_message(self, user_id: int, message: str):
        """Track sent messages to avoid duplicates"""
        if user_id not in self.sent_messages_cache:
            self.sent_messages_cache[user_id] = []
        
        self.sent_messages_cache[user_id].append(message[:100])  # Store first 100 chars for comparison
        
        # Maintain cache size
        if len(self.sent_messages_cache[user_id]) > self.max_cache_size:
            self.sent_messages_cache[user_id] = self.sent_messages_cache[user_id][-self.max_cache_size:]
    
    def is_duplicate_message(self, user_id: int, new_message: str, similarity_threshold: int = 70) -> bool:
        """Check if message is too similar to recently sent messages"""
        if user_id not in self.sent_messages_cache:
            return False
            
        new_msg_short = new_message[:100]
        for sent_msg in self.sent_messages_cache[user_id][-5:]:  # Check last 5 messages
            if self.calculate_similarity(sent_msg, new_msg_short) > similarity_threshold:
                return True
        return False
    
    def calculate_similarity(self, str1: str, str2: str) -> int:
        """Calculate simple similarity between two strings"""
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())
        
        if not words1 or not words2:
            return 0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return int((len(intersection) / len(union)) * 100)

# Global instance
daily_mgr = DailyMotivationManager()

# ------------------------
# Load and Save Functions
# ------------------------

def save_prompt_cache():
    with data_lock:
        try:
            temp_file = CACHE_FILE + ".tmp"
            with open(temp_file, "w") as f:
                json.dump({uid: {mood: list(seeds) for mood, seeds in moods.items()} for uid, moods in user_prompt_cache.items()}, f)
            os.replace(temp_file, CACHE_FILE)
            logger.info("✅ Prompt cache saved.")
        except Exception as e:
            logger.error("❌ Failed to save prompt cache.", exc_info=True)

def load_prompt_cache():
    global user_prompt_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                raw_cache = json.load(f)
                user_prompt_cache = {
                    int(uid): {
                        mood: set(seeds)
                        for mood, seeds in moods.items()
                    } for uid, moods in raw_cache.items()
                }
            logger.info("✅ Prompt cache loaded from file.")
        except Exception as e:
            logger.error("❌ Failed to load prompt cache.", exc_info=True)

def save_user_data():
    with data_lock:
        try:
            temp_file = USER_DATA_FILE + ".tmp"
            with open(temp_file, "w") as f:
                data = {
                    "user_ids": list(user_ids),
                    "user_timezones": user_timezones,
                    "user_tones": user_tones,
                    "user_names": user_names,
                    "daily_messages_cache": daily_mgr.sent_messages_cache  # NEW: Save daily cache
                }
                json.dump(data, f, indent=2)
                logger.info(f"💾 Saving user data: {len(user_ids)} users, {len(user_timezones)} timezones, {len(user_tones)} tones, {len(user_names)} names")
            
            os.replace(temp_file, USER_DATA_FILE)
            logger.info("✅ User data saved.")
        except Exception as e:
            logger.error("❌ Failed to save user data.", exc_info=True)

def load_user_data():
    global user_ids, user_timezones, user_tones, user_names
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r") as f:
                data = json.load(f)
                user_ids = set(data.get("user_ids", []))
                user_timezones = {int(k): int(v) for k, v in data.get("user_timezones", {}).items()}
                user_tones = {int(k): v for k, v in data.get("user_tones", {}).items()}
                user_names = {int(k): v for k, v in data.get("user_names", {}).items()}
                # Load daily cache
                daily_mgr.sent_messages_cache = {int(k): v for k, v in data.get("daily_messages_cache", {}).items()}
            logger.info(f"✅ User data loaded: {len(user_ids)} users, {len(user_timezones)} timezones, {len(user_tones)} tones, {len(user_names)} names, {len(daily_mgr.sent_messages_cache)} daily caches")
        except Exception as e:
            logger.error("❌ Failed to load user data.", exc_info=True)

def save_knowledge_base():
    with data_lock:
        try:
            temp_file = KNOWLEDGE_FILE + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(KNOWLEDGE_BASE, f, indent=2)
            os.replace(temp_file, KNOWLEDGE_FILE)
            logger.info("✅ Knowledge base saved.")
        except Exception as e:
            logger.error("❌ Failed to save knowledge base.", exc_info=True)

def load_knowledge_base():
    global KNOWLEDGE_BASE
    DEFAULT_ENGLISH_KB = {
        "motivation": [
            "The only way to do great work is to love what you do. - Steve Jobs",
            "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill"
        ],
        "sad": [
            "This feeling is temporary. Brighter days will come.",
            "It's okay not to feel okay. What matters is that you keep moving forward."
        ],
        "anxious": [
            "Take a breath. You are stronger than you think.",
            "You've already survived 100% of your worst days so far. You can get through this too."
        ],
        "happy": [
            "Happiness is not something ready-made. It comes from your own actions. - Dalai Lama",
            "The more you praise and celebrate your life, the more there is in life to celebrate. - Oprah Winfrey"
        ]
    }

    if os.path.exists(KNOWLEDGE_FILE):
        try:
            with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            
            KNOWLEDGE_BASE = raw
            logger.info("✅ Knowledge base loaded from file.")
            
        except Exception as e:
            logger.error("❌ Failed to load knowledge base.", exc_info=True)
            KNOWLEDGE_BASE = DEFAULT_ENGLISH_KB.copy()
            save_knowledge_base()
            logger.info("✅ Knowledge base initialized with English defaults due to load error.")
    else:
        KNOWLEDGE_BASE = DEFAULT_ENGLISH_KB.copy()
        save_knowledge_base()
        logger.info("✅ Knowledge base file not found; created English default KB.")

def save_feedback_data():
    """Menyimpan data feedback pengguna"""
    with data_lock:
        try:
            temp_file = FEEDBACK_FILE + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(user_feedback, f, indent=2)
            os.replace(temp_file, FEEDBACK_FILE)
            logger.info("✅ Feedback data saved.")
        except Exception as e:
            logger.error("❌ Failed to save feedback data.", exc_info=True)

def load_feedback_data():
    """Memuat data feedback pengguna"""
    global user_feedback
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r") as f:
                user_feedback = json.load(f)
            logger.info("✅ Feedback data loaded.")
        except Exception as e:
            logger.error("❌ Failed to load feedback data.", exc_info=True)
            user_feedback = {}

# ------------------------
# RAG Core Functions (Improved)
# ------------------------

def retrieve_relevant_knowledge(user_input: str, mood: Optional[str] = None, user_id: Optional[int] = None) -> List[str]:
    """Retrieve relevant knowledge entries WITH VARIETY"""
    user_tone = user_tones.get(user_id, "Motivational") if user_id else "Motivational"
    
    # Use the new varied knowledge system for daily motivation
    if "daily motivation" in user_input.lower():
        return daily_mgr.get_varied_knowledge(mood or "motivation", user_tone, 3)
    
    # Original logic for non-daily requests with variety improvement
    relevant_knowledge = []
    
    if mood and mood in KNOWLEDGE_BASE:
        mood_items = KNOWLEDGE_BASE[mood].copy()
        random.shuffle(mood_items)  # Shuffle for variety
        for item in mood_items[:2]:
            if isinstance(item, str):
                relevant_knowledge.append(item)
    
    # Add tone-specific knowledge with variety
    user_tone = user_tones.get(user_id, "Motivational") if user_id else "Motivational"
    if user_tone == "Captain" and "captain_style" in KNOWLEDGE_BASE and len(relevant_knowledge) < 3:
        captain_items = KNOWLEDGE_BASE["captain_style"].copy()
        random.shuffle(captain_items)
        for item in captain_items[:3-len(relevant_knowledge)]:
            if isinstance(item, str):
                relevant_knowledge.append(item)
    
    # Add general motivation with variety if still needed
    if len(relevant_knowledge) < 3 and "motivation" in KNOWLEDGE_BASE:
        general_items = KNOWLEDGE_BASE["motivation"].copy()
        random.shuffle(general_items)
        for item in general_items[:3-len(relevant_knowledge)]:
            if isinstance(item, str):
                relevant_knowledge.append(item)
    
    return relevant_knowledge[:3]

def generate_rag_prompt(user_input: str, mood: Optional[str] = None, tone: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """Generate concise prompt for Cortensor API - IMPROVED"""
    retrieved = retrieve_relevant_knowledge(user_input, mood, user_id)

    # Tone instruction yang lebih spesifik dan jelas
    tone_instruction = ""
    if tone and tone in AVAILABLE_TONES:
        if tone == "Captain":
            tone_instruction = "Speak like a strict but caring military captain: use short, firm but encouraging commands. Address the user as 'Soldier'. Use military terminology. Be direct and authoritative but not harsh. "
        elif tone == "SteveHarvey":
            tone_instruction = "Speak like Steve Harvey: motivational, inspirational, with humor and personal stories. Be engaging and relatable. Avoid clichés. "
        elif tone == "Motivational":
            tone_instruction = "Use energetic, inspiring, and uplifting tone. Focus on empowerment and positive action. Avoid generic phrases. "
        elif tone == "Friendly":
            tone_instruction = "Use warm, friendly, supportive, and understanding language. Be empathetic and compassionate. Speak like a caring friend, not a formal advisor. "
    
    # Personalisasi dengan nama pengguna jika tersedia
    personalization = ""
    if user_id and user_id in user_names:
        personalization = f" Address the user as {user_names[user_id]} in a natural way if appropriate."
    
    # Instruksi khusus untuk mencegah format yang tidak diinginkan
    structure_instruction = (
        "Provide only ONE coherent motivational message. "
        "Do not create multiple separate responses or quotes. "
        "Do not include any signatures, tags, or identifiers like '- Eliza', '(id:1234)', or '<|eot_id|>'. "
        "Do not mention that you are an AI or bot. Just provide the motivational message directly."
    )
    
    # Prompt yang lebih fokus dan efektif
    if not retrieved:
        return (
            f"Create a personalized motivational message about: '{user_input}'. "
            f"{tone_instruction}"
            f"{structure_instruction} "
            f"Keep it under 50 words. Be authentic and impactful.{personalization}"
        )

    # Pastikan semua item adalah string sebelum dipotong
    knowledge_items = []
    for item in retrieved:
        if isinstance(item, str):
            knowledge_items.append(item[:80])
        else:
            knowledge_items.append(str(item)[:80])
    
    knowledge_str = " | ".join(knowledge_items)

    return (
        f"Create a personalized motivational message about: '{user_input}'. "
        f"Context: {knowledge_str}. "
        f"{tone_instruction}"
        f"{structure_instruction} "
        f"Keep it under 60 words. Be authentic and impactful.{personalization}"
    )

# ------------------------
# Core Bot Functions
# ------------------------

def clean_motivation_output(text: str) -> str:
    """
    Membersihkan output motivasi dari elemen yang tidak diinginkan:
    - Tanda tangan (seperti '- Eliza', '- Captain', dll.)
    - ID (seperti '(id:8877)')
    - Token khusus (seperti '<|eot_id|>')
    - Multiple responses
    - Prefix yang tidak perlu
    """
    # Hapus token khusus seperti <|eot_id|>
    text = re.sub(r'<\|eot_id\|>', '', text)
    
    # Hapus identifier (id:1234)
    text = re.sub(r'\(id:\s*\d+\)', '', text)
    
    # Hapus baris yang mengandung "User:" atau "Eliza:"
    text = re.sub(r'^(User|Eliza|Captain|Steve|Motivator|Friend):.*$', '', text, flags=re.MULTILINE)
    
    # Hapus tanda tangan di akhir pesan
    text = re.sub(r'[-\u2013\u2014]\s*(Eliza|Captain|Steve|Motivator|Friend)\.?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[-\u2013\u2014]\s*[A-Za-z\s]+\.?$', '', text, flags=re.MULTILINE)
    
    # Hapus prefix yang tidak diinginkan
    prefixes = [
        "Here is", "Here you go", "This is", "Allow me", "I want to share",
        "Your quote is", "Fresh motivational quote", "Here is a motivational quote",
        "Below", "This is something", "As a", "In the style of"
    ]
    
    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()):
            # Hapus prefix dan ambil teks setelahnya
            text = re.sub(r'^' + re.escape(prefix) + r'[\s,:]+', '', text, flags=re.IGNORECASE)
            break
    
    # Hapus tag <s> dan </s>
    text = text.replace("<s>", "").replace("</s>", "")
    
    # Hapus garis horizontal dan teks setelahnya di baris yang sama
    text = re.sub(r'[-\u2013\u2014]\s*[^"\n]+$', '', text).strip()
    
    # Jika masih ada multiple responses, ambil hanya yang pertama
    if "\n\n" in text:
        parts = text.split("\n\n")
        # Prioritaskan bagian yang lebih panjang dan bermakna
        text = max(parts, key=lambda x: len(x.strip()))
    
    # Hapus whitespace dan quotes yang tidak perlu
    text = text.strip(' "\n""')
    
    # Pastikan tidak ada multiple line breaks berlebihan
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()

def validate_and_clean_response(text: str, tone: str) -> str:
    """
    Validasi dan bersihkan respons untuk memastikan tidak mengandung elemen yang tidak diinginkan
    """
    # Daftar pola yang harus dihapus
    patterns_to_remove = [
        r'\(id:\s*\d+\)',
        r'<\|eot_id\|>',
        r'[-\u2013\u2014]\s*(Eliza|Captain|Steve|Motivator|Friend)\.?',
        r'^(User|Eliza|Captain|Steve|Motivator|Friend):',
        r'As a (friendly|motivational|captain|Steve Harvey) (bot|AI|assistant)',
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Untuk setiap gaya, pastikan tidak ada tanda tangan khusus
    if tone == "Captain":
        text = re.sub(r'[-\u2013\u2014]\s*Captain\.?$', '', text)
    elif tone == "SteveHarvey":
        text = re.sub(r'[-\u2013\u2014]\s*Steve\.?$', '', text)
    elif tone == "Motivational":
        text = re.sub(r'[-\u2013\u2014]\s*Motivator\.?$', '', text)
    elif tone == "Friendly":
        text = re.sub(r'[-\u2013\u2014]\s*Friend\.?$', '', text)
    
    return text.strip()

def ask_cortensor_motivation(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {CORTENSOR_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "session_id": int(CORTENSOR_SESSION_ID),
        "prompt": prompt,
        "prompt_type": 0,
        "stream": False,
        "timeout": 180
    }
    try:
        response = requests.post(
            CORTENSOR_API_URL, 
            headers=headers, 
            json=payload, 
            timeout=320
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['text'].strip()
    except requests.exceptions.Timeout:
        logger.error("❌ Cortensor API timeout")
        return "Timeout API"
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Connection error to Cortensor: {str(e)}")
        return "Cortensor connection error"

# ------------------------
# Daily Motivation System (IMPROVED)
# ------------------------

def send_daily_motivation(bot: Bot, chat_id: int):
    try:
        # Get varied mood instead of just previous moods
        previous_moods = list(user_prompt_cache.get(chat_id, {}).keys())
        current_mood = daily_mgr.get_varied_mood(chat_id, previous_moods)
        
        user_tone = user_tones.get(chat_id, "Motivational")
        
        # Generate prompt with varied context
        prompt = generate_rag_prompt(f"daily motivation about {current_mood}", current_mood, user_tone, chat_id)
        
        result = ask_cortensor_motivation(prompt)
        cleaned_result = clean_motivation_output(result)
        cleaned_result = validate_and_clean_response(cleaned_result, user_tone)
        
        # Check for duplicates before sending
        if daily_mgr.is_duplicate_message(chat_id, cleaned_result):
            logger.info(f"🔄 Duplicate detected for {chat_id}, generating alternative...")
            # Generate alternative with different mood
            alternative_mood = daily_mgr.get_varied_mood(chat_id, previous_moods + [current_mood])
            prompt = generate_rag_prompt(f"daily motivation about {alternative_mood}", alternative_mood, user_tone, chat_id)
            result = ask_cortensor_motivation(prompt)
            cleaned_result = clean_motivation_output(result)
            cleaned_result = validate_and_clean_response(cleaned_result, user_tone)
        
        # Track the sent message
        daily_mgr.track_sent_message(chat_id, cleaned_result)
        
        # Personalize greeting
        greeting = ""
        if chat_id in user_names:
            greeting = f", {user_names[chat_id]}"
            
        final_message = f"🌅 Good Morning{greeting}! Here's your daily motivation ({user_tone} tone):\n\n{cleaned_result}"
        
        # Send message and add feedback button
        message = bot.send_message(chat_id=chat_id, text=final_message)
        add_feedback_button(None, chat_id, message.message_id, cleaned_result)
        
        logger.info(f"✉️ Varied motivation sent to {chat_id} with {user_tone} tone - Mood: {current_mood}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send motivation to {chat_id}", exc_info=True)

def schedule_daily_jobs(scheduler: BackgroundScheduler, bot: Bot):
    current_jobs = {job.id for job in scheduler.get_jobs()}
    needed_jobs = set()
    
    for chat_id, offset in user_timezones.items():
        job_id = f"motivation_{chat_id}"
        needed_jobs.add(job_id)
        
        if not scheduler.get_job(job_id):
            utc_hour = (8 - offset) % 24
            scheduler.add_job(
                send_daily_motivation,
                trigger='cron',
                hour=utc_hour,
                minute=0,
                args=[bot, chat_id],
                id=job_id,
                replace_existing=True
            )
    
    for job_id in current_jobs - needed_jobs:
        scheduler.remove_job(job_id)
    
    logger.info(f"⏰ Updated {len(needed_jobs)} daily motivation jobs")

# ------------------------
# Fitur Baru: Feedback System
# ------------------------

def add_feedback_button(context: CallbackContext, chat_id: int, message_id: int, message_text: str):
    """Menambahkan tombol feedback ke pesan motivasi"""
    keyboard = [
        [InlineKeyboardButton("👍 Helpful", callback_data=f"fb_helpful_{message_id}"),
         InlineKeyboardButton("👎 Not Helpful", callback_data=f"fb_nothelpful_{message_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Edit pesan untuk menambahkan tombol feedback
        if context and context.bot:
            context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
        
        # Simpan pesan untuk referensi feedback
        if chat_id not in user_feedback:
            user_feedback[chat_id] = {}
        
        user_feedback[chat_id][message_id] = {
            "text": message_text,
            "timestamp": datetime.now().isoformat(),
            "feedback": None
        }
        save_feedback_data()
    except Exception as e:
        logger.error(f"❌ Failed to add feedback button: {e}")

def handle_feedback(update: Update, context: CallbackContext):
    """Menangani feedback dari pengguna"""
    query = update.callback_query
    user_id = query.message.chat.id
    message_id = query.message.message_id
    feedback_data = query.data
    
    # Parse feedback data
    if feedback_data.startswith("fb_helpful_"):
        feedback_type = "helpful"
        response_text = "🙏 Thank you for your feedback! We're glad this was helpful."
    elif feedback_data.startswith("fb_nothelpful_"):
        feedback_type = "not_helpful"
        response_text = "😔 We're sorry this wasn't helpful. We'll try to improve."
    else:
        return
    
    # Simpan feedback
    if user_id in user_feedback and message_id in user_feedback[user_id]:
        user_feedback[user_id][message_id]["feedback"] = feedback_type
        save_feedback_data()
    
    # Beri respons dan hapus tombol feedback
    query.answer()
    query.edit_message_reply_markup(reply_markup=None)
    context.bot.send_message(chat_id=user_id, text=response_text)

# ------------------------
# Fitur Baru: Personalization dengan Nama
# ------------------------

def set_name(update: Update, context: CallbackContext):
    """Mengatur nama pengguna"""
    user_id = update.message.chat_id
    
    if not context.args:
        update.message.reply_text("Please provide your name after the command. Example: /setname John")
        return
    
    name = " ".join(context.args)
    user_names[user_id] = name
    save_user_data()
    
    update.message.reply_text(f"✅ Your name has been set to: {name}. I'll use this to personalize your experience!")

# ------------------------
# Fitur Baru: Bantuan dan Informasi
# ------------------------

def help_command(update: Update, context: CallbackContext):
    """Menampilkan pesan bantuan"""
    help_text = """
🤖 *Daily Motivation Bot Help* 🤖

*Available Commands:*
/start - Start the bot and set your preferences
/settimezone - Set your timezone again
/settone - Change your communication style
/setname [name] - Set your name for personalization
/help - Show this help message
/about - Learn more about this bot

*How to use:*
- The bot will send you daily motivation at 8 AM your local time
- You can request motivation anytime by sending a message about how you feel
- Use the feedback buttons to rate motivational messages

*Communication Styles:*
- *Captain*: Strict and authoritative, like a military captain
- *SteveHarvey*: Motivational with humor and personal stories
- *Motivational*: Energetic and inspiring
- *Friendly*: Warm and supportive

Feel free to chat with me anytime you need motivation or support! 💪
"""
    update.message.reply_text(help_text, parse_mode='Markdown')

def about_command(update: Update, context: CallbackContext):
    """Menampilkan informasi tentang bot"""
    about_text = """
🌟 *About Daily Motivation Bot* 🌟

This bot is designed to provide daily motivational messages tailored to your preferences and current mood.

*Features:*
- Personalized daily motivation at 8 AM your local time
- Multiple communication styles to choose from
- Context-aware responses based on your mood
- Feedback system to improve quality

*Technology:*
Powered by Cortensor AI for generating authentic and impactful motivational messages.

Your feedback helps us improve the quality of the messages we generate. Use the 👍/👎 buttons to rate messages.

*Privacy:* Your data is stored securely and only used to personalize your experience.
"""
    update.message.reply_text(about_text, parse_mode='Markdown')

# ------------------------
# Handlers (user-facing)
# ------------------------

def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_ids.add(user_id)
    
    # Set default tone
    if user_id not in user_tones:
        user_tones[user_id] = "Motivational"
    
    save_user_data()
    
    keyboard = [[str(i)] for i in range(0, 24)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(
        "👋 Hello! I am the Daily Motivation Bot from the Cortensor Network.\n\n"
        "Before we start, please set your local timezone (UTC offset) so I can deliver daily motivation at 08:00 your local time.",
        reply_markup=reply_markup
    )
    return ASK_TIMEZONE

def handle_timezone(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    try:
        offset = int(update.message.text.strip())
        if 0 <= offset <= 23:
            user_timezones[user_id] = offset
            save_user_data()
            
            keyboard = [[tone] for tone in AVAILABLE_TONES.keys()]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            update.message.reply_text(
                "✅ Timezone set!\n\n"
                "Now choose your preferred communication style:",
                reply_markup=reply_markup
            )
            return ASK_TONE
        else:
            raise ValueError
    except ValueError:
        update.message.reply_text("Invalid input. Please choose a number between 0 and 23.")
        return ASK_TIMEZONE

def handle_tone(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    chosen_tone = update.message.text.strip()
    
    if chosen_tone in AVAILABLE_TONES:
        user_tones[user_id] = chosen_tone
        save_user_data()
        
        keyboard = [["Happy", "Sad", "Anxious", "Motivated"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        update.message.reply_text(
            f"✅ Your style has been set to: {chosen_tone}!\n\n"
            "How are you feeling right now? 😊😢😰💪",
            reply_markup=reply_markup
        )
        schedule_daily_jobs(context.bot_data['scheduler'], context.bot)
        return ASK_FEELING
    else:
        update.message.reply_text("Invalid selection. Please choose from the available options.")
        return ASK_TONE

def handle_feeling(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    mood = update.message.text.lower()
    user_tone = user_tones.get(user_id, "Motivational")
    
    if user_id not in user_prompt_cache:
        user_prompt_cache[user_id] = {}
    if mood not in user_prompt_cache[user_id]:
        user_prompt_cache[user_id][mood] = set()
    
    prompt = generate_rag_prompt(f"I feel {mood}", mood, user_tone, user_id)
    
    try:
        update.message.reply_text("Creating something special for you... 💭")
        result = ask_cortensor_motivation(prompt)
        
        if "error" not in result.lower():
            cleaned_result = clean_motivation_output(result)
            cleaned_result = validate_and_clean_response(cleaned_result, user_tone)
            
            # Jika masih ada multiple responses, ambil hanya yang pertama
            if "\n\n" in cleaned_result:
                parts = cleaned_result.split("\n\n")
                cleaned_result = max(parts, key=lambda x: len(x.strip()))
            
            message = update.message.reply_text(f"({user_tone} style):\n\n{cleaned_result}")
            
            # Tambahkan tombol feedback
            add_feedback_button(context, user_id, message.message_id, cleaned_result)
            
            if mood in KNOWLEDGE_BASE:
                KNOWLEDGE_BASE[mood].append(cleaned_result)
            else:
                KNOWLEDGE_BASE[mood] = [cleaned_result]
            save_knowledge_base()
        
    except Exception as e:
        logger.error("❌ Cortensor error", exc_info=True)
    
    return ConversationHandler.END

def set_timezone_command(update: Update, context: CallbackContext):
    keyboard = [[str(i)] for i in range(0, 24)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Please choose your timezone (UTC offset):", reply_markup=reply_markup)
    return ASK_TIMEZONE

def set_tone_command(update: Update, context: CallbackContext):
    keyboard = [[tone] for tone in AVAILABLE_TONES.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    update.message.reply_text(
        "Please choose your preferred communication style:",
        reply_markup=reply_markup
    )
    return ASK_TONE

def handle_motivation_request(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_input = update.message.text.lower()
    user_tone = user_tones.get(user_id, "Motivational")
    
    motivation_patterns = [
        r"motivation", r"motivat", r"encourag", r"inspir", r"quote", r"wise",
        r"support", r"rise", r"sad", r"depress", r"happy", r"joy",
        r"tired", r"exhausted", r"despair", r"bored", r"rise", r"move on",
        r"disappointed", r"heartbreak", r"stress", r"anxious", r"worried", r"nervous",
        r"spirit", r"goal", r"target", r"success", r"fail", r"lose", r"win",
        r"effort", r"hard work", r"keep going", r"give me motivation"
    ]
    
    blocked_topics = [
        r"what is", r"who is", r"where", r"when", r"why", r"how",
        r"definition", r"meaning", r"explain", r"describe", r"creator", r"founder",
        r"history", r"origin", r"biography", r"about", r"math", r"calculate",
        r"business", r"economy", r"physics", r"chemistry", r"homework", r"assignment", r"project",
        r"how to", r"tutorial", r"guide", r"instruction", r"step", r"\d+\s*[+\-*/]\s*\d+",
        r"capital", r"population", r"currency", r"language", r"president", r"leader",
        r"what time", r"what date", r"what day", r"current time"
    ]
    
    is_math_expression = any([
        re.search(r"^\s*\d+\s*[+\-*/]\s*\d+\s*$", user_input),
        re.search(r"^\s*[\d\s+\-*/]+\s*=\s*\?*\s*$", user_input)
    ])
    
    is_factual_question = any([
        re.search(r"^(what|who|where|when|why|how)\s+", user_input),
        re.search(r"\?$", user_input) and not re.search(r"motivat", user_input)
    ])
    
    is_blocked = any(re.search(pattern, user_input) for pattern in blocked_topics)
    is_motivation = any(re.search(pattern, user_input) for pattern in motivation_patterns)
    
    if is_blocked or is_math_expression or (is_factual_question and not is_motivation):
        update.message.reply_text(
            "❌ Sorry, this request is not relevant to my purpose.\n"
            "I only provide motivational quotes.\n\n"
            "Examples of requests I can help with:\n"
            "- Give me motivation for work\n"
            "- I'm feeling sad and need encouragement\n"
            "- Help me get back up after failure\n"
            "- I need inspiration to keep going"
        )
        return
    
    user_ids.add(user_id)
    save_user_data()
    
    user_moods = user_prompt_cache.get(user_id, {})
    current_mood = random.choice(list(user_moods.keys())) if user_moods else None
    
    prompt = generate_rag_prompt(user_input, current_mood, user_tone, user_id)
    
    try:
        update.message.reply_text("Creating your personalized motivation... 💭")
        result = ask_cortensor_motivation(prompt)
        
        if "error" not in result.lower():
            cleaned_result = clean_motivation_output(result)
            cleaned_result = validate_and_clean_response(cleaned_result, user_tone)
            
            # Jika masih ada multiple responses, ambil hanya yang pertama
            if "\n\n" in cleaned_result:
                parts = cleaned_result.split("\n\n")
                cleaned_result = max(parts, key=lambda x: len(x.strip()))
            
            message = update.message.reply_text(f"({user_tone} style):\n\n{cleaned_result}")
            
            # Tambahkan tombol feedback
            add_feedback_button(context, user_id, message.message_id, cleaned_result)
            
            if current_mood and current_mood in KNOWLEDGE_BASE:
                KNOWLEDGE_BASE[current_mood].append(cleaned_result)
            else:
                if "motivation" not in KNOWLEDGE_BASE:
                    KNOWLEDGE_BASE["motivation"] = []
                KNOWLEDGE_BASE["motivation"].append(cleaned_result)
            save_knowledge_base()
        
    except Exception as e:
        logger.error("❌ Motivation error", exc_info=True)

# ------------------------
# Main with Shutdown Hook
# ------------------------

def main():
    load_prompt_cache()
    load_user_data()
    load_knowledge_base()
    load_feedback_data()
    
    if not all([TELEGRAM_BOT_TOKEN, CORTENSOR_API_URL, CORTENSOR_API_KEY, CORTENSOR_SESSION_ID]):
        logger.critical("❌ .env configuration incomplete. Bot cannot start.")
        return
    
    try:
        updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        scheduler = BackgroundScheduler(timezone=utc)
        scheduler.start()
        dispatcher.bot_data['scheduler'] = scheduler
        schedule_daily_jobs(scheduler, updater.bot)
        
        onboarding_conversation = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                ASK_TIMEZONE: [MessageHandler(Filters.text & ~Filters.command, handle_timezone)],
                ASK_TONE: [MessageHandler(Filters.text & ~Filters.command, handle_tone)],
                ASK_FEELING: [MessageHandler(Filters.text & ~Filters.command, handle_feeling)]
            },
            fallbacks=[],
            conversation_timeout=300
        )
        
        set_timezone_handler = ConversationHandler(
            entry_points=[CommandHandler("settimezone", set_timezone_command)],
            states={
                ASK_TIMEZONE: [MessageHandler(Filters.text & ~Filters.command, handle_timezone)]
            },
            fallbacks=[]
        )
        
        set_tone_handler = ConversationHandler(
            entry_points=[CommandHandler("settone", set_tone_command)],
            states={
                ASK_TONE: [MessageHandler(Filters.text & ~Filters.command, handle_tone)]
            },
            fallbacks=[]
        )
        
        dispatcher.add_handler(onboarding_conversation)
        dispatcher.add_handler(set_timezone_handler)
        dispatcher.add_handler(set_tone_handler)
        dispatcher.add_handler(CommandHandler("setname", set_name))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("about", about_command))
        dispatcher.add_handler(CallbackQueryHandler(handle_feedback, pattern=r"^fb_"))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_motivation_request))
        
        updater.start_polling()
        logger.info("🤖 Daily Motivation Bot is running...")
        updater.idle()
        
    except Exception as e:
        logger.critical("❌ Failed to start the bot", exc_info=True)
    finally:
        save_user_data()
        save_prompt_cache()
        save_knowledge_base()
        save_feedback_data()
        logger.info("🛑 Bot stopped. All data saved.")

if __name__ == '__main__':
    main()
