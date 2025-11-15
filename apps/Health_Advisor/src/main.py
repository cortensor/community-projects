import os
import logging
import requests
import re
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    JobQueue
)

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CORTENSOR_API_URL = os.getenv("CORTENSOR_API_URL")
CORTENSOR_API_KEY = os.getenv("CORTENSOR_API_KEY")
CORTENSOR_SESSION_ID = os.getenv("CORTENSOR_SESSION_ID")

# State untuk conversation handler
SYMPTOMS, LIFESTYLE, GOALS, SYMPTOM_TRACKING, PROGRESS_UPDATE = range(5)

# Data structures untuk health journey
user_profiles = {}
health_journeys = {}
daily_symptoms = {}

@dataclass
class HealthJourney:
    """Class untuk menyimpan perjalanan kesehatan user"""
    user_id: int
    consultations: List[Dict]
    symptom_timeline: List[Dict]
    progress_metrics: Dict
    weekly_checkins: List[Dict]
    health_score: int
    start_date: datetime
    last_activity: datetime
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.consultations = []
        self.symptom_timeline = []
        self.progress_metrics = {
            "symptom_improvement": 0,
            "goal_achievement": 0,
            "consistency_score": 0
        }
        self.weekly_checkins = []
        self.health_score = 50  # Default score
        self.start_date = datetime.now()
        self.last_activity = datetime.now()

@dataclass
class DailySymptom:
    """Class untuk tracking gejala harian"""
    user_id: int
    date: datetime
    symptoms: Dict
    severity: int  # 1-10 scale
    notes: str
    mood: str  # happy, neutral, sad

def escape_markdown(text: str) -> str:
    """Escape karakter khusus Markdown untuk menghindari parsing error"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def clean_cortensor_response(response_text: str) -> str:
    """Membersihkan respons Cortensor dari markup dan spasi berlebihan"""
    # Hapus tag </s> dan spasi berlebihan
    cleaned = re.sub(r'\s*</s>\s*', '', response_text)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Hapus kalimat pembuka yang tidak diinginkan
    cleaned = re.sub(
        r'^(Hello! I\'m [A-Za-z]+, your Health Advisor AI\. I understand that you\'re |'
        r'^Hello! I\'m your Health Advisor AI\. I see that you\'ve |'
        r'^As your Health Advisor AI, I ).*?\.\s*',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    return cleaned.strip()

def format_health_response(response_text: str) -> str:
    """Memformat respons kesehatan dengan memperbaiki penomoran dan formatting"""
    cleaned_text = clean_cortensor_response(response_text)
    
    # PERBAIKI PENOMORAN YANG TIDAK KONSISTEN
    # Ganti semua "1." yang berulang dengan penomoran yang benar
    sections = [
        ("1. Brief condition analysis:", "🩺 **BRIEF CONDITION ANALYSIS:**"),
        ("1. Specific recommendations", "📋 **SPECIFIC RECOMMENDATIONS:**"),
        ("1. Weekly targets:", "🎯 **WEEKLY TARGETS:**"),
        ("1. Warning if dangerous symptoms detected:", "⚠️ **WARNING IF DANGEROUS SYMPTOMS DETECTED:**"),
        ("2. Specific recommendations:", "📋 **SPECIFIC RECOMMENDATIONS:**"),
        ("3. Weekly targets:", "🎯 **WEEKLY TARGETS:**"),
        ("4. Warning if dangerous symptoms detected:", "⚠️ **WARNING IF DANGEROUS SYMPTOMS DETECTED:**")
    ]
    
    for wrong, correct in sections:
        cleaned_text = cleaned_text.replace(wrong, f"\n\n{correct}\n")
    
    # HAPUS ESCAPE CHARACTERS YANG TIDAK PERLU
    cleaned_text = cleaned_text.replace('\\.', '.')
    cleaned_text = cleaned_text.replace('\\*', '•')
    
    # FORMAT BULLET POINTS
    cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'**\1**', cleaned_text)  # Maintain bold formatting
    
    # Pastikan ada spasi yang cukup antara sections
    cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
    
    return cleaned_text.strip()

def start_command(update: Update, context: CallbackContext) -> None:
    """Memulai interaksi dengan user - VERSION 2.0 dengan Health Journey"""
    user = update.message.from_user
    
    # Initialize health journey jika belum ada
    if user.id not in health_journeys:
        health_journeys[user.id] = HealthJourney(user.id)
    
    welcome_message = (
        f"👋 Hello {user.first_name}! I am your personal *Health Advisor 2.0* 🚀\n\n"
        "🌟 *New Features:*\n"
        "• 📊 Health Journey Tracking\n"
        "• 📈 Progress Analytics\n"
        "• 🔄 Weekly Follow-ups\n"
        "• 🎯 Personalized Goals\n"
        "• 📝 Daily Symptom Tracker\n\n"
        "Start your health journey with /consult or track daily symptoms with /track"
    )
    
    keyboard = [
        [InlineKeyboardButton("🩺 Start Health Journey", callback_data='consult')],
        [InlineKeyboardButton("📝 Track Daily Symptoms", callback_data='track_symptoms')],
        [InlineKeyboardButton("📊 View Progress", callback_data='view_progress')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def start_consultation(update: Update, context: CallbackContext) -> int:
    """Memulai proses konsultasi dengan health journey integration"""
    if update.callback_query:
        query = update.callback_query
        query.answer()
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        user_id = query.from_user.id
    else:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        message_id = None
    
    # Initialize health journey jika belum ada
    if user_id not in health_journeys:
        health_journeys[user_id] = HealthJourney(user_id)
    
    user_profiles[user_id] = {
        'symptoms': "",
        'lifestyle': "",
        'goals': "",
        'consultation_id': str(uuid.uuid4())[:8]
    }
    
    message_text = (
        "🩺 *Health Journey Assessment*\n\n"
        "📍 *Step 1 of 3: Current Symptoms*\n"
        "Describe your main symptoms:\n"
        "*(Example: 'Headache in the morning, low energy throughout day')*"
    )
    
    if update.callback_query:
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=message_text,
            parse_mode='Markdown'
        )
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode='Markdown'
        )
    
    return SYMPTOMS

def receive_symptoms(update: Update, context: CallbackContext) -> int:
    """Menerima gejala dari user dan simpan ke health journey"""
    user_id = update.message.from_user.id
    symptoms = update.message.text
    
    anon_symptoms = anonymize_health_data(symptoms)
    user_profiles[user_id]['symptoms'] = anon_symptoms
    
    # Track symptoms untuk analytics
    if user_id in health_journeys:
        health_journeys[user_id].symptom_timeline.append({
            "date": datetime.now(),
            "symptoms": anon_symptoms,
            "type": "consultation_input"
        })
    
    update.message.reply_text(
        "📍 *Step 2 of 3: Lifestyle Profile*\n\n"
        "Tell me about your daily habits:\n"
        "- 🍽️ Diet type & eating schedule\n"
        "- 🏃 Physical activity & exercise\n"
        "- 😴 Sleep patterns & quality\n"
        "- 🚭 Habits (smoking, alcohol, etc)\n\n"
        "*Example:* 'Vegetarian diet, exercise 3x/week, sleep 7 hours, non-smoker'",
        parse_mode='Markdown'
    )
    
    return LIFESTYLE

def receive_lifestyle(update: Update, context: CallbackContext) -> int:
    """Menerima data gaya hidup"""
    user_id = update.message.from_user.id
    lifestyle = update.message.text
    
    anon_lifestyle = anonymize_health_data(lifestyle)
    user_profiles[user_id]['lifestyle'] = anon_lifestyle
    
    update.message.reply_text(
        "📍 *Step 3 of 3: Health Goals*\n\n"
        "What would you like to achieve?\n"
        "• 🏋️ Fitness improvement\n"  
        "• 🧘 Stress management\n"
        "• 🍎 Better nutrition\n"
        "• 😴 Sleep optimization\n"
        "• 📉 Symptom reduction\n\n"
        "*Example:* 'Reduce headache frequency, improve sleep quality, more energy'",
        parse_mode='Markdown'
    )
    
    return GOALS

def receive_goals(update: Update, context: CallbackContext) -> int:
    """Menerima tujuan kesehatan dan proses ke Cortensor dengan health journey integration"""
    user_id = update.message.from_user.id
    goals = update.message.text
    
    anon_goals = anonymize_health_data(goals)
    user_profiles[user_id]['goals'] = anon_goals
    
    # Update health journey
    if user_id in health_journeys:
        health_journeys[user_id].last_activity = datetime.now()
    
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action='typing'
    )
    
    processing_msg = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🧠 *Analyzing your health profile with AI... Creating your personalized health journey...*",
        parse_mode='Markdown'
    )
    
    # Payload dengan prompt yang diperbaiki
    payload = {
        "session_id": int(CORTENSOR_SESSION_ID),
        "prompt": create_health_prompt(user_profiles[user_id]),
        "prompt_type": 0,
        "stream": False,
        "timeout": 180,
        "privacy_level": "high"
    }
    
    headers = {
        "Authorization": f"Bearer {CORTENSOR_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            CORTENSOR_API_URL,
            headers=headers,
            json=payload,
            timeout=320
        )
        response.raise_for_status()
        
        response_data = response.json()
        raw_advice = response_data['choices'][0]['text'].strip()
        
        # GUNAKAN FUNGSI FORMATTING YANG DIPERBAIKI
        advice = format_health_response(raw_advice)
        
        # Simpan ke health journey
        if user_id in health_journeys:
            consultation_data = {
                "consultation_id": user_profiles[user_id]['consultation_id'],
                "date": datetime.now(),
                "symptoms": user_profiles[user_id]['symptoms'],
                "lifestyle": user_profiles[user_id]['lifestyle'],
                "goals": user_profiles[user_id]['goals'],
                "advice": advice,
                "health_score": calculate_health_score(user_profiles[user_id])
            }
            health_journeys[user_id].consultations.append(consultation_data)
            health_journeys[user_id].health_score = consultation_data['health_score']
        
        # FORMATTING FINAL YANG LEBIH BAIK - GUNAKAN MARKDOWN
        formatted_advice = (
            f"🩺 *Personal Health Insights*\n\n"
            f"{advice}\n\n"
            f"📊 *Health Journey Started!*\n"
            f"Your health score: {health_journeys[user_id].health_score if user_id in health_journeys else '50'}/100\n\n"
            f"💡 *Disclaimer:* This advice is informational and not a substitute for professional medical diagnosis."
        )
        
        # Schedule follow-up
        schedule_follow_up(context, user_id)
        
        keyboard = [
            [InlineKeyboardButton("💾 Save to Health Journey", callback_data='save_advice')],
            [InlineKeyboardButton("📝 Track Symptoms", callback_data='track_symptoms')],
            [InlineKeyboardButton("📊 View Progress", callback_data='view_progress')],
            [InlineKeyboardButton("🔄 New Consultation", callback_data='new_consult')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id,
            text=formatted_advice,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"Consultation successful for user ID: {user_id}")
        
    except Exception as e:
        logger.error(f"Cortensor error: {str(e)}")
        
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id,
            text="⚠️ Sorry, we encountered an error processing your request. "
                 "Please try again later or use /consult to start over."
        )
    
    if user_id in user_profiles:
        del user_profiles[user_id]
    
    return ConversationHandler.END

def start_symptom_tracking(update: Update, context: CallbackContext) -> int:
    """Memulai daily symptom tracking"""
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    
    if update.callback_query:
        query = update.callback_query
        query.answer()
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                "📝 *Daily Symptom Tracker*\n\n"
                "How are you feeling today? Rate your main symptom severity (1-10):\n\n"
                "*1-3:* Mild (noticeable but not affecting daily life)\n"
                "*4-6:* Moderate (affecting some activities)\n"
                "*7-10:* Severe (significantly impacting daily life)\n\n"
                "*Example:* 'Headache level 6, fatigue level 4'"
            ),
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            "📝 *Daily Symptom Tracker*\n\n"
            "How are you feeling today? Rate your main symptom severity (1-10):\n\n"
            "*1-3:* Mild (noticeable but not affecting daily life)\n"
            "*4-6:* Moderate (affecting some activities)\n"
            "*7-10:* Severe (significantly impacting daily life)\n\n"
            "*Example:* 'Headache level 6, fatigue level 4'",
            parse_mode='Markdown'
        )
    
    return SYMPTOM_TRACKING

def receive_symptom_tracking(update: Update, context: CallbackContext) -> int:
    """Menerima dan memproses symptom tracking harian"""
    user_id = update.message.from_user.id
    symptoms_input = update.message.text
    
    # Extract severity levels from input
    severity_match = re.findall(r'(\d+)/10', symptoms_input)
    avg_severity = 5  # Default
    
    if severity_match:
        severities = [int(match) for match in severity_match]
        avg_severity = sum(severities) // len(severities)
    
    # Simpan symptom tracking
    if user_id not in daily_symptoms:
        daily_symptoms[user_id] = []
    
    daily_symptom = DailySymptom(
        user_id=user_id,
        date=datetime.now(),
        symptoms={"description": symptoms_input, "severity": avg_severity},
        severity=avg_severity,
        notes=symptoms_input,
        mood="neutral"  # Bisa dikembangkan dengan sentiment analysis
    )
    
    daily_symptoms[user_id].append(daily_symptom)
    
    # Update health journey
    if user_id in health_journeys:
        health_journeys[user_id].symptom_timeline.append({
            "date": datetime.now(),
            "symptoms": symptoms_input,
            "severity": avg_severity,
            "type": "daily_tracking"
        })
        health_journeys[user_id].last_activity = datetime.now()
    
    # Berikan feedback berdasarkan severity
    if avg_severity <= 3:
        feedback = "🌟 Great! Your symptoms are mild today. Keep up the good work!"
    elif avg_severity <= 6:
        feedback = "📋 Moderate symptoms noted. Remember to follow your health plan."
    else:
        feedback = "⚠️ Severe symptoms detected. Please consider consulting a healthcare professional if this continues."
    
    update.message.reply_text(
        f"📊 *Symptom Logged Successfully!*\n\n"
        f"{feedback}\n\n"
        f"📈 *Trend Analysis:*\n"
        f"Today's severity: {avg_severity}/10\n"
        f"Logged to your Health Journey\n\n"
        f"Use /progress to see your symptom trends over time.",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

def view_progress(update: Update, context: CallbackContext) -> None:
    """Menampilkan progress dan analytics health journey"""
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    
    if update.callback_query:
        query = update.callback_query
        query.answer()
        chat_id = query.message.chat_id
        message_id = query.message.message_id
    else:
        chat_id = update.message.chat_id
        message_id = None
    
    if user_id not in health_journeys or not health_journeys[user_id].consultations:
        message_text = (
            "📊 *Health Progress*\n\n"
            "No health journey data yet. Start your first consultation with /consult "
            "or track daily symptoms with /track to begin building your health analytics!"
        )
    else:
        journey = health_journeys[user_id]
        
        # Calculate some basic analytics
        total_consultations = len(journey.consultations)
        days_active = (datetime.now() - journey.start_date).days
        symptom_entries = len(journey.symptom_timeline)
        
        # Simple trend analysis
        recent_symptoms = [s for s in journey.symptom_timeline if s['type'] == 'daily_tracking']
        if recent_symptoms:
            avg_recent_severity = sum(s.get('severity', 5) for s in recent_symptoms[-5:]) / min(5, len(recent_symptoms))
            severity_trend = "improving" if avg_recent_severity < 6 else "stable" if avg_recent_severity == 6 else "needs attention"
        else:
            severity_trend = "no data"
        
        message_text = (
            f"📊 *Your Health Journey Progress*\n\n"
            f"🏆 *Health Score:* {journey.health_score}/100\n"
            f"📅 *Days Active:* {days_active} days\n"
            f"🩺 *Consultations:* {total_consultations}\n"
            f"📝 *Symptom Entries:* {symptom_entries}\n"
            f"📈 *Symptom Trend:* {severity_trend}\n\n"
            f"*Recent Activity:*\n"
        )
        
        # Show last 3 activities
        recent_activities = sorted(
            journey.consultations + [
                {"date": s["date"], "type": "symptom_tracking", "description": "Symptom check"} 
                for s in journey.symptom_timeline if s['type'] == 'daily_tracking'
            ],
            key=lambda x: x['date'],
            reverse=True
        )[:3]
        
        for activity in recent_activities:
            if 'consultation_id' in activity:
                message_text += f"• 🩺 Consultation on {activity['date'].strftime('%b %d')}\n"
            else:
                message_text += f"• 📝 Symptom check on {activity['date'].strftime('%b %d')}\n"
    
    keyboard = [
        [InlineKeyboardButton("📝 Track Today's Symptoms", callback_data='track_symptoms')],
        [InlineKeyboardButton("🩺 New Consultation", callback_data='consult')],
        [InlineKeyboardButton("📈 Detailed Analytics", callback_data='detailed_analytics')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

def calculate_health_score(profile: dict) -> int:
    """Menghitung health score sederhana berdasarkan input user"""
    score = 50  # Base score
    
    # Simple heuristic scoring (bisa dikembangkan lebih kompleks)
    if any(word in profile['symptoms'].lower() for word in ['severe', 'pain', 'chronic', 'constant']):
        score -= 20
    elif any(word in profile['symptoms'].lower() for word in ['mild', 'occasional', 'sometimes']):
        score -= 10
    
    if 'exercise' in profile['lifestyle'].lower():
        if '3' in profile['lifestyle'] or 'three' in profile['lifestyle']:
            score += 15
        elif '2' in profile['lifestyle'] or 'two' in profile['lifestyle']:
            score += 10
    
    if 'sleep' in profile['lifestyle'].lower():
        if '7' in profile['lifestyle'] or '8' in profile['lifestyle']:
            score += 10
        elif '6' in profile['lifestyle']:
            score += 5
    
    return max(0, min(100, score))

def schedule_follow_up(context: CallbackContext, user_id: int, days: int = 7) -> None:
    """Menjadwalkan follow-up otomatis"""
    try:
        # Schedule follow-up message
        context.job_queue.run_once(
            callback=send_follow_up_reminder,
            when=timedelta(days=days),
            context=user_id,
            name=f"followup_{user_id}_{datetime.now().strftime('%Y%m%d')}"
        )
        logger.info(f"Scheduled follow-up for user {user_id} in {days} days")
    except Exception as e:
        logger.error(f"Error scheduling follow-up: {e}")

def send_follow_up_reminder(context: CallbackContext) -> None:
    """Mengirim reminder follow-up"""
    job = context.job
    user_id = job.context
    
    try:
        message = (
            "🔔 *Health Journey Follow-up*\n\n"
            "How are you feeling since your last consultation?\n\n"
            "📝 Track your current symptoms with /track\n"
            "🩺 Start a new consultation with /consult\n"
            "📊 Check your progress with /progress\n\n"
            "Your health journey continues! 🌟"
        )
        
        context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"Sent follow-up reminder to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending follow-up to user {user_id}: {e}")

def anonymize_health_data(raw_input: str) -> str:
    """Anonimisasi data kesehatan sensitif"""
    anonymized = re.sub(r'(nama|name):?\s*[a-zA-Z]+', '[REDACTED]', raw_input, flags=re.IGNORECASE)
    anonymized = re.sub(r'(\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})', 
                        '[REDACTED_PHONE]', anonymized)
    anonymized = re.sub(r'(jalan|jl\.?|jr|street|st)\s+[\w\s]+?(\s+no\.?\s*\d+)?', 
                        '[REDACTED_ADDRESS]', anonymized, flags=re.IGNORECASE)
    anonymized = re.sub(r'(\bumur|usia|age)\s*:\s*\d{1,3}', 
                        lambda m: f"{m.group(1)}: [AGE_RANGE]", anonymized, flags=re.IGNORECASE)
    return anonymized

def create_health_prompt(profile: dict) -> str:
    """Membuat prompt terstruktur untuk Cortensor"""
    return (
        "You are a Health Advisor AI. Provide personalized health advice based on the user's profile.\n\n"
        f"**SYMPTOMS**: {profile['symptoms']}\n"
        f"**LIFESTYLE**: {profile['lifestyle']}\n"
        f"**HEALTH GOALS**: {profile['goals']}\n\n"
        "**IMPORTANT: PLEASE FOLLOW THIS EXACT RESPONSE FORMAT:**\n\n"
        "1. Brief condition analysis:\n[Provide your analysis here]\n\n"
        "2. Specific recommendations:\n- Diet: [recommendations]\n- Activities: [recommendations]  \n- Habits: [recommendations]\n\n"
        "3. Weekly targets:\n- [Target 1]\n- [Target 2]\n- [Target 3]\n\n"
        "4. Warning if dangerous symptoms detected:\n[Provide warnings if any]\n\n"
        "**FORMATTING RULES:**\n"
        "- Use proper numbering (1, 2, 3, 4) for each main section\n"
        "- Use bullet points with asterisks (*) or hyphens (-) for lists\n"
        "- Be concise and professional\n"
        "- Do not use HTML tags or complex markdown"
    )

def cancel_consultation(update: Update, context: CallbackContext) -> int:
    """Membatalkan proses konsultasi"""
    user_id = update.message.from_user.id
    if user_id in user_profiles:
        del user_profiles[user_id]
    
    update.message.reply_text(
        "❌ Consultation canceled. "
        "Temporary data deleted. Use /consult to start over."
    )
    return ConversationHandler.END

def button_handler(update: Update, context: CallbackContext) -> None:
    """Menangani interaksi tombol inline - FIXED VERSION"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'consult':
        start_consultation(update, context)
    elif query.data == 'track_symptoms':
        start_symptom_tracking(update, context)
    elif query.data == 'view_progress':
        view_progress(update, context)
    elif query.data == 'save_advice':
        # KIRIM PESAN KONFIRMASI BARU - PESAN ASLI TETAP ADA
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="💾 *Recommendation saved to your Health Journey!*\n\n"
                 "📊 This advice is now part of your health analytics. "
                 "We'll track your progress and provide follow-up reminders.\n\n"
                 "Use /progress to view your health journey anytime.",
            parse_mode='Markdown'
        )
        # OPSIONAL: Beri feedback bahwa sudah disimpan
        query.answer("✅ Saved successfully!", show_alert=False)
    elif query.data == 'new_consult':
        start_consultation(update, context)
    elif query.data == 'detailed_analytics':
        query.edit_message_text(
            text="📈 *Detailed Analytics Feature*\n\n"
                 "This advanced feature is coming soon!\n\n"
                 "• 📊 Symptom trend charts\n"
                 "• 🎯 Goal achievement tracking\n"
                 "• 📱 Health journey timeline\n"
                 "• 🔄 Progress comparisons\n\n"
                 "Stay tuned for updates! 🚀",
            parse_mode='Markdown'
        )

def help_command(update: Update, context: CallbackContext) -> None:
    """Menampilkan perintah bantuan versi 2.0"""
    help_text = (
        "🆘 *Health Advisor 2.0 - Available Commands*\n\n"
        "*Core Features:*\n"
        "/start - Start your health journey\n"
        "/consult - Health consultation with AI analysis\n"
        "/track - Daily symptom tracking\n"
        "/progress - View health journey progress\n"
        "/help - Show this help message\n\n"
        "*New in 2.0:*\n"
        "• 📊 Health Journey Tracking\n"
        "• 📈 Progress Analytics\n"
        "• 🔄 Automated Follow-ups\n"
        "• 🎯 Personalized Health Scoring\n\n"
        "Start with /consult for full analysis or /track for daily monitoring!"
    )
    update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Menjalankan bot dengan fitur health journey"""
    if not all([TELEGRAM_BOT_TOKEN, CORTENSOR_API_URL, CORTENSOR_API_KEY, CORTENSOR_SESSION_ID]):
        logger.critical("FATAL: Missing environment variables! Bot cannot start.")
        return

    logger.info("Starting Health Advisor Bot 2.0 with Health Journey Tracking...")

    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Setup conversation handler untuk konsultasi
    consultation_handler = ConversationHandler(
        entry_points=[
            CommandHandler('consult', start_consultation),
            CallbackQueryHandler(start_consultation, pattern='^consult$')
        ],
        states={
            SYMPTOMS: [MessageHandler(Filters.text & ~Filters.command, receive_symptoms)],
            LIFESTYLE: [MessageHandler(Filters.text & ~Filters.command, receive_lifestyle)],
            GOALS: [MessageHandler(Filters.text & ~Filters.command, receive_goals)]
        },
        fallbacks=[CommandHandler('cancel', cancel_consultation)],
        allow_reentry=True
    )

    # Setup conversation handler untuk symptom tracking
    symptom_tracking_handler = ConversationHandler(
        entry_points=[
            CommandHandler('track', start_symptom_tracking),
            CallbackQueryHandler(start_symptom_tracking, pattern='^track_symptoms$')
        ],
        states={
            SYMPTOM_TRACKING: [MessageHandler(Filters.text & ~Filters.command, receive_symptom_tracking)]
        },
        fallbacks=[CommandHandler('cancel', cancel_consultation)],
        allow_reentry=True
    )

    # Register handlers
    dispatcher.add_handler(CommandHandler('start', start_command))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('progress', view_progress))
    dispatcher.add_handler(consultation_handler)
    dispatcher.add_handler(symptom_tracking_handler)
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    logger.info("Health Advisor Bot 2.0 is running with Health Journey Tracking!")
    updater.idle()

if __name__ == '__main__':
    main()
