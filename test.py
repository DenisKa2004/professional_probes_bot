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


# Инициализация бота и диспетчера с хранилищем состояний
load_dotenv()
bot = Bot(os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Список проф проб (можно изменить на любые другие)
prof_prob_list = ["Программа 1", "Программа 2", "Программа 3"]

# Состояния для FSM
class Form(StatesGroup):
    consent = State()        # Согласие на обработку персональных данных
    fio = State()            # Ввод ФИО
    phone = State()          # Ввод номера телефона
    school_class = State()   # Ввод класса обучения
    prof_prob = State()      # Выбор проф пробы
    rating = State()         # Оценка проф пробы
    review = State()         # Отзыв (необязательно)

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
    # Дополнительно можно добавить проверку формата телефона
    await state.update_data(phone=phone)
    await message.answer("Введите ваш класс обучения:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Form.school_class)

# Ввод класса обучения и выбор проф пробы
@dp.message(Form.school_class)
async def handle_class(message: types.Message, state: FSMContext):
    school_class = message.text.strip()
    if not school_class:
        await message.answer("Класс обучения не может быть пустым. Пожалуйста, введите ваш класс обучения:")
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

    # Удаляем клавиатуру после выбора
    await message.answer("Вы выбрали: " + selected_prob, reply_markup=ReplyKeyboardRemove())

    # Создаём клавиатуру с оценками от 1 до 5
    rating_buttons = [[KeyboardButton(text=str(i))] for i in range(1, 6)]
    keyboard = create_keyboard(rating_buttons)
    await message.answer("Оцените выбранную проф пробу от 1 до 5:", reply_markup=keyboard)
    await state.set_state(Form.rating)

# Оценка проф пробы
@dp.message(Form.rating)
async def handle_rating(message: types.Message, state: FSMContext):
    rating = message.text.strip()
    if rating not in [str(i) for i in range(1, 6)]:
        await message.answer("Пожалуйста, выберите оценку от 1 до 5.")
        return
    await state.update_data(rating=rating)

    # Клавиатура для отзыва с кнопкой пропустить
    buttons = [
        [KeyboardButton(text="Скипнуть отзыв")]
    ]
    keyboard = create_keyboard(buttons)
    await message.answer("Оставьте отзыв о проф пробе (необязательно):", reply_markup=keyboard)
    await state.set_state(Form.review)

# Отзыв или скип
@dp.message(Form.review)
async def handle_review(message: types.Message, state: FSMContext):
    if message.text.strip() == "Скипнуть отзыв":
        review = "Отзыв не предоставлен"
    else:
        review = message.text.strip()
        if not review:
            await message.answer("Отзыв не может быть пустым. Пожалуйста, оставьте отзыв или нажмите 'Скипнуть отзыв':")
            return
    await state.update_data(review=review)

    # Удаляем клавиатуру после отзыва
    await message.answer("Спасибо за ваш отзыв!", reply_markup=ReplyKeyboardRemove())

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
    await message.answer(response)
    await state.clear()

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
