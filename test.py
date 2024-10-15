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

# Загрузка переменных окружения
load_dotenv()
router = Router()
# Инициализация бота и хранилища состояний
bot = Bot(os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Настройка доступа к Google Sheets
def get_sheets_client():
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    return gspread.authorize(creds)

def add_user_to_google_sheets(user_data):
    client = get_sheets_client()
    sheet = client.open_by_url(os.getenv('SHEETS_URL')).sheet1
    sheet.append_row([
        user_data.get('fio'), 
        user_data.get('phone'), 
        user_data.get('school_class'), 
        user_data.get('prof_prob'), 
        user_data.get('rating'), 
        user_data.get('review')
    ])

# Список проф проб
prof_prob_list = ["Основы работы с нейросетями и их обучение", 
                  "Кабельная система локальной сети", 
                  "Сборка-разборка персонального компьютера", 
                  "Анимация «трансформация» в Power Point", 
                  "Разработка приложения «1С: Школьный дневник»"]

# Определение состояний
class Form(StatesGroup):
    consent = State()
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


moderators = []

# Command handler to add a moderator
@dp.message(Command(commands=["add_moderator"]))
async def add_moderator(message: types.Message):
    if message.from_user.id == 987863133:
        try:
            moderator_id = int(message.text.split()[1])  # Assume the command is /add_moderator <user_id>
            if moderator_id not in moderators:
                moderators.append(moderator_id)
                await message.answer(f"Пользователь с ID {moderator_id} добавлен в качестве модератора.")
            else:
                await message.answer("Этот пользователь уже является модератором.")
        except (IndexError, ValueError):
            await message.answer("Пожалуйста, укажите корректный ID пользователя после команды.")
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")


# Обработчик команды /start
@dp.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext):
    buttons = [[KeyboardButton(text="Согласен")]]
    if message.from_user.id == 987863133:
        buttons.append([KeyboardButton(text="Скачать Excel файл")])
    keyboard = create_keyboard(buttons)
    await message.answer("Вы согласны на обработку персональных данных?", reply_markup=keyboard)
    await state.set_state(Form.consent)

@dp.message(lambda message: message.text == "Скачать Excel файл")
async def handle_download_excel(message: types.Message):
    if message.from_user.id == 987863133 or message.from_user.id in moderators:
        sent_message = await message.answer("Генерируется файл...")  # Notification of file generation
        file_path = generate_excel_from_sheets()
        
        document = FSInputFile(file_path)
        await message.answer_document(document)
        await sent_message.delete()  # Delete the "Generating file..." message
    else:
        await message.answer("У вас нет доступа к этой функции.")


@dp.message(Form.consent)
async def handle_consent(message: types.Message, state: FSMContext):
    if message.text == "Согласен":
        await message.answer("Пожалуйста, введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Form.fio)
    else:
        await message.answer("Для продолжения требуется согласие на обработку персональных данных.")
        await state.clear()

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
    response = f"Ваши данные:\nФИО: {user_data.get('fio')}\nТелефон: {user_data.get('phone')}\nКласс: {user_data.get('school_class')}\nПроф проба: {user_data.get('prof_prob')}\nОценка: {user_data.get('rating')}\nОтзыв: {user_data.get('review')}"
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

@router.message(Command(commands=["myid"]))
async def send_user_id(message: Message):
    user_id = message.from_user.id
    await message.answer(f"Ваш ID: {user_id}")

async def main():
    dp.include_router(router)
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
