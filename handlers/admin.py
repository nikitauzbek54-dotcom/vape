import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import (
    admin_menu, admin_products_menu, admin_categories_menu,
    admin_product_edit_menu, admin_orders_menu, admin_order_menu,
    admin_settings_menu, admin_admins_menu, admin_back_menu,
    CATEGORIES, STATUSES,
)

router = Router()


class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    stock = State()
    strength = State()
    flavor = State()
    category = State()
    photos = State()


class AdminEdit(StatesGroup):
    edit_price = State()
    edit_stock = State()
    edit_desc = State()
    edit_photos = State()
    add_admin = State()
    broadcast = State()
    set_pickup = State()
    set_about = State()
    set_banner = State()


def is_admin_check(user_id: int, admin_ids: list) -> bool:
    return user_id in admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, admin_ids):
    if not is_admin_check(message.from_user.id, admin_ids):
        return
    await message.answer("🔧 <b>Админ-панель</b>", reply_markup=admin_menu())


@router.callback_query(F.data == "adm_back")
async def adm_back(call: CallbackQuery, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    try:
        await call.message.edit_text("🔧 <b>Админ-панель</b>", reply_markup=admin_menu())
    except Exception:
        await call.message.answer("🔧 <b>Админ-панель</b>", reply_markup=admin_menu())
    await call.answer()


# ===== ТОВАРЫ =====
@router.callback_query(F.data == "adm_products")
async def adm_products(call: CallbackQuery, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    try:
        await call.message.edit_text("📦 <b>Товары</b>", reply_markup=admin_products_menu())
    except Exception:
        await call.message.answer("📦 <b>Товары</b>", reply_markup=admin_products_menu())
    await call.answer()


@router.callback_query(F.data == "adm_add_product")
async def adm_add_product(call: CallbackQuery, admin_ids, state: FSMContext):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    await state.clear()
    await state.set_state(AddProduct.name)
    try:
        await call.message.edit_text("✏️ Введи <b>название</b> товара:")
    except Exception:
        await call.message.answer("✏️ Введи <b>название</b> товара:")
    await call.answer()


@router.message(AddProduct.name)
async def add_name(message: Message, state: FSMContext, admin_ids):
    if not is_admin_check(message.from_user.id, admin_ids):
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProduct.description)
    await message.answer("📝 Введи <b>описание</b> (или «-» чтобы пропустить):")


@router.message(AddProduct.description)
async def add_description(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(description=None if text == "-" else text)
    await state.set_state(AddProduct.price)
    await message.answer("💰 Введи <b>цену</b> (число, в рублях):")


@router.message(AddProduct.price)
async def add_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    await state.update_data(price=price)
    await state.set_state(AddProduct.stock)
    await message.answer("📦 Введи <b>остаток</b> (число):")


@router.message(AddProduct.stock)
async def add_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введи число!")
        return
    await state.update_data(stock=stock)
    await state.set_state(AddProduct.strength)
    await message.answer("⚡ Введи <b>крепость</b> (например «20mg», или «-»):")


@router.message(AddProduct.strength)
async def add_strength(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(strength=None if text == "-" else text)
    await state.set_state(AddProduct.flavor)
    await message.answer("🍓 Введи <b>вкус</b> (или «-»):")


@router.message(AddProduct.flavor)
async def add_flavor(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(flavor=None if text == "-" else text)
    await state.set_state(AddProduct.category)
    await message.answer("📂 Выбери <b>категорию</b>:", reply_markup=admin_categories_menu())


@router.callback_query(F.data.startswith("adm_pcat_"), AddProduct.category)
async def add_category(call: CallbackQuery, state: FSMContext):
    cat = call.data.replace("adm_pcat_", "")
    await state.update_data(category=cat)
    await state.set_state(AddProduct.photos)
    try:
        await call.message.edit_text(
            "🖼 Отправь <b>фото товара</b> (до 5 штук).\n"
            "Когда закончишь — напиши «готово»."
        )
    except Exception:
        await call.message.answer(
            "🖼 Отправь <b>фото товара</b> (до 5 штук).\n"
            "Когда закончишь — напиши «готово»."
        )
    await call.answer()


@router.message(AddProduct.photos, F.photo)
async def add_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if len(photos) >= 5:
        await message.answer("⚠️ Максимум 5 фото. Напиши «готово».")
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"✅ Фото добавлено ({len(photos)}/5). Ещё или «готово».")


@router.message(AddProduct.photos, F.text)
async def add_photos_done(message: Message, state: FSMContext, db):
    if message.text.strip().lower() != "готово":
        await message.answer("Отправь фото или напиши «готово».")
        return
    data = await state.get_data()
    product_id = await db.add_product(
        data["name"], data.get("description"), data["price"], data["stock"],
        data.get("strength"), data.get("flavor"), data["category"],
        data.get("photos", [])
    )
    await state.clear()
    await message.answer(f"✅ Товар добавлен! ID: {product_id}", reply_markup=admin_products_menu())


@router.callback_query(F.data == "adm_list_products")
async def adm_list_products(call: CallbackQuery, admin_ids, db):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    products = await db.get_all_products()
    if not products:
        text = "📋 Товаров пока нет"
        kb = admin_products_menu()
    else:
        text = "📋 <b>Все товары:</b>"
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        rows = [[InlineKeyboardButton(
            text=f"{p['name']} — {p['price']}₽ (ост. {p['stock']})",
            callback_data=f"adm_prod_{p['id']}"
        )] for p in products]
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_products")])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("adm_prod_"))
async def adm_show_product(call: CallbackQuery, admin_ids, db):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    product_id = int(call.data.replace("adm_prod_", ""))
    p = await db.get_product(product_id)
    if not p:
        await call.answer("Не найден", show_alert=True)
        return
    text = (
        f"📦 <b>{p['name']}</b>\n"
        f"ID: {p['id']}\n"
        f"💰 {p['price']}₽\n"
        f"📦 Остаток: {p['stock']}\n"
        f"📂 {CATEGORIES.get(p['category'], p['category'])}"
    )
    if p["description"]:
        text += f"\n📝 {p['description']}"
    if p["strength"]:
        text += f"\n⚡ {p['strength']}"
    if p["flavor"]:
        text += f"\n🍓 {p['flavor']}"
    try:
        await call.message.edit_text(text, reply_markup=admin_product_edit_menu(product_id))
    except Exception:
        await call.message.answer(text, reply_markup=admin_product_edit_menu(product_id))
    await call.answer()


@router.callback_query(F.data.startswith("adm_edit_price_"))
async def adm_edit_price(call: CallbackQuery, state: FSMContext, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    product_id = int(call.data.replace("adm_edit_price_", ""))
    await state.update_data(product_id=product_id)
    await state.set_state(AdminEdit.edit_price)
    await call.message.answer("💰 Введи новую цену:")
    await call.answer()


@router.message(AdminEdit.edit_price)
async def save_price(message: Message, state: FSMContext, db):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Число!")
        return
    data = await state.get_data()
    await db.update_product(data["product_id"], price=price)
    await state.clear()
    await message.answer("✅ Цена обновлена!", reply_markup=admin_products_menu())


@router.callback_query(F.data.startswith("adm_edit_stock_"))
async def adm_edit_stock(call: CallbackQuery, state: FSMContext, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    product_id = int(call.data.replace("adm_edit_stock_", ""))
    await state.update_data(product_id=product_id)
    await state.set_state(AdminEdit.edit_stock)
    await call.message.answer("📦 Введи новый остаток:")
    await call.answer()


@router.message(AdminEdit.edit_stock)
async def save_stock(message: Message, state: FSMContext, db):
    try:
        stock = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Число!")
        return
    data = await state.get_data()
    await db.update_product(data["product_id"], stock=stock)
    await state.clear()
    await message.answer("✅ Остаток обновлён!", reply_markup=admin_products_menu())


@router.callback_query(F.data.startswith("adm_edit_desc_"))
async def adm_edit_desc(call: CallbackQuery, state: FSMContext, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    product_id = int(call.data.replace("adm_edit_desc_", ""))
    await state.update_data(product_id=product_id)
    await state.set_state(AdminEdit.edit_desc)
    await call.message.answer("📝 Введи новое описание:")
    await call.answer()


@router.message(AdminEdit.edit_desc)
async def save_desc(message: Message, state: FSMContext, db):
    data = await state.get_data()
    await db.update_product(data["product_id"], description=message.text.strip())
    await state.clear()
    await message.answer("✅ Описание обновлено!", reply_markup=admin_products_menu())


@router.callback_query(F.data.startswith("adm_edit_photos_"))
async def adm_edit_photos(call: CallbackQuery, state: FSMContext, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    product_id = int(call.data.replace("adm_edit_photos_", ""))
    await state.update_data(product_id=product_id, photos=[])
    await state.set_state(AdminEdit.edit_photos)
    await call.message.answer("🖼 Отправь новые фото (до 5). Потом «готово».")
    await call.answer()


@router.message(AdminEdit.edit_photos, F.photo)
async def edit_photos_add(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if len(photos) >= 5:
        await message.answer("Максимум 5.")
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"✅ {len(photos)}/5. Ещё или «готово».")


@router.message(AdminEdit.edit_photos, F.text)
async def edit_photos_done(message: Message, state: FSMContext, db):
    if message.text.strip().lower() != "готово":
        return
    data = await state.get_data()
    await db.update_product(data["product_id"], photos=json.dumps(data.get("photos", [])))
    await state.clear()
    await message.answer("✅ Фото обновлены!", reply_markup=admin_products_menu())


@router.callback_query(F.data.startswith("adm_del_"))
async def adm_del_product(call: CallbackQuery, admin_ids, db):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    product_id = int(call.data.replace("adm_del_", ""))
    await db.delete_product(product_id)
    await call.answer("Удалено")
    try:
        await call.message.edit_text("🗑 Товар удалён", reply_markup=admin_products_menu())
    except Exception:
        await call.message.answer("🗑 Товар удалён", reply_markup=admin_products_menu())


# ===== ЗАКАЗЫ =====
@router.callback_query(F.data == "adm_orders")
async def adm_orders(call: CallbackQuery, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    try:
        await call.message.edit_text("📋 <b>Заказы</b>", reply_markup=admin_orders_menu())
    except Exception:
        await call.message.answer("📋 <b>Заказы</b>", reply_markup=admin_orders_menu())
    await call.answer()


@router.callback_query(F.data.startswith("adm_ord_"))
async def adm_orders_filter(call: CallbackQuery, admin_ids, db):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    status = call.data.replace("adm_ord_", "")
    if status == "all":
        orders = await db.get_all_orders()
    else:
        orders = await db.get_orders_by_status(status)
    if not orders:
        text = "Заказов нет"
        kb = admin_orders_menu()
    else:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        rows = []
        for o in orders:
            st = STATUSES.get(o["status"], o["status"])
            rows.append([InlineKeyboardButton(
                text=f"#{o['id']} — {o['name']} — {o['total']}₽ — {st}",
                callback_data=f"adm_view_{o['id']}"
            )])
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_orders")])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        text = "📋 <b>Заказы:</b>"
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("adm_view_"))
async def adm_view_order(call: CallbackQuery, admin_ids, db):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    order_id = int(call.data.replace("adm_view_", ""))
    o = await db.get_order(order_id)
    if not o:
        await call.answer("Не найден", show_alert=True)
        return
    items = await db.get_order_items(order_id)
    lines = [f"📦 <b>Заказ #{order_id}</b>", ""]
    lines.append(f"👤 {o['name']}")
    if o["phone"]:
        lines.append(f"📱 {o['phone']}")
    lines.append(f"🚚 {'Курьер' if o['delivery_type'] == 'courier' else 'Самовывоз'}")
    if o["metro_station"]:
        lines.append(f"📍 {o['metro_station']}")
    if o["comment"]:
        lines.append(f"💬 {o['comment']}")
    lines.append(f"📊 {STATUSES.get(o['status'], o['status'])}")
    lines.append("")
    for i in items:
        lines.append(f"• {i['name']} × {i['quantity']} = {i['price'] * i['quantity']}₽")
    lines.append("")
    lines.append(f"💰 Итого: <b>{o['total']}₽</b>")
    lines.append(f"👤 Юзер: <code>{o['user_id']}</code>")
    try:
        await call.message.edit_text("\n".join(lines), reply_markup=admin_order_menu(order_id))
    except Exception:
        await call.message.answer("\n".join(lines), reply_markup=admin_order_menu(order_id))
    await call.answer()


@router.callback_query(F.data.startswith("adm_set_"))
async def adm_set_status(call: CallbackQuery, admin_ids, db, bot):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    parts = call.data.replace("adm_set_", "").split("_")
    order_id = int(parts[0])
    status = parts[1]
    await db.update_order_status(order_id, status)
    await call.answer(f"Статус: {STATUSES[status]}")
    o = await db.get_order(order_id)
    if o:
        try:
            await bot.send_message(
                o["user_id"],
                f"📦 Статус заказа #{order_id} изменён: {STATUSES[status]}"
            )
        except Exception:
            pass


# ===== ПОЛЬЗОВАТЕЛИ =====
@router.callback_query(F.data == "adm_users")
async def adm_users(call: CallbackQuery, admin_ids, db):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    users = await db.get_all_users()
    await call.answer()
    try:
        await call.message.edit_text(
            f"👥 Всего пользователей: <b>{len(users)}</b>",
            reply_markup=admin_back_menu()
        )
    except Exception:
        await call.message.answer(
            f"👥 Всего пользователей: <b>{len(users)}</b>",
            reply_markup=admin_back_menu()
        )


# ===== РАССЫЛКА =====
@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(call: CallbackQuery, admin_ids, state: FSMContext):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    await state.set_state(AdminEdit.broadcast)
    await call.message.answer("📢 Напиши текст рассылки:")
    await call.answer()


@router.message(AdminEdit.broadcast)
async def do_broadcast(message: Message, state: FSMContext, db, bot):
    text = message.text
    users = await db.get_all_users()
    count = 0
    for u in users:
        try:
            await bot.send_message(u["tg_id"], text)
            count += 1
        except Exception:
            pass
    await state.clear()
    await message.answer(f"✅ Отправлено {count}/{len(users)}", reply_markup=admin_menu())


# ===== АДМИНЫ =====
@router.callback_query(F.data == "adm_admins")
async def adm_admins(call: CallbackQuery, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    try:
        await call.message.edit_text("👤 <b>Админы</b>", reply_markup=admin_admins_menu())
    except Exception:
        await call.message.answer("👤 <b>Админы</b>", reply_markup=admin_admins_menu())
    await call.answer()


@router.callback_query(F.data == "adm_add_admin")
async def adm_add_admin(call: CallbackQuery, admin_ids, state: FSMContext):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    await state.set_state(AdminEdit.add_admin)
    await call.message.answer("👤 Отправь <b>ID</b> нового админа:")
    await call.answer()


@router.message(AdminEdit.add_admin)
async def save_admin(message: Message, state: FSMContext, db, admin_ids):
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Число!")
        return
    await db.add_admin(tg_id)
    admin_ids.append(tg_id)
    await state.clear()
    await message.answer(f"✅ Админ {tg_id} добавлен", reply_markup=admin_menu())


@router.callback_query(F.data == "adm_list_admins")
async def adm_list_admins(call: CallbackQuery, admin_ids, db):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    admins = await db.get_all_admins()
    lines = ["👥 <b>Админы:</b>", ""]
    for a in admins:
        lines.append(f"• <code>{a['tg_id']}</code> — {a['role']}")
    try:
        await call.message.edit_text("\n".join(lines), reply_markup=admin_admins_menu())
    except Exception:
        await call.message.answer("\n".join(lines), reply_markup=admin_admins_menu())
    await call.answer()


# ===== НАСТРОЙКИ =====
@router.callback_query(F.data == "adm_settings")
async def adm_settings(call: CallbackQuery, admin_ids):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    try:
        await call.message.edit_text("⚙️ <b>Настройки</b>", reply_markup=admin_settings_menu())
    except Exception:
        await call.message.answer("⚙️ <b>Настройки</b>", reply_markup=admin_settings_menu())
    await call.answer()


@router.callback_query(F.data == "adm_set_pickup")
async def adm_set_pickup(call: CallbackQuery, admin_ids, state: FSMContext):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    await state.set_state(AdminEdit.set_pickup)
    await call.message.answer("🏠 Введи адрес самовывоза:")
    await call.answer()


@router.message(AdminEdit.set_pickup)
async def save_pickup(message: Message, state: FSMContext, db):
    await db.set_setting("pickup_address", message.text.strip())
    await state.clear()
    await message.answer("✅ Адрес обновлён!", reply_markup=admin_menu())


@router.callback_query(F.data == "adm_set_about")
async def adm_set_about(call: CallbackQuery, admin_ids, state: FSMContext):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    await state.set_state(AdminEdit.set_about)
    await call.message.answer("ℹ️ Введи текст «О магазине»:")
    await call.answer()


@router.message(AdminEdit.set_about)
async def save_about(message: Message, state: FSMContext, db):
    await db.set_setting("about_text", message.text.strip())
    await state.clear()
    await message.answer("✅ Текст обновлён!", reply_markup=admin_menu())


@router.callback_query(F.data == "adm_set_banner")
async def adm_set_banner(call: CallbackQuery, admin_ids, state: FSMContext):
    if not is_admin_check(call.from_user.id, admin_ids):
        return
    await state.set_state(AdminEdit.set_banner)
    await call.message.answer("🖼 Отправь новую картинку-баннер:")
    await call.answer()


@router.message(AdminEdit.set_banner, F.photo)
async def save_banner(message: Message, state: FSMContext, db):
    await db.set_setting("banner", message.photo[-1].file_id)
    await state.clear()
    await message.answer("✅ Баннер обновлён!", reply_markup=admin_menu())