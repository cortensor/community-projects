"""
Configuration validators for XGenBot.
Validates .env settings on startup to catch misconfigurations early.
"""
import os
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


def validate_required_env(name: str, value: Optional[str]) -> Tuple[bool, str]:
    """Validate that a required environment variable is set"""
    if not value or not value.strip():
        return False, f"Required config '{name}' is missing or empty"
    return True, ""


def validate_positive_int(name: str, value: str, min_val: int = 1, max_val: int = None) -> Tuple[bool, str]:
    """Validate that a value is a positive integer within range"""
    try:
        v = int(value)
        if v < min_val:
            return False, f"Config '{name}' must be >= {min_val}, got {v}"
        if max_val and v > max_val:
            return False, f"Config '{name}' must be <= {max_val}, got {v}"
        return True, ""
    except (ValueError, TypeError):
        return False, f"Config '{name}' must be a valid integer, got '{value}'"


def validate_positive_float(name: str, value: str, min_val: float = 0.0) -> Tuple[bool, str]:
    """Validate that a value is a positive float"""
    try:
        v = float(value)
        if v < min_val:
            return False, f"Config '{name}' must be >= {min_val}, got {v}"
        return True, ""
    except (ValueError, TypeError):
        return False, f"Config '{name}' must be a valid number, got '{value}'"


def validate_url(name: str, value: str) -> Tuple[bool, str]:
    """Validate that a value looks like a URL"""
    if not value:
        return False, f"Config '{name}' is missing"
    if not (value.startswith('http://') or value.startswith('https://')):
        return False, f"Config '{name}' must be a valid HTTP(S) URL, got '{value}'"
    return True, ""


def validate_comma_list(name: str, value: str, min_items: int = 1) -> Tuple[bool, str]:
    """Validate that a value is a non-empty comma-separated list"""
    if not value:
        return False, f"Config '{name}' is missing"
    items = [x.strip() for x in value.split(',') if x.strip()]
    if len(items) < min_items:
        return False, f"Config '{name}' must have at least {min_items} items"
    return True, ""


def validate_choice(name: str, value: str, choices: List[str]) -> Tuple[bool, str]:
    """Validate that a value is one of allowed choices"""
    if not value:
        return False, f"Config '{name}' is missing"
    if value.lower() not in [c.lower() for c in choices]:
        return False, f"Config '{name}' must be one of {choices}, got '{value}'"
    return True, ""


def validate_all_configs() -> List[str]:
    """
    Validate all configuration settings.
    Returns list of error messages (empty if all valid).
    """
    errors = []
    
    # Required configs
    required = [
        ('TELEGRAM_BOT_TOKEN', os.getenv('TELEGRAM_BOT_TOKEN')),
        ('CORTENSOR_API_URL', os.getenv('CORTENSOR_API_URL')),
        ('CORTENSOR_API_KEY', os.getenv('CORTENSOR_API_KEY')),
        ('CORTENSOR_SESSION_ID', os.getenv('CORTENSOR_SESSION_ID')),
    ]
    
    for name, value in required:
        ok, msg = validate_required_env(name, value)
        if not ok:
            errors.append(msg)
    
    # URL validation
    api_url = os.getenv('CORTENSOR_API_URL', '')
    if api_url:
        ok, msg = validate_url('CORTENSOR_API_URL', api_url)
        if not ok:
            errors.append(msg)
    
    # Integer validations
    int_configs = [
        ('CORTENSOR_TIMEOUT', os.getenv('CORTENSOR_TIMEOUT', '45'), 1, 600),
        ('TWEET_CHAR_LIMIT', os.getenv('TWEET_CHAR_LIMIT', '280'), 100, 10000),
        ('PREVIEW_CHAR_LIMIT', os.getenv('PREVIEW_CHAR_LIMIT', '3900'), 500, 10000),
        ('THREAD_CONTINUE_BATCH', os.getenv('THREAD_CONTINUE_BATCH', '3'), 1, 25),
        ('DEFAULT_THREAD_N', os.getenv('DEFAULT_THREAD_N', '6'), 2, 25),
        ('MIN_THREAD_POSTS', os.getenv('MIN_THREAD_POSTS', '2'), 1, 10),
        ('MAX_THREAD_POSTS', os.getenv('MAX_THREAD_POSTS', '25'), 5, 100),
        ('LENGTH_SHORT_CHARS', os.getenv('LENGTH_SHORT_CHARS', '140'), 50, 500),
        ('LENGTH_MEDIUM_CHARS', os.getenv('LENGTH_MEDIUM_CHARS', '200'), 100, 1000),
        ('LENGTH_LONG_CHARS', os.getenv('LENGTH_LONG_CHARS', '240'), 100, 1500),
    ]
    
    for name, value, min_v, max_v in int_configs:
        ok, msg = validate_positive_int(name, value, min_v, max_v)
        if not ok:
            errors.append(msg)
    
    # Float validations
    float_configs = [
        ('TWITTER_FETCH_TIMEOUT', os.getenv('TWITTER_FETCH_TIMEOUT', '6.0'), 1.0),
    ]
    
    for name, value, min_v in float_configs:
        ok, msg = validate_positive_float(name, value, min_v)
        if not ok:
            errors.append(msg)
    
    # Choice validations
    prompt_type = os.getenv('PROMPT_TYPE', '0')
    ok, msg = validate_choice('PROMPT_TYPE', prompt_type, ['0', '1'])
    if not ok:
        errors.append(msg)
    
    default_length = os.getenv('DEFAULT_LENGTH', 'medium')
    ok, msg = validate_choice('DEFAULT_LENGTH', default_length, ['short', 'medium', 'long', 'auto'])
    if not ok:
        errors.append(msg)
    
    thread_enum = os.getenv('THREAD_ENUM_FORMAT', 'fraction')
    ok, msg = validate_choice('THREAD_ENUM_FORMAT', thread_enum, ['none', 'ofx', 'fraction'])
    if not ok:
        errors.append(msg)
    
    # List validations
    tones = os.getenv('AVAILABLE_TONES', 'concise,informative')
    ok, msg = validate_comma_list('AVAILABLE_TONES', tones, 1)
    if not ok:
        errors.append(msg)
    
    char_presets = os.getenv('CHAR_LIMIT_PRESETS', '280,400,600')
    ok, msg = validate_comma_list('CHAR_LIMIT_PRESETS', char_presets, 1)
    if not ok:
        errors.append(msg)
    
    # Logical validations
    min_posts = int(os.getenv('MIN_THREAD_POSTS', '2'))
    max_posts = int(os.getenv('MAX_THREAD_POSTS', '25'))
    default_n = int(os.getenv('DEFAULT_THREAD_N', '6'))
    
    if min_posts > max_posts:
        errors.append(f"MIN_THREAD_POSTS ({min_posts}) cannot be greater than MAX_THREAD_POSTS ({max_posts})")
    
    if not (min_posts <= default_n <= max_posts):
        errors.append(f"DEFAULT_THREAD_N ({default_n}) must be between MIN ({min_posts}) and MAX ({max_posts})")
    
    return errors


def run_startup_validation(strict: bool = False) -> bool:
    """
    Run config validation on startup.
    
    Args:
        strict: If True, raise exception on errors. If False, log warnings.
    
    Returns:
        True if all validations passed, False otherwise.
    """
    logger.info("Running configuration validation...")
    errors = validate_all_configs()
    
    if not errors:
        logger.info("✅ All configuration validations passed")
        return True
    
    for err in errors:
        if strict:
            logger.error(f"❌ Config error: {err}")
        else:
            logger.warning(f"⚠️ Config warning: {err}")
    
    if strict:
        raise ConfigValidationError(f"Configuration validation failed with {len(errors)} error(s)")
    
    logger.warning(f"⚠️ {len(errors)} configuration warning(s) found. Bot may not work correctly.")
    return False
