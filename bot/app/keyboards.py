from urllib.parse import quote_plus
import os

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


ENABLE_PREMIUM_ICONS = _env_bool("BUTTON_PREMIUM_EMOJI", default=False)


def _icon(env_name: str) -> str | None:
    if not ENABLE_PREMIUM_ICONS:
        return None
    value = (os.getenv(env_name) or "").strip()
    if value and value.isdigit():
        return value
    return None


def _kb(
    text: str,
    *,
    style: str | None = None,
    icon_custom_emoji_id: str | None = None,
    request_contact: bool = False,
) -> KeyboardButton:
    # Bot API 9.4 visual fields are optional; fallback keeps compatibility.
    kwargs = {"text": text, "request_contact": request_contact}
    if style:
        kwargs["style"] = style
    if icon_custom_emoji_id:
        kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
    try:
        return KeyboardButton(**kwargs)
    except Exception:
        return KeyboardButton(text=text, request_contact=request_contact)


def _ikb(
    text: str,
    *,
    url: str | None = None,
    callback_data: str | None = None,
    style: str | None = None,
    icon_custom_emoji_id: str | None = None,
) -> InlineKeyboardButton:
    # Bot API 9.4 visual fields are optional; fallback keeps compatibility.
    kwargs = {"text": text}
    if url is not None:
        kwargs["url"] = url
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if style:
        kwargs["style"] = style
    if icon_custom_emoji_id:
        kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
    try:
        return InlineKeyboardButton(**kwargs)
    except Exception:
        if url is not None:
            return InlineKeyboardButton(text=text, url=url)
        return InlineKeyboardButton(text=text, callback_data=callback_data or "")


def main_menu(is_admin: bool, is_staff: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [
            _kb(text="📝 Новая заявка", style="primary", icon_custom_emoji_id=_icon("ICON_NEW_ORDER")),
            _kb(text="📄 Мои заявки", style="primary", icon_custom_emoji_id=_icon("ICON_MY_ORDERS")),
        ],
        [
            _kb(text="📦 Статус заявки", style="primary", icon_custom_emoji_id=_icon("ICON_ORDER_STATUS")),
            _kb(text="📍 Адреса", style="primary", icon_custom_emoji_id=_icon("ICON_ADDRESSES")),
        ],
        [
            _kb(text="🏢 О сервисе", style="primary", icon_custom_emoji_id=_icon("ICON_ABOUT")),
            _kb(text="🆘 Поддержка", style="danger", icon_custom_emoji_id=_icon("ICON_SUPPORT")),
        ],
    ]
    if is_admin:
        buttons.append([_kb(text="🛠 Админ-панель", style="success", icon_custom_emoji_id=_icon("ICON_ADMIN"))])
    if is_staff and not is_admin:
        buttons.append([_kb(text="🎧 Обращения", style="success", icon_custom_emoji_id=_icon("ICON_TICKETS"))])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [
            _kb(text="📊 Сводка (сегодня)", style="primary", icon_custom_emoji_id=_icon("ICON_SUMMARY_TODAY")),
            _kb(text="📈 Сводка (7 дней)", style="primary", icon_custom_emoji_id=_icon("ICON_SUMMARY_WEEK")),
        ],
        [
            _kb(text="📅 Сводка (30 дней)", style="primary", icon_custom_emoji_id=_icon("ICON_SUMMARY_MONTH")),
            _kb(text="➕ Добавить сотрудника", style="success", icon_custom_emoji_id=_icon("ICON_ADD_STAFF")),
        ],
        [
            _kb(text="⬇️ Скачать CSV", style="success", icon_custom_emoji_id=_icon("ICON_EXPORT_CSV")),
            _kb(text="⬇️ Скачать Excel", style="success", icon_custom_emoji_id=_icon("ICON_EXPORT_XLSX")),
        ],
        [_kb(text="⬅️ Назад", style="danger", icon_custom_emoji_id=_icon("ICON_BACK"))],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def add_staff_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [_kb(text="⬅️ Назад", style="danger", icon_custom_emoji_id=_icon("ICON_BACK"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def device_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                _kb(text="📱 Смартфон", style="primary"),
                _kb(text="💻 Ноутбук", style="primary"),
            ],
            [
                _kb(text="📟 Планшет", style="primary"),
                _kb(text="❌ Отмена", style="danger", icon_custom_emoji_id=_icon("ICON_CANCEL")),
            ],
            [_kb(text="⬅️ Назад", style="danger", icon_custom_emoji_id=_icon("ICON_BACK"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def issues_menu(device: str) -> ReplyKeyboardMarkup:
    options = {
        "phone": [
            "Не включается",
            "Разбит экран",
            "Не заряжается",
            "Быстро разряжается",
            "Нет сети/связи",
            "Другая проблема",
        ],
        "laptop": [
            "Не включается",
            "Перегрев",
            "Не заряжается",
            "Медленно работает",
            "Разбит экран",
            "Другая проблема",
        ],
        "tablet": [
            "Не включается",
            "Разбит экран",
            "Не заряжается",
            "Быстро разряжается",
            "Нет Wi-Fi",
            "Другая проблема",
        ],
    }
    rows = []
    option_list = options[device]
    for idx in range(0, len(option_list), 2):
        pair = [_kb(text=option_list[idx], style="primary")]
        if idx + 1 < len(option_list):
            pair.append(_kb(text=option_list[idx + 1], style="primary"))
        rows.append(pair)
    rows.append([
        _kb(text="⬅️ Назад", style="danger", icon_custom_emoji_id=_icon("ICON_BACK")),
        _kb(text="❌ Отмена", style="danger", icon_custom_emoji_id=_icon("ICON_CANCEL")),
    ])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def contact_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [_kb(text="📞 Поделиться контактом", style="success", icon_custom_emoji_id=_icon("ICON_SHARE_CONTACT"), request_contact=True)],
            [_kb(text="✍️ Ввести вручную", style="primary", icon_custom_emoji_id=_icon("ICON_TYPE_MANUAL")), _kb(text="❌ Отмена", style="danger", icon_custom_emoji_id=_icon("ICON_CANCEL"))],
            [_kb(text="⬅️ Назад", style="danger", icon_custom_emoji_id=_icon("ICON_BACK"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def branches_menu(branches: list[dict]) -> ReplyKeyboardMarkup:
    rows = []
    branch_buttons = []
    for idx, branch in enumerate(branches, start=1):
        name = branch.get("name", "")
        address = branch.get("address", "")
        label = f"{name} - {address}" if address else name
        branch_buttons.append(_kb(text=f"{idx}) {label}", style="primary"))
    for i in range(0, len(branch_buttons), 2):
        row = [branch_buttons[i]]
        if i + 1 < len(branch_buttons):
            row.append(branch_buttons[i + 1])
        rows.append(row)
    rows.append([
        _kb(text="⬅️ Назад", style="danger", icon_custom_emoji_id=_icon("ICON_BACK")),
        _kb(text="❌ Отмена", style="danger", icon_custom_emoji_id=_icon("ICON_CANCEL")),
    ])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def confirm_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [_kb(text="✅ Подтвердить", style="success", icon_custom_emoji_id=_icon("ICON_CONFIRM")), _kb(text="🔄 Исправить", style="primary", icon_custom_emoji_id=_icon("ICON_EDIT"))],
            [_kb(text="⬅️ Назад", style="danger", icon_custom_emoji_id=_icon("ICON_BACK")), _kb(text="❌ Отмена", style="danger", icon_custom_emoji_id=_icon("ICON_CANCEL"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def map_links(lat: float | None = None, lon: float | None = None, address: str | None = None) -> InlineKeyboardMarkup:
    if lat is not None and lon is not None:
        two_gis = f"https://2gis.ru/ekaterinburg?m={lon},{lat}/17"
        yandex = f"https://yandex.ru/maps/?pt={lon},{lat}&z=17&l=map"
        google = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    else:
        q = quote_plus(address or "")
        two_gis = f"https://2gis.ru/ekaterinburg/search/{q}"
        yandex = f"https://yandex.ru/maps/?text={q}"
        google = f"https://www.google.com/maps/search/?api=1&query={q}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _ikb(text="🗺 2ГИС", url=two_gis, style="primary", icon_custom_emoji_id=_icon("ICON_MAP_2GIS")),
                _ikb(text="🧭 Яндекс", url=yandex, style="success", icon_custom_emoji_id=_icon("ICON_MAP_YANDEX")),
            ],
            [_ikb(text="🌍 Google Maps", url=google, style="primary", icon_custom_emoji_id=_icon("ICON_MAP_GOOGLE"))],
        ]
    )
