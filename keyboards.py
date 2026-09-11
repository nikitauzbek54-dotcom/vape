from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

CATEGORIES = {
    "pods": "💨 Одноразки",
    "liquid": "💧 Жидкости",
    "devices": "🔋 Поды",
    "parts": "🔧 Расходники",
}

METRO_STATIONS = [
    "Площадь Ленина", "Октябрьская", "Речной вокзал", "Спортивная",
    "Студенческая", "Площадь Маркса", "Гагаринская", "Заельцовская",
    "Красный проспект", "Сибирская", "Маршала Покрышкина",
    "Берёзовая роща", "Золотая нива",
]

STATUSES = {
    "new": "🆕 Новый",
    "accepted": "✅ Принят",
    "delivery": "🚚 В доставке / Готов",
    "done": "✔️ Завершён",
    "cancelled": "❌ Отменён",
}


# ============ ГЛАВНОЕ МЕНЮ ============
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🧺 Корзина", callback_data="cart")],
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton(text="ℹ️ О магазине", callback_data="about")],
    ])


def catalog_menu():
    rows = [[InlineKeyboardButton(text=name, callback_data=f"cat_{key}")]
            for key, name in CATEGORIES.items()]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_menu(category: str, products: list):
    rows = []
    for p in products:
        stock_icon = "🟢" if p["stock"] > 0 else "🔴"
        rows.append([InlineKeyboardButton(
            text=f"{stock_icon} {p['name']} — {p['price']}₽",
            callback_data=f"prod_{p['id']}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_menu(product_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ В корзину", callback_data=f"add_{product_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog")],
    ])


def cart_menu(items: list):
    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(
            text=f"{item['name']} ({item['quantity']}шт)",
            callback_data="noop"
        )])
        rows.append([
            InlineKeyboardButton(text="➖", callback_data=f"qty_{item['cart_id']}_-1"),
            InlineKeyboardButton(text=f"{item['quantity']} × {item['price']}₽",
                                 callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"qty_{item['cart_id']}_+1"),
            InlineKeyboardButton(text="❌", callback_data=f"rm_{item['cart_id']}"),
        ])
    if items:
        rows.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")])
        rows.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delivery_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚚 Курьер", callback_data="delivery_courier")],
        [InlineKeyboardButton(text="🏠 Самовывоз", callback_data="delivery_pickup")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="cart")],
    ])


def metro_menu():
    rows = []
    for i in range(0, len(METRO_STATIONS), 2):
        row = []
        for station in METRO_STATIONS[i:i+2]:
            row.append(InlineKeyboardButton(
                text=station, callback_data=f"metro_{station}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="checkout")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_order_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cart")],
    ])


def skip_phone_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_phone")],
    ])


def skip_comment_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_comment")],
    ])


def my_orders_menu(orders: list):
    rows = []
    for o in orders:
        status = STATUSES.get(o["status"], o["status"])
        rows.append([InlineKeyboardButton(
            text=f"Заказ #{o['id']} — {status} — {o['total']}₽",
            callback_data=f"order_{o['id']}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")],
    ])


# ============ АДМИНКА ============
def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Товары", callback_data="adm_products")],
        [InlineKeyboardButton(text="📋 Заказы", callback_data="adm_orders")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="👤 Админы", callback_data="adm_admins")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="adm_settings")],
    ])


def admin_products_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm_add_product")],
        [InlineKeyboardButton(text="📋 Список товаров", callback_data="adm_list_products")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")],
    ])


def admin_categories_menu():
    rows = [[InlineKeyboardButton(text=name, callback_data=f"adm_pcat_{key}")]
            for key, name in CATEGORIES.items()]
    rows.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="adm_products")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_product_edit_menu(product_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"adm_edit_price_{product_id}")],
        [InlineKeyboardButton(text="📦 Изменить остаток", callback_data=f"adm_edit_stock_{product_id}")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"adm_edit_desc_{product_id}")],
        [InlineKeyboardButton(text="🖼 Изменить фото", callback_data=f"adm_edit_photos_{product_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"adm_del_{product_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_list_products")],
    ])


def admin_orders_menu():
    rows = [
        [InlineKeyboardButton(text="🆕 Новые", callback_data="adm_ord_new")],
        [InlineKeyboardButton(text="✅ Принятые", callback_data="adm_ord_accepted")],
        [InlineKeyboardButton(text="🚚 В доставке", callback_data="adm_ord_delivery")],
        [InlineKeyboardButton(text="✔️ Завершённые", callback_data="adm_ord_done")],
        [InlineKeyboardButton(text="❌ Отменённые", callback_data="adm_ord_cancelled")],
        [InlineKeyboardButton(text="📋 Все заказы", callback_data="adm_ord_all")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_order_menu(order_id: int):
    rows = []
    for key, name in STATUSES.items():
        rows.append([InlineKeyboardButton(text=name, callback_data=f"adm_set_{order_id}_{key}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_orders")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_settings_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Адрес самовывоза", callback_data="adm_set_pickup")],
        [InlineKeyboardButton(text="ℹ️ Текст 'О магазине'", callback_data="adm_set_about")],
        [InlineKeyboardButton(text="🖼 Баннер", callback_data="adm_set_banner")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")],
    ])


def admin_admins_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="adm_add_admin")],
        [InlineKeyboardButton(text="📋 Список админов", callback_data="adm_list_admins")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")],
    ])


def admin_back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")],
    ])
