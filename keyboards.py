from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(roles):
    """
    Отримує список ролей користувача і повертає відповідне меню.
    """
    if "admin" in roles:
        # Адмін має всі функції
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📋 Перевірити ящик"), KeyboardButton(text="📊 Загальний звіт")],
                [KeyboardButton(text="🔧 Керування інструментами"), KeyboardButton(text="📸 Фото інструментів")],
                [KeyboardButton(text="👥 Керування ролями"), KeyboardButton(text="📦 Керування ящиками")],
                [KeyboardButton(text="📜 Історія моїх перевірок"), KeyboardButton(text="🏷️ Змінити користувача")],
                [KeyboardButton(text="📊 Глобальна статистика"), KeyboardButton(text="ℹ️ Інформація")],
                [KeyboardButton(text="🔄 Перемкнути роль")],
            ],
            resize_keyboard=True
        )
    elif "mechanic" in roles:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Загальний звіт"), KeyboardButton(text="🔧 Керування інструментами")],
                [KeyboardButton(text="📸 Фото інструментів"), KeyboardButton(text="🏷️ Змінити останнього користувача")],
                [KeyboardButton(text="ℹ️ Інформація"), KeyboardButton(text="🔄 Перемкнути роль")],
            ],
            resize_keyboard=True
        )
    else:  # operator
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📋 Перевірити ящик")],
                [KeyboardButton(text="📸 Фото інструментів")],
                [KeyboardButton(text="📜 Історія моїх перевірок")],
                [KeyboardButton(text="ℹ️ Інформація")],
                [KeyboardButton(text="🔄 Перемкнути роль")] if len(roles) > 1 else [],
            ],
            resize_keyboard=True
        )


def main_menu_by_role(role):
    """
    Повертає меню на основі ОДНІЄЇ ролі (для перемикання)
    """
    if role == "admin":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📋 Перевірити ящик"), KeyboardButton(text="📊 Загальний звіт")],
                [KeyboardButton(text="🔧 Керування інструментами"), KeyboardButton(text="📸 Фото інструментів")],
                [KeyboardButton(text="👥 Керування ролями"), KeyboardButton(text="📦 Керування ящиками")],
                [KeyboardButton(text="📜 Історія моїх перевірок"), KeyboardButton(text="🏷️ Змінити користувача")],
                [KeyboardButton(text="📊 Глобальна статистика"), KeyboardButton(text="ℹ️ Інформація")],
                [KeyboardButton(text="🔄 Перемкнути роль")],
            ],
            resize_keyboard=True
        )
    elif role == "mechanic":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Загальний звіт"), KeyboardButton(text="🔧 Керування інструментами")],
                [KeyboardButton(text="📸 Фото інструментів"), KeyboardButton(text="🏷️ Змінити останнього користувача")],
                [KeyboardButton(text="ℹ️ Інформація"), KeyboardButton(text="🔄 Перемкнути роль")],
            ],
            resize_keyboard=True
        )
    else:  # operator
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📋 Перевірити ящик")],
                [KeyboardButton(text="📸 Фото інструментів")],
                [KeyboardButton(text="📜 Історія моїх перевірок")],
                [KeyboardButton(text="ℹ️ Інформація")],
                [KeyboardButton(text="🔄 Перемкнути роль")],
            ],
            resize_keyboard=True
        )


def admin_roles_kb(current_roles):
    """Клавіатура для керування ролями (адмін може додавати/видаляти ролі)"""
    buttons = []
    for role in ["operator", "mechanic", "admin"]:
        if role in current_roles:
            buttons.append([InlineKeyboardButton(text=f"✅ {role} (видалити)", callback_data=f"remove_role_{role}")])
        else:
            buttons.append([InlineKeyboardButton(text=f"➕ {role} (додати)", callback_data=f"add_role_{role}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def toolboxes_list_kb(toolboxes, prefix="check"):
    """Клавіатура зі списком ящиків"""
    buttons = []
    for tb in toolboxes:
        buttons.append([InlineKeyboardButton(text=tb.name, callback_data=f"{prefix}_{tb.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Додати ящик", callback_data="add_toolbox")])
    buttons.append([InlineKeyboardButton(text="❌ Видалити ящик", callback_data="delete_toolbox")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_tools_kb(toolbox_id, tools):
    """Клавіатура для редагування інструментів"""
    buttons = []
    for tool in tools:
        buttons.append([InlineKeyboardButton(text=f"✏️ {tool}", callback_data=f"edit_tool_{toolbox_id}_{tool}")])
        buttons.append([InlineKeyboardButton(text=f"🗑️ Видалити {tool}", callback_data=f"del_tool_{toolbox_id}_{tool}")])
    buttons.append([InlineKeyboardButton(text="➕ Додати інструмент", callback_data=f"add_tool_{toolbox_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_boxes")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def role_switch_kb(roles):
    """Клавіатура для перемикання активної ролі (якщо в користувача їх кілька)"""
    buttons = []
    for role in roles:
        buttons.append([InlineKeyboardButton(text=f"🔧 {role.capitalize()}", callback_data=f"switch_role_{role}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)