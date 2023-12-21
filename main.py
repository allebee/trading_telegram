import csv
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import datetime
import json

# Load configuration from JSON file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Access configuration values
API_TOKEN = config['API_TOKEN']
ADMIN_PASSWORD = config['ADMIN_PASSWORD']
CSV_FILE = config['CSV_FILE']
IMAGE_DIR = config['IMAGE_DIR']
USER_STATS_FILE = config['USER_STATS_FILE']
USER_IDS_FILE = config['USER_IDS_FILE']
ADMIN_USER_IDS = config['ADMIN_USER_IDS']
print(ADMIN_USER_IDS)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


# Define fieldnames for the user statistics CSV file
USER_STATS_FIELDNAMES = ['day', 'week', 'month', 'total',
                         'last_update_week']
USER_IDS_FILE = 'user_ids.txt'


# States
request_count_24h = 0
request_count_7d = 0
request_count_30d = 0
total_request_count = 0


class Form(StatesGroup):
    role = State()
    password = State()
    edit_coin = State()
    edit_timeframe = State()
    edit_price = State()
    edit_image = State()
    user_coin = State()
    user_timeframe = State()
    send_message_to_all = State()


def store_user_ids(user_ids, filename):
    """Stores user IDs in a text file."""

    with open(filename, 'w') as file:
        for user_id in user_ids:
            file.write(f"{user_id}\n")


def read_user_ids(filename):
    """Reads user IDs from a text file."""

    user_ids = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                user_ids.append(int(line.strip()))
    except FileNotFoundError:
        pass  # If the file doesn't exist, return an empty list
    return user_ids


# def count_requests_last_24_hours():
#     """Counts user requests in the last 24 hours."""

#     current_timestamp = datetime.datetime.now().timestamp()
#     last_24_hours = 24 * 60 * 60  # 24 hours in seconds

#     count = 0
#     for user_id, timestamp in user_request_timestamps.items():
#         if current_timestamp - timestamp <= last_24_hours:
#             count += 1

#     return count


# def count_requests_last_7_days():
#     """Counts user requests in the last 7 days."""

#     current_timestamp = datetime.datetime.now().timestamp()
#     last_7_days = 7 * 24 * 60 * 60  # 7 days in seconds

#     count = 0
#     for user_id, timestamp in user_request_timestamps.items():
#         if current_timestamp - timestamp <= last_7_days:
#             count += 1

#     return count


# def count_requests_last_month():
#     """Counts user requests in the last month."""

#     current_timestamp = datetime.datetime.now().timestamp()
#     last_month = 30 * 24 * 60 * 60  # Approximately 30 days in seconds

#     count = 0
#     for user_id, timestamp in user_request_timestamps.items():
#         if current_timestamp - timestamp <= last_month:
#             count += 1

#     return count


def update_request_counts():
    """Updates various request count variables."""

    global request_count_24h, request_count_7d, request_count_30d, total_request_count

    with open(USER_STATS_FILE, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            request_count_24h = int(row['day'])
            request_count_7d = int(row['week'])
            request_count_30d = int(row['month'])
            total_request_count = int(row['total'])


def go_back_button():
    """Generates a "Go Back" button for inline keyboard."""

    button = types.InlineKeyboardButton("Go Back", callback_data="go_back")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(button)
    return keyboard


async def send_message_to_all_users(message_text, user_ids):

    """ Sends a message to all users."""

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message_text)
        except Exception as e:
            print(f"Error sending message to user {user_id}: {str(e)}")


def read_data():
    """Reads data from a CSV file."""

    crypto_data = {}
    with open(CSV_FILE, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            coin = row['coin']
            crypto_data[coin] = {
                'day': {
                    'price': float(row['day_price']),
                    'image': row['day_image']
                },
                'week': {
                    'price': float(row['week_price']),
                    'image': row['week_image']
                },
                'month': {
                    'price': float(row['month_price']),
                    'image': row['month_image']
                }
            }
    return crypto_data

# Function to write data to the CSV file


def read_user_stats():
    """Reads user statistics from a CSV file."""

    user_stats = {
        'day': 0,
        'week': 0,
        'month': 0,
        'total': 0,
        'last_update_week': None
    }
    try:
        with open(USER_STATS_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                user_stats['day'] = int(row['day'])
                user_stats['week'] = int(row['week'])
                user_stats['month'] = int(row['month'])
                user_stats['total'] = int(row['total'])
                user_stats['last_update_week'] = row['last_update_week']
    except FileNotFoundError:
        pass  # If the file doesn't exist, start with default values
    return user_stats


def write_data(crypto_data):
    """Writes data to a CSV file."""

    with open(CSV_FILE, 'w', newline='') as csvfile:
        fieldnames = ['coin', 'day_price', 'day_image',
                      'week_price', 'week_image', 'month_price', 'month_image']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for coin, data in crypto_data.items():
            writer.writerow({
                'coin': coin,
                'day_price': data['day']['price'],
                'day_image': data['day']['image'],
                'week_price': data['week']['price'],
                'week_image': data['week']['image'],
                'month_price': data['month']['price'],
                'month_image': data['month']['image']
            })


async def update_user_statistics():

    """Updates user statistics."""

    global user_statistics

    current_week = datetime.date.today().isocalendar()[1]

    if user_statistics['last_update_week'] != str(current_week):
        user_statistics['week'] = 0
        user_statistics['last_update_week'] = str(current_week)

    user_statistics['day'] += 1
    user_statistics['week'] += 1
    user_statistics['month'] += 1
    user_statistics['total'] += 1

    # Write updated user statistics to CSV file
    with open(USER_STATS_FILE, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=USER_STATS_FIELDNAMES)
        writer.writeheader()
        writer.writerow(user_statistics)


@dp.message_handler(lambda message: message.from_user.id not in read_user_ids(USER_IDS_FILE))
async def handle_new_user(message: types.Message):

    """Handles new user registrations."""
    user_id = message.from_user.id
    user_ids = read_user_ids(USER_IDS_FILE)

    if user_id not in user_ids:
        user_ids.append(user_id)
        store_user_ids(user_ids, USER_IDS_FILE)


@dp.message_handler(commands=['send_to_all'], state='*')
async def send_to_all_users(message: types.Message):

    """Handles the command to send a message to all users."""
    user_id = message.from_user.id
    if user_id in ADMIN_USER_IDS:
        await message.answer("Enter the message you want to send to all users:")
        await Form.send_message_to_all.set()
    else:
        await message.answer("You are not authorized to use this command.")


@dp.message_handler(state=Form.send_message_to_all)
async def process_send_message_to_all(message: types.Message, state: FSMContext):

    """Processes the message to be sent to all users."""
    user_id = message.from_user.id
    if user_id in ADMIN_USER_IDS:
        user_ids = read_user_ids(USER_IDS_FILE)
        message_text = message.text

        await send_message_to_all_users(message_text, user_ids)
        await message.answer(f"Message sent to {len(user_ids)} users.")
        await state.finish()
    else:
        await message.answer("You are not authorized to use this command.")


@dp.message_handler(commands=['send_to_all'], state='*')
async def send_to_all_users(message: types.Message):

    """Handles the command to send a message to all users."""
    user_id = message.from_user.id
    if user_id in ADMIN_USER_IDS:
        await message.answer("Enter the message you want to send to all users:")
        await Form.send_message.set()
    else:
        await message.answer("You are not authorized to use this command.")


# Load data from CSV file at startup
crypto_data = read_data()

# Start command
# Initialize user statistics
user_statistics = read_user_stats()

user_request_timestamps = {}


# Admin password entry


@dp.message_handler(state=Form.password)
async def process_password(message: types.Message, state: FSMContext):

    """Processes the entered password for admin access."""
    if message.text == ADMIN_PASSWORD:
        await message.answer("Password correct. You can now edit the database.")
        await show_coins(message, state, Form.edit_coin)
    else:
        await message.answer("Wrong password, try again:")

# Show coins for selection


@dp.callback_query_handler(lambda c: c.data in crypto_data, state=[Form.edit_coin, Form.user_coin])
async def process_coin(callback_query: types.CallbackQuery, state: FSMContext):

    """Processes the selected coin for editing."""
    coin = callback_query.data
    await state.update_data(coin=coin)
    keyboard = types.InlineKeyboardMarkup()
    for timeframe in ["Day", "Week", "Month"]:
        button = types.InlineKeyboardButton(
            timeframe, callback_data=timeframe.lower())
        keyboard.row(button)
    keyboard.row(types.InlineKeyboardButton(
        "Go Back", callback_data="go_back"))  # Add "Go Back" button
    await callback_query.message.answer(f"Selected {coin}. Choose timeframe:", reply_markup=keyboard)
    current_state = await state.get_state()
    next_state = Form.edit_timeframe if current_state == Form.edit_coin.state else Form.user_timeframe
    await next_state.set()

# Timeframe selection for Admin


@dp.callback_query_handler(lambda c: c.data in ["day", "week", "month"], state=Form.edit_timeframe)
async def process_edit_timeframe(callback_query: types.CallbackQuery, state: FSMContext):

    """Processes the selected timeframe for editing."""
    timeframe = callback_query.data
    await state.update_data(timeframe=timeframe)
    await callback_query.message.answer("Enter the price:")
    await Form.edit_price.set()

# Handler for editing the price and image


@dp.message_handler(state=Form.edit_price)
async def process_edit_price(message: types.Message, state: FSMContext):

    """Processes the entered price for editing."""
    async with state.proxy() as data:
        coin = data['coin']
        timeframe = data['timeframe']
        try:
            price = float(message.text)
            await message.answer(f"Updating price for {coin} ({timeframe}) to: {price}")
            crypto_data[coin][timeframe]['price'] = price
            await message.answer("Now, please send the new image for this coin and timeframe (Day, Week, Month):")
            await Form.edit_image.set()
        except ValueError:
            await message.answer("Please enter a valid number.")

# Handler for receiving the new image


@dp.message_handler(content_types=['photo'], state=Form.edit_image)
async def receive_image(message: types.Message, state: FSMContext):

    """Processes the received image for editing."""
    photo = message.photo[-1]  # Get the largest photo
    file_id = photo.file_id
    async with state.proxy() as data:
        coin = data['coin']
        timeframe = data['timeframe']
        file_path = os.path.join(IMAGE_DIR, coin, f"{timeframe}.png")
        file_info = await bot.get_file(file_id)
        file = await bot.download_file(file_info.file_path)

        # Save the downloaded file to the specified path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as new_image:
            new_image.write(file.read())

        crypto_data[coin][timeframe]['image'] = file_path
        write_data(crypto_data)
        await message.answer("Image updated successfully.")
    await state.reset_state()

# Timeframe selection for User


@dp.callback_query_handler(lambda c: c.data in ["day", "week", "month"], state=Form.user_timeframe)
async def process_user_timeframe(callback_query: types.CallbackQuery, state: FSMContext):

    """Processes the selected timeframe for user requests."""
    global total_request_count
    timeframe = callback_query.data
    user_id = callback_query.from_user.id

    async with state.proxy() as data:
        price = crypto_data[data['coin']][timeframe]['price']
        image_path = crypto_data[data['coin']][timeframe]['image']

        # Get the current timestamp
        current_timestamp = datetime.datetime.now().timestamp()

        # Store the timestamp for the user's request
        user_request_timestamps[user_id] = current_timestamp
        additional_data = {
            "day": (1.3, 4),
            "week": (3, 10),
            "month": (14, 44),
        }
        with open(image_path, 'rb') as image_file:
            await bot.send_photo(
                callback_query.from_user.id,
                photo=image_file,
                caption=(
                    f"Cудя по анализу за последние недели, лучшая зона для покупок {data['coin']} ({timeframe}) это зона : {price} $"
                    f"\n\n\nМожно поставить от этой цены стоп-лосс {additional_data[timeframe][0]}%, и тейк {additional_data[timeframe][1]}%"
                ),
                reply_markup=go_back_button()
            )

        # Increment total_request_count
        total_request_count += 1

        # Update user statistics
        await update_user_statistics()


@dp.message_handler(commands='start', state='*')
async def cmd_start(message: types.Message, callback_query: types.CallbackQuery = None):

    """Handles the start command and role selection for users."""
    user_id = message.from_user.id

    # Welcome message
    welcome_text = (
        """
    Привет! Я твой карманный аналитик . 🤓

    Я работаю таким образом, что анализирую большой объем данных на бирже, и определяю для тебя безопасные точки покупок монет. 

    Что я не делаю:
    ❌Я не даю сигналов на шорт
    ❌Я не даю сигналов на монеты которые уже сильно выросли
    ❌Я не торгую за вас

    Что я могу для вас сделать:
    ✅Вы выбирайте монету
    ✅Выбирайте время сколько готовы ждать пока монета упадет: день, неделя, месяц.
    ✅Отправляю вам по какой цене самая высокая вероятность отскока 
    ✅На страховку говорю где поставить стоп лосс - его нужно ставить обязательно
    ✅И закрепляю график

    Я помогаю людям не сливать депозит, и показать системный трейдинг. 

    Не обещаю что со мной начнете зарабатывать, но как минимум научитесь терпению, и действительно находиться хорошие точки входа в лонг по моим сигналам

    Поехали! Выбирай монету.
    """
    )

    if user_id in ADMIN_USER_IDS:
        # If the user is an admin, show both options
        keyboard = types.InlineKeyboardMarkup()
        admin_button = types.InlineKeyboardButton(
            "Admin", callback_data="admin")
        user_button = types.InlineKeyboardButton("User", callback_data="user")
        keyboard.row(admin_button, user_button)
        text = "Choose your role:"
    else:
        # If the user is not an admin, show only the user option
        keyboard = types.InlineKeyboardMarkup()
        user_button = types.InlineKeyboardButton("User", callback_data="user")
        keyboard.row(user_button)
        text = "Choose your role:"

    if callback_query:
        await callback_query.message.edit_text(welcome_text, reply_markup=keyboard)
    else:
        await message.answer(welcome_text, reply_markup=keyboard)

    await Form.role.set()


@dp.callback_query_handler(lambda c: c.data == "go_back", state="*")
async def go_back(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state == "Form:edit_price":
        # Edit the message to show the coin selection keyboard
        await show_coins(callback_query.message, state, Form.edit_coin, callback_query=callback_query)
    elif current_state == "Form:edit_timeframe":
        # Edit the message to show the role selection keyboard
        await cmd_start(callback_query.message, callback_query=callback_query)
    elif current_state == "Form:edit_coin":
        # Edit the message to ask for the admin password
        await callback_query.message.edit_text("Enter admin password:")
        await Form.password.set()
    elif current_state == "Form:password":
        # Edit the message to show the role selection keyboard
        await cmd_start(callback_query.message, callback_query=callback_query)
    elif current_state == "Form:user_timeframe":
        # Edit the message to show the coin selection keyboard
        await show_coins(callback_query.message, state, Form.user_coin, callback_query=callback_query)
    elif current_state == "Form:user_coin":
        # Edit the message to show the role selection keyboard
        await cmd_start(callback_query.message, callback_query=callback_query)
    elif current_state == "Form:role":
        # Edit the message to restart
        await cmd_start(callback_query.message, callback_query=callback_query)
    else:
        # Handle other cases if needed
        pass


async def show_coins(message, state, next_state, callback_query=None):

    """Displays a list of available coins to the user."""
    keyboard = InlineKeyboardMarkup()
    for coin in crypto_data:
        button = InlineKeyboardButton(coin, callback_data=coin)
        keyboard.row(button)
    keyboard.row(InlineKeyboardButton("Go Back", callback_data="go_back"))
    text = "Choose a coin:"

    # Check if it's a callback_query and edit the message accordingly
    if callback_query:
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)
    await next_state.set()


@dp.callback_query_handler(lambda c: c.data in ["admin", "user"], state=Form.role)
async def process_role(callback_query: types.CallbackQuery, state: FSMContext):

    """Processes the selected role (admin or user) for users."""
    role = callback_query.data
    await state.update_data(role=role)
    if role == 'admin':
        await callback_query.message.answer("Enter admin password:")
        await Form.password.set()
    elif role == 'user':
        await show_coins(callback_query.message, state, Form.user_coin, callback_query)


@dp.message_handler(commands='stats')
async def show_user_stats(message: types.Message):

    """Displays user statistics to admins."""
    user_id = message.from_user.id
    print(user_id)
    print(ADMIN_USER_IDS)
    if user_id in ADMIN_USER_IDS:
        global request_count_24h, request_count_7d, request_count_30d, total_request_count, user_statistics
        # Read user statistics from the CSV file
        user_statistics = read_user_stats()

        # Update the variables
        request_count_24h = user_statistics['day']
        request_count_7d = user_statistics['week']
        request_count_30d = user_statistics['month']
        total_request_count = user_statistics['total']
        user_ids = read_user_ids(USER_IDS_FILE)
        num_users = len(user_ids)
        # Display the updated statistics
        stats_message = (
            # f"User Request Statistics:\n"
            # f"Requests in the last 24 hours: {request_count_24h}\n"
            # f"Requests in the last 7 days: {request_count_7d}\n"
            # f"Requests in the last month: {request_count_30d}\n"
            f"Total requests: {total_request_count}"
            f"\nTotal users: {num_users}"
        )
        await message.answer(stats_message)
    else:
        await message.answer("You are not authorized to use this command.")


# Run the bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
