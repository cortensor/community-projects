# src/event_listener.py
import asyncio
import logging
from telegram import Bot
from .response_filters import post_process_response
from . import config
from .telegram_bot import resolve_chat_id_from_reference
# You must import the specific library for listening to Cortensor events
# from some_cortensor_event_library import EventListener

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Telegram Bot Instance ---
# We create a new bot instance here just for sending messages
telegram_sender = Bot(token=config.TELEGRAM_BOT_TOKEN)

# --- Event Handler ---
async def handle_cortensor_event(event):
    """
    Processes a received event and sends the result back to the user on Telegram.
    """
    try:
        # NOTE: The structure of 'event' is hypothetical.
        # You must adapt this to the actual event structure from Cortensor.
        task_result = event['data']['resultText']
        client_reference = event['data']['clientReference']
        chat_id = resolve_chat_id_from_reference(client_reference) or client_reference

        if not task_result or not chat_id:
            logger.warning(f"Received event with missing data: {event}")
            return
            
        logger.info(f"Result received for chat_reference {client_reference}. Sending message.")

        if not isinstance(chat_id, int):
            try:
                chat_id = int(chat_id)
            except (TypeError, ValueError):
                logger.error("Cannot resolve chat_id for client_reference %s", client_reference)
                return

        # Send the final result to the user (filtered & concise)
        filtered = post_process_response("", task_result, brief_default=True)
        await telegram_sender.send_message(chat_id=chat_id, text=filtered)

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error parsing event data: {e}. Event: {event}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in handle_cortensor_event: {e}", exc_info=True)


# --- Main Listener Function ---
async def main():
    """
    Connects to the Cortensor event stream and listens for new task results.
    """
    logger.info("Starting Cortensor event listener...")
    
    # This is where you would implement the connection logic.
    # It requires documentation from Cortensor on how to subscribe to events.
    # Example using a hypothetical library:
    #
    # listener = EventListener(endpoint="wss://your-cortensor-node/events")
    # await listener.subscribe("TaskResultEvent", handle_cortensor_event)
    # await listener.start()
    
    # Placeholder loop since the actual library is unknown
    logger.warning("Event listener is running in placeholder mode.")
    logger.warning("You must implement the actual connection to the Cortensor event stream.")
    while True:
        await asyncio.sleep(60)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Event listener stopped by user.")
