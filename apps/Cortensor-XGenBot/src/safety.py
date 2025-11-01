from better_profanity import profanity

profanity.load_censor_words()

def sanitize(text: str) -> str:
    return profanity.censor(text or '')
