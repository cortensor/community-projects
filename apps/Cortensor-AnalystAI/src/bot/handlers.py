import logging
import uuid
from telegram import Update
from telegram.ext import CallbackContext
from src.utils.database import (
    add_task_to_queue,
    get_all_user_tasks,
    delete_task_by_id,
    get_task_by_id,
    get_all_schedules,
    delete_schedule,
    add_portfolio_asset,
    get_user_portfolio,
    remove_portfolio_asset,
    clear_user_portfolio,
    get_user_settings,
    update_user_setting,
    reset_user_settings,
    add_dca_schedule,
    get_user_dca_schedules,
    get_active_dca_schedules,
    update_dca_execution,
    toggle_dca_schedule,
    delete_dca_schedule,
    get_dca_schedule_by_id
)
from src.utils.caching import delete_cached_result, clear_all_cache
from src.core.scheduler_manager import SchedulerManager
from src.services.market_data_api import get_market_data
from src.bot.formatter import escape_html

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: CallbackContext):
    """Handles the /start command and lists all available commands."""
    start_message = (
        "🤖 <b>Welcome to The Analyst Bot</b> 🤖\n"
        "<i>Your AI-powered financial analysis companion by Cortensor Network</i>\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "📊 <b>Market Analysis</b>\n"
        "• <code>/analyze &lt;asset&gt;</code> - Get comprehensive market analysis\n"
        "• <code>/refresh &lt;asset&gt;</code> - Force refresh analysis with latest data\n\n"
        
        "⚙️ <b>Task Management</b>\n"
        "• <code>/list_jobs</code> - View your analysis requests\n"
        "• <code>/status &lt;request_id&gt;</code> - Check request status\n"
        "• <code>/delete_job &lt;request_id&gt;</code> - Cancel pending request\n\n"
        
        "📅 <b>Automated Scheduling</b>\n"
        "• <code>/schedule &lt;asset&gt; &lt;HH:MM&gt;</code> - Set daily analysis\n"
        "• <code>/list_schedules</code> - Manage your schedules\n"
        "• <code>/delete_schedule &lt;job_id&gt;</code> - Remove schedule\n\n"
        
        "💼 <b>Portfolio Tracking</b>\n"
        "• <code>/add_asset &lt;symbol&gt; &lt;quantity&gt;</code> - Add to portfolio\n"
        "• <code>/remove_asset &lt;symbol&gt;</code> - Remove from portfolio\n"
        "• <code>/view_portfolio</code> - View portfolio analysis\n"
        "• <code>/clear_portfolio</code> - Clear all holdings\n\n"
        
        "💸 <b>DCA (Dollar Cost Averaging)</b>\n"
        "• <code>/dca add &lt;symbol&gt; &lt;amount&gt; &lt;currency&gt; &lt;frequency&gt; &lt;time&gt;</code> - Create DCA schedule\n"
        "• <code>/dca list</code> - View DCA schedules\n"
        "• <code>/dca stats &lt;dca_id&gt;</code> - View DCA performance\n"
        "• <code>/dca summary</code> - Overall DCA summary\n\n"
        
        "🛠️ <b>System & Settings</b>\n"
        "• <code>/help</code> - Show detailed help & documentation\n"
        "• <code>/settings</code> - Configure bot preferences\n"
        "• <code>/clearcache</code> - Clear analysis cache\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <b>Quick Start:</b> Try <code>/analyze Bitcoin</code> or <code>/help</code>\n"
        "📈 <i>Real-time data • Expert insights • News integration</i>\n"
        "🔗 <i>Powered by Cortensor Network</i>"
    )
    await update.message.reply_text(start_message, parse_mode='HTML')

async def help_command(update: Update, context: CallbackContext):
    """Handles the /help command with detailed documentation."""
    help_message = (
        "📖 <b>The Analyst Bot - Complete Guide</b>\n"
        "<i>Your AI-powered financial analysis companion by Cortensor Network</i>\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🚀 <b>Getting Started</b>\n"
        "• Use <code>/analyze Bitcoin</code> to get your first analysis\n"
        "• Configure preferences with <code>/settings</code>\n"
        "• Add assets to portfolio with <code>/add_asset BTC 0.5</code>\n"
        "• Schedule daily reports with <code>/schedule NVDA 09:00</code>\n\n"
        
        "📊 <b>Market Analysis Commands</b>\n"
        "• <code>/analyze &lt;asset&gt;</code>\n"
        "  Get comprehensive analysis with technical indicators, news, and price predictions\n"
        "  Examples: Bitcoin, NVDA, Ethereum, TSLA, Gold\n\n"
        
        "• <code>/refresh &lt;asset&gt;</code>\n"
        "  Force refresh cached data and get latest analysis\n"
        "  Useful when markets are volatile\n\n"
        
        "⚙️ <b>Task Management</b>\n"
        "• <code>/list_jobs</code> - View all your analysis requests with status\n"
        "• <code>/status &lt;request_id&gt;</code> - Check specific request progress\n"
        "• <code>/delete_job &lt;request_id&gt;</code> - Cancel pending analysis\n\n"
        
        "� <b>Automated Scheduling</b>\n"
        "• <code>/schedule &lt;asset&gt; &lt;HH:MM&gt;</code>\n"
        "  Set daily recurring analysis (24-hour format, WIB timezone)\n"
        "  Example: <code>/schedule Bitcoin 07:00</code>\n\n"
        
        "• <code>/list_schedules</code> - View and manage all your schedules\n"
        "• <code>/delete_schedule &lt;job_id&gt;</code> - Remove specific schedule\n\n"
        
        "💼 <b>Portfolio Management</b>\n"
        "• <code>/add_asset &lt;symbol&gt; &lt;quantity&gt;</code>\n"
        "  Add assets to track portfolio performance\n"
        "  Example: <code>/add_asset BTC 0.5</code>\n\n"
        
        "• <code>/view_portfolio</code> - View current portfolio with live prices\n"
        "• <code>/remove_asset &lt;symbol&gt;</code> - Remove specific asset\n"
        "• <code>/clear_portfolio</code> - Remove all portfolio assets\n\n"
        
        "💸 <b>DCA - Dollar Cost Averaging</b>\n"
        "• <code>/dca add &lt;symbol&gt; &lt;amount&gt; &lt;currency&gt; &lt;frequency&gt; &lt;time&gt;</code>\n"
        "  Automate regular investments\n"
        "  Example: <code>/dca add BTC 50 USD daily 15:00</code>\n\n"
        
        "• <code>/dca list</code> - View all DCA schedules\n"
        "• <code>/dca stats &lt;dca_id&gt;</code> - View DCA performance\n"
        "• <code>/dca summary</code> - Overall DCA portfolio summary\n"
        "• <code>/dca pause/resume/delete &lt;dca_id&gt;</code> - Manage schedules\n\n"
        
        "🛠️ <b>System & Configuration</b>\n"
        "• <code>/settings</code> - Configure timezone, currency, alerts, etc.\n"
        "• <code>/clearcache</code> - Clear all cached analysis data\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <b>Pro Tips:</b>\n"
        "• Analysis includes technical indicators, sentiment, and news\n"
        "• Scheduled analyses run automatically daily\n"
        "• Portfolio tracks real-time values and changes\n"
        "• DCA automates regular investments to reduce timing risk\n"
        "• All times are in your configured timezone (default: WIB GMT+7)\n"
        "• Use <code>/settings</code> to customize currency, timezone, etc.\n\n"
        
        "🔗 <b>Powered by Cortensor Network</b>\n"
        "Advanced AI models for accurate financial analysis and predictions\n\n"
        
        "📞 <b>Support:</b> Questions? Use <code>/start</code> for quick commands"
    )
    await update.message.reply_text(help_message, parse_mode='HTML')

async def analyze_command(update: Update, context: CallbackContext):
    """Handles the /analyze command and queues the task."""
    if not context.args:
        await update.message.reply_text(
            "📊 <b>Market Analysis Service</b>\n\n"
            "🎯 <b>Usage:</b> <code>/analyze &lt;asset/topic&gt;</code>\n\n"
            "📈 <b>Examples:</b>\n"
            "• <code>/analyze Bitcoin</code>\n"
            "• <code>/analyze NVDA</code>\n"
            "• <code>/analyze Ethereum</code>\n"
            "• <code>/analyze TSLA</code>\n\n"
            "💡 <b>Supported Assets:</b>\n"
            "• Cryptocurrencies (Bitcoin, Ethereum, etc.)\n"
            "• Stocks (AAPL, MSFT, NVDA, etc.)\n"
            "• Market topics and sectors\n\n"
            "⚡ <b>Features:</b> Real-time data, expert analysis, news integration",
            parse_mode='HTML'
        )
        return

    topic = " ".join(context.args)
    user_id = update.effective_user.id
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    try:
        # Send acknowledgment message first
        ack_message = await update.message.reply_text(
            f"📊 <b>Analysis Request Received</b>\n\n"
            f"🎯 <b>Asset/Topic:</b> <code>{escape_html(topic)}</code>\n"
            f"🆔 <b>Request ID:</b> <code>{request_id}</code>\n"
            f"👤 <b>Status:</b> <i>Processing in queue</i>\n\n"
            f"⏳ <b>Expected Completion:</b> 1-2 minutes\n"
            f"📱 <b>Delivery:</b> Your comprehensive analysis report will be delivered as a new message\n\n"
            f"💡 <i>You can continue using the bot while we prepare your analysis</i>",
            parse_mode='HTML'
        )
        
        # Add task to queue with acknowledgment message ID
        add_task_to_queue(request_id, user_id, topic, ack_message.message_id)
        logger.info(f"Task {request_id} for topic '{topic}' queued for user {user_id}.")
        
    except Exception as e:
        logger.error(f"Failed to queue task for topic '{topic}': {e}", exc_info=True)
        await update.message.reply_text(
            "❌ <b>Request Processing Error</b>\n\n"
            "🔧 <b>Issue:</b> Unable to process your analysis request\n"
            "📋 <b>Possible Causes:</b>\n"
            "• High server load\n"
            "• Temporary system maintenance\n"
            "• Network connectivity issue\n\n"
            "🔄 <b>Solution:</b> Please try again in a few moments\n"
            "💬 <b>Support:</b> If the issue persists, contact support",
            parse_mode='HTML'
        )

async def refresh_command(update: Update, context: CallbackContext):
    """Deletes the cache for a specific topic and re-runs the analysis."""
    if not context.args:
        await update.message.reply_text("Usage: <code>/refresh &lt;topic&gt;</code>\nExample: <code>/refresh Bitcoin</code>", parse_mode='HTML') # Changed to HTML
        return

    topic = " ".join(context.args)
    logger.info(f"Received refresh request for topic: {topic}")

    was_deleted = delete_cached_result(topic)
    if was_deleted:
        await update.message.reply_text(f"Cache for '{topic}' has been cleared. Re-running analysis...", parse_mode='HTML') # Changed to HTML
    else:
        await update.message.reply_text(f"No cache found for '{topic}'. Running new analysis...", parse_mode='HTML') # Changed to HTML

    await analyze_command(update, context)

async def list_jobs_command(update: Update, context: CallbackContext):
    """Lists all one-time analysis jobs for the user."""
    user_id = update.effective_user.id
    tasks = get_all_user_tasks(user_id)

    if not tasks:
        await update.message.reply_text(
            "📋 <b>Your Analysis Requests</b>\n\n"
            "🔍 <b>Status:</b> No active or completed analysis requests found\n\n"
            "💡 <b>Get Started:</b>\n"
            "• Use <code>/analyze Bitcoin</code> to request your first analysis\n"
            "• Use <code>/analyze NVDA</code> for stock analysis\n"
            "• Use <code>/schedule Bitcoin 07:00</code> for daily reports\n\n"
            "📊 <i>All your analysis requests will appear here with detailed status tracking</i>",
            parse_mode='HTML'
        )
        return

    message = "� <b>Your Analysis Requests</b>\n\n"
    message += f"📊 <b>Total Requests:</b> {len(tasks)}\n"
    message += f"📅 <b>Request History & Status</b>\n\n"
    
    # Group tasks by status for better organization
    status_groups = {"PENDING": [], "PROCESSING": [], "COMPLETED": [], "FAILED": []}
    for task in tasks:
        status = task.get('status', 'UNKNOWN')
        if status in status_groups:
            status_groups[status].append(task)
        else:
            status_groups["FAILED"].append(task)
    
    # Display tasks by status priority
    for status in ["PROCESSING", "PENDING", "COMPLETED", "FAILED"]:
        if not status_groups[status]:
            continue
            
        status_info = {
            "PENDING": {"emoji": "⏳", "title": "Queued for Analysis"},
            "PROCESSING": {"emoji": "⚙️", "title": "Currently Processing"},
            "COMPLETED": {"emoji": "✅", "title": "Analysis Complete"},
            "FAILED": {"emoji": "❌", "title": "Analysis Failed"}
        }
        
        info = status_info[status]
        message += f"{info['emoji']} <b>{info['title']} ({len(status_groups[status])})</b>\n"
        
        for task in status_groups[status][:5]:  # Limit to 5 per status
            topic = escape_html(task.get('topic', 'Unknown'))
            request_id = task.get('request_id', 'Unknown')
            
            message += f"  • <b>{topic}</b>\n"
            message += f"    🆔 <code>{request_id}</code>\n"
            
            if status == "COMPLETED":
                message += f"    ✅ <i>Analysis delivered successfully</i>\n"
            elif status == "PROCESSING":
                message += f"    ⚙️ <i>Gathering data and analyzing...</i>\n"
            elif status == "PENDING":
                message += f"    ⏳ <i>Waiting in queue for processing</i>\n"
            elif status == "FAILED":
                message += f"    ❌ <i>Analysis failed - try again</i>\n"
            
            message += "\n"
        
        if len(status_groups[status]) > 5:
            message += f"    <i>... and {len(status_groups[status]) - 5} more</i>\n"
        message += "\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "<b>📋 Management Commands:</b>\n"
    message += "• <code>/status &lt;request_id&gt;</code> - Check specific request\n"
    message += "• <code>/delete_job &lt;request_id&gt;</code> - Cancel pending request\n"
    message += "• <code>/analyze &lt;asset&gt;</code> - Request new analysis\n\n"
    message += "💡 <i>Completed analyses are automatically delivered as messages</i>"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def status_command(update: Update, context: CallbackContext):
    """Checks the status of a specific one-time job."""
    if not context.args:
        await update.message.reply_text(
            "🔍 <b>Request Status Check</b>\n\n"
            "📋 <b>Usage:</b> <code>/status &lt;request_id&gt;</code>\n\n"
            "💡 <b>How to get Request ID:</b>\n"
            "• Use <code>/list_jobs</code> to see all your requests\n"
            "• Copy the ID from your analysis request\n"
            "• Request IDs look like: <code>req_abc123def456</code>\n\n"
            "📊 <b>Example:</b> <code>/status req_abc123def456</code>\n\n"
            "🔄 <i>Real-time status tracking for all your analysis requests</i>",
            parse_mode='HTML'
        )
        return

    request_id = context.args[0]
    user_id = update.effective_user.id
    task = get_task_by_id(request_id, user_id)

    if not task:
        await update.message.reply_text(
            f"❌ <b>Request Not Found</b>\n\n"
            f"🔍 <b>Request ID:</b> <code>{escape_html(request_id)}</code>\n\n"
            f"📋 <b>Possible Reasons:</b>\n"
            f"• Request ID doesn't exist\n"
            f"• Request belongs to another user\n"
            f"• Request was deleted\n"
            f"• Typo in Request ID\n\n"
            f"💡 <b>Solution:</b> Use <code>/list_jobs</code> to see valid Request IDs",
            parse_mode='HTML'
        )
        return

    status = task.get('status', 'UNKNOWN')
    topic = escape_html(task.get('topic', 'N/A'))

    status_info = {
        "PENDING": {
            "emoji": "⏳",
            "title": "Queued for Processing",
            "description": "Your analysis request is waiting in queue",
            "action": "Please wait - processing will begin shortly"
        },
        "PROCESSING": {
            "emoji": "⚙️",
            "title": "Currently Processing",
            "description": "AI models are analyzing market data and generating insights",
            "action": "Analysis in progress - results coming soon"
        },
        "COMPLETED": {
            "emoji": "✅",
            "title": "Analysis Complete",
            "description": "Your comprehensive analysis has been delivered",
            "action": "Check your messages for the complete report"
        },
        "FAILED": {
            "emoji": "❌",
            "title": "Analysis Failed",
            "description": "Unable to complete analysis due to technical issues",
            "action": "Please try submitting the request again"
        }
    }

    info = status_info.get(status, {
        "emoji": "❓",
        "title": "Unknown Status",
        "description": "Status information unavailable",
        "action": "Contact support if this persists"
    })

    message = (
        f"� <b>Analysis Request Status</b>\n\n"
        f"🆔 <b>Request ID:</b> <code>{escape_html(request_id)}</code>\n"
        f"📊 <b>Asset/Topic:</b> <code>{topic}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>Status:</b> {info['title']}\n"
        f"📋 <b>Description:</b> {info['description']}\n"
        f"🎯 <b>Next Action:</b> {info['action']}\n\n"
    )
    
    if status == "PROCESSING":
        message += "⏱️ <b>Estimated Time:</b> 1-2 minutes remaining\n\n"
    elif status == "PENDING":
        message += "📈 <b>Queue Position:</b> Processing in order received\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "<b>📋 Available Commands:</b>\n"
    message += "• <code>/list_jobs</code> - View all your requests\n"
    message += "• <code>/delete_job &lt;request_id&gt;</code> - Cancel this request\n"
    message += "• <code>/analyze &lt;asset&gt;</code> - Submit new analysis request\n\n"
    message += "🔄 <i>Status updates automatically - no need to check repeatedly</i>"

    await update.message.reply_text(message, parse_mode='HTML')

async def delete_job_command(update: Update, context: CallbackContext):
    """Deletes a one-time analysis job by its ID."""
    if not context.args:
        await update.message.reply_text("Usage: <code>/delete_job &lt;request_id&gt;</code>", parse_mode='HTML') # Changed to HTML
        return

    request_id_to_delete = context.args[0]
    user_id = update.effective_user.id
    deleted_count = delete_task_by_id(request_id_to_delete, user_id)

    if deleted_count > 0:
        logger.info(f"User {user_id} successfully deleted job {request_id_to_delete}.")
        await update.message.reply_text(f"✅ Successfully deleted request with ID: <code>{request_id_to_delete}</code>", parse_mode='HTML') # Changed to HTML
    else:
        logger.warning(f"User {user_id} failed to delete job {request_id_to_delete} (not found or not owner).")
        await update.message.reply_text(f"❌ Could not find a request with that ID belonging to you.", parse_mode='HTML') # Changed to HTML

async def schedule_command(update: Update, context: CallbackContext):
    """Handles /schedule <topic> <HH:MM>"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "📅 <b>Schedule Analysis</b>\n\n"
            "Create a daily recurring analysis for any asset or topic.\n\n"
            "<b>Usage:</b> <code>/schedule &lt;Topic&gt; &lt;HH:MM&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/schedule Bitcoin 07:00</code>\n"
            "• <code>/schedule NVDA 09:30</code>\n"
            "• <code>/schedule Gold 14:00</code>\n\n"
            "<b>Time Format:</b> 24-hour format (HH:MM) in WIB timezone\n"
            "<b>Note:</b> Analysis will run automatically every day at the specified time",
            parse_mode='HTML'
        )
        return

    try:
        time_str = context.args[-1]
        topic = " ".join(context.args[:-1])
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("Invalid time format.")
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ <b>Invalid Time Format</b>\n\n"
            "Please use 24-hour format: <code>/schedule &lt;Topic&gt; &lt;HH:MM&gt;</code>\n\n"
            "<b>Valid examples:</b>\n"
            "• <code>/schedule Bitcoin 07:00</code> (7:00 AM)\n"
            "• <code>/schedule TSLA 14:30</code> (2:30 PM)\n"
            "• <code>/schedule Ethereum 23:59</code> (11:59 PM)",
            parse_mode='HTML'
        )
        return

    user_id = update.effective_user.id
    scheduler = SchedulerManager()
    job_id = scheduler.schedule_daily_analysis(user_id, topic, hour, minute)

    if job_id:
        await update.message.reply_text(
            f"✅ <b>Schedule Created Successfully!</b>\n\n"
            f"📊 <b>Asset/Topic:</b> {topic}\n"
            f"⏰ <b>Daily Time:</b> {hour:02d}:{minute:02d} WIB (GMT+7)\n"
            f"🆔 <b>Job ID:</b> <code>{job_id}</code>\n\n"
            f"🤖 I will automatically analyze <b>'{topic}'</b> every day at <b>{hour:02d}:{minute:02d} WIB</b> and send you the report.\n\n"
            f"<b>Management Commands:</b>\n"
            f"• <code>/list_schedules</code> - View all your schedules\n"
            f"• <code>/delete_schedule {job_id}</code> - Cancel this schedule",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Failed to Create Schedule</b>\n\n"
            "There might be:\n"
            "• An existing similar schedule for this topic and time\n"
            "• An internal system issue\n\n"
            "Please try again or use <code>/list_schedules</code> to check existing schedules.",
            parse_mode='HTML'
        )

async def list_schedules_command(update: Update, context: CallbackContext):
    """Lists all active schedules for the user."""
    user_id = update.effective_user.id
    schedules = get_all_schedules(user_id)
    if not schedules:
        await update.message.reply_text(
            "📅 <b>Your Scheduled Analyses</b>\n\n"
            "You have no active analysis schedules.\n\n"
            "💡 <b>Create a schedule:</b>\n"
            "<code>/schedule Bitcoin 07:00</code>\n"
            "<code>/schedule NVDA 09:30</code>\n\n"
            "ℹ️ Scheduled analyses run automatically daily at your specified time.",
            parse_mode='HTML'
        )
        return

    message = "� <b>Your Scheduled Analyses</b>\n\n"
    message += f"📊 Total active schedules: <b>{len(schedules)}</b>\n"
    message += "⏰ All times are in WIB (GMT+7)\n\n"
    
    for i, s in enumerate(schedules, 1):
        message += f"<b>{i}.</b> 📈 <b>{s['topic']}</b>\n"
        message += f"   ⏰ Daily at <b>{s['hour']:02d}:{s['minute']:02d}</b>\n"
        message += f"   🆔 <code>{s['job_id']}</code>\n"
        message += f"   🗑️ Delete: <code>/delete_schedule {s['job_id']}</code>\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━\n"
    message += "<b>Management Commands:</b>\n"
    message += "• <code>/schedule &lt;topic&gt; &lt;HH:MM&gt;</code> - Add new schedule\n"
    message += "• <code>/delete_schedule &lt;job_id&gt;</code> - Remove schedule"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def delete_schedule_command(update: Update, context: CallbackContext):
    """Deletes a scheduled job by its ID."""
    if not context.args:
        await update.message.reply_text(
            "🗑️ <b>Delete Schedule</b>\n\n"
            "Remove a scheduled analysis by providing its Job ID.\n\n"
            "<b>Usage:</b> <code>/delete_schedule &lt;job_id&gt;</code>\n\n"
            "<b>Example:</b> <code>/delete_schedule job_12345abc</code>\n\n"
            "💡 Use <code>/list_schedules</code> to see all your scheduled analyses and their Job IDs.",
            parse_mode='HTML'
        )
        return

    job_id = context.args[0]
    user_id = update.effective_user.id
    scheduler = SchedulerManager()

    if scheduler.delete_scheduled_job(job_id, user_id):
        await update.message.reply_text(
            f"✅ <b>Schedule Deleted Successfully!</b>\n\n"
            f"🗑️ Removed schedule with ID: <code>{job_id}</code>\n\n"
            f"💡 Use <code>/list_schedules</code> to view remaining schedules\n"
            f"📅 Use <code>/schedule &lt;topic&gt; &lt;HH:MM&gt;</code> to create new schedules",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Schedule Not Found</b>\n\n"
            "Could not find a schedule with that Job ID, or you don't have permission to delete it.\n\n"
            "💡 <b>Possible reasons:</b>\n"
            "• Job ID doesn't exist\n"
            "• Job ID belongs to another user\n"
            "• Job was already deleted\n\n"
            "Use <code>/list_schedules</code> to see your active schedules.",
            parse_mode='HTML'
        )

async def clearcache_command(update: Update, context: CallbackContext):
    """Deletes the entire cache."""
    logger.info("Received request to clear the entire cache.")
    deleted_count = clear_all_cache()
    await update.message.reply_text(f"✅ Successfully cleared the cache. All {deleted_count} cached items were removed.", parse_mode='HTML') # Changed to HTML
    
async def settings_command(update: Update, context: CallbackContext):
    """Handles the /settings command with comprehensive configuration options."""
    user_id = update.effective_user.id
    user_settings = get_user_settings(user_id)
    
    if not context.args:
        # Show main settings menu with current values
        settings_message = (
            "⚙️ <b>Bot Settings & Configuration</b>\n\n"
            
            "🔧 <b>Available Settings:</b>\n\n"
            
            "📊 <b>Analysis Preferences</b>\n"
            f"• <code>/settings timezone &lt;timezone&gt;</code>\n"
            f"  Current: <b>{user_settings.get('timezone', 'Asia/Jakarta')}</b>\n"
            f"  Examples: US/Eastern, Europe/London, Asia/Tokyo\n\n"
            
            f"• <code>/settings language &lt;lang&gt;</code>\n"
            f"  Current: <b>{user_settings.get('language', 'en').upper()}</b>\n"
            f"  Available: en, id (coming soon)\n\n"
            
            "🔔 <b>Notification Settings</b>\n"
            f"• <code>/settings notifications &lt;on/off&gt;</code>\n"
            f"  Current: <b>{'ON' if user_settings.get('notifications', True) else 'OFF'}</b>\n"
            f"  Controls: Scheduled analysis notifications\n\n"
            
            f"• <code>/settings alerts &lt;threshold&gt;</code>\n"
            f"  Current: <b>{user_settings.get('alerts_threshold', 5)}%</b>\n"
            f"  Portfolio alerts for price changes > threshold\n\n"
            
            "📈 <b>Display Preferences</b>\n"
            f"• <code>/settings currency &lt;currency&gt;</code>\n"
            f"  Current: <b>{user_settings.get('currency', 'USD')}</b>\n"
            f"  Available: USD, EUR, JPY, IDR, GBP, SGD\n\n"
            
            f"• <code>/settings charts &lt;on/off&gt;</code>\n"
            f"  Current: <b>{'ON' if user_settings.get('charts_enabled', True) else 'OFF'}</b>\n"
            f"  Include price charts in analysis\n\n"
            
            "🗃️ <b>Data Management</b>\n"
            f"• <code>/settings cache_duration &lt;minutes&gt;</code>\n"
            f"  Current: <b>{user_settings.get('cache_duration', 60)} minutes</b>\n"
            f"  How long to cache analysis results\n\n"
            
            f"• <code>/settings export_format &lt;format&gt;</code>\n"
            f"  Current: <b>{user_settings.get('export_format', 'HTML')}</b>\n"
            f"  Available: HTML, PDF (coming soon)\n\n"
            
            "🔐 <b>Privacy & Security</b>\n"
            f"• <code>/settings data_retention &lt;days&gt;</code>\n"
            f"  Current: <b>{user_settings.get('data_retention_days', 30)} days</b>\n"
            f"  How long to keep your analysis history\n\n"
            
            f"• <code>/settings privacy_mode &lt;on/off&gt;</code>\n"
            f"  Current: <b>{'ON' if user_settings.get('privacy_mode', False) else 'OFF'}</b>\n"
            f"  Hide sensitive portfolio values\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>Quick Actions:</b>\n"
            "• <code>/settings reset</code> - Reset all to defaults\n"
            "• <code>/settings export</code> - Export your settings\n"
            "• <code>/settings import &lt;data&gt;</code> - Import settings\n\n"
            
            "💡 <b>Examples:</b>\n"
            "• <code>/settings timezone US/Eastern</code>\n"
            "• <code>/settings alerts 10</code>\n"
            "• <code>/settings notifications off</code>"
        )
        await update.message.reply_text(settings_message, parse_mode='HTML')
        return
    
    # Handle specific setting changes
    setting_type = context.args[0].lower()
    
    if setting_type == "timezone":
        if len(context.args) < 2:
            await update.message.reply_text(
                "⏰ <b>Timezone Setting</b>\n\n"
                "<b>Usage:</b> <code>/settings timezone &lt;timezone&gt;</code>\n\n"
                "<b>Popular Timezones:</b>\n"
                "• <code>Asia/Jakarta</code> (WIB, GMT+7)\n"
                "• <code>US/Eastern</code> (EST/EDT)\n"
                "• <code>US/Pacific</code> (PST/PDT)\n"
                "• <code>Europe/London</code> (GMT/BST)\n"
                "• <code>Asia/Tokyo</code> (JST, GMT+9)\n"
                "• <code>Asia/Singapore</code> (SGT, GMT+8)\n\n"
                f"<b>Current:</b> {user_settings.get('timezone', 'Asia/Jakarta')}",
                parse_mode='HTML'
            )
        else:
            timezone = " ".join(context.args[1:])
            if update_user_setting(user_id, 'timezone', timezone):
                await update.message.reply_text(
                    f"⏰ <b>Timezone Updated</b>\n\n"
                    f"🌍 <b>New Timezone:</b> {timezone}\n"
                    f"📅 <b>Note:</b> This will affect all future scheduled analyses and reports.\n\n"
                    f"✅ Setting saved successfully!",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ <b>Error</b>\n\nFailed to update timezone setting.",
                    parse_mode='HTML'
                )
    
    elif setting_type == "notifications":
        if len(context.args) < 2:
            await update.message.reply_text(
                "🔔 <b>Notification Settings</b>\n\n"
                "<b>Usage:</b> <code>/settings notifications &lt;on/off&gt;</code>\n\n"
                f"<b>Current Status:</b> {'ON' if user_settings.get('notifications', True) else 'OFF'}\n"
                "• Scheduled analysis notifications\n"
                "• Portfolio alerts\n"
                "• System updates",
                parse_mode='HTML'
            )
        else:
            status = context.args[1].lower()
            if status in ['on', 'off', 'enable', 'disable']:
                is_enabled = status in ['on', 'enable']
                if update_user_setting(user_id, 'notifications', is_enabled):
                    status_text = "ON" if is_enabled else "OFF"
                    emoji = "🔔" if is_enabled else "🔕"
                    await update.message.reply_text(
                        f"{emoji} <b>Notifications {status_text}</b>\n\n"
                        f"📱 <b>Status:</b> Notifications are now <b>{status_text}</b>\n"
                        f"🎯 <b>Applies to:</b> Scheduled analyses, portfolio alerts, system updates\n\n"
                        f"✅ Setting saved successfully!",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        "❌ <b>Error</b>\n\nFailed to update notification setting.",
                        parse_mode='HTML'
                    )
    
    elif setting_type == "alerts":
        if len(context.args) < 2:
            await update.message.reply_text(
                "📊 <b>Portfolio Alert Threshold</b>\n\n"
                "<b>Usage:</b> <code>/settings alerts &lt;percentage&gt;</code>\n\n"
                f"<b>Current Threshold:</b> {user_settings.get('alerts_threshold', 5)}%\n"
                f"• Get notified when portfolio assets change > {user_settings.get('alerts_threshold', 5)}%\n\n"
                "<b>Examples:</b>\n"
                "• <code>/settings alerts 3</code> (3% threshold)\n"
                "• <code>/settings alerts 10</code> (10% threshold)",
                parse_mode='HTML'
            )
        else:
            try:
                threshold = float(context.args[1])
                if 0 < threshold <= 100:
                    if update_user_setting(user_id, 'alerts_threshold', threshold):
                        await update.message.reply_text(
                            f"📊 <b>Alert Threshold Updated</b>\n\n"
                            f"⚡ <b>New Threshold:</b> {threshold}%\n"
                            f"🎯 <b>Trigger:</b> When portfolio assets change > {threshold}%\n\n"
                            f"✅ Setting saved successfully!",
                            parse_mode='HTML'
                        )
                    else:
                        await update.message.reply_text(
                            "❌ <b>Error</b>\n\nFailed to update alerts threshold.",
                            parse_mode='HTML'
                        )
                else:
                    await update.message.reply_text(
                        "❌ <b>Invalid Threshold</b>\n\n"
                        "Please enter a percentage between 0.1 and 100.\n"
                        "Example: <code>/settings alerts 5</code>",
                        parse_mode='HTML'
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ <b>Invalid Number</b>\n\n"
                    "Please enter a valid percentage.\n"
                    "Example: <code>/settings alerts 5</code>",
                    parse_mode='HTML'
                )
    
    elif setting_type == "currency":
        if len(context.args) < 2:
            await update.message.reply_text(
                "💱 <b>Currency Setting</b>\n\n"
                "<b>Usage:</b> <code>/settings currency &lt;currency&gt;</code>\n\n"
                "<b>Available Currencies:</b>\n"
                "• <code>USD</code> - US Dollar ($)\n"
                "• <code>EUR</code> - Euro (€)\n"
                "• <code>JPY</code> - Japanese Yen (¥)\n"
                "• <code>IDR</code> - Indonesian Rupiah (Rp)\n"
                "• <code>GBP</code> - British Pound (£)\n"
                "• <code>SGD</code> - Singapore Dollar (S$)\n\n"
                f"<b>Current:</b> {user_settings.get('currency', 'USD')}",
                parse_mode='HTML'
            )
        else:
            currency = context.args[1].upper()
            valid_currencies = ['USD', 'EUR', 'JPY', 'IDR', 'GBP', 'SGD', 'AUD', 'CAD']
            if currency in valid_currencies:
                if update_user_setting(user_id, 'currency', currency):
                    currency_symbols = {
                        'USD': '$', 'EUR': '€', 'JPY': '¥', 'IDR': 'Rp',
                        'GBP': '£', 'SGD': 'S$', 'AUD': 'A$', 'CAD': 'C$'
                    }
                    symbol = currency_symbols.get(currency, currency)
                    await update.message.reply_text(
                        f"💱 <b>Currency Updated</b>\n\n"
                        f"💰 <b>New Currency:</b> {currency} ({symbol})\n"
                        f"📊 <b>Note:</b> All prices will now be displayed in {currency}\n\n"
                        f"✅ Setting saved successfully!",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        "❌ <b>Error</b>\n\nFailed to update currency setting.",
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    "❌ <b>Invalid Currency</b>\n\n"
                    f"'{currency}' is not supported.\n"
                    "Please use: USD, EUR, JPY, IDR, GBP, SGD, AUD, CAD",
                    parse_mode='HTML'
                )
    
    elif setting_type == "charts":
        if len(context.args) < 2:
            await update.message.reply_text(
                "📈 <b>Chart Display Setting</b>\n\n"
                "<b>Usage:</b> <code>/settings charts &lt;on/off&gt;</code>\n\n"
                f"<b>Current Status:</b> {'ON' if user_settings.get('charts_enabled', True) else 'OFF'}\n"
                "• Price charts included in analysis\n"
                "• Technical indicators displayed\n"
                "• Visual trend analysis",
                parse_mode='HTML'
            )
        else:
            status = context.args[1].lower()
            if status in ['on', 'off', 'enable', 'disable']:
                is_enabled = status in ['on', 'enable']
                if update_user_setting(user_id, 'charts_enabled', is_enabled):
                    status_text = "ON" if is_enabled else "OFF"
                    emoji = "📈" if is_enabled else "📊"
                    await update.message.reply_text(
                        f"{emoji} <b>Charts {status_text}</b>\n\n"
                        f"📊 <b>Status:</b> Chart display is now <b>{status_text}</b>\n"
                        f"🎯 <b>Applies to:</b> Analysis reports, technical indicators, price trends\n\n"
                        f"✅ Setting saved successfully!",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        "❌ <b>Error</b>\n\nFailed to update charts setting.",
                        parse_mode='HTML'
                    )
    
    elif setting_type == "privacy_mode":
        if len(context.args) < 2:
            await update.message.reply_text(
                "🔐 <b>Privacy Mode Setting</b>\n\n"
                "<b>Usage:</b> <code>/settings privacy_mode &lt;on/off&gt;</code>\n\n"
                f"<b>Current Status:</b> {'ON' if user_settings.get('privacy_mode', False) else 'OFF'}\n"
                "• Hide portfolio values\n"
                "• Mask sensitive numbers\n"
                "• Protect financial data",
                parse_mode='HTML'
            )
        else:
            status = context.args[1].lower()
            if status in ['on', 'off', 'enable', 'disable']:
                is_enabled = status in ['on', 'enable']
                if update_user_setting(user_id, 'privacy_mode', is_enabled):
                    status_text = "ON" if is_enabled else "OFF"
                    emoji = "🔐" if is_enabled else "👁️"
                    await update.message.reply_text(
                        f"{emoji} <b>Privacy Mode {status_text}</b>\n\n"
                        f"🛡️ <b>Status:</b> Privacy mode is now <b>{status_text}</b>\n"
                        f"🎯 <b>Applies to:</b> Portfolio values, transaction amounts, sensitive data\n\n"
                        f"✅ Setting saved successfully!",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        "❌ <b>Error</b>\n\nFailed to update privacy mode setting.",
                        parse_mode='HTML'
                    )
    
    elif setting_type == "reset":
        if reset_user_settings(user_id):
            await update.message.reply_text(
                "🔄 <b>Settings Reset</b>\n\n"
                "✅ <b>All settings have been reset to defaults:</b>\n\n"
                "⏰ Timezone: Asia/Jakarta (WIB)\n"
                "🔔 Notifications: ON\n"
                "📊 Alert Threshold: 5%\n"
                "💱 Currency: USD\n"
                "📈 Charts: ON\n"
                "🗃️ Cache Duration: 60 minutes\n"
                "🔐 Privacy Mode: OFF\n\n"
                "💡 Use <code>/settings</code> to reconfigure as needed.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ <b>Error</b>\n\nFailed to reset settings.",
                parse_mode='HTML'
            )
    
    elif setting_type == "export":
        current_settings = get_user_settings(user_id)
        settings_text = f"""timezone: {current_settings.get('timezone', 'Asia/Jakarta')}
notifications: {'ON' if current_settings.get('notifications', True) else 'OFF'}
alerts_threshold: {current_settings.get('alerts_threshold', 5)}
currency: {current_settings.get('currency', 'USD')}
charts_enabled: {'ON' if current_settings.get('charts_enabled', True) else 'OFF'}
cache_duration: {current_settings.get('cache_duration', 60)}
privacy_mode: {'ON' if current_settings.get('privacy_mode', False) else 'OFF'}
language: {current_settings.get('language', 'en')}
data_retention_days: {current_settings.get('data_retention_days', 30)}"""
        
        await update.message.reply_text(
            f"📤 <b>Settings Export</b>\n\n"
            f"<code>{settings_text}</code>\n\n"
            f"💾 <b>How to use:</b>\n"
            f"• Copy the settings above\n"
            f"• Share with other devices\n"
            f"• Use <code>/settings import</code> to restore\n\n"
            f"🔒 <b>Note:</b> This export does not contain sensitive data.",
            parse_mode='HTML'
        )
    
    else:
        await update.message.reply_text(
            "❌ <b>Unknown Setting</b>\n\n"
            f"'{setting_type}' is not a valid setting option.\n\n"
            "Use <code>/settings</code> to see all available settings.",
            parse_mode='HTML'
        )

# --- New Handlers for Portfolio Management ---

async def add_asset_command(update: Update, context: CallbackContext):
    """Adds an asset and quantity to the user's portfolio."""
    if len(context.args) != 2:
        await update.message.reply_text(
            "💼 <b>Add Asset to Portfolio</b>\n\n"
            "📋 <b>Usage:</b> <code>/add_asset &lt;symbol&gt; &lt;quantity&gt;</code>\n\n"
            "📊 <b>Examples:</b>\n"
            "• <code>/add_asset BTC 0.5</code> - Add 0.5 Bitcoin\n"
            "• <code>/add_asset NVDA 10</code> - Add 10 NVIDIA shares\n"
            "• <code>/add_asset ETH 2.5</code> - Add 2.5 Ethereum\n"
            "• <code>/add_asset TSLA 5</code> - Add 5 Tesla shares\n\n"
            "💡 <b>Supported Assets:</b>\n"
            "• Cryptocurrencies: BTC, ETH, ADA, SOL, etc.\n"
            "• Stocks: NVDA, TSLA, AAPL, MSFT, etc.\n"
            "• Any valid trading symbol\n\n"
            "📈 <i>Build your investment portfolio with real-time tracking!</i>",
            parse_mode='HTML'
        )
        return

    symbol = context.args[0].upper()
    try:
        quantity = float(context.args[1])
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
    except ValueError:
        await update.message.reply_text(
            "❌ <b>Invalid Quantity</b>\n\n"
            "📊 <b>Error:</b> Quantity must be a positive number\n\n"
            "✅ <b>Valid Examples:</b>\n"
            "• <code>/add_asset BTC 0.5</code>\n"
            "• <code>/add_asset NVDA 10</code>\n"
            "• <code>/add_asset ETH 2.75</code>\n\n"
            "💡 <b>Tip:</b> Use decimal numbers for fractional shares/coins",
            parse_mode='HTML'
        )
        return

    user_id = update.effective_user.id
    
    # Validate symbol by checking market data
    market_data = get_market_data(symbol)
    if not market_data:
        await update.message.reply_text(
            f"❌ <b>Asset Not Found</b>\n\n"
            f"🔍 <b>Symbol:</b> <code>{escape_html(symbol)}</code>\n\n"
            f"📋 <b>Issue:</b> Unable to find market data for this symbol\n\n"
            f"💡 <b>Suggestions:</b>\n"
            f"• Check symbol spelling (e.g., BTC, not Bitcoin)\n"
            f"• Use official ticker symbols (e.g., NVDA, not Nvidia)\n"
            f"• Try popular symbols: BTC, ETH, NVDA, TSLA, AAPL\n\n"
            f"🔄 <b>Alternative:</b> Try <code>/analyze {escape_html(symbol)}</code> to verify symbol exists",
            parse_mode='HTML'
        )
        return

    if add_portfolio_asset(user_id, symbol, quantity):
        current_price = market_data.get('current_price', 0)
        asset_value = quantity * current_price if current_price else 0
        asset_name = market_data.get('name', symbol)
        
        await update.message.reply_text(
            f"✅ <b>Asset Added Successfully!</b>\n\n"
            f"🏷️ <b>Asset:</b> {asset_name} ({symbol})\n"
            f"📊 <b>Quantity Added:</b> <code>{quantity:,.6f}</code> units\n"
            f"💰 <b>Current Price:</b> <code>${current_price:,.2f} USD</code>\n"
            f"💎 <b>Total Value:</b> <code>${asset_value:,.2f} USD</code>\n\n"
            f"📈 <b>Portfolio Status:</b>\n"
            f"• Asset successfully added to your portfolio\n"
            f"• Real-time price tracking enabled\n"
            f"• 24/7 performance monitoring active\n\n"
            f"🛠️ <b>Next Steps:</b>\n"
            f"• <code>/view_portfolio</code> - View complete portfolio\n"
            f"• <code>/analyze {symbol}</code> - Get detailed asset analysis\n"
            f"• <code>/add_asset &lt;symbol&gt; &lt;quantity&gt;</code> - Add more assets\n\n"
            f"💡 <i>Your portfolio value updates automatically with market prices</i>",
            parse_mode='HTML'
        )
        logger.info(f"User {user_id} added {quantity} of {symbol} to portfolio.")
    else:
        await update.message.reply_text(
            f"❌ <b>Failed to Add Asset</b>\n\n"
            f"🔧 <b>Technical Issue:</b> Unable to add {escape_html(symbol)} to your portfolio\n\n"
            f"📋 <b>Possible Causes:</b>\n"
            f"• Database connectivity issue\n"
            f"• Temporary system maintenance\n"
            f"• Asset already exists (use different quantity)\n\n"
            f"🔄 <b>Solution:</b> Please try again in a few moments\n"
            f"💬 <b>Support:</b> If the issue persists, contact support",
            parse_mode='HTML'
        )

async def remove_asset_command(update: Update, context: CallbackContext):
    """Removes an asset from the user's portfolio."""
    if len(context.args) != 1:
        await update.message.reply_text(
            "🗑️ <b>Remove Asset from Portfolio</b>\n\n"
            "📋 <b>Usage:</b> <code>/remove_asset &lt;symbol&gt;</code>\n\n"
            "📊 <b>Examples:</b>\n"
            "• <code>/remove_asset BTC</code> - Remove Bitcoin\n"
            "• <code>/remove_asset NVDA</code> - Remove NVIDIA shares\n"
            "• <code>/remove_asset ETH</code> - Remove Ethereum\n\n"
            "💡 <b>Tips:</b>\n"
            "• Use <code>/view_portfolio</code> to see all your assets\n"
            "• Symbol must match exactly (case-insensitive)\n"
            "• This removes the entire holding for that asset\n\n"
            "⚠️ <i>This action cannot be undone - asset will be completely removed</i>",
            parse_mode='HTML'
        )
        return

    symbol = context.args[0].upper()
    user_id = update.effective_user.id

    deleted_count = remove_portfolio_asset(user_id, symbol)
    if deleted_count > 0:
        await update.message.reply_text(
            f"✅ <b>Asset Removed Successfully!</b>\n\n"
            f"🗑️ <b>Removed Asset:</b> <code>{escape_html(symbol)}</code>\n"
            f"📊 <b>Status:</b> Completely removed from your portfolio\n\n"
            f"📈 <b>Portfolio Update:</b>\n"
            f"• Asset is no longer tracked\n"
            f"• Portfolio value recalculated\n"
            f"• Real-time monitoring stopped for this asset\n\n"
            f"🛠️ <b>Next Steps:</b>\n"
            f"• <code>/view_portfolio</code> - View updated portfolio\n"
            f"• <code>/add_asset {escape_html(symbol)} &lt;quantity&gt;</code> - Re-add if needed\n"
            f"• <code>/add_asset &lt;symbol&gt; &lt;quantity&gt;</code> - Add different assets\n\n"
            f"💡 <i>You can always add this asset back later with any quantity</i>",
            parse_mode='HTML'
        )
        logger.info(f"User {user_id} removed {symbol} from portfolio.")
    else:
        await update.message.reply_text(
            f"❌ <b>Asset Not Found in Portfolio</b>\n\n"
            f"🔍 <b>Symbol:</b> <code>{escape_html(symbol)}</code>\n\n"
            f"📋 <b>Issue:</b> This asset is not currently in your portfolio\n\n"
            f"💡 <b>Suggestions:</b>\n"
            f"• Check symbol spelling\n"
            f"• Use <code>/view_portfolio</code> to see all your assets\n"
            f"• Verify the correct ticker symbol\n\n"
            f"🛠️ <b>Available Commands:</b>\n"
            f"• <code>/view_portfolio</code> - See all portfolio assets\n"
            f"• <code>/add_asset &lt;symbol&gt; &lt;quantity&gt;</code> - Add new assets",
            parse_mode='HTML'
        )

async def view_portfolio_command(update: Update, context: CallbackContext):
    """Views the user's current portfolio with market data."""
    user_id = update.effective_user.id
    portfolio_assets = get_user_portfolio(user_id)
    
    # Get user settings for currency preference
    user_settings = get_user_settings(user_id)
    user_currency = user_settings.get('currency', 'USD')
    
    # Currency symbols mapping
    currency_symbols = {
        'USD': '$', 'EUR': '€', 'JPY': '¥', 'IDR': 'Rp',
        'GBP': '£', 'SGD': 'S$', 'AUD': 'A$', 'CAD': 'C$'
    }
    currency_symbol = currency_symbols.get(user_currency, user_currency)
    
    # Currency conversion rates (simplified - in real app, you'd fetch these from an API)
    conversion_rates = {
        'USD': 1.0,
        'EUR': 0.85,
        'JPY': 110.0,
        'IDR': 15000.0,  # Approximate IDR to USD rate
        'GBP': 0.75,
        'SGD': 1.35,
        'AUD': 1.45,
        'CAD': 1.25
    }
    conversion_rate = conversion_rates.get(user_currency, 1.0)

    if not portfolio_assets:
        await update.message.reply_text(
            "💼 <b>Your Investment Portfolio</b>\n\n"
            "📊 <b>Status:</b> Portfolio is currently empty\n\n"
            "🚀 <b>Get Started:</b>\n"
            "• <code>/add_asset BTC 0.5</code> - Add Bitcoin to portfolio\n"
            "• <code>/add_asset NVDA 10</code> - Add NVIDIA stocks\n"
            "• <code>/add_asset ETH 2</code> - Add Ethereum to portfolio\n\n"
            "💡 <b>Portfolio Features:</b>\n"
            "• Real-time price tracking\n"
            "• 24-hour performance monitoring\n"
            "• Total portfolio value calculation\n"
            "• Professional portfolio analysis\n\n"
            "📈 <i>Start building your investment portfolio today!</i>",
            parse_mode='HTML'
        )
        return

    message = "� <b>Your Investment Portfolio</b>\n"
    message += f"<i>Real-time market data • Currency: {user_currency}</i>\n\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    total_portfolio_value = 0.0
    performing_assets = []
    
    for asset in portfolio_assets:
        symbol = asset['symbol']
        quantity = asset['quantity']
        
        market_data = get_market_data(symbol)
        
        if market_data and market_data.get('current_price'):
            current_price_usd = market_data['current_price']
            current_price = current_price_usd * conversion_rate
            asset_value = quantity * current_price
            total_portfolio_value += asset_value
            price_change_24h_pct = market_data.get('price_change_24h_pct') or market_data.get('price_change_pct', 0)
            
            # Determine performance emoji
            if price_change_24h_pct > 0:
                change_emoji = "📈"
                change_color = "🟢"
            elif price_change_24h_pct < 0:
                change_emoji = "📉"
                change_color = "🔴"
            else:
                change_emoji = "➡️"
                change_color = "⚪"
            
            performing_assets.append({
                'symbol': symbol,
                'change': price_change_24h_pct,
                'value': asset_value
            })

            message += (
                f"🏷️ <b>{market_data.get('name', symbol)} ({symbol})</b>\n"
                f"📊 <b>Holdings:</b> <code>{quantity:,.6f}</code> units\n"
                f"💰 <b>Current Price:</b> <code>{currency_symbol}{current_price:,.2f} {user_currency}</code>\n"
                f"💎 <b>Total Value:</b> <code>{currency_symbol}{asset_value:,.2f} {user_currency}</code>\n"
                f"{change_emoji} <b>24h Change:</b> {change_color} <code>{price_change_24h_pct:+.2f}%</code>\n\n"
            )
        else:
            message += (
                f"🏷️ <b>{symbol}</b>\n"
                f"📊 <b>Holdings:</b> <code>{quantity:,.6f}</code> units\n"
                f"⚠️ <b>Status:</b> <i>Market data temporarily unavailable</i>\n"
                f"🔄 <i>Please try again in a few moments</i>\n\n"
            )

    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"💼 <b>Total Portfolio Value:</b> <code>{currency_symbol}{total_portfolio_value:,.2f} {user_currency}</code>\n\n"
    
    # Portfolio performance summary
    if performing_assets:
        best_performer = max(performing_assets, key=lambda x: x['change'])
        worst_performer = min(performing_assets, key=lambda x: x['change'])
        
        message += "📊 <b>Portfolio Performance Summary:</b>\n"
        message += f"🏆 <b>Best Performer:</b> {best_performer['symbol']} ({best_performer['change']:+.2f}%)\n"
        message += f"📉 <b>Needs Attention:</b> {worst_performer['symbol']} ({worst_performer['change']:+.2f}%)\n"
        message += f"🏢 <b>Total Assets:</b> {len(portfolio_assets)} different holdings\n\n"
    
    message += "🛠️ <b>Portfolio Management:</b>\n"
    message += "• <code>/add_asset &lt;symbol&gt; &lt;quantity&gt;</code> - Add new holding\n"
    message += "• <code>/remove_asset &lt;symbol&gt;</code> - Remove specific asset\n"
    message += "• <code>/clear_portfolio</code> - Clear all holdings\n"
    message += "• <code>/analyze &lt;symbol&gt;</code> - Get detailed asset analysis\n\n"
    
    message += "📅 <i>Last updated: Real-time market data</i>\n"
    message += "⚠️ <i>This is not financial advice. Please do your own research.</i>\n"
    message += "🔗 <i>Powered by Cortensor Network</i>"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def clear_portfolio_command(update: Update, context: CallbackContext):
    """Clears all assets from the user's portfolio."""
    user_id = update.effective_user.id
    deleted_count = clear_user_portfolio(user_id)

    if deleted_count > 0:
        await update.message.reply_text(
            f"✅ <b>Portfolio Cleared Successfully!</b>\n\n"
            f"🗑️ <b>Assets Removed:</b> {deleted_count} assets\n"
            f"📊 <b>Status:</b> Your portfolio is now empty\n\n"
            f"📈 <b>Portfolio Reset Complete:</b>\n"
            f"• All assets and quantities removed\n"
            f"• Portfolio value reset to $0.00\n"
            f"• Real-time tracking stopped for all assets\n"
            f"• Portfolio history cleared\n\n"
            f"🚀 <b>Start Fresh:</b>\n"
            f"• <code>/add_asset BTC 0.5</code> - Add Bitcoin\n"
            f"• <code>/add_asset NVDA 10</code> - Add NVIDIA shares\n"
            f"• <code>/add_asset ETH 2</code> - Add Ethereum\n\n"
            f"💡 <b>Portfolio Features:</b>\n"
            f"• Real-time price tracking\n"
            f"• 24-hour performance monitoring\n"
            f"• Professional portfolio analysis\n"
            f"• Total value calculation\n\n"
            f"📱 <i>Ready to build your new investment portfolio!</i>",
            parse_mode='HTML'
        )
        logger.info(f"User {user_id} cleared their portfolio ({deleted_count} assets).")
    else:
        await update.message.reply_text(
            "💼 <b>Portfolio Status</b>\n\n"
            "📊 <b>Current Status:</b> Your portfolio is already empty\n\n"
            "🚀 <b>Get Started:</b>\n"
            "• <code>/add_asset BTC 0.5</code> - Add Bitcoin to portfolio\n"
            "• <code>/add_asset NVDA 10</code> - Add NVIDIA stocks\n"
            "• <code>/add_asset ETH 2</code> - Add Ethereum to portfolio\n\n"
            "💡 <b>Portfolio Benefits:</b>\n"
            "• Track multiple assets in one place\n"
            "• Real-time value updates\n"
            "• Performance monitoring\n"
            "• Professional analysis reports\n\n"
            "📈 <i>Start building your investment portfolio today!</i>",
            parse_mode='HTML'
        )

# --- DCA (Dollar Cost Averaging) Handlers ---

async def dca_command(update: Update, context: CallbackContext):
    """Handles DCA-related commands."""
    if not context.args:
        await update.message.reply_text(
            "💸 <b>DCA - Dollar Cost Averaging</b>\n\n"
            "🔄 <b>Available Commands:</b>\n\n"
            "📅 <b>Schedule Management:</b>\n"
            "• <code>/dca add &lt;symbol&gt; &lt;amount&gt; &lt;currency&gt; &lt;frequency&gt; &lt;time&gt;</code>\n"
            "  Create new DCA schedule\n"
            "• <code>/dca list</code> - View all DCA schedules\n"
            "• <code>/dca pause &lt;dca_id&gt;</code> - Pause DCA schedule\n"
            "• <code>/dca resume &lt;dca_id&gt;</code> - Resume DCA schedule\n"
            "• <code>/dca delete &lt;dca_id&gt;</code> - Delete DCA schedule\n\n"
            "📊 <b>Statistics:</b>\n"
            "• <code>/dca stats &lt;dca_id&gt;</code> - View DCA performance\n"
            "• <code>/dca summary</code> - Overall DCA summary\n\n"
            "💡 <b>Examples:</b>\n"
            "• <code>/dca add BTC 50 USD daily 15:00</code>\n"
            "  Buy $50 worth of BTC daily at 3:00 PM\n"
            "• <code>/dca add ETH 100 USD weekly 09:30</code>\n"
            "  Buy $100 worth of ETH weekly at 9:30 AM\n"
            "• <code>/dca add NVDA 200 USD monthly 10:00</code>\n"
            "  Buy $200 worth of NVDA monthly at 10:00 AM\n\n"
            "📈 <b>Supported Frequencies:</b> daily, weekly, monthly\n"
            "💱 <b>Supported Currencies:</b> USD, EUR, IDR, JPY, GBP, SGD\n"
            "⏰ <b>Time Format:</b> HH:MM (24-hour format)\n\n"
            "🎯 <i>Automate your investments with disciplined DCA strategy!</i>",
            parse_mode='HTML'
        )
        return

    command = context.args[0].lower()
    
    if command == "add":
        await dca_add_command(update, context)
    elif command == "list":
        await dca_list_command(update, context)
    elif command == "pause":
        await dca_pause_command(update, context)
    elif command == "resume":
        await dca_resume_command(update, context)
    elif command == "delete":
        await dca_delete_command(update, context)
    elif command == "stats":
        await dca_stats_command(update, context)
    elif command == "summary":
        await dca_summary_command(update, context)
    else:
        await update.message.reply_text(
            "❌ <b>Unknown DCA Command</b>\n\n"
            f"'{command}' is not a valid DCA command.\n\n"
            "Use <code>/dca</code> to see all available commands.",
            parse_mode='HTML'
        )

async def dca_add_command(update: Update, context: CallbackContext):
    """Adds a new DCA schedule."""
    if len(context.args) != 6:
        await update.message.reply_text(
            "💸 <b>Add DCA Schedule</b>\n\n"
            "📋 <b>Usage:</b>\n"
            "<code>/dca add &lt;symbol&gt; &lt;amount&gt; &lt;currency&gt; &lt;frequency&gt; &lt;time&gt;</code>\n\n"
            "📊 <b>Parameters:</b>\n"
            "• <b>Symbol:</b> BTC, ETH, NVDA, TSLA, etc.\n"
            "• <b>Amount:</b> Investment amount per execution\n"
            "• <b>Currency:</b> USD, EUR, IDR, JPY, GBP, SGD\n"
            "• <b>Frequency:</b> daily, weekly, monthly\n"
            "• <b>Time:</b> HH:MM (24-hour format)\n\n"
            "💡 <b>Examples:</b>\n"
            "• <code>/dca add BTC 50 USD daily 15:00</code>\n"
            "• <code>/dca add ETH 100 EUR weekly 09:30</code>\n"
            "• <code>/dca add NVDA 200 USD monthly 10:00</code>\n\n"
            "🎯 <i>Build wealth consistently with automated investing!</i>",
            parse_mode='HTML'
        )
        return
    
    _, symbol, amount_str, currency, frequency, time = context.args
    user_id = update.effective_user.id
    
    # Validate inputs
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await update.message.reply_text(
            "❌ <b>Invalid Amount</b>\n\n"
            "💰 <b>Error:</b> Amount must be a positive number\n\n"
            "✅ <b>Valid Examples:</b>\n"
            "• <code>50</code> (for $50)\n"
            "• <code>100.50</code> (for $100.50)\n"
            "• <code>25</code> (for $25)",
            parse_mode='HTML'
        )
        return
    
    # Validate currency
    valid_currencies = ['USD', 'EUR', 'IDR', 'JPY', 'GBP', 'SGD', 'AUD', 'CAD']
    currency = currency.upper()
    if currency not in valid_currencies:
        await update.message.reply_text(
            "❌ <b>Invalid Currency</b>\n\n"
            f"💱 <b>Error:</b> '{currency}' is not supported\n\n"
            "✅ <b>Supported Currencies:</b>\n"
            "• USD, EUR, JPY, IDR\n"
            "• GBP, SGD, AUD, CAD",
            parse_mode='HTML'
        )
        return
    
    # Validate frequency
    valid_frequencies = ['daily', 'weekly', 'monthly']
    frequency = frequency.lower()
    if frequency not in valid_frequencies:
        await update.message.reply_text(
            "❌ <b>Invalid Frequency</b>\n\n"
            f"📅 <b>Error:</b> '{frequency}' is not supported\n\n"
            "✅ <b>Supported Frequencies:</b>\n"
            "• <code>daily</code> - Every day\n"
            "• <code>weekly</code> - Every week\n"
            "• <code>monthly</code> - Every month",
            parse_mode='HTML'
        )
        return
    
    # Validate time format
    try:
        hour, minute = map(int, time.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time range")
    except ValueError:
        await update.message.reply_text(
            "❌ <b>Invalid Time Format</b>\n\n"
            "⏰ <b>Error:</b> Time must be in HH:MM format (24-hour)\n\n"
            "✅ <b>Valid Examples:</b>\n"
            "• <code>15:00</code> (3:00 PM)\n"
            "• <code>09:30</code> (9:30 AM)\n"
            "• <code>21:45</code> (9:45 PM)",
            parse_mode='HTML'
        )
        return
    
    # Validate symbol with market data
    from src.services.market_data_api import get_market_data
    market_data = get_market_data(symbol.upper())
    if not market_data:
        await update.message.reply_text(
            f"❌ <b>Asset Not Found</b>\n\n"
            f"🔍 <b>Symbol:</b> <code>{escape_html(symbol.upper())}</code>\n\n"
            f"📋 <b>Issue:</b> Unable to find market data for this symbol\n\n"
            f"💡 <b>Suggestions:</b>\n"
            f"• Check symbol spelling (e.g., BTC, not Bitcoin)\n"
            f"• Use official ticker symbols (e.g., NVDA, not Nvidia)\n"
            f"• Try popular symbols: BTC, ETH, NVDA, TSLA, AAPL",
            parse_mode='HTML'
        )
        return
    
    # Create DCA schedule
    dca_id = add_dca_schedule(user_id, symbol.upper(), amount, currency, frequency, time)
    
    if dca_id:
        current_price_usd = market_data.get('current_price', 0)
        asset_name = market_data.get('name', symbol.upper())
        currency_symbols = {
            'USD': '$', 'EUR': '€', 'JPY': '¥', 'IDR': 'Rp',
            'GBP': '£', 'SGD': 'S$', 'AUD': 'A$', 'CAD': 'C$'
        }
        currency_symbol = currency_symbols.get(currency, currency)
        
        # Currency conversion rates
        conversion_rates = {
            'USD': 1.0,
            'EUR': 0.85,
            'JPY': 110.0,
            'IDR': 15000.0,  # Approximate IDR to USD rate
            'GBP': 0.75,
            'SGD': 1.35,
            'AUD': 1.45,
            'CAD': 1.25
        }
        conversion_rate = conversion_rates.get(currency, 1.0)
        current_price = current_price_usd * conversion_rate
        
        await update.message.reply_text(
            f"✅ <b>DCA Schedule Created!</b>\n\n"
            f"🎯 <b>DCA ID:</b> <code>{dca_id}</code>\n"
            f"🏷️ <b>Asset:</b> {asset_name} ({symbol.upper()})\n"
            f"💰 <b>Amount:</b> {currency_symbol}{amount:,.2f} {currency}\n"
            f"📅 <b>Frequency:</b> {frequency.title()}\n"
            f"⏰ <b>Time:</b> {time}\n"
            f"💎 <b>Current Price:</b> {currency_symbol}{current_price:,.2f} {currency}\n\n"
            f"🔄 <b>Next Execution:</b> Based on your schedule\n"
            f"📊 <b>Status:</b> Active and ready\n\n"
            f"🛠️ <b>Management Commands:</b>\n"
            f"• <code>/dca pause {dca_id}</code> - Pause this schedule\n"
            f"• <code>/dca stats {dca_id}</code> - View performance\n"
            f"• <code>/dca list</code> - View all schedules\n\n"
            f"💡 <i>Your DCA strategy is now automated!</i>",
            parse_mode='HTML'
        )
        logger.info(f"User {user_id} created DCA schedule {dca_id} for {symbol} {amount} {currency} {frequency} at {time}")
    else:
        await update.message.reply_text(
            "❌ <b>Failed to Create DCA Schedule</b>\n\n"
            "🔧 <b>Technical Issue:</b> Unable to create the DCA schedule\n\n"
            "🔄 <b>Solution:</b> Please try again in a few moments\n"
            "💬 <b>Support:</b> If the issue persists, contact support",
            parse_mode='HTML'
        )

async def dca_list_command(update: Update, context: CallbackContext):
    """Lists all DCA schedules for the user."""
    user_id = update.effective_user.id
    dca_schedules = get_user_dca_schedules(user_id)
    
    if not dca_schedules:
        await update.message.reply_text(
            "💸 <b>Your DCA Schedules</b>\n\n"
            "📊 <b>Status:</b> No DCA schedules found\n\n"
            "🚀 <b>Get Started:</b>\n"
            "• <code>/dca add BTC 50 USD daily 15:00</code>\n"
            "• <code>/dca add ETH 100 USD weekly 09:30</code>\n"
            "• <code>/dca add NVDA 200 USD monthly 10:00</code>\n\n"
            "💡 <b>Benefits of DCA:</b>\n"
            "• Reduce timing risk\n"
            "• Build discipline\n"
            "• Average out market volatility\n"
            "• Automate your investments\n\n"
            "📈 <i>Start your DCA journey today!</i>",
            parse_mode='HTML'
        )
        return
    
    user_settings = get_user_settings(user_id)
    user_currency = user_settings.get('currency', 'USD')
    currency_symbols = {
        'USD': '$', 'EUR': '€', 'JPY': '¥', 'IDR': 'Rp',
        'GBP': '£', 'SGD': 'S$', 'AUD': 'A$', 'CAD': 'C$'
    }
    
    message = "💸 <b>Your DCA Schedules</b>\n\n"
    
    for i, schedule in enumerate(dca_schedules, 1):
        status_emoji = "🟢" if schedule['is_active'] else "🔴"
        status_text = "Active" if schedule['is_active'] else "Paused"
        currency_symbol = currency_symbols.get(schedule['currency'], schedule['currency'])
        
        total_invested = schedule.get('total_invested', 0)
        execution_count = schedule.get('execution_count', 0)
        
        message += (
            f"{status_emoji} <b>#{i} - {schedule['symbol']}</b>\n"
            f"🆔 <code>{schedule['dca_id']}</code>\n"
            f"💰 {currency_symbol}{schedule['amount']:,.2f} {schedule['currency']} • {schedule['frequency']}\n"
            f"⏰ {schedule['time']} • {status_text}\n"
            f"📊 Executed: {execution_count}x • Total: {currency_symbol}{total_invested:,.2f}\n\n"
        )
    
    message += (
        "🛠️ <b>Quick Actions:</b>\n"
        "• <code>/dca pause &lt;dca_id&gt;</code> - Pause schedule\n"
        "• <code>/dca resume &lt;dca_id&gt;</code> - Resume schedule\n"
        "• <code>/dca stats &lt;dca_id&gt;</code> - View performance\n"
        "• <code>/dca delete &lt;dca_id&gt;</code> - Delete schedule\n\n"
        "💡 <i>Manage your automated investment strategy!</i>"
    )
    
    await update.message.reply_text(message, parse_mode='HTML')

async def dca_pause_command(update: Update, context: CallbackContext):
    """Pauses a DCA schedule."""
    if len(context.args) != 2:
        await update.message.reply_text(
            "⏸️ <b>Pause DCA Schedule</b>\n\n"
            "📋 <b>Usage:</b> <code>/dca pause &lt;dca_id&gt;</code>\n\n"
            "💡 <b>Example:</b> <code>/dca pause dca_1234567890</code>\n\n"
            "🔍 <b>Find DCA ID:</b> Use <code>/dca list</code>",
            parse_mode='HTML'
        )
        return
    
    dca_id = context.args[1]
    user_id = update.effective_user.id
    
    if toggle_dca_schedule(dca_id, user_id, False):
        await update.message.reply_text(
            f"⏸️ <b>DCA Schedule Paused</b>\n\n"
            f"🆔 <b>DCA ID:</b> <code>{dca_id}</code>\n"
            f"📊 <b>Status:</b> Paused\n"
            f"🔄 <b>Note:</b> No automatic purchases will occur\n\n"
            f"▶️ <b>Resume:</b> <code>/dca resume {dca_id}</code>\n"
            f"🗑️ <b>Delete:</b> <code>/dca delete {dca_id}</code>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Failed to Pause DCA</b>\n\n"
            f"🔍 <b>DCA ID:</b> <code>{dca_id}</code>\n\n"
            "📋 <b>Possible Causes:</b>\n"
            "• Invalid DCA ID\n"
            "• DCA doesn't belong to you\n"
            "• Already paused\n\n"
            "💡 <b>Solution:</b> Use <code>/dca list</code> to verify ID",
            parse_mode='HTML'
        )

async def dca_resume_command(update: Update, context: CallbackContext):
    """Resumes a paused DCA schedule."""
    if len(context.args) != 2:
        await update.message.reply_text(
            "▶️ <b>Resume DCA Schedule</b>\n\n"
            "📋 <b>Usage:</b> <code>/dca resume &lt;dca_id&gt;</code>\n\n"
            "💡 <b>Example:</b> <code>/dca resume dca_1234567890</code>\n\n"
            "🔍 <b>Find DCA ID:</b> Use <code>/dca list</code>",
            parse_mode='HTML'
        )
        return
    
    dca_id = context.args[1]
    user_id = update.effective_user.id
    
    if toggle_dca_schedule(dca_id, user_id, True):
        await update.message.reply_text(
            f"▶️ <b>DCA Schedule Resumed</b>\n\n"
            f"🆔 <b>DCA ID:</b> <code>{dca_id}</code>\n"
            f"📊 <b>Status:</b> Active\n"
            f"🔄 <b>Note:</b> Automatic purchases will resume according to schedule\n\n"
            f"⏸️ <b>Pause:</b> <code>/dca pause {dca_id}</code>\n"
            f"📊 <b>Stats:</b> <code>/dca stats {dca_id}</code>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Failed to Resume DCA</b>\n\n"
            f"🔍 <b>DCA ID:</b> <code>{dca_id}</code>\n\n"
            "📋 <b>Possible Causes:</b>\n"
            "• Invalid DCA ID\n"
            "• DCA doesn't belong to you\n"
            "• Already active\n\n"
            "💡 <b>Solution:</b> Use <code>/dca list</code> to verify ID",
            parse_mode='HTML'
        )

async def dca_delete_command(update: Update, context: CallbackContext):
    """Deletes a DCA schedule."""
    if len(context.args) != 2:
        await update.message.reply_text(
            "🗑️ <b>Delete DCA Schedule</b>\n\n"
            "📋 <b>Usage:</b> <code>/dca delete &lt;dca_id&gt;</code>\n\n"
            "💡 <b>Example:</b> <code>/dca delete dca_1234567890</code>\n\n"
            "🔍 <b>Find DCA ID:</b> Use <code>/dca list</code>\n\n"
            "⚠️ <b>Warning:</b> This action cannot be undone!",
            parse_mode='HTML'
        )
        return
    
    dca_id = context.args[1]
    user_id = update.effective_user.id
    
    if delete_dca_schedule(dca_id, user_id):
        await update.message.reply_text(
            f"🗑️ <b>DCA Schedule Deleted</b>\n\n"
            f"🆔 <b>DCA ID:</b> <code>{dca_id}</code>\n"
            f"📊 <b>Status:</b> Permanently removed\n"
            f"🔄 <b>Note:</b> All automated purchases have been stopped\n\n"
            f"🚀 <b>Create New:</b> <code>/dca add &lt;symbol&gt; &lt;amount&gt; &lt;currency&gt; &lt;frequency&gt; &lt;time&gt;</code>\n"
            f"📋 <b>View All:</b> <code>/dca list</code>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Failed to Delete DCA</b>\n\n"
            f"🔍 <b>DCA ID:</b> <code>{dca_id}</code>\n\n"
            "📋 <b>Possible Causes:</b>\n"
            "• Invalid DCA ID\n"
            "• DCA doesn't belong to you\n"
            "• Already deleted\n\n"
            "💡 <b>Solution:</b> Use <code>/dca list</code> to verify ID",
            parse_mode='HTML'
        )

async def dca_stats_command(update: Update, context: CallbackContext):
    """Shows statistics for a specific DCA schedule."""
    if len(context.args) != 2:
        await update.message.reply_text(
            "📊 <b>DCA Statistics</b>\n\n"
            "📋 <b>Usage:</b> <code>/dca stats &lt;dca_id&gt;</code>\n\n"
            "💡 <b>Example:</b> <code>/dca stats dca_1234567890</code>\n\n"
            "🔍 <b>Find DCA ID:</b> Use <code>/dca list</code>",
            parse_mode='HTML'
        )
        return
    
    dca_id = context.args[1]
    user_id = update.effective_user.id
    
    schedule = get_dca_schedule_by_id(dca_id, user_id)
    if not schedule:
        await update.message.reply_text(
            "❌ <b>DCA Schedule Not Found</b>\n\n"
            f"🔍 <b>DCA ID:</b> <code>{dca_id}</code>\n\n"
            "📋 <b>Possible Causes:</b>\n"
            "• Invalid DCA ID\n"
            "• DCA doesn't belong to you\n"
            "• DCA was deleted\n\n"
            "💡 <b>Solution:</b> Use <code>/dca list</code> to see valid IDs",
            parse_mode='HTML'
        )
        return
    
    # Get current market data
    from src.services.market_data_api import get_market_data
    market_data = get_market_data(schedule['symbol'])
    current_price_usd = market_data.get('current_price', 0) if market_data else 0
    
    # Currency conversion for DCA schedule currency
    conversion_rates = {
        'USD': 1.0,
        'EUR': 0.85,
        'JPY': 110.0,
        'IDR': 15000.0,  # Approximate IDR to USD rate
        'GBP': 0.75,
        'SGD': 1.35,
        'AUD': 1.45,
        'CAD': 1.25
    }
    conversion_rate = conversion_rates.get(schedule['currency'], 1.0)
    current_price = current_price_usd * conversion_rate
    
    currency_symbols = {
        'USD': '$', 'EUR': '€', 'JPY': '¥', 'IDR': 'Rp',
        'GBP': '£', 'SGD': 'S$', 'AUD': 'A$', 'CAD': 'C$'
    }
    currency_symbol = currency_symbols.get(schedule['currency'], schedule['currency'])
    
    total_invested = schedule.get('total_invested', 0)
    total_quantity = schedule.get('total_quantity', 0)
    execution_count = schedule.get('execution_count', 0)
    
    # Calculate performance metrics
    current_value = total_quantity * current_price if current_price > 0 else 0
    profit_loss = current_value - total_invested
    profit_loss_percent = (profit_loss / total_invested * 100) if total_invested > 0 else 0
    avg_price = total_invested / total_quantity if total_quantity > 0 else 0
    
    status_emoji = "🟢" if schedule['is_active'] else "🔴"
    status_text = "Active" if schedule['is_active'] else "Paused"
    
    pl_emoji = "📈" if profit_loss >= 0 else "📉"
    pl_color = "+" if profit_loss >= 0 else ""
    
    message = (
        f"📊 <b>DCA Performance Report</b>\n\n"
        f"🎯 <b>Schedule Info:</b>\n"
        f"🆔 DCA ID: <code>{schedule['dca_id']}</code>\n"
        f"🏷️ Asset: {schedule['symbol']}\n"
        f"💰 Amount: {currency_symbol}{schedule['amount']:,.2f} {schedule['currency']}\n"
        f"📅 Frequency: {schedule['frequency'].title()}\n"
        f"⏰ Time: {schedule['time']}\n"
        f"{status_emoji} Status: {status_text}\n\n"
        f"💎 <b>Investment Summary:</b>\n"
        f"🔄 Executions: {execution_count}x\n"
        f"💸 Total Invested: {currency_symbol}{total_invested:,.2f}\n"
        f"📦 Total Quantity: {total_quantity:,.6f} {schedule['symbol']}\n"
        f"⚖️ Avg Purchase Price: {currency_symbol}{avg_price:,.2f}\n\n"
        f"📈 <b>Current Performance:</b>\n"
        f"💰 Current Price: {currency_symbol}{current_price:,.2f}\n"
        f"💎 Current Value: {currency_symbol}{current_value:,.2f}\n"
        f"{pl_emoji} P&L: {pl_color}{currency_symbol}{profit_loss:,.2f} ({pl_color}{profit_loss_percent:,.2f}%)\n\n"
    )
    
    if execution_count > 0:
        last_executed = schedule.get('last_executed', 'Never')
        last_price_usd = schedule.get('last_execution_price', 0)
        last_price = last_price_usd * conversion_rate  # Convert to schedule currency
        last_quantity = schedule.get('last_quantity_purchased', 0)
        
        message += (
            f"📅 <b>Last Execution:</b>\n"
            f"🕐 Date: {last_executed[:19] if last_executed != 'Never' else 'Never'}\n"
            f"💰 Price: {currency_symbol}{last_price:,.2f} {schedule['currency']}\n"
            f"📦 Quantity: {last_quantity:,.6f} {schedule['symbol']}\n\n"
        )
    
    message += (
        f"🛠️ <b>Quick Actions:</b>\n"
        f"• <code>/dca pause {dca_id}</code> - Pause schedule\n"
        f"• <code>/dca resume {dca_id}</code> - Resume schedule\n"
        f"• <code>/dca delete {dca_id}</code> - Delete schedule\n\n"
        f"💡 <i>DCA helps reduce timing risk through regular investments!</i>"
    )
    
    await update.message.reply_text(message, parse_mode='HTML')

async def dca_summary_command(update: Update, context: CallbackContext):
    """Shows overall DCA summary for the user."""
    user_id = update.effective_user.id
    dca_schedules = get_user_dca_schedules(user_id)
    
    if not dca_schedules:
        await update.message.reply_text(
            "📊 <b>DCA Portfolio Summary</b>\n\n"
            "📈 <b>Status:</b> No DCA schedules found\n\n"
            "🚀 <b>Start DCA Investing:</b>\n"
            "• <code>/dca add BTC 50 USD daily 15:00</code>\n"
            "• <code>/dca add ETH 100 USD weekly 09:30</code>\n"
            "• <code>/dca add NVDA 200 USD monthly 10:00</code>\n\n"
            "💡 <b>DCA Benefits:</b>\n"
            "• Reduces market timing risk\n"
            "• Builds investment discipline\n"
            "• Averages out price volatility\n"
            "• Automates wealth building\n\n"
            "📈 <i>Start your DCA journey today!</i>",
            parse_mode='HTML'
        )
        return
    
    user_settings = get_user_settings(user_id)
    user_currency = user_settings.get('currency', 'USD')
    currency_symbols = {
        'USD': '$', 'EUR': '€', 'JPY': '¥', 'IDR': 'Rp',
        'GBP': '£', 'SGD': 'S$', 'AUD': 'A$', 'CAD': 'C$'
    }
    
    # Calculate totals
    total_schedules = len(dca_schedules)
    active_schedules = len([s for s in dca_schedules if s['is_active']])
    total_invested = sum(s.get('total_invested', 0) for s in dca_schedules)
    total_executions = sum(s.get('execution_count', 0) for s in dca_schedules)
    
    # Group by asset
    assets = {}
    for schedule in dca_schedules:
        symbol = schedule['symbol']
        if symbol not in assets:
            assets[symbol] = {
                'quantity': 0,
                'invested': 0,
                'schedules': 0,
                'active': 0
            }
        assets[symbol]['quantity'] += schedule.get('total_quantity', 0)
        assets[symbol]['invested'] += schedule.get('total_invested', 0)
        assets[symbol]['schedules'] += 1
        if schedule['is_active']:
            assets[symbol]['active'] += 1
    
    message = (
        f"📊 <b>DCA Portfolio Summary</b>\n\n"
        f"📈 <b>Overview:</b>\n"
        f"🎯 Total Schedules: {total_schedules}\n"
        f"🟢 Active: {active_schedules} • 🔴 Paused: {total_schedules - active_schedules}\n"
        f"💸 Total Invested: ${total_invested:,.2f}\n"
        f"🔄 Total Executions: {total_executions}\n\n"
        f"💎 <b>Assets Portfolio:</b>\n"
    )
    
    for symbol, data in assets.items():
        message += (
            f"• <b>{symbol}:</b> {data['quantity']:,.6f} units\n"
            f"  💰 Invested: ${data['invested']:,.2f}\n"
            f"  📅 Schedules: {data['active']}/{data['schedules']} active\n\n"
        )
    
    message += (
        f"🛠️ <b>Quick Actions:</b>\n"
        f"• <code>/dca list</code> - View all schedules\n"
        f"• <code>/dca add ...</code> - Create new schedule\n"
        f"• <code>/view_portfolio</code> - View complete portfolio\n\n"
        f"💡 <i>DCA is building your wealth automatically!</i>"
    )
    
    await update.message.reply_text(message, parse_mode='HTML')