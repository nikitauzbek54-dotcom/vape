import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import (
    main_menu, catalog_menu, products_menu, product_menu, cart_menu,
    delivery_menu, metro_menu, confirm_order_menu, skip_phone_menu,
    skip_comment_menu, my_orders_menu, back_to_main_menu,
    CATEGORIES, STATUSES,
)

router = Router()


class OrderFSM(StatesGroup):
    waiting_phone = State()
    waiting_comment = State()


def product_caption(p):
    lines = [f"<b>{p['name']}</b>", ""]
    if p["description"]:
        lines.append(p["description"])
        lines.append("")
    lines.append(f"💰 Цена: <b>{p['price']}₽</b>")
    if p["stock"] > 0:
        lines.append(f"📦 В наличии: {p['stock']} шт")
    else:
        lines.append("🔴 Нет в наличии")
    if p["strength"]:
        lines.append(f"⚡ Крепость: {p['strength']}")
    if p["flavor"]:
        lines.append(f"🍓 Вкус: {p['flavor']}")
    return "\n".join(lines)


@router.message(CommandStart())
async def cmd_start(message: Message, db):
    user = await db.get_user(message.from_user.id)
    text = (
        f"👋 Добро пожаловать в <b>Ondetlin shop</b>!\n\n"
        "🛍 Одноразки, жидкости, поды и расходники.\n"
        "🚚 Доставка курьером или самовывоз."
    )
    banner = await db.get_setting("banner")
    if banner:
        try:
            await message.answer_photo(banner, caption=text, reply_markup=main_menu())
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=main_menu())


@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, db):
    count = await db.cart_count(call.from_user.id)
    text = "🏠 <b>Главное меню</b>"
    try:
        await call.message.edit_text(text, reply_markup=main_menu())
    except Exception:
        await call.message.answer(text, reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "catalog")
async def show_catalog(call: CallbackQuery):
    try:
        await call.message.edit_text("🛍 <b>Выбери категорию:</b>", reply_markup=catalog_menu())
    except Exception:
        await call.message.answer("🛍 <b>Выбери категорию:</b>", reply_markup=catalog_menu())
    await call.answer()


@router.callback_query(F.data.startswith("cat_"))
async def show_category(call: CallbackQuery, db):
    cat = call.data.replace("cat_", "")
    products = await db.get_products_by_category(cat)
    if not products:
        try:
            await call.message.edit_text(
                f"{CATEGORIES[cat]}\n\nПока пусто 😔",
                reply_markup=catalog_menu()
            )
        except Exception:
            await call.message.answer(
                f"{CATEGORIES[cat]}\n\nПока пусто 😔",
                reply_markup=catalog_menu()
            )
    else:
        try:
            await call.message.edit_text(
                f"{CATEGORIES[cat]}\n\nВыбери товар:",
                reply_markup=products_menu(cat, products)
            )
        except Exception:
            await call.message.answer(
                f"{CATEGORIES[cat]}\n\nВыбери товар:",
                reply_markup=products_menu(cat, products)
            )
    await call.answer()


@router.callback_query(F.data.startswith("prod_"))
async def show_product(call: CallbackQuery, db):
    product_id = int(call.data.replace("prod_", ""))
    p = await db.get_product(product_id)
    if not p:
        await call.answer("Товар не найден", show_alert=True)
        return
    photos = json.loads(p["photos"]) if p["photos"] else []
    caption = product_caption(p)
    kb = product_menu(product_id) if p["stock"] > 0 else back_to_main_menu()
    try:
        if photos:
            await call.message.answer_photo(photos[0], caption=caption, reply_markup=kb)
        else:
            await call.message.answer(caption, reply_markup=kb)
    except Exception:
        await call.message.answer(caption, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("add_"))
async def add_to_cart(call: CallbackQuery, db):
    product_id = int(call.data.replace("add_", ""))
    p = await db.get_product(product_id)
    if not p or p["stock"] <= 0:
        await call.answer("Нет в наличии", show_alert=True)
        return
    await db.add_to_cart(call.from_user.id, product_id)
    await call.answer("✅ Добавлено в корзину")


@router.callback_query(F.data == "cart")
async def show_cart(call: CallbackQuery, db):
    items = await db.get_cart(call.from_user.id)
    if not items:
        text = "🧺 <b>Корзина пуста</b>"
    else:
        total = sum(i["price"] * i["quantity"] for i in items)
        text = f"🧺 <b>Корзина</b>\n\nИтого: <b>{total}₽</b>"
    try:
        await call.message.edit_text(text, reply_markup=cart_menu(items))
    except Exception:
        await call.message.answer(text, reply_markup=cart_menu(items))
    await call.answer()


@router.callback_query(F.data.startswith("qty_"))
async def cart_qty(call: CallbackQuery, db):
    _, cart_id, delta = call.data.split("_")
    await db.update_cart_qty(int(cart_id), int(delta))
    items = await db.get_cart(call.from_user.id)
    total = sum(i["price"] * i["quantity"] for i in items)
    text = f"🧺 <b>Корзина</b>\n\nИтого: <b>{total}₽</b>" if items else "🧺 <b>Корзина пуста</b>"
    try:
        await call.message.edit_text(text, reply_markup=cart_menu(items))
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("rm_"))
async def cart_remove(call: CallbackQuery, db):
    cart_id = int(call.data.replace("rm_", ""))
    await db.remove_from_cart(cart_id)
    items = await db.get_cart(call.from_user.id)
    total = sum(i["price"] * i["quantity"] for i in items)
    text = f"🧺 <b>Корзина</b>\n\nИтого: <b>{total}₽</b>" if items else "🧺 <b>Корзина пуста</b>"
    try:
        await call.message.edit_text(text, reply_markup=cart_menu(items))
    except Exception:
        pass
    await call.answer("Удалено")


@router.callback_query(F.data == "clear_cart")
async def cart_clear(call: CallbackQuery, db):
    await db.clear_cart(call.from_user.id)
    try:
        await call.message.edit_text("🧺 <b>Корзина пуста</b>", reply_markup=cart_menu([]))
    except Exception:
        pass
    await call.answer("Очищено")


@router.callback_query(F.data == "checkout")
async def start_checkout(call: CallbackQuery, db, state: FSMContext):
    items = await db.get_cart(call.from_user.id)
    if not items:
        await call.answer("Корзина пуста", show_alert=True)
        return
    await state.update_data(delivery=None, metro=None, phone=None, comment=None)
    try:
        await call.message.edit_text(
            "🚚 <b>Как получить заказ?</b>", reply_markup=delivery_menu()
        )
    except Exception:
        await call.message.answer(
            "🚚 <b>Как получить заказ?</b>", reply_markup=delivery_menu()
        )
    await call.answer()


@router.callback_query(F.data == "delivery_pickup")
async def choose_pickup(call: CallbackQuery, db, state: FSMContext):
    address = await db.get_setting("pickup_address", "Уточните у менеджера")
    await state.update_data(delivery="pickup")
    await state.update_data(metro=None)
    # Сразу к телефону
    user = await db.get_user(call.from_user.id)
    if user and user["phone"]:
        await state.update_data(phone=user["phone"])
        await state.set_state(OrderFSM.waiting_comment)
        try:
            await call.message.edit_text(
                f"🏠 Самовывоз: <b>{address}</b>\n\n"
                "💬 Напиши комментарий к заказу или нажми «Пропустить»:",
                reply_markup=skip_comment_menu()
            )
        except Exception:
            await call.message.answer(
                f"🏠 Самовывоз: <b>{address}</b>\n\n"
                "💬 Напиши комментарий к заказу или нажми «Пропустить»:",
                reply_markup=skip_comment_menu()
            )
    else:
        await state.set_state(OrderFSM.waiting_phone)
        try:
            await call.message.edit_text(
                f"🏠 Самовывоз: <b>{address}</b>\n\n"
                "📱 Отправь номер телефона или нажми «Пропустить»:",
                reply_markup=skip_phone_menu()
            )
        except Exception:
            await call.message.answer(
                f"🏠 Самовывоз: <b>{address}</b>\n\n"
                "📱 Отправь номер телефона или нажми «Пропустить»:",
                reply_markup=skip_phone_menu()
            )
    await call.answer()


@router.callback_query(F.data == "delivery_courier")
async def choose_courier(call: CallbackQuery, state: FSMContext):
    await state.update_data(delivery="courier")
    try:
        await call.message.edit_text(
            "📍 <b>Выбери станцию метро:</b>", reply_markup=metro_menu()
        )
    except Exception:
        await call.message.answer(
            "📍 <b>Выбери станцию метро:</b>", reply_markup=metro_menu()
        )
    await call.answer()


@router.callback_query(F.data.startswith("metro_"))
async def choose_metro(call: CallbackQuery, db, state: FSMContext):
    metro = call.data.replace("metro_", "")
    await state.update_data(metro=metro)
    user = await db.get_user(call.from_user.id)
    if user and user["phone"]:
        await state.update_data(phone=user["phone"])
        await state.set_state(OrderFSM.waiting_comment)
        try:
            await call.message.edit_text(
                f"📍 Метро: <b>{metro}</b>\n\n"
                "💬 Напиши комментарий к заказу или нажми «Пропустить»:",
                reply_markup=skip_comment_menu()
            )
        except Exception:
            await call.message.answer(
                f"📍 Метро: <b>{metro}</b>\n\n"
                "💬 Напиши комментарий к заказу или нажми «Пропустить»:",
                reply_markup=skip_comment_menu()
            )
    else:
        await state.set_state(OrderFSM.waiting_phone)
        try:
            await call.message.edit_text(
                f"📍 Метро: <b>{metro}</b>\n\n"
                "📱 Отправь номер телефона или нажми «Пропустить»:",
                reply_markup=skip_phone_menu()
            )
        except Exception:
            await call.message.answer(
                f"📍 Метро: <b>{metro}</b>\n\n"
                "📱 Отправь номер телефона или нажми «Пропустить»:",
                reply_markup=skip_phone_menu()
            )
    await call.answer()


@router.callback_query(F.data == "skip_phone")
async def skip_phone(call: CallbackQuery, state: FSMContext):
    await state.update_data(phone=None)
    await state.set_state(OrderFSM.waiting_comment)
    try:
        await call.message.edit_text(
            "💬 Напиши комментарий к заказу или нажми «Пропустить»:",
            reply_markup=skip_comment_menu()
        )
    except Exception:
        await call.message.answer(
            "💬 Напиши комментарий к заказу или нажми «Пропустить»:",
            reply_markup=skip_comment_menu()
        )
    await call.answer()


@router.message(OrderFSM.waiting_phone)
async def got_phone(message: Message, state: FSMContext, db):
    phone = message.text.strip()
    await db.update_user_phone(message.from_user.id, phone)
    await state.update_data(phone=phone)
    await state.set_state(OrderFSM.waiting_comment)
    await message.answer(
        "💬 Напиши комментарий к заказу или нажми «Пропустить»:",
        reply_markup=skip_comment_menu()
    )


@router.callback_query(F.data == "skip_comment")
async def skip_comment(call: CallbackQuery, state: FSMContext, db):
    await state.update_data(comment=None)
    await show_confirm(call, state, db)
    await call.answer()


@router.message(OrderFSM.waiting_comment)
async def got_comment(message: Message, state: FSMContext, db):
    await state.update_data(comment=message.text.strip())
    # Показываем подтверждение
    data = await state.get_data()
    items = await db.get_cart(message.from_user.id)
    total = sum(i["price"] * i["quantity"] for i in items)
    lines = ["📋 <b>Подтверди заказ:</b>", ""]
    for i in items:
        lines.append(f"• {i['name']} × {i['quantity']} = {i['price'] * i['quantity']}₽")
    lines.append("")
    lines.append(f"💰 Итого: <b>{total}₽</b>")
    lines.append(f"🚚 Способ: {'Курьер' if data['delivery'] == 'courier' else 'Самовывоз'}")
    if data.get("metro"):
        lines.append(f"📍 Метро: {data['metro']}")
    if data.get("phone"):
        lines.append(f"📱 Телефон: {data['phone']}")
    if data.get("comment"):
        lines.append(f"💬 Комментарий: {data['comment']}")
    lines.append("")
    lines.append("💵 Оплата при встрече.")
    await message.answer("\n".join(lines), reply_markup=confirm_order_menu())


async def show_confirm(call: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    items = await db.get_cart(call.from_user.id)
    total = sum(i["price"] * i["quantity"] for i in items)
    lines = ["📋 <b>Подтверди заказ:</b>", ""]
    for i in items:
        lines.append(f"• {i['name']} × {i['quantity']} = {i['price'] * i['quantity']}₽")
    lines.append("")
    lines.append(f"💰 Итого: <b>{total}₽</b>")
    lines.append(f"🚚 Способ: {'Курьер' if data['delivery'] == 'courier' else 'Самовывоз'}")
    if data.get("metro"):
        lines.append(f"📍 Метро: {data['metro']}")
    if data.get("phone"):
        lines.append(f"📱 Телефон: {data['phone']}")
    if data.get("comment"):
        lines.append(f"💬 Комментарий: {data['comment']}")
    lines.append("")
    lines.append("💵 Оплата при встрече.")
    try:
        await call.message.edit_text("\n".join(lines), reply_markup=confirm_order_menu())
    except Exception:
        await call.message.answer("\n".join(lines), reply_markup=confirm_order_menu())


@router.callback_query(F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext, db, bot, admin_ids):
    data = await state.get_data()
    items = await db.get_cart(call.from_user.id)
    if not items:
        await call.answer("Корзина пуста", show_alert=True)
        return
    total = sum(i["price"] * i["quantity"] for i in items)
    user = await db.get_user(call.from_user.id)
    name = user["name"] if user and user["name"] else call.from_user.full_name

    order_id = await db.create_order(
        call.from_user.id, name, data.get("phone"),
        data.get("delivery"), data.get("metro"),
        data.get("comment"), total
    )
    for i in items:
        await db.add_order_item(order_id, i["id"], i["name"], i["price"], i["quantity"])
        await db.decrease_stock(i["id"], i["quantity"])
    await db.clear_cart(call.from_user.id)
    await state.clear()

    try:
        await call.message.edit_text(
            f"✅ <b>Заказ #{order_id} оформлен!</b>\n\n"
            f"💰 Сумма: <b>{total}₽</b>\n"
            "💵 Оплата при встрече.\n\n"
            "Мы свяжемся с тобой для подтверждения.",
            reply_markup=back_to_main_menu()
        )
    except Exception:
        await call.message.answer(
            f"✅ <b>Заказ #{order_id} оформлен!</b>\n\n"
            f"💰 Сумма: <b>{total}₽</b>\n"
            "💵 Оплата при встрече.",
            reply_markup=back_to_main_menu()
        )

    # Уведомление админам
    lines = [f"🔔 <b>Новый заказ #{order_id}</b>", ""]
    lines.append(f"👤 {name}")
    if data.get("phone"):
        lines.append(f"📱 {data['phone']}")
    lines.append(f"🚚 {'Курьер' if data.get('delivery') == 'courier' else 'Самовывоз'}")
    if data.get("metro"):
        lines.append(f"📍 {data['metro']}")
    if data.get("comment"):
        lines.append(f"💬 {data['comment']}")
    lines.append("")
    for i in items:
        lines.append(f"• {i['name']} × {i['quantity']} = {i['price'] * i['quantity']}₽")
    lines.append("")
    lines.append(f"💰 Итого: <b>{total}₽</b>")
    lines.append(f"👤 Юзер: <code>{call.from_user.id}</code>")
    notify_text = "\n".join(lines)
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, notify_text)
        except Exception:
            pass
    await call.answer()


@router.callback_query(F.data == "my_orders")
async def my_orders(call: CallbackQuery, db):
    orders = await db.get_user_orders(call.from_user.id)
    if not orders:
        text = "📦 <b>У тебя пока нет заказов</b>"
        try:
            await call.message.edit_text(text, reply_markup=back_to_main_menu())
        except Exception:
            await call.message.answer(text, reply_markup=back_to_main_menu())
    else:
        try:
            await call.message.edit_text(
                "📦 <b>Твои заказы:</b>", reply_markup=my_orders_menu(orders)
            )
        except Exception:
            await call.message.answer(
                "📦 <b>Твои заказы:</b>", reply_markup=my_orders_menu(orders)
            )
    await call.answer()


@router.callback_query(F.data.startswith("order_"))
async def show_order(call: CallbackQuery, db):
    order_id = int(call.data.replace("order_", ""))
    o = await db.get_order(order_id)
    if not o or o["user_id"] != call.from_user.id:
        await call.answer("Заказ не найден", show_alert=True)
        return
    items = await db.get_order_items(order_id)
    lines = [f"📦 <b>Заказ #{order_id}</b>", ""]
    lines.append(f"Статус: {STATUSES.get(o['status'], o['status'])}")
    lines.append(f"🚚 {'Курьер' if o['delivery_type'] == 'courier' else 'Самовывоз'}")
    if o["metro_station"]:
        lines.append(f"📍 {o['metro_station']}")
    lines.append("")
    for i in items:
        lines.append(f"• {i['name']} × {i['quantity']} = {i['price'] * i['quantity']}₽")
    lines.append("")
    lines.append(f"💰 Итого: <b>{o['total']}₽</b>")
    await call.message.answer("\n".join(lines), reply_markup=back_to_main_menu())
    await call.answer()


@router.callback_query(F.data == "about")
async def about(call: CallbackQuery, db):
    about_text = await db.get_setting("about_text", "Ondetlin shop — вейп-шоп в Новосибирске.")
    pickup = await db.get_setting("pickup_address", "Уточните у менеджера")
    text = f"ℹ️ <b>О магазине</b>\n\n{about_text}\n\n🏠 Самовывоз: {pickup}\n🚚 Курьер по метро"
    try:
        await call.message.edit_text(text, reply_markup=back_to_main_menu())
    except Exception:
        await call.message.answer(text, reply_markup=back_to_main_menu())
    await call.answer()


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()