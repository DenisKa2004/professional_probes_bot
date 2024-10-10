import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv 

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal, UserData, engine  # Импортируем необходимые элементы из database.py

# Инициализация бота и диспетчера с хранилищем состояний
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')  # Убедитесь, что DATABASE_URL установлен в .env

bot = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Список проф проб (можно изменить на любые другие)
prof_prob_list = ["Основы работы с нейросетями и их обучение", "Кабельная система локальной сети", "Сборка-разборка персонального компьютера", "Анимация «трансформация» в Power Point", "Разработка приложения «1С: Школьный дневник»"]

# Состояние
class Form(StatesGroup):
    consent = State()        # Согласие на обработку персональных данных
    fio = State()            # Ввод ФИО
    phone = State()          # Ввод номера телефона
    school_class = State()   # Ввод класса обучения
    prof_prob = State()      # Выбор проф пробы
    rating = State()         # Оценка проф пробы
    review = State()         # Отзыв (необязательно)
    final_choice = State()   # Выбор "Отправить" или "Изменить"

# Функция для создания клавиатуры из списка кнопок
def create_keyboard(buttons):
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

# Согласие на обработку данных
@dp.message(CommandStart())
async def hand_start(message: types.Message, state: FSMContext):
    buttons = [
        [KeyboardButton(text="Согласен")]
    ]
    keyboard = create_keyboard(buttons)
    await message.answer("Вы согласны на обработку персональных данных?", reply_markup=keyboard)
    await state.set_state(Form.consent)

# Обработка согласия
@dp.message(Form.consent)
async def handle_consent(message: types.Message, state: FSMContext):
    if message.text == "Согласен":
        await message.answer("Пожалуйста, введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Form.fio)
    else:
        await message.answer("Для продолжения требуется согласие на обработку персональных данных.", reply_markup=ReplyKeyboardRemove())
        await state.clear()

# Ввод ФИО
@dp.message(Form.fio)
async def handle_fio(message: types.Message, state: FSMContext):
    fio = message.text.strip()
    if not fio:
        await message.answer("ФИО не может быть пустым. Пожалуйста, введите ваше ФИО:")
        return
    await state.update_data(fio=fio)
    await message.answer("Введите ваш номер телефона:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Form.phone)

# Ввод номера телефона
@dp.message(Form.phone)
async def handle_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not phone:
        await message.answer("Номер телефона не может быть пустым. Пожалуйста, введите ваш номер телефона:")
        return
    await state.update_data(phone=phone)
    
    # Создаём клавиатуру с выбором класса (8-11 классы) - Горизонтальная клавиатура
    class_buttons = [[KeyboardButton(text=str(i)) for i in range(8, 12)]]
    keyboard = create_keyboard(class_buttons)
    await message.answer("Выберите ваш класс обучения:", reply_markup=keyboard)
    await state.set_state(Form.school_class)

# Ввод класса обучения и выбор проф пробы
@dp.message(Form.school_class)
async def handle_class(message: types.Message, state: FSMContext):
    school_class = message.text.strip()
    if school_class not in ["8", "9", "10", "11"]:
        await message.answer("Пожалуйста, выберите ваш класс обучения.")
        return
    await state.update_data(school_class=school_class)

    # Создаём клавиатуру с выбором проф пробы
    buttons = [[KeyboardButton(text=prof_prob)] for prof_prob in prof_prob_list]
    keyboard = create_keyboard(buttons)
    await message.answer("Выберите проф пробу:", reply_markup=keyboard)
    await state.set_state(Form.prof_prob)

# Выбор проф пробы и оценка
@dp.message(Form.prof_prob)
async def handle_prof_prob(message: types.Message, state: FSMContext):
    selected_prob = message.text.strip()
    if selected_prob not in prof_prob_list:
        await message.answer("Пожалуйста, выберите проф пробу из списка.")
        return
    await state.update_data(prof_prob=selected_prob)

    # Создаём горизонтальную клавиатуру с оценками от 1 до 5
    rating_buttons = [[KeyboardButton(text=str(i)) for i in range(1, 6)]]
    keyboard = create_keyboard(rating_buttons)
    await message.answer("Оцените выбранную профпробу по шкале от 1 до 5, где 1 — очень плохо, а 5 — отлично:", reply_markup=keyboard)
    await state.set_state(Form.rating)

# Оценка проф пробы
@dp.message(Form.rating)
async def handle_rating(message: types.Message, state: FSMContext):
    rating = message.text.strip()
    if rating not in [str(i) for i in range(1, 6)]:
        await message.answer("Пожалуйста, выберите оценку от 1 до 5.")
        return
    await state.update_data(rating=int(rating))

    # Клавиатура для отзыва с кнопкой пропустить
    buttons = [
        [KeyboardButton(text="Пропустить →")]
    ]
    keyboard = create_keyboard(buttons)
    await message.answer("Оставьте отзыв о проф пробе (необязательно):", reply_markup=keyboard)
    await state.set_state(Form.review)

# Показываем собранные данные и предлагаем кнопки "Отправить" и "Изменить"
@dp.message(Form.review)
async def handle_review(message: types.Message, state: FSMContext):
    if message.text.strip() == "Пропустить →":
        review = "Отзыв не предоставлен"
    else:
        review = message.text.strip()
        if not review:
            await message.answer("Отзыв не может быть пустым. Пожалуйста, оставьте отзыв или нажмите 'Пропустить →':")
            return
    await state.update_data(review=review)

    # Собираем все данные
    user_data = await state.get_data()
    response = (
        f"Спасибо! Вот ваши данные:\n\n"
        f"ФИО: {user_data.get('fio')}\n"
        f"Телефон: {user_data.get('phone')}\n"
        f"Класс: {user_data.get('school_class')}\n"
        f"Проф проба: {user_data.get('prof_prob')}\n"
        f"Оценка: {user_data.get('rating')}\n"
        f"Отзыв: {user_data.get('review')}"
    )

    # Добавляем кнопки "Отправить" и "Изменить"
    buttons = [
        [KeyboardButton(text="Отправить"), KeyboardButton(text="Изменить")]
    ]
    keyboard = create_keyboard(buttons)
    await message.answer(response, reply_markup=keyboard)
    
    # Устанавливаем новое состояние для выбора действия
    await state.set_state(Form.final_choice)

# Обработка финального выбора
@dp.message(Form.final_choice)
async def handle_final_choice(message: types.Message, state: FSMContext):
    if message.text == "Отправить":
        user_data = await state.get_data()
        telegram_id = message.from_user.id
        async with SessionLocal() as session:
            try:
                # Проверяем, существует ли уже запись для этого пользователя
                stmt = select(UserData).where(UserData.telegram_id == telegram_id)
                result = await session.execute(stmt)
                existing_user = result.scalars().first()

                if existing_user:
                    # Если запись существует, обновляем её
                    existing_user.fio = user_data.get('fio')
                    existing_user.phone = user_data.get('phone')
                    existing_user.school_class = user_data.get('school_class')
                    existing_user.prof_prob = user_data.get('prof_prob')
                    existing_user.rating = user_data.get('rating')
                    existing_user.review = user_data.get('review')
                else:
                    # Если записи нет, создаём новую
                    new_user = UserData(
                        telegram_id=telegram_id,
                        fio=user_data.get('fio'),
                        phone=user_data.get('phone'),
                        school_class=user_data.get('school_class'),
                        prof_prob=user_data.get('prof_prob'),
                        rating=user_data.get('rating'),
                        review=user_data.get('review')
                    )
                    session.add(new_user)
                
                await session.commit()
                await message.answer("Ваши данные успешно сохранены!", reply_markup=ReplyKeyboardRemove())
                await state.clear()
            except SQLAlchemyError as e:
                await message.answer("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.", reply_markup=ReplyKeyboardRemove())
                logging.error(f"Database error: {e}")
                await state.clear()
    elif message.text == "Изменить":
        # Позволяем пользователю начать заново
        await message.answer("Пожалуйста, введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Form.fio)
    else:
        await message.answer("Пожалуйста, выберите одну из предложенных опций: 'Отправить' или 'Изменить'.", reply_markup=create_keyboard([
            [KeyboardButton(text="Отправить"), KeyboardButton(text="Изменить")]
        ]))

# Обработка любых других сообщений
@dp.message()
async def fallback(message: types.Message):
    await message.answer("Пожалуйста, следуйте инструкциям или используйте команду /start для начала.", reply_markup=ReplyKeyboardRemove())

# Основная функция для запуска бота
async def main():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
