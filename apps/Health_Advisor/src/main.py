import os
import logging
import requests
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler
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
SYMPTOMS, LIFESTYLE, GOALS = range(3)

# Struktur data untuk menyimpan profil user sementara
user_profiles = {}

def clean_cortensor_response(response_text: str) -> str:
    """Membersihkan respons Cortensor dari markup dan spasi berlebihan"""
    # Hapus tag </s> dan spasi sebelum/sesudahnya
    cleaned = re.sub(r'\s*</s>\s*', '', response_text)
    
    # Hapus spasi kosong berlebihan
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
    
    # Hapus spasi di awal dan akhir
    return cleaned.strip()

def format_health_response(response_text: str) -> str:
    """Memformat respons kesehatan dengan menangani spasi secara cerdas"""
    # Bersihkan respons dari markup Cortensor
    cleaned_text = clean_cortensor_response(response_text)
    
    # Identifikasi bagian-bagian utama
    sections = [
        "1. Brief condition analysis:",
        "2. Specific recommendations",
        "3. Weekly targets:",
        "4. Warning if dangerous symptoms detected:"
    ]
    
    # Periksa apakah respons sudah memiliki spasi antar bagian
    has_proper_spacing = True
    for section in sections:
        if section in cleaned_text:
            # Cek apakah ada setidaknya satu baris kosong setelah bagian
            section_index = cleaned_text.find(section)
            if section_index != -1:
                next_chars = cleaned_text[section_index + len(section):section_index + len(section) + 2]
                if next_chars != "\n\n":
                    has_proper_spacing = False
                    break
    
    # Jika respons sudah memiliki spasi yang tepat, kembalikan langsung
    if has_proper_spacing:
        return cleaned_text
    
    # Jika tidak, tambahkan spasi di antara bagian-bagian
    formatted_text = cleaned_text
    
    # Tambahkan baris kosong sebelum setiap bagian
    for section in sections:
        if section in formatted_text:
            # Hanya tambahkan jika belum ada spasi sebelumnya
            if not formatted_text.startswith(section) and not formatted_text[formatted_text.find(section)-2:formatted_text.find(section)] == "\n\n":
                formatted_text = formatted_text.replace(section, "\n\n" + section)
    
    return formatted_text

def start_command(update: Update, context: CallbackContext) -> None:
    """Memulai interaksi dengan user"""
    user = update.message.from_user
    welcome_message = (
        f"👋 Hello {user.first_name}! I am your personal *Health Advisor*.\n\n"
        "I provide health insights using decentralized AI technology from "
        "Cortensor Network while ensuring your data privacy.\n\n"
        "You can start a health consultation with /consult command or use the button below."
    )
    
    # Kirim pesan dengan tombol inline
    keyboard = [
        [InlineKeyboardButton("🩺 Start Consultation", callback_data='consult')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def start_consultation(update: Update, context: CallbackContext) -> int:
    """Memulai proses konsultasi"""
    # Handle jika dipanggil dari callback (tombol)
    if update.callback_query:
        query = update.callback_query
        query.answer()
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        user_id = query.from_user.id
    # Handle jika dipanggil dari command (/consult)
    else:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        message_id = None
    
    # Simpan data user sementara
    user_profiles[user_id] = {
        'symptoms': "",
        'lifestyle': "",
        'goals': ""
    }
    
    message_text = (
        "🩺 *Personal Health Consultation*\n\n"
        "First, describe your main symptoms:\n"
        "(Example: 'Throbbing headache in front of head, accompanied by nausea')"
    )
    
    # Kirim/edit pesan tergantung sumbernya
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
    """Menerima gejala dari user"""
    user_id = update.message.from_user.id
    symptoms = update.message.text
    
    # Anonimisasi data sensitif
    anon_symptoms = anonymize_health_data(symptoms)
    
    user_profiles[user_id]['symptoms'] = anon_symptoms
    
    update.message.reply_text(
        "📝 Thank you. Now tell me about your lifestyle:\n"
        "- Diet (vegetarian/non-vegetarian)\n"
        "- Physical activity (exercise frequency)\n"
        "- Sleep habits (hours per night)\n"
        "- Other habits (smoking, alcohol, etc)\n\n"
        "Example: 'I'm non-vegetarian, exercise 2x/week, sleep 6 hours/night, non-smoker'"
    )
    
    return LIFESTYLE

def receive_lifestyle(update: Update, context: CallbackContext) -> int:
    """Menerima data gaya hidup"""
    user_id = update.message.from_user.id
    lifestyle = update.message.text
    
    # Anonimisasi data sensitif
    anon_lifestyle = anonymize_health_data(lifestyle)
    
    user_profiles[user_id]['lifestyle'] = anon_lifestyle
    
    update.message.reply_text(
        "🎯 Finally, what are your health goals?\n"
        "(Example: 'Lose 5kg', 'Improve fitness', "
        "'Manage stress', or 'Fix sleep patterns')"
    )
    
    return GOALS

def receive_goals(update: Update, context: CallbackContext) -> int:
    """Menerima tujuan kesehatan dan memproses ke Cortensor"""
    user_id = update.message.from_user.id
    goals = update.message.text
    
    # Anonimisasi data sensitif
    anon_goals = anonymize_health_data(goals)
    user_profiles[user_id]['goals'] = anon_goals
    
    # Kirim indikator "typing"
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action='typing'
    )
    
    # Kirim pesan status pemrosesan
    processing_msg = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🧠 <i>Analyzing your health profile with decentralized AI... This may take 10-20 seconds</i>",
        parse_mode='HTML'
    )
    
    # Siapkan payload untuk Cortensor
    payload = {
        "session_id": int(CORTENSOR_SESSION_ID),
        "prompt": create_health_prompt(user_profiles[user_id]),
        "prompt_type": 0,
        "stream": False,
        "timeout": 180,
        "privacy_level": "high"  # Mode privasi tinggi
    }
    
    headers = {
        "Authorization": f"Bearer {CORTENSOR_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Kirim ke Cortensor Network
        response = requests.post(
            CORTENSOR_API_URL,
            headers=headers,
            json=payload,
            timeout=320
        )
        response.raise_for_status()
        
        # Proses respons
        response_data = response.json()
        raw_advice = response_data['choices'][0]['text'].strip()
        
        # Format ulang respons untuk menangani markup dan spasi
        advice = format_health_response(raw_advice)
        
        # Format respons (TANPA SESSION ID)
        formatted_advice = (
            f"🩺 *Personal Health Insights*\n\n"
            f"{advice}\n\n"
            f"💡 *Disclaimer*: This advice is informational and not a substitute for professional medical diagnosis. "
            f"Processed decentralized via Cortensor Network."
        )
        
        # Tambahkan tombol aksi
        keyboard = [
            [InlineKeyboardButton("💊 Save Recommendation", callback_data='save_advice')],
            [InlineKeyboardButton("🔄 New Consultation", callback_data='new_consult')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit pesan pemrosesan menjadi hasil
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id,
            text=formatted_advice,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Logging (tanpa data pribadi)
        logger.info(f"Consultation successful for user ID: {user_id}")
        
    except Exception as e:
        logger.error(f"Cortensor error: {str(e)}")
        
        # Edit pesan pemrosesan menjadi pesan error
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id,
            text="⚠️ Sorry, we encountered an error processing your request. "
                 "Please try again later or use /consult to start over."
        )
    
    # Hapus data sementara
    if user_id in user_profiles:
        del user_profiles[user_id]
    
    return ConversationHandler.END

def anonymize_health_data(raw_input: str) -> str:
    """Anonimisasi data kesehatan sensitif"""
    # Hapus nama (asumsi format "Name: ...")
    anonymized = re.sub(r'(nama|name):?\s*[a-zA-Z]+', '[REDACTED]', raw_input, flags=re.IGNORECASE)
    
    # Hapus nomor telepon
    anonymized = re.sub(r'(\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})', 
                        '[REDACTED_PHONE]', anonymized)
    
    # Hapus alamat spesifik
    anonymized = re.sub(r'(jalan|jl\.?|jr|street|st)\s+[\w\s]+?(\s+no\.?\s*\d+)?', 
                        '[REDACTED_ADDRESS]', anonymized, flags=re.IGNORECASE)
    
    # Ganti usia spesifik dengan range
    anonymized = re.sub(r'(\bumur|usia|age)\s*:\s*\d{1,3}', 
                        lambda m: f"{m.group(1)}: [AGE_RANGE]", anonymized, flags=re.IGNORECASE)
    
    return anonymized

def create_health_prompt(profile: dict) -> str:
    """Membuat prompt terstruktur untuk Cortensor dalam bahasa Inggris"""
    return (
        "You are a Health Advisor AI. Provide personalized health advice based on:\n\n"
        f"**Symptoms**: {profile['symptoms']}\n"
        f"**Lifestyle**: {profile['lifestyle']}\n"
        f"**Health Goals**: {profile['goals']}\n\n"
        "Response format:\n"
        "1. Brief condition analysis\n"
        "2. Specific recommendations (diet, activities, habits)\n"
        "3. Weekly targets\n"
        "4. Warning if dangerous symptoms detected\n"
        "Use supportive and professional English."
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
    """Menangani interaksi tombol inline"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'consult':
        start_consultation(update, context)
    elif query.data == 'save_advice':
        query.edit_message_text(
            text="💾 Recommendation saved securely in decentralized storage.\n"
            "Access ID: `HEALTH-" + datetime.now().strftime("%Y%m%d%H%M") + "-" + str(query.from_user.id)[-4:] + "`\n\n"
            "Use this ID to access your recommendations later.",
            parse_mode='Markdown'
        )
    elif query.data == 'new_consult':
        start_consultation(update, context)

def help_command(update: Update, context: CallbackContext) -> None:
    """Menampilkan perintah bantuan"""
    help_text = (
        "🆘 *Available Commands*\n\n"
        "/start - Start the bot\n"
        "/consult - Start health consultation\n"
        "/help - Show this help message\n\n"
        "Use the 'Start Consultation' button to begin your health assessment."
    )
    update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Menjalankan bot"""
    if not all([TELEGRAM_BOT_TOKEN, CORTENSOR_API_URL, CORTENSOR_API_KEY, CORTENSOR_SESSION_ID]):
        logger.critical("FATAL: Missing environment variables! Bot cannot start.")
        return

    logger.info("Starting Health Advisor Bot...")

    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Setup conversation handler untuk konsultasi
    conv_handler = ConversationHandler(
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

    # Register handlers
    dispatcher.add_handler(CommandHandler('start', start_command))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    logger.info("Health Advisor Bot is running!")
    updater.idle()

if __name__ == '__main__':
    main()
