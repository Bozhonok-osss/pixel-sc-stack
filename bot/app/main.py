import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.types.input_file import BufferedInputFile

from app.api import api
from app.config import settings
from app.keyboards import (
    admin_menu,
    add_staff_menu,
    branches_menu,
    confirm_menu,
    contact_menu,
    device_menu,
    issues_menu,
    main_menu,
    map_links,
)


def is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


def is_staff(user_id: int | None) -> bool:
    return bool(user_id and (user_id in settings.admin_ids or user_id in STAFF_IDS))


SUPPORT_TICKETS: dict[int, dict] = {}
SUPPORT_COUNTER = 0
STAFF_IDS = set(settings.support_staff_ids)


async def _refresh_staff_ids():
    global STAFF_IDS
    try:
        staff = await api.list_support_staff()
        STAFF_IDS = {int(s.get("telegram_id")) for s in staff if s.get("telegram_id")}
    except Exception:
        STAFF_IDS = set(settings.support_staff_ids)


def _support_ticket_kb(ticket_id: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Взять", callback_data=f"ticket:take:{ticket_id}")],
            [InlineKeyboardButton(text="💬 Ответить", callback_data=f"ticket:reply:{ticket_id}")],
            [InlineKeyboardButton(text="✅ Закрыть", callback_data=f"ticket:close:{ticket_id}")],
        ]
    )


BRANCHES_FALLBACK = [
    {
        "id": 1,
        "name": "Белореченская",
        "address": "ул. Белореченская, 28, 1 этаж, салон связи МОТИВ (ТЦ GOODMART)",
        "schedule": "09:00–21:00",
        "lat": 56.8168,
        "lon": 60.5625,
    },
    {
        "id": 2,
        "name": "Дирижабль",
        "address": "ТЦ «Дирижабль», 1 этаж, салон связи МОТИВ (ул. Академика Шварца, 17)",
        "schedule": "10:00–22:00",
        "lat": 56.7969,
        "lon": 60.6268,
    },
    {
        "id": 3,
        "name": "Титова",
        "address": "ул. Титова, 26, салон связи МОТИВ",
        "schedule": "09:00–20:00",
        "lat": 56.7798,
        "lon": 60.6096,
    },
]


def _parse_branch_index(text: str) -> int | None:
    text = (text or "").strip()
    if ")" in text:
        num = text.split(")", 1)[0]
        if num.isdigit():
            return int(num)
    return None


def _resolve_branch_by_text(text: str, branches: list[dict]) -> dict | None:
    """Resolve branch from user text (supports '1) Name' and name-only)."""
    idx = _parse_branch_index(text)
    if idx and 1 <= idx <= len(branches):
        return branches[idx - 1]
    name = (text or "").strip().lower()
    if not name:
        return None
    for branch in branches:
        bname = (branch.get("name") or "").strip().lower()
        if bname and (bname == name or name in bname):
            return branch
    return None


async def _load_branches() -> list[dict]:
    try:
        data = await api.list_branches_public()
        if isinstance(data, list) and data:
            # Fill missing coordinates from fallback by name.
            fallback_map = {b["name"].strip().lower(): b for b in BRANCHES_FALLBACK}
            for branch in data:
                if branch.get("lat") is not None and branch.get("lon") is not None:
                    continue
                name = (branch.get("name") or "").strip().lower()
                fb = fallback_map.get(name)
                if fb:
                    branch["lat"] = fb.get("lat")
                    branch["lon"] = fb.get("lon")
            return data
    except Exception:
        pass
    return BRANCHES_FALLBACK


async def _cleanup_user_message(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


async def _send_step(message: Message, state: FSMContext, text: str, reply_markup=None):
    data = await state.get_data()
    last_id = data.get("last_bot_message_id")
    if last_id:
        try:
            await message.bot.delete_message(message.chat.id, last_id)
        except Exception:
            pass
    sent = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(last_bot_message_id=sent.message_id)


class OrderStates(StatesGroup):
    device_type = State()
    model = State()
    issue = State()
    issue_custom = State()
    contact = State()
    manual_name = State()
    manual_phone = State()
    branch = State()
    confirm = State()


class AddressStates(StatesGroup):
    branch = State()


class SupportStates(StatesGroup):
    message = State()


class SupportStaffStates(StatesGroup):
    reply = State()
    add = State()
    add_id = State()


async def start(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "👋 Добро пожаловать в Pixel SC!\n\n"
        "🔧 Ремонтируем смартфоны, планшеты и ноутбуки\n"
        "⚡ Быстрая диагностика и честные сроки\n"
        "✅ Качественные запчасти и гарантия\n"
        "🧾 Прозрачные цены и квитанции\n\n"
        "Выберите действие в меню ниже."
    )
    await message.answer(text, reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))


async def new_order_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(OrderStates.device_type)
    await _send_step(message, state, "Выберите устройство:", reply_markup=device_menu())


async def device_selected(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Отмена":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))
        return
    if text == "⬅️ Назад":
        await start(message, state)
        return

    device_map = {"📱 Смартфон": "phone", "💻 Ноутбук": "laptop", "📟 Планшет": "tablet"}
    if text not in device_map:
        await _send_step(message, state, "Выберите устройство кнопкой ниже:", reply_markup=device_menu())
        await _cleanup_user_message(message)
        return

    await state.update_data(device_type=device_map[text])
    await state.set_state(OrderStates.model)
    await _send_step(message, state, "Введите модель устройства:", reply_markup=ReplyKeyboardRemove())
    await _cleanup_user_message(message)


async def model_entered(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await state.set_state(OrderStates.issue)
    data = await state.get_data()
    await _send_step(message, state, "Выберите тип поломки:", reply_markup=issues_menu(data["device_type"]))
    await _cleanup_user_message(message)


async def issue_selected(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Отмена":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))
        return
    if text == "⬅️ Назад":
        await state.set_state(OrderStates.model)
        await _send_step(message, state, "Введите модель устройства:", reply_markup=ReplyKeyboardRemove())
        await _cleanup_user_message(message)
        return

    if text == "Другая проблема":
        await state.set_state(OrderStates.issue_custom)
        await _send_step(message, state, "Опишите проблему:", reply_markup=ReplyKeyboardRemove())
        await _cleanup_user_message(message)
        return

    await state.update_data(problem_description=text)
    await state.set_state(OrderStates.contact)
    await _send_step(message, state, "Отправьте контакт или введите вручную:", reply_markup=contact_menu())
    await _cleanup_user_message(message)


async def issue_custom_entered(message: Message, state: FSMContext):
    await state.update_data(problem_description=message.text)
    await state.set_state(OrderStates.contact)
    await _send_step(message, state, "Отправьте контакт или введите вручную:", reply_markup=contact_menu())
    await _cleanup_user_message(message)


async def contact_choice(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if message.contact:
        await _set_contact_from_message(message, state)
        await _cleanup_user_message(message)
        return
    if text == "❌ Отмена":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))
        return
    if text == "⬅️ Назад":
        await state.set_state(OrderStates.issue)
        data = await state.get_data()
        await _send_step(message, state, "Выберите тип поломки:", reply_markup=issues_menu(data["device_type"]))
        await _cleanup_user_message(message)
        return

    if text == "✍️ Ввести вручную":
        await state.set_state(OrderStates.manual_name)
        await _send_step(message, state, "Введите ваше имя:", reply_markup=ReplyKeyboardRemove())
        await _cleanup_user_message(message)
        return

    await _cleanup_user_message(message)


async def _set_contact_from_message(message: Message, state: FSMContext):
    name = message.contact.first_name or "Клиент"
    phone = message.contact.phone_number or ""
    await state.update_data(client_name=name.strip() or "Клиент", client_phone=phone)
    branches = await _load_branches()
    await state.update_data(branches=branches)
    await state.set_state(OrderStates.branch)
    await _send_step(message, state, "Выберите филиал:", reply_markup=branches_menu(branches))


async def contact_shared(message: Message, state: FSMContext):
    await _set_contact_from_message(message, state)
    await _cleanup_user_message(message)


async def manual_name_entered(message: Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await state.set_state(OrderStates.manual_phone)
    await _send_step(message, state, "Введите номер телефона:", reply_markup=ReplyKeyboardRemove())
    await _cleanup_user_message(message)


async def manual_phone_entered(message: Message, state: FSMContext):
    await state.update_data(client_phone=message.text)
    branches = await _load_branches()
    await state.update_data(branches=branches)
    await state.set_state(OrderStates.branch)
    await _send_step(message, state, "Выберите филиал:", reply_markup=branches_menu(branches))
    await _cleanup_user_message(message)


async def branch_selected(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Отмена":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))
        return
    if text == "⬅️ Назад":
        await state.set_state(OrderStates.contact)
        await _send_step(message, state, "Отправьте контакт или введите вручную:", reply_markup=contact_menu())
        await _cleanup_user_message(message)
        return

    data = await state.get_data()
    branches = data.get("branches") or await _load_branches()
    branch = _resolve_branch_by_text(text, branches)
    if not branch:
        await _send_step(message, state, "Выберите филиал кнопкой ниже:", reply_markup=branches_menu(branches))
        await _cleanup_user_message(message)
        return
    await state.update_data(
        branch_id=branch.get("id"),
        branch_name=branch.get("name"),
        branch_address=branch.get("address"),
    )

    lat = branch.get("lat")
    lon = branch.get("lon")
    if lat is not None and lon is not None:
        await message.answer_location(latitude=lat, longitude=lon)
        await message.answer("Открыть на карте:", reply_markup=map_links(lat=lat, lon=lon))
    else:
        await message.answer("Открыть на карте:", reply_markup=map_links(address=branch.get("address", "") or ""))

    await send_confirmation(message, state)
    await _cleanup_user_message(message)


async def send_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    device_map = {"phone": "Смартфон", "laptop": "Ноутбук", "tablet": "Планшет"}
    text = (
        "Проверьте данные заявки:\n\n"
        f"Устройство: {device_map.get(data['device_type'], data['device_type'])}\n"
        f"Модель: {data['model']}\n"
        f"Проблема: {data['problem_description']}\n"
        f"Контакт: {data['client_name']} / {data['client_phone']}\n"
        f"Филиал: {data.get('branch_name', '')}\n"
        f"Адрес: {data.get('branch_address', '')}\n\n"
        "Подтверждаете?"
    )
    await state.set_state(OrderStates.confirm)
    await _send_step(message, state, text, reply_markup=confirm_menu())


async def confirm(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()

    if text == "✅ Подтвердить":
        payload = {
            "branch_id": data["branch_id"],
            "client_name": data["client_name"],
            "client_phone": data["client_phone"],
            "client_telegram": str(message.from_user.id),
            "device_type": {"phone": "Смартфон", "laptop": "Ноутбук", "tablet": "Планшет"}.get(
                data["device_type"], data["device_type"]
            ),
            "model": data.get("model"),
            "problem_description": data["problem_description"],
        }
        try:
            created = await api.create_order(payload)
            await state.clear()
            zammad_number = created.get("zammad_ticket_number")
            erp_issue = created.get("erpnext_issue")
            erp_line = f"\nERPNext issue: {erp_issue}" if erp_issue else ""
            z_line = f"\nZammad: {zammad_number}" if zammad_number else ""
            await message.answer(
                f"✅ Заявка создана! Номер: {created.get('number', '')}{z_line}{erp_line}",
                reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)),
            )
        except Exception as exc:
            await message.answer(f"Ошибка создания заявки: {exc}")
        return

    if text == "🔄 Исправить" or text == "⬅️ Назад":
        await state.set_state(OrderStates.branch)
        branches = data.get("branches") or await _load_branches()
        await _send_step(message, state, "Выберите филиал:", reply_markup=branches_menu(branches))
        await _cleanup_user_message(message)
        return

    if text == "❌ Отмена":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))
        return


async def show_status(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер заявки (например PIX-202602-0001):", reply_markup=ReplyKeyboardRemove())


async def status_number_entered(message: Message, state: FSMContext):
    number = (message.text or "").strip()
    try:
        order = await api.get_order(number)
        await message.answer(
            f"Статус заявки {order.get('number')}: {order.get('status')}\n"
            f"Филиал: {order.get('branch_id')}\n"
            f"Модель: {order.get('model')}\n",
            reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)),
        )
    except Exception as exc:
        await message.answer(f"Не найдено: {exc}")


async def my_orders(message: Message, state: FSMContext):
    await state.clear()
    try:
        orders = await api.list_orders({"client_telegram": str(message.from_user.id)})
        if not orders:
            await message.answer("У вас пока нет заявок.")
            return
        text = "\n\n".join(
            [f"{o.get('number')} — {o.get('status')}" for o in orders]
        )
        await message.answer(text)
    except Exception as exc:
        await message.answer(f"Ошибка: {exc}")


async def show_service_info(message: Message):
    company = {
        "name": settings.company_name,
        "inn": settings.company_inn,
        "ogrn": settings.company_ogrn,
        "address": settings.company_address,
        "phone": settings.company_phone,
    }
    try:
        company = await api.get_company_settings()
    except Exception:
        pass

    text = (
        "🏢 Pixel SC — сервисный центр по ремонту цифровой техники в Екатеринбурге.\n\n"
        "🔧 Мы ремонтируем: смартфоны, планшеты, ноутбуки\n"
        "⚡ Частые услуги: замена дисплеев, аккумуляторов, разъёмов, восстановление после влаги\n"
        "✅ Оригинальные и качественные запчасти\n"
        "🧾 Оформляем квитанцию и выдаём гарантию\n"
        "⏱ Среднее время диагностики — от 15 минут\n"
    )
    await message.answer(text, reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))


async def show_addresses(message: Message, state: FSMContext):
    branches = await _load_branches()
    await state.update_data(branches=branches)
    await state.set_state(AddressStates.branch)
    await message.answer("Выберите филиал, чтобы получить карту:", reply_markup=branches_menu(branches))


async def address_branch_selected(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Отмена":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))
        return

    data = await state.get_data()
    branches = data.get("branches") or await _load_branches()
    branch = _resolve_branch_by_text(text, branches)
    if not branch:
        await message.answer("Выберите филиал кнопкой ниже:", reply_markup=branches_menu(branches))
        return
    await message.answer(
        f"📍 {branch.get('name', '')}\n{branch.get('address', '')}\n⏰ {branch.get('schedule', '')}"
    )
    lat = branch.get("lat")
    lon = branch.get("lon")
    if lat is not None and lon is not None:
        await message.answer_location(latitude=lat, longitude=lon)
        await message.answer("Открыть на карте:", reply_markup=map_links(lat=lat, lon=lon))
    else:
        await message.answer("Открыть на карте:", reply_markup=map_links(address=branch.get("address", "") or ""))
    await state.clear()


async def support_start(message: Message, state: FSMContext):
    await state.set_state(SupportStates.message)
    await message.answer(
        f"Связь с поддержкой: {settings.support_phone}\n\n"
        "Напишите сообщение, мы передадим его сотруднику.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def support_message(message: Message, state: FSMContext):
    text = message.text or ""
    global SUPPORT_COUNTER
    SUPPORT_COUNTER += 1
    ticket_id = SUPPORT_COUNTER
    SUPPORT_TICKETS[ticket_id] = {
        "id": ticket_id,
        "user_id": message.from_user.id,
        "user_name": message.from_user.full_name or "",
        "text": text,
        "status": "open",
        "assignee_id": None,
    }
    notify_ids = set(settings.admin_ids) | set(STAFF_IDS)
    for admin_id in notify_ids:
        try:
            await message.bot.send_message(
                admin_id,
                f"🆘 Обращение #{ticket_id}\n"
                f"От: {message.from_user.full_name} (id {message.from_user.id})\n"
                f"Текст: {text}",
                reply_markup=_support_ticket_kb(ticket_id),
            )
        except Exception:
            pass
    await state.clear()
    await message.answer(
        f"Обращение #{ticket_id} отправлено. Мы скоро ответим.",
        reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)),
    )


async def support_ticket_action(call: CallbackQuery, state: FSMContext):
    data = (call.data or "").split(":")
    if len(data) != 3 or data[0] != "ticket":
        return
    if not is_staff(call.from_user.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return
    action = data[1]
    try:
        ticket_id = int(data[2])
    except ValueError:
        await call.answer("Неверный тикет", show_alert=True)
        return
    ticket = SUPPORT_TICKETS.get(ticket_id)
    if not ticket:
        await call.answer("Тикет не найден", show_alert=True)
        return

    if action == "take":
        if ticket["assignee_id"] and ticket["assignee_id"] != call.from_user.id:
            await call.answer("Тикет уже взят", show_alert=True)
            return
        ticket["assignee_id"] = call.from_user.id
        ticket["status"] = "in_progress"
        await call.answer("Вы взяли обращение")
        try:
            await call.message.edit_text(
                call.message.text + f"\n\nНазначен: {call.from_user.full_name} (id {call.from_user.id})",
                reply_markup=_support_ticket_kb(ticket_id),
            )
        except Exception:
            pass
        try:
            await call.bot.send_message(ticket["user_id"], f"Ваше обращение #{ticket_id} принято в работу.")
        except Exception:
            pass
        return

    if action == "reply":
        if ticket["assignee_id"] and ticket["assignee_id"] != call.from_user.id:
            await call.answer("Тикет уже у другого сотрудника", show_alert=True)
            return
        ticket["assignee_id"] = call.from_user.id
        await state.set_state(SupportStaffStates.reply)
        await state.update_data(ticket_id=ticket_id)
        await call.answer("Введите ответ")
        await call.message.answer("Введите сообщение клиенту:")
        return

    if action == "close":
        ticket["status"] = "closed"
        await call.answer("Обращение закрыто")
        try:
            await call.message.edit_text(
                call.message.text + "\n\nСтатус: закрыто",
                reply_markup=None,
            )
        except Exception:
            pass
        try:
            await call.bot.send_message(ticket["user_id"], f"Ваше обращение #{ticket_id} закрыто.")
        except Exception:
            pass
        return


async def support_staff_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    ticket = SUPPORT_TICKETS.get(ticket_id)
    if not ticket:
        await message.answer("Тикет не найден.")
        await state.clear()
        return
    if not is_staff(message.from_user.id):
        await message.answer("Недостаточно прав.")
        await state.clear()
        return

    reply_text = message.text or ""
    try:
        await message.bot.send_message(
            ticket["user_id"],
            f"Ответ по обращению #{ticket_id}:\n{reply_text}",
        )
    except Exception:
        pass
    await message.answer("Ответ отправлен.")
    await state.clear()


async def staff_tickets(message: Message, state: FSMContext):
    if not is_staff(message.from_user.id):
        return
    open_tickets = [t for t in SUPPORT_TICKETS.values() if t["status"] != "closed"]
    if not open_tickets:
        await message.answer("Активных обращений нет.")
        return
    await message.answer(f"Активных обращений: {len(open_tickets)}")
    for t in open_tickets:
        await message.answer(
            f"🆘 Обращение #{t['id']}\n"
            f"От: {t['user_name']} (id {t['user_id']})\n"
            f"Текст: {t['text']}\n"
            f"Статус: {t['status']}",
            reply_markup=_support_ticket_kb(t["id"]),
        )


async def add_staff_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(SupportStaffStates.add)
    await message.answer(
        "Отправьте контакт сотрудника или введите его Telegram ID:",
        reply_markup=add_staff_menu(),
    )


async def add_staff_contact(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer("Админ меню:", reply_markup=admin_menu())
        return
    text = (message.text or "").strip()
    if text.isdigit():
        try:
            await api.add_support_staff(int(text))
            await _refresh_staff_ids()
        except Exception:
            pass
        await state.clear()
        await message.answer(f"Сотрудник добавлен: {text}", reply_markup=admin_menu())
        return
    if message.forward_from and message.forward_from.id:
        try:
            await api.add_support_staff(message.forward_from.id, message.forward_from.full_name)
            await _refresh_staff_ids()
        except Exception:
            pass
        await state.clear()
        await message.answer(
            f"Сотрудник добавлен: {message.forward_from.id}",
            reply_markup=admin_menu(),
        )
        return
    if message.contact and message.contact.user_id:
        try:
            await api.add_support_staff(message.contact.user_id, message.contact.full_name)
            await _refresh_staff_ids()
        except Exception:
            pass
        try:
            await message.bot.send_message(
                message.contact.user_id,
                "Вы добавлены как сотрудник поддержки. Меню обновлено.",
                reply_markup=main_menu(False, True),
            )
        except Exception:
            pass
        await state.clear()
        await message.answer(
            f"Сотрудник добавлен: {message.contact.user_id}",
            reply_markup=admin_menu(),
        )
        return
    await state.set_state(SupportStaffStates.add_id)
    await message.answer("Не удалось определить ID. Введите Telegram ID числом:")


async def add_staff_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = (message.text or "").strip()
    if text == "⬅️ Назад":
        await state.clear()
        await message.answer("Админ меню:", reply_markup=admin_menu())
        return
    if not text.isdigit():
        await message.answer("ID должен быть числом. Попробуйте ещё раз:")
        return
    try:
        await api.add_support_staff(int(text))
        await _refresh_staff_ids()
    except Exception:
        pass
    try:
        await message.bot.send_message(
            int(text),
            "Вы добавлены как сотрудник поддержки. Меню обновлено.",
            reply_markup=main_menu(False, True),
        )
    except Exception:
        pass
    await state.clear()
    await message.answer(f"Сотрудник добавлен: {text}", reply_markup=admin_menu())


async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Админ меню:", reply_markup=admin_menu())


async def admin_back(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    current = await state.get_state()
    if current and current.startswith(SupportStaffStates.__name__):
        return
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu(is_admin(message.from_user.id), is_staff(message.from_user.id)))


async def admin_summary(message: Message, days: int):
    now = datetime.now(ZoneInfo(settings.timezone))
    date_to = now.replace(tzinfo=None, microsecond=0).isoformat()
    date_from = (now - timedelta(days=days)).replace(tzinfo=None, microsecond=0).isoformat()
    try:
        summary = await api.analytics_summary(date_from, date_to)
        await message.answer(
            f"Сводка за {days} дней:\n"
            f"Заявки: {summary.get('orders')}\n"
            f"Выручка: {summary.get('revenue')}\n"
            f"Затраты: {summary.get('costs')}\n"
            f"Прибыль: {summary.get('profit')}"
        )
    except Exception as exc:
        await message.answer(f"Ошибка сводки: {exc}")


async def admin_summary_today(message: Message):
    await admin_summary(message, 1)


async def admin_summary_7(message: Message):
    await admin_summary(message, 7)


async def admin_summary_30(message: Message):
    await admin_summary(message, 30)


async def admin_csv(message: Message):
    try:
        content = await api.export_csv()
        doc = BufferedInputFile(content, filename="orders.csv")
        await message.answer_document(doc, caption="Отчет CSV")
    except Exception as exc:
        await message.answer(f"Ошибка CSV: {exc}")


async def admin_xlsx(message: Message):
    try:
        content = await api.export_xlsx()
        doc = BufferedInputFile(content, filename="orders.xlsx")
        await message.answer_document(doc, caption="Отчет Excel")
    except Exception as exc:
        await message.answer(f"Ошибка Excel: {exc}")


async def main():
    await _refresh_staff_ids()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.message.register(start, F.text == "/start")

    dp.message.register(new_order_start, F.text == "📝 Новая заявка")
    dp.message.register(device_selected, OrderStates.device_type)
    dp.message.register(model_entered, OrderStates.model)
    dp.message.register(issue_selected, OrderStates.issue)
    dp.message.register(issue_custom_entered, OrderStates.issue_custom)
    dp.message.register(contact_shared, OrderStates.contact, F.contact)
    dp.message.register(contact_choice, OrderStates.contact)
    dp.message.register(manual_name_entered, OrderStates.manual_name)
    dp.message.register(manual_phone_entered, OrderStates.manual_phone)
    dp.message.register(branch_selected, OrderStates.branch)
    dp.message.register(confirm, OrderStates.confirm)

    dp.message.register(show_status, F.text == "📦 Статус заявки")
    dp.message.register(status_number_entered, F.text.regexp(r"^PIX-"))

    dp.message.register(my_orders, F.text == "📄 Мои заявки")
    dp.message.register(show_service_info, F.text == "🏢 О сервисе")
    dp.message.register(show_addresses, F.text == "📍 Адреса")
    dp.message.register(address_branch_selected, AddressStates.branch)
    dp.message.register(support_start, F.text == "🆘 Поддержка")
    dp.message.register(support_message, SupportStates.message)
    dp.message.register(staff_tickets, F.text == "🎧 Обращения")
    dp.message.register(support_staff_reply, SupportStaffStates.reply)
    dp.message.register(add_staff_start, F.text == "➕ Добавить сотрудника")
    dp.message.register(add_staff_contact, SupportStaffStates.add, F.contact)
    dp.message.register(add_staff_contact, SupportStaffStates.add)
    dp.message.register(add_staff_id, SupportStaffStates.add_id)
    dp.callback_query.register(support_ticket_action, F.data.startswith("ticket:"))

    dp.message.register(admin_panel, F.text == "🛠 Админ‑панель")
    dp.message.register(admin_summary_today, F.text == "📊 Сводка (сегодня)")
    dp.message.register(admin_summary_7, F.text == "📈 Сводка (7 дней)")
    dp.message.register(admin_summary_30, F.text == "📅 Сводка (30 дней)")
    dp.message.register(admin_csv, F.text == "⬇️ Скачать CSV")
    dp.message.register(admin_xlsx, F.text == "⬇️ Скачать Excel")
    dp.message.register(admin_back, F.text == "⬅️ Назад")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


