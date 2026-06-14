# Module quản lý ngôn ngữ (Language Management Module)
# Hỗ trợ: 'vi' (Tiếng Việt), 'en' (English)

_CURRENT = {"lang": "vi"}


def get_texts() -> dict:
    """Trả về từ điển text theo ngôn ngữ hiện tại."""
    if _CURRENT["lang"] == "vi":
        from src.lang.vi import TEXTS
    else:
        from src.lang.en import TEXTS
    return TEXTS


def set_language(lang_code: str):
    """Chuyển đổi ngôn ngữ. Hỗ trợ: 'vi', 'en'."""
    if lang_code in ("vi", "en"):
        _CURRENT["lang"] = lang_code


def current_lang() -> str:
    """Trả về mã ngôn ngữ hiện tại."""
    return _CURRENT["lang"]
