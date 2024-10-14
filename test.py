import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Загрузка переменных окружения
load_dotenv()

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
    client = gspread.authorize(creds)
    return client

def add_user_to_google_sheets(user_data):
    client = get_sheets_client()
    sheet = client.open_by_url(os.getenv('SHEETS_URL')).sheet1
    # Добавляем данные в Google Sheets
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

@dp.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext):
    buttons = [[KeyboardButton(text="Согласен")]]
    keyboard = create_keyboard(buttons)
    await message.answer("Вы согласны на обработку персональных данных?", reply_markup=keyboard)
    await state.set_state(Form.consent)

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
    keyboard = create_keyboard(class_buttons)
    await message.answer("Выберите ваш класс обучения:", reply_markup=keyboard)
    await state.set_state(Form.school_class)

@dp.message(Form.school_class)
async def handle_class(message: types.Message, state: FSMContext):
    school_class = message.text.strip()
    await state.update_data(school_class=school_class)
    buttons = [[KeyboardButton(text=prob)] for prob in prof_prob_list]
    keyboard = create_keyboard(buttons)
    await message.answer("Выберите проф пробу:", reply_markup=keyboard)
    await state.set_state(Form.prof_prob)

@dp.message(Form.prof_prob)
async def handle_prof_prob(message: types.Message, state: FSMContext):
    selected_prob = message.text.strip()
    await state.update_data(prof_prob=selected_prob)
    rating_buttons = [[KeyboardButton(text=str(i)) for i in range(1, 6)]]
    keyboard = create_keyboard(rating_buttons)
    await message.answer("Оцените профпробу от 1 до 5:", reply_markup=keyboard)
    await state.set_state(Form.rating)

@dp.message(Form.rating)
async def handle_rating(message: types.Message, state: FSMContext):
    rating = message.text.strip()
    await state.update_data(rating=rating)
    buttons = [[KeyboardButton(text="Пропустить →")]]
    keyboard = create_keyboard(buttons)
    await message.answer("Оставьте отзыв о проф пробе (необязательно):", reply_markup=keyboard)
    await state.set_state(Form.review)

@dp.message(Form.review)
async def handle_review(message: types.Message, state: FSMContext):
    review = message.text.strip()
    await state.update_data(review=review if review != "Пропустить →" else "Отзыв не предоставлен")
    user_data = await state.get_data()
    response = f"Ваши данные:\nФИО: {user_data.get('fio')}\nТелефон: {user_data.get('phone')}\nКласс: {user_data.get('school_class')}\nПроф проба: {user_data.get('prof_prob')}\nОценка: {user_data.get('rating')}\nОтзыв: {user_data.get('review')}"
    buttons = [[KeyboardButton(text="Отправить"), KeyboardButton(text="Изменить")]]
    keyboard = create_keyboard(buttons)
    await message.answer(response, reply_markup=keyboard)
    await state.set_state(Form.final_choice)

@dp.message(Form.final_choice)
async def handle_final_choice(message: types.Message, state: FSMContext):
    if message.text == "Отправить":
        user_data = await state.get_data()
        add_user_to_google_sheets(user_data)
        await message.answer("Ваши данные сохранены в Google Sheets!", reply_markup=ReplyKeyboardRemove())
        await state.clear()
    elif message.text == "Изменить":
        await message.answer("Введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Form.fio)
    else:
        await message.answer("Выберите 'Отправить' или 'Изменить'.", reply_markup=create_keyboard([[KeyboardButton(text="Отправить"), KeyboardButton(text="Изменить")]]))

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
