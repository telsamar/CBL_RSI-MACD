# utils.py
import re

def escape_markdown(text: str) -> str:
    """
    Экранирует символы, используемые в MarkdownV2.

    :param text: Текст для экранирования.
    :return: Экранированный текст.
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
