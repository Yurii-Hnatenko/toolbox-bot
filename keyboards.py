from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_by_role(role):
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
                [KeyboardButton(text="📊 Загальний звіт"), KeyboardButton(text="📋 Детальний звіт")],
                [KeyboardButton(text="🔧 Керування інструментами"), KeyboardButton(text="📸 Фото інструментів")],
                [KeyboardButton(text="🏷️ Змінити останнього користувача"), KeyboardButton(text="ℹ️ Інформація")],
                [KeyboardButton(text="🔄 Перемкнути роль")],
            ],
            resize_keyboard=True
        )
    else:
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

def toolboxes_list_kb(toolboxes, prefix="check"):
    buttons = []
    for tb in toolboxes:
        buttons.append([InlineKeyboardButton(text=tb.name, callback_data=f"{prefix}_{tb.id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def report_boxes_list_kb(toolboxes):
    buttons = []
    for tb in toolboxes:
        buttons.append([InlineKeyboardButton(text=f"📊 {tb.name}", callback_data=f"report_{tb.id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
