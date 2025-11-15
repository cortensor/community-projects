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
    USER_PROJECTS_FILE = "user_projects.pkl"
    CONVERSATION_CONTEXT_FILE = "conversation_context.pkl"
    USER_CONTRIBUTIONS_FILE = "user_contributions.pkl"
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

# NEW: Advanced Knowledge Base with Hybrid Search
class AdvancedKnowledgeBase(KnowledgeBase):
    def __init__(self):
        super().__init__()
        self.user_contributions = PersistentDict(Config.USER_CONTRIBUTIONS_FILE)
    
    def hybrid_search(self, query: str, user_id: int = None) -> List[Tuple[dict, float]]:
        # Combine semantic search with keyword matching and user context
        semantic_results = self.search(query)
        
        # Boost results from user's previous contributions
        if user_id:
            user_docs = self.user_contributions.get(user_id, [])
            for doc in user_docs:
                if self.keyword_match(query, doc["content"]):
                    # Add user's documents with boost
                    semantic_results.append((doc, 0.8))  # High similarity score
        
        # Remove duplicates and sort
        seen_titles = set()
        unique_results = []
        for doc, score in sorted(semantic_results, key=lambda x: x[1], reverse=True):
            if doc["title"] not in seen_titles:
                seen_titles.add(doc["title"])
                unique_results.append((doc, score))
        
        return unique_results[:Config.TOP_K]
    
    def keyword_match(self, query: str, content: str) -> bool:
        query_terms = query.lower().split()
        content_lower = content.lower()
        return any(term in content_lower for term in query_terms if len(term) > 3)
    
    def add_user_contribution(self, user_id: int, title: str, content: str):
        # Add to main knowledge base
        self.add_document(title, content)
        
        # Also store in user contributions
        if user_id not in self.user_contributions.data:
            self.user_contributions.data[user_id] = []
        
        user_doc = {
            "title": title,
            "content": content,
            "timestamp": time.time()
        }
        self.user_contributions.data[user_id].append(user_doc)
        self.user_contributions._save_data()

# NEW: AI Collaboration Manager
class AICollaborationManager:
    def __init__(self):
        self.active_sessions = {}
        self.agent_workflows = {
            "research_team": {
                "researcher": "Gather and verify information",
                "analyst": "Analyze data and find patterns", 
                "synthesizer": "Combine insights into coherent report"
            },
            "content_team": {
                "ideator": "Generate creative ideas",
                "writer": "Create compelling content",
                "editor": "Refine and optimize output"
            },
            "tech_team": {
                "architect": "Design system architecture",
                "developer": "Write and test code",
                "reviewer": "Code review and optimization"
            }
        }
    
    async def start_collaboration_session(self, user_id: int, project_type: str, goal: str):
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "project_type": project_type,
            "goal": goal,
            "current_step": 0,
            "contributions": {},
            "status": "active",
            "created_at": time.time()
        }
        return session_id
    
    async def get_agent_perspective(self, session_id: str, agent_role: str, question: str):
        # Each agent has specialized prompting and perspective
        agent_prompts = {
            "researcher": f"As a research specialist, provide detailed, evidence-based information about: {question}. Focus on accuracy and credible sources.",
            "analyst": f"As a data analyst, examine this from quantitative perspective: {question}. Provide insights, patterns, and data-driven recommendations.",
            "creative_writer": f"As a creative writer, approach this creatively: {question}. Focus on storytelling, engagement, and unique perspectives.",
            "technical_expert": f"As a technical expert, provide detailed technical analysis of: {question}. Include specifications, implementations, and best practices.",
            "synthesizer": f"As a synthesis specialist, combine different perspectives on: {question}. Create a cohesive, comprehensive overview.",
            "ideator": f"As a creative ideator, brainstorm innovative ideas about: {question}. Think outside the box and provide unique concepts.",
            "writer": f"As a professional writer, create well-structured content about: {question}. Focus on clarity, engagement, and impact.",
            "editor": f"As an editor, review and improve content about: {question}. Focus on clarity, structure, and effectiveness.",
            "architect": f"As a system architect, design solutions for: {question}. Focus on scalability, maintainability, and best practices.",
            "developer": f"As a developer, provide practical implementation for: {question}. Include code examples and technical details.",
            "reviewer": f"As a code reviewer, analyze technical solutions for: {question}. Focus on quality, security, and performance."
        }
        
        prompt = agent_prompts.get(agent_role, question)
        return await CortensorAPI.query(prompt)

# NEW: Project Manager
class ProjectManager:
    def __init__(self):
        self.user_projects = PersistentDict(Config.USER_PROJECTS_FILE)
    
    def create_project(self, user_id: int, project_name: str, template: str):
        project_id = str(uuid.uuid4())
        project_data = {
            "name": project_name,
            "template": template,
            "steps": self.get_template_steps(template),
            "current_step": 0,
            "completed_steps": [],
            "created_at": time.time(),
            "documents": {},
            "status": "active"
        }
        
        if user_id not in self.user_projects.data:
            self.user_projects.data[user_id] = {}
        self.user_projects.data[user_id][project_id] = project_data
        self.user_projects._save_data()
        
        return project_id
    
    def get_template_steps(self, template: str):
        templates = {
            "business_plan": [
                "Executive Summary",
                "Company Description", 
                "Market Analysis",
                "Organization Structure",
                "Products/Services",
                "Marketing Strategy",
                "Financial Projections"
            ],
            "research_paper": [
                "Abstract",
                "Introduction", 
                "Literature Review",
                "Methodology",
                "Results",
                "Discussion",
                "Conclusion"
            ],
            "software_project": [
                "Requirements Analysis",
                "System Design",
                "Implementation Plan",
                "Testing Strategy",
                "Deployment Plan",
                "Documentation"
            ],
            "content_strategy": [
                "Audience Analysis",
                "Content Objectives",
                "Topic Research",
                "Content Calendar",
                "Creation Workflow",
                "Distribution Plan",
                "Performance Metrics"
            ]
        }
        return templates.get(template, [])
    
    def get_available_templates(self):
        return ["business_plan", "research_paper", "software_project", "content_strategy"]
    
    def get_user_projects(self, user_id: int):
        return self.user_projects.get(user_id, {})

# NEW: Context Manager
class ContextManager:
    def __init__(self):
        self.conversation_context = PersistentDict(Config.CONVERSATION_CONTEXT_FILE)
    
    def update_user_context(self, user_id: int, message: str, response: str):
        if user_id not in self.conversation_context.data:
            self.conversation_context.data[user_id] = {
                "topics": [],
                "preferences": {},
                "recent_interactions": [],
                "knowledge_gaps": [],
                "total_interactions": 0
            }
        
        # Analyze topic from conversation
        topics = self.extract_topics(message)
        for topic in topics:
            if topic not in self.conversation_context.data[user_id]["topics"]:
                self.conversation_context.data[user_id]["topics"].append(topic)
        
        # Store recent interaction
        self.conversation_context.data[user_id]["recent_interactions"].append({
            "user_message": message,
            "bot_response": response,
            "timestamp": time.time()
        })
        
        # Update total interactions
        self.conversation_context.data[user_id]["total_interactions"] += 1
        
        # Keep only last 20 interactions
        self.conversation_context.data[user_id]["recent_interactions"] = \
            self.conversation_context.data[user_id]["recent_interactions"][-20:]
        
        self.conversation_context._save_data()
    
    def extract_topics(self, text: str) -> List[str]:
        # Simple topic extraction - bisa ditingkatkan dengan NLP
        topics = []
        common_topics = ["technology", "business", "science", "programming", 
                        "education", "health", "finance", "creative", "research",
                        "ai", "machine learning", "data", "analysis", "writing",
                        "development", "startup", "marketing", "strategy"]
        
        text_lower = text.lower()
        for topic in common_topics:
            if topic in text_lower:
                topics.append(topic)
        
        return topics
    
    def get_user_insights(self, user_id: int) -> Dict:
        context = self.conversation_context.get(user_id, {})
        if not context:
            return {}
        
        topics = context.get("topics", [])
        total_interactions = context.get("total_interactions", 0)
        recent_count = len(context.get("recent_interactions", []))
        
        return {
            "total_interactions": total_interactions,
            "recent_activity": recent_count,
            "top_interests": topics[:5],
            "engagement_level": "High" if recent_count > 10 else "Medium" if recent_count > 5 else "Low"
        }

# Initialize storage and managers
prompt_cache = PromptCache(Config.PROMPT_CACHE_FILE)
user_history = UserHistory(Config.USER_HISTORY_FILE)
knowledge_base = AdvancedKnowledgeBase()
collaboration_manager = AICollaborationManager()
project_manager = ProjectManager()
context_manager = ContextManager()

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
    async def query_with_rag(prompt: str, user_id: int = None) -> str:
        try:
            relevant_docs = knowledge_base.hybrid_search(prompt, user_id)
            
            context_parts = []
            if relevant_docs:
                context_parts.append("📚 Relevant Context:\n" + "\n".join(
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
🤖 Welcome to Decentralized Prompt Helper Bot By Cortensor Network 

🌟 <b>Unique Features:</b>

🤝 <b>AI Collaboration</b>
• Research Teams - Deep analysis & fact-checking
• Content Teams - Creative writing & optimization  
• Tech Teams - Technical development & code review

🚀 <b>Project Workflows</b>
• Business Plans - Complete business documentation
• Research Papers - Academic research workflow
• Software Projects - Development lifecycle
• Content Strategy - Marketing content planning

🧠 <b>Smart Features</b>
• Context Awareness - Remembers your preferences
• Advanced RAG - Hybrid semantic search
• Usage Insights - Personal analytics

💡 <b>How to use:</b>
1. Send your question/prompt for quick answers
2. Use /collaborate for team-based projects
3. Use /project for structured workflows
4. Use /insights to see your usage patterns

Send your question or choose a command to start!
"""
    await safe_send_message(message.chat.id, welcome_text, parse_mode="HTML")

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

@dp.message_handler(commands=["collaborate"])
async def cmd_collaborate(message: types.Message):
    """Start AI collaboration session"""
    kb = types.InlineKeyboardMarkup(row_width=1)
    teams = collaboration_manager.agent_workflows.keys()
    
    for team in teams:
        kb.add(types.InlineKeyboardButton(
            f"👥 {team.replace('_', ' ').title()}",
            callback_data=f"team|{team}"
        ))
    
    await safe_send_message(
        message.chat.id,
        "🤝 <b>AI Collaboration Teams</b>\n\n"
        "Choose a specialized team to collaborate with:\n\n"
        "• <b>Research Team</b>: Deep research, analysis, and synthesis\n"
        "• <b>Content Team</b>: Creative writing, ideation, and editing\n"
        "• <b>Tech Team</b>: Technical development, architecture, and review\n\n"
        "<i>Each team has specialized AI agents working together!</i>",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.message_handler(commands=["project"])
async def cmd_project(message: types.Message):
    """Start a project workflow"""
    kb = types.InlineKeyboardMarkup(row_width=1)
    templates = project_manager.get_available_templates()
    
    for template in templates:
        kb.add(types.InlineKeyboardButton(
            f"📁 {template.replace('_', ' ').title()}",
            callback_data=f"template|{template}"
        ))
    
    await safe_send_message(
        message.chat.id,
        "🚀 <b>Project Workflow</b>\n\n"
        "Start a structured project with guided steps:\n\n"
        "• <b>Business Plan</b>: Complete business documentation\n"
        "• <b>Research Paper</b>: Academic research workflow\n"
        "• <b>Software Project</b>: Development lifecycle\n"
        "• <b>Content Strategy</b>: Marketing content planning\n\n"
        "<i>Guided step-by-step process with AI assistance!</i>",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.message_handler(commands=["insights"])
async def cmd_insights(message: types.Message):
    """Get insights about your usage patterns"""
    insights = context_manager.get_user_insights(message.from_user.id)
    
    if not insights:
        return await safe_send_message(
            message.chat.id, 
            "📊 No insights yet. Keep using the bot to generate usage patterns!"
        )
    
    engagement_emoji = {
        "High": "🔥",
        "Medium": "⚡", 
        "Low": "🌱"
    }
    
    insight_text = [
        "🧠 <b>Your Personal AI Insights</b>",
        "",
        f"📊 <b>Total Interactions</b>: {insights['total_interactions']}",
        f"🔄 <b>Recent Activity</b>: {insights['recent_activity']} conversations",
        f"{engagement_emoji.get(insights['engagement_level'], '📈')} <b>Engagement Level</b>: {insights['engagement_level']}",
        "",
        "🎯 <b>Top Interests</b>:",
    ]
    
    if insights['top_interests']:
        for topic in insights['top_interests']:
            insight_text.append(f"• {topic.title()}")
    else:
        insight_text.append("• Still discovering your interests...")
    
    insight_text.extend([
        "",
        "<i>💡 Pro Tip: The more you collaborate, the better I understand your needs!</i>"
    ])
    
    await safe_send_message(
        message.chat.id,
        "\n".join(insight_text),
        parse_mode="HTML"
    )

@dp.message_handler(commands=["myprojects"])
async def cmd_my_projects(message: types.Message):
    """Show user's active projects"""
    projects = project_manager.get_user_projects(message.from_user.id)
    
    if not projects:
        return await safe_send_message(
            message.chat.id,
            "📂 You don't have any active projects yet.\n\n"
            "Use /project to start a new structured workflow!"
        )
    
    project_text = ["📂 <b>Your Active Projects</b>\n"]
    
    for project_id, project_data in projects.items():
        if project_data.get('status') == 'active':
            steps = project_data['steps']
            current_step = project_data['current_step']
            completed = len(project_data['completed_steps'])
            total = len(steps)
            
            progress = f"({completed}/{total} steps)"
            project_text.append(
                f"\n📁 <b>{project_data['name']}</b>\n"
                f"   📋 {project_data['template'].replace('_', ' ').title()}\n"
                f"   📊 Progress: {progress}\n"
                f"   🎯 Current: {steps[current_step] if current_step < total else 'Completed'}"
            )
    
    project_text.append("\n💡 <i>Use /project to create new projects</i>")
    
    await safe_send_message(
        message.chat.id,
        "\n".join(project_text),
        parse_mode="HTML"
    )

# Message handler
@dp.message_handler()
async def handle_message(message: types.Message):
    """Main handler for user prompts"""
    user_prompt = message.text.strip()
    if not user_prompt:
        return await safe_send_message(message.chat.id, "Please provide a prompt.")
    
    try:
        # Update context before processing
        context_manager.update_user_context(
            message.from_user.id, 
            user_prompt, 
            "processing..."
        )
        
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
        
        # Add collaboration option
        kb.add(types.InlineKeyboardButton(
            "🤝 AI Collaboration", 
            callback_data=f"collab_start|{original_key}"
        ))
        
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
                f"<i>{escape_md(imp['improved_prompt'][:80])}...</i>"
            )
        
        response.extend([
            "",
            "🤝 <b>AI Collaboration</b>: Work with specialized AI teams",
            "",
            "<i>Choose an option below:</i>"
        ])
        
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
        
        # Execute prompt with user context
        response = await CortensorAPI.query_with_rag(
            prompt_data["prompt"] if prompt_data["type"] == "original" 
            else prompt_data["prompt"].split("\n\n")[0],
            callback.from_user.id
        )
        
        # Update context with final response
        context_manager.update_user_context(
            callback.from_user.id,
            prompt_data["prompt"],
            response[:500] + "..." if len(response) > 500 else response
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

@dp.callback_query_handler(lambda c: c.data.startswith("team|"))
async def handle_team_selection(callback: types.CallbackQuery):
    """Handle AI team selection"""
    try:
        _, team = callback.data.split("|", 1)
        
        # Store team selection in cache
        session_key = f"team_{uuid.uuid4().hex[:8]}"
        prompt_cache[session_key] = {
            "type": "team_session",
            "team": team,
            "timestamp": time.time()
        }
        
        agents = collaboration_manager.agent_workflows.get(team, {})
        
        text = [
            f"🤝 <b>{team.replace('_', ' ').title()} Selected</b>",
            "",
            "<b>Available Agents:</b>"
        ]
        
        for agent, description in agents.items():
            text.append(f"• <b>{agent.title()}</b>: {description}")
        
        text.extend([
            "",
            "💡 <b>How to collaborate:</b>",
            "1. Choose an agent to start with",
            "2. Provide your question/task", 
            "3. Get specialized perspective",
            "4. Continue with other agents as needed",
            "",
            "<i>Select an agent to begin:</i>"
        ])
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        for agent in agents.keys():
            kb.add(types.InlineKeyboardButton(
                f"👤 {agent.title()}",
                callback_data=f"agent|{session_key}|{agent}"
            ))
        
        await callback.message.edit_text(
            "\n".join(text),
            parse_mode="HTML",
            reply_markup=kb
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Team selection error: {e}")
        await callback.answer("Error selecting team")

@dp.callback_query_handler(lambda c: c.data.startswith("agent|"))
async def handle_agent_selection(callback: types.CallbackQuery):
    """Handle AI agent selection and get input"""
    try:
        _, session_key, agent = callback.data.split("|", 2)
        
        session_data = prompt_cache.get(session_key)
        if not session_data:
            await callback.answer("Session expired")
            return
        
        # Store agent selection
        prompt_cache[session_key]["current_agent"] = agent
        
        await callback.message.edit_text(
            f"👤 <b>{agent.title()} Agent Ready</b>\n\n"
            f"Please provide your question or task for the {agent}:\n\n"
            f"<i>Example: 'Research the latest AI trends in healthcare'</i>",
            parse_mode="HTML"
        )
        
        # Set state to wait for user input for this agent
        prompt_cache[f"waiting_{callback.from_user.id}"] = {
            "session_key": session_key,
            "agent": agent,
            "timestamp": time.time()
        }
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Agent selection error: {e}")
        await callback.answer("Error selecting agent")

@dp.callback_query_handler(lambda c: c.data.startswith("template|"))
async def handle_template_selection(callback: types.CallbackQuery):
    """Handle project template selection"""
    try:
        _, template = callback.data.split("|", 1)
        
        # Store template selection and ask for project name
        template_key = f"template_{uuid.uuid4().hex[:8]}"
        prompt_cache[template_key] = {
            "type": "project_template",
            "template": template,
            "timestamp": time.time()
        }
        
        steps = project_manager.get_template_steps(template)
        
        text = [
            f"📁 <b>{template.replace('_', ' ').title()} Project</b>",
            "",
            "<b>Project Steps:</b>"
        ]
        
        for i, step in enumerate(steps, 1):
            text.append(f"{i}. {step}")
        
        text.extend([
            "",
            "Please provide a name for your project:",
            "<i>Example: 'My Startup Business Plan'</i>"
        ])
        
        await callback.message.edit_text(
            "\n".join(text),
            parse_mode="HTML"
        )
        
        # Set state to wait for project name
        prompt_cache[f"project_name_{callback.from_user.id}"] = {
            "template_key": template_key,
            "timestamp": time.time()
        }
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Template selection error: {e}")
        await callback.answer("Error selecting template")

@dp.callback_query_handler(lambda c: c.data.startswith("collab_start|"))
async def handle_collaboration_start(callback: types.CallbackQuery):
    """Start collaboration from existing prompt"""
    try:
        _, prompt_key = callback.data.split("|", 1)
        
        prompt_data = prompt_cache.get(prompt_key)
        if not prompt_data:
            await callback.answer("Prompt not found")
            return
        
        # Store the original prompt for collaboration
        collab_key = f"collab_{uuid.uuid4().hex[:8]}"
        prompt_cache[collab_key] = {
            "type": "collaboration_start",
            "original_prompt": prompt_data["prompt"],
            "timestamp": time.time()
        }
        
        # Show team selection
        kb = types.InlineKeyboardMarkup(row_width=1)
        teams = collaboration_manager.agent_workflows.keys()
        
        for team in teams:
            kb.add(types.InlineKeyboardButton(
                f"👥 {team.replace('_', ' ').title()}",
                callback_data=f"team|{team}"
            ))
        
        await callback.message.edit_text(
            f"🤝 <b>AI Collaboration</b>\n\n"
            f"Original prompt: <i>{prompt_data['prompt'][:100]}...</i>\n\n"
            f"Choose a specialized team to collaborate with:",
            parse_mode="HTML",
            reply_markup=kb
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Collaboration start error: {e}")
        await callback.answer("Error starting collaboration")

# Special message handlers for collaboration and projects
@dp.message_handler()
async def handle_special_requests(message: types.Message):
    """Handle special requests like collaboration inputs and project names"""
    user_id = message.from_user.id
    user_input = message.text.strip()
    
    # Check if user is providing input for an agent
    waiting_key = f"waiting_{user_id}"
    waiting_data = prompt_cache.get(waiting_key)
    
    if waiting_data:
        # User is providing input for an AI agent
        session_key = waiting_data["session_key"]
        agent = waiting_data["agent"]
        
        session_data = prompt_cache.get(session_key)
        if not session_data:
            await safe_send_message(message.chat.id, "Session expired. Please start over.")
            return
        
        # Get agent perspective
        processing_msg = await show_processing_message(
            message.chat.id,
            f"{agent} Agent"
        )
        
        response = await collaboration_manager.get_agent_perspective(
            session_key, agent, user_input
        )
        
        # Update context
        context_manager.update_user_context(user_id, user_input, response)
        
        # Clean up waiting state
        del prompt_cache[waiting_key]
        
        # Store the response in knowledge base as user contribution
        knowledge_base.add_user_contribution(
            user_id,
            f"Collaboration with {agent}",
            f"User input: {user_input}\n\nAgent response: {response}"
        )
        
        # Send response with option to continue
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            "🔄 Continue with Another Agent",
            callback_data=f"team|{session_data['team']}"
        ))
        
        for chunk in chunks(response):
            await safe_send_message(
                message.chat.id,
                f"👤 <b>{agent.title()} Perspective:</b>\n\n{chunk}",
                parse_mode="HTML"
            )
        
        await safe_send_message(
            message.chat.id,
            "💡 <i>Would you like to continue with another agent?</i>",
            parse_mode="HTML",
            reply_markup=kb
        )
        return
    
    # Check if user is providing project name
    project_name_key = f"project_name_{user_id}"
    project_name_data = prompt_cache.get(project_name_key)
    
    if project_name_data:
        # User is providing project name
        template_key = project_name_data["template_key"]
        template_data = prompt_cache.get(template_key)
        
        if not template_data:
            await safe_send_message(message.chat.id, "Session expired. Please start over.")
            return
        
        # Create project
        project_id = project_manager.create_project(
            user_id, user_input, template_data["template"]
        )
        
        project_data = project_manager.user_projects[user_id][project_id]
        
        # Clean up
        del prompt_cache[project_name_key]
        del prompt_cache[template_key]
        
        # Show project created message
        steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(project_data["steps"])])
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            "🚀 Start First Step",
            callback_data=f"project_step|{project_id}|0"
        ))
        
        await safe_send_message(
            message.chat.id,
            f"🎉 <b>Project Created!</b>\n\n"
            f"📁 <b>{user_input}</b>\n"
            f"📋 Template: {template_data['template'].replace('_', ' ').title()}\n\n"
            f"<b>Project Steps:</b>\n{steps_text}\n\n"
            f"<i>Ready to start the first step?</i>",
            parse_mode="HTML",
            reply_markup=kb
        )
        return
    
    # If no special handling, process as normal message
    await handle_message(message)

@dp.callback_query_handler(lambda c: c.data.startswith("project_step|"))
async def handle_project_step(callback: types.CallbackQuery):
    """Handle project step execution"""
    try:
        _, project_id, step_index = callback.data.split("|", 2)
        step_index = int(step_index)
        
        user_projects = project_manager.get_user_projects(callback.from_user.id)
        project_data = user_projects.get(project_id)
        
        if not project_data:
            await callback.answer("Project not found")
            return
        
        steps = project_data["steps"]
        if step_index >= len(steps):
            await callback.answer("Project completed!")
            return
        
        current_step = steps[step_index]
        
        # Ask user for input for this step
        step_key = f"project_step_{uuid.uuid4().hex[:8]}"
        prompt_cache[step_key] = {
            "type": "project_step",
            "project_id": project_id,
            "step_index": step_index,
            "step_name": current_step,
            "timestamp": time.time()
        }
        
        step_guides = {
            "Executive Summary": "Provide the main overview of your business/project",
            "Company Description": "Describe your company, mission, and vision", 
            "Market Analysis": "Provide information about your target market and competition",
            "Organization Structure": "Describe your team and organizational structure",
            "Abstract": "Provide the main summary of your research",
            "Introduction": "Introduce your research topic and objectives",
            "Requirements Analysis": "Describe the functional and non-functional requirements",
            "System Design": "Provide details about the system architecture",
            # Add more step guides as needed
        }
        
        guide = step_guides.get(current_step, f"Provide information for: {current_step}")
        
        await callback.message.edit_text(
            f"📋 <b>Project Step: {current_step}</b>\n\n"
            f"Project: <i>{project_data['name']}</i>\n\n"
            f"💡 <b>What to provide:</b>\n{guide}\n\n"
            f"<i>Please provide your input for this step:</i>",
            parse_mode="HTML"
        )
        
        # Set state to wait for step input
        prompt_cache[f"step_input_{callback.from_user.id}"] = {
            "step_key": step_key,
            "timestamp": time.time()
        }
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Project step error: {e}")
        await callback.answer("Error processing project step")

# Error handler
@dp.errors_handler()
async def errors_handler(update: types.Update, exception: Exception):
    logger.error(f"Update {update} caused error: {exception}", exc_info=True)
    return True

# Main execution
if __name__ == "__main__":
    logger.info("Starting Advanced AI Collaboration Bot...")
    try:
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        logger.info("Bot stopped")
