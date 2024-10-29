import os
import asyncio
import logging
import gspread
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from openpyxl import Workbook
from aiogram.types import FSInputFile
from aiogram.filters import Command
import json

MODERATORS_FILE = "moderators.json"
CONFIG_FILE = "config.json"

ADMIN_ID = 0
# Загрузка переменных окружения
load_dotenv()
router = Router()
# Инициализация бота и хранилища состояний
bot = Bot(os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def load_admins():
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
            return config.get("ADMINS", [])  # возвращаем список администраторов или пустой список
    except FileNotFoundError:
        logging.error("Config file not found. Ensure config.json is present.")
        return []

admins = load_admins()
# Настройка доступа к Google Sheets
def get_sheets_client():
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    return gspread.authorize(creds)

# Обновленная функция для добавления пользователя в Google Sheets
def add_user_to_google_sheets(user_data):
    client = get_sheets_client()
    sheet = client.open_by_url(os.getenv('SHEETS_URL')).sheet1
    next_row = len(sheet.get_all_values()) + 1
    sheet.append_row([
        user_data.get('event'),   # Сохранение выбранного мероприятия
        user_data.get('fio'),
        user_data.get('phone'),
        user_data.get('school_class'),
        user_data.get('prof_prob'),
        user_data.get('rating'),
        user_data.get('review')
    ], table_range=f'A{next_row}')

events_list = [
    "День открытых дверей",
    "Профессиональные пробы",
    "Билет в будущее",
    "Профессиональное образование без границ",
    "Фестиваль колледжей"
]
# Список проф проб
prof_prob_list = ["Основы работы с нейросетями и их обучение", 
                  "Кабельная система локальной сети", 
                  "Сборка-разборка персонального компьютера", 
                  "Анимация «трансформация» в Power Point", 
                  "Разработка приложения «1С: Школьный дневник»"]

# Определение состояний
class Form(StatesGroup):
    consent = State()
    event = State()
    fio = State()
    phone = State()
    school_class = State()
    prof_prob = State()
    rating = State()
    review = State()
    final_choice = State()

# Функция для создания клавиатуры
def create_keyboard(buttons):
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

# Функция для создания Excel файла из Google Sheets
def generate_excel_from_sheets():
    client = get_sheets_client()
    sheet = client.open_by_url(os.getenv('SHEETS_URL')).sheet1
    data = sheet.get_all_values()
    
    workbook = Workbook()
    excel_sheet = workbook.active

    for row in data:
        excel_sheet.append(row)
    
    file_path = "data.xlsx"
    workbook.save(file_path)
    return file_path


# Обработчик команды для добавления модератора
@dp.message(Command(commands=["add_moderator"]))
async def add_moderator(message: types.Message):
    if message.from_user.id in admins:
        try:
            moderator_id = int(message.text.split()[1])
            if moderator_id not in moderators:
                moderators.append(moderator_id)
                save_moderators(moderators)
                await message.answer(f"Пользователь с ID {moderator_id} добавлен в качестве модератора.")
                # Перезагружаем клавиатуру для нового модератора
                if moderator_id == message.from_user.id:
                    await handle_start(message)  # Перезагрузка клавиатуры для самого админа
            else:
                await message.answer("Этот пользователь уже является модератором.")
        except (IndexError, ValueError):
            await message.answer("Пожалуйста, укажите корректный ID пользователя после команды.")
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")

# Обработчик команды для удаления модератора
@dp.message(Command(commands=["remove_moderator"]))
async def remove_moderator(message: types.Message):
    if message.from_user.id in admins:
        try:
            moderator_id = int(message.text.split()[1])  # Предполагаем, что команда вида /remove_moderator <user_id>
            if moderator_id in moderators:
                moderators.remove(moderator_id)
                save_moderators(moderators)  # Сохранение обновленного списка
                await message.answer(f"Пользователь с ID {moderator_id} удалён из списка модераторов.")
                # Обновляем интерфейс, если администратор удаляет сам себя как модератора
                if moderator_id == message.from_user.id:
                    await handle_start(message)
            else:
                await message.answer("Этот пользователь не является модератором.")
        except (IndexError, ValueError):
            await message.answer("Пожалуйста, укажите корректный ID пользователя после команды.")
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")

# Функция для загрузки модераторов из JSON-файла
def load_moderators():
    try:
        with open(MODERATORS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

# Функция для сохранения модераторов в JSON-файл
def save_moderators(moderators):
    with open(MODERATORS_FILE, "w") as file:
        json.dump(moderators, file)

# Инициализация списка модераторов при запуске бота
moderators = load_moderators()

# Обработчик команды /start
@dp.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext):
    buttons = []
    if message.from_user.id in admins or message.from_user.id in moderators:
        buttons.append([KeyboardButton(text="Сгенерировать Excel файл")])

    if message.from_user.id in admins:
        buttons.append([KeyboardButton(text="Очистить Excel таблицу")])
        await message.answer("Добро пожаловать администратор")
    
    # Добавляем кнопку "Согласен" для всех остальных пользователей
    if message.from_user.id not in admins and message.from_user.id not in moderators:
        buttons.append([KeyboardButton(text="Согласен")])
        keyboard = create_keyboard(buttons)
        await message.answer("Согласие на обработку данных:", reply_markup=keyboard)
        await state.set_state(Form.consent)
    
    if buttons and (message.from_user.id in admins or message.from_user.id in moderators):  # Отправка кнопок, если они есть
        keyboard = create_keyboard(buttons)
        await message.answer("Выберите действие:", reply_markup=keyboard)
    elif(message.from_user.id in admins or message.from_user.id in moderators):
        await message.answer("У вас нет доступных действий.")






@dp.message(lambda message: message.text == "Сгенерировать Excel файл")
async def handle_download_excel(message: types.Message):
    if message.from_user.id in admins or message.from_user.id in moderators:
        sent_message = await message.answer("Генерируется файл...")
        file_path = generate_excel_from_sheets()
        
        document = FSInputFile(file_path)
        await message.answer_document(document)
        await sent_message.delete()  # Удаляем сообщение о генерации файла
    else:
        await message.answer("У вас нет доступа к этой функции.")



@dp.message(Form.consent)
async def handle_consent(message: types.Message, state: FSMContext):
    if message.text == "Согласен":
        event_buttons = [[KeyboardButton(text=event)] for event in events_list]
        await message.answer("Выберите мероприятие:", reply_markup=create_keyboard(event_buttons))
        await state.set_state(Form.event)
    else:
        await message.answer("Для продолжения требуется согласие на обработку персональных данных.")
        await state.clear()

@dp.message(Form.event)
async def handle_event(message: types.Message, state: FSMContext):
    selected_event = message.text.strip()
    await state.update_data(event=selected_event)
    
    await message.answer("Пожалуйста, введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Form.fio)

@dp.message(Form.fio)
async def handle_fio(message: types.Message, state: FSMContext):
    fio = message.text.strip()
    if not fio:
        await message.answer("ФИО не может быть пустым.")
        return
    await state.update_data(fio=fio)
    await message.answer("Введите ваш номер телефона:")
    await state.set_state(Form.phone)

@dp.message(Form.phone)
async def handle_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not phone:
        await message.answer("Номер телефона не может быть пустым.")
        return
    await state.update_data(phone=phone)
    class_buttons = [[KeyboardButton(text=str(i)) for i in range(8, 12)]]
    await message.answer("Выберите ваш класс обучения:", reply_markup=create_keyboard(class_buttons))
    await state.set_state(Form.school_class)

@dp.message(Form.school_class)
async def handle_class(message: types.Message, state: FSMContext):
    await state.update_data(school_class=message.text.strip())
    user_data = await state.get_data()

    # Если мероприятие "Фестиваль колледжей," пропускаем выбор профпробы и сразу переходим к оценке
    if user_data.get('event') == "Фестиваль колледжей":
        rating_buttons = [[KeyboardButton(text=str(i)) for i in range(1, 6)]]
        await message.answer("Оцените мероприятие от 1 до 5:", reply_markup=create_keyboard(rating_buttons))
        await state.set_state(Form.rating)
    else:
        # Иначе продолжаем с выбором профпробы
        buttons = [[KeyboardButton(text=prob)] for prob in prof_prob_list]
        await message.answer("Выберите проф пробу:", reply_markup=create_keyboard(buttons))
        await state.set_state(Form.prof_prob)

@dp.message(Form.prof_prob)
async def handle_prof_prob(message: types.Message, state: FSMContext):
    await state.update_data(prof_prob=message.text.strip())
    rating_buttons = [[KeyboardButton(text=str(i)) for i in range(1, 6)]]
    await message.answer("Оцените профпробу от 1 до 5:", reply_markup=create_keyboard(rating_buttons))
    await state.set_state(Form.rating)

@dp.message(Form.rating)
async def handle_rating(message: types.Message, state: FSMContext):
    await state.update_data(rating=message.text.strip())
    await message.answer("Оставьте отзыв о проф пробе (необязательно):", reply_markup=create_keyboard([[KeyboardButton(text="Пропустить →")]]))
    await state.set_state(Form.review)

@dp.message(Form.review)
async def handle_review(message: types.Message, state: FSMContext):
    review = message.text.strip()
    await state.update_data(review=review if review != "Пропустить →" else "Отзыв не предоставлен")
    user_data = await state.get_data()
    
    # Формируем итоговое сообщение для "Фестиваля колледжей" без упоминания профпробы
    if user_data.get('event') == "Фестиваль колледжей":
        response = (
            f"Ваши данные:\n"
            f"ФИО: {user_data.get('fio')}\n"
            f"Мероприятие: {user_data.get('event')}\n"
            f"Телефон: {user_data.get('phone')}\n"
            f"Класс: {user_data.get('school_class')}\n"
            f"Оценка: {user_data.get('rating')}\n"
            f"Отзыв: {user_data.get('review')}"
        )
    else:
        # Итоговое сообщение для других мероприятий, включая профпробу
        response = (
            f"Ваши данные:\n"
            f"ФИО: {user_data.get('fio')}\n"
            f"Мероприятие: {user_data.get('event')}\n"
            f"Телефон: {user_data.get('phone')}\n"
            f"Класс: {user_data.get('school_class')}\n"
            f"Проф проба: {user_data.get('prof_prob')}\n"
            f"Оценка: {user_data.get('rating')}\n"
            f"Отзыв: {user_data.get('review')}"
        )
    
    await message.answer(response, reply_markup=create_keyboard([[KeyboardButton(text="Отправить"), KeyboardButton(text="Изменить")]]))
    await state.set_state(Form.final_choice)


@dp.message(Form.final_choice)
async def handle_final_choice(message: types.Message, state: FSMContext):
    if message.text == "Отправить":
        sent_message = await message.answer("Отправка...")  # Сообщение о начале отправки
        add_user_to_google_sheets(await state.get_data())
        await message.answer("Ваши данные отправлены!", reply_markup=ReplyKeyboardRemove())
        await sent_message.delete()  # Удаляем сообщение о начале отправки
        await state.clear()
    elif message.text == "Изменить":
        await message.answer("Введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Form.fio)
    else:
        await message.answer("Выберите 'Отправить' или 'Изменить'.", reply_markup=create_keyboard([[KeyboardButton(text="Отправить"), KeyboardButton(text="Изменить")]]))

@dp.message(lambda message: message.text == "Очистить Excel таблицу")
async def clear_google_sheets(message: types.Message):
    if message.from_user.id in admins:
        client = get_sheets_client()
        sheet = client.open_by_url(os.getenv('SHEETS_URL')).sheet1
        sheet.clear()
        await message.answer("Excel таблица очищена.")
    else:
        await message.answer("У вас нет доступа к этой функции.")


# Обработчик команды /myid
@router.message(Command(commands=["myid"]))
async def send_user_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer(f"Ваш ID: {user_id}")



async def main():
    dp.include_router(router)
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
