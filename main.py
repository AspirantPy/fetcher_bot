from logging import getLogger
import re

from telegram import (
    Bot,
    ParseMode,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    utils
)

from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler,
    CallbackQueryHandler, 
    Filters,
    ConversationHandler,
)

# Чтобы точно знать, подключился ли бот к Телеграму или нет:

from telegram.utils.request import Request

from config import load_config

from db import (
    init_db,
    register_questions,
    fetch_messages_from_same_user,
    delete_message_by_id,
    find_user_by_msg_id,
    add_to_hashtag_list,
    parse_hashtags,
    delete_hashtag_from_list
)

config = load_config()
logger = getLogger(__name__)

admins = config.ADMIN_GROUP
channel = config.CHANNEL

button_list = []

user_caption, user_attachment = range(2)
write_question = range(2)
add_or_delete_hashtag, add_hashtag, delete_hashtag = range(3)

def debug_requests(function):
    '''Отладка событий от Телеграма'''

    def wrapper(*args, **kwargs):

        try:
            logger.info(f"Обращение в функцию {function.__name__}")
            return function(*args, **kwargs)
        
        except Exception:
            logger.exception(f"Ошибка в обработчике {function.__name__}")
            raise

    return wrapper

# Идентификаторы статических кнопок

BASE_USER_BUTTON1_INSTRUCTION = 'Инструкция'
BASE_USER_BUTTON2_ASK_TEXT = '/question'
BASE_USER_BUTTON3_ASK_WITH_ATTACHMENT = '/attachment'


CALLBACK_BUTTON1_LEFT = 'callback_button1_left'
CALLBACK_BUTTON2_CENTRE = 'callback_button2_centre'
CALLBACK_BUTTON3_RIGHT = 'callback_button3_right'
CALLBACK_BUTTON4_BOTTOM = 'callback_button4_bottom'

TITLES = {
    CALLBACK_BUTTON1_LEFT: "Хэштэги",
    CALLBACK_BUTTON2_CENTRE: "Сгруппировать",
    CALLBACK_BUTTON3_RIGHT: "Удалить",
    CALLBACK_BUTTON4_BOTTOM: "Опубликовать"
}


# Каждый список внутри "keyboard" - один горизонтальный ряд кнопок; каждый элемент внутри списка - вертикальный столбец, сколько кнопок - столько столбцов

@debug_requests

def base_user_keyboard():

    keyboard = [
        [
            KeyboardButton(BASE_USER_BUTTON1_INSTRUCTION),
            KeyboardButton(BASE_USER_BUTTON2_ASK_TEXT),
            KeyboardButton(BASE_USER_BUTTON3_ASK_WITH_ATTACHMENT),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


@debug_requests

def get_base_inline_keyboard():

    keyboard = [        
        [
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON1_LEFT], callback_data=CALLBACK_BUTTON1_LEFT),
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON2_CENTRE], callback_data=CALLBACK_BUTTON2_CENTRE),
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON3_RIGHT], callback_data=CALLBACK_BUTTON3_RIGHT)
        ],
        [   InlineKeyboardButton(TITLES[CALLBACK_BUTTON4_BOTTOM], callback_data=CALLBACK_BUTTON4_BOTTOM)
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


@debug_requests

def build_menu(buttons,n_cols,header_buttons=None,footer_buttons=None):

    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)

    return menu


@debug_requests

def dynamic_inline_keyboard():

    global button_list

    list_of_hashtags = parse_hashtags()

    button_list = []

    for each in list_of_hashtags:
        button_list.append(InlineKeyboardButton(each, callback_data = each))


    return InlineKeyboardMarkup(build_menu(button_list,n_cols=3)) #n_cols = number of columns


# Обработчик всех кнопок со всех подстрочных клавиатур.
# Слишком старые сообщения нельзя редактировать (старше 48 ч.) - ограничение Телеграма!

@debug_requests

def keyboard_callback_handler(update, context, chat_data=None, **kwargs):

    query = update.callback_query
    data = query.data

    incoming_message = update.effective_message

    message_type = utils.helpers.effective_message_type(incoming_message)

    current_text = incoming_message.text or incoming_message.caption

    if data == CALLBACK_BUTTON1_LEFT:

        try: 
            
            if message_type == 'text': query.edit_message_text(text=current_text, reply_markup=dynamic_inline_keyboard())

            else: query.edit_message_caption(caption=current_text, reply_markup=dynamic_inline_keyboard())          

        except:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"{current_text}", reply_markup=get_base_inline_keyboard())
            context.bot.send_message(chat_id=update.effective_chat.id, text="Хэштэгов в базе пока нет или вы их уже добавили к сообщению")
        
        
    elif data == CALLBACK_BUTTON2_CENTRE:

        try:
            actual_name = re.findall("^Вопрос от (.+):", current_text, re.DOTALL)[0]

            fetched_msg_ids = fetch_messages_from_same_user(actual_name=actual_name.strip())
            extracted_ids = [i for tuple in fetched_msg_ids[0] for i in tuple]
            fetched_messages = [message for tuple in fetched_msg_ids[1] for message in tuple]

            temp_str = "\n".join(fetched_messages)
            clean_results = f"Вопрос от {actual_name}:\n\n{temp_str}"

            if message_type == 'text':

                sent = context.bot.send_message(chat_id=update.effective_chat.id, text=f"{clean_results}", reply_markup=get_base_inline_keyboard())
                new_message_id = sent.message_id
                for i in extracted_ids: context.bot.delete_message(chat_id=update.effective_chat.id, message_id=i)


            else:

                query.edit_message_caption(caption=f"{clean_results}", reply_markup=get_base_inline_keyboard())
                new_message_id = query.message.message_id #though it isn't new

                for i in extracted_ids: 

                    if int(i) != new_message_id:

                        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=i)

            try:

                register_questions(user_id=fetched_msg_ids[2][0], message=temp_str, actual_name=actual_name, admins_msg_id=new_message_id)
        
            except TypeError:

                context.bot.send_message(chat_id=update.effective_chat.id, text="В базе данных информации об этом сообщении уже нет.")
            
        except IndexError:

            context.bot.send_message(chat_id=update.effective_chat.id, text="В базе данных информации об этом сообщении уже нет.")


    elif data == CALLBACK_BUTTON3_RIGHT:

        to_delete = query.message.message_id
        delete_message_by_id(admins_msg_id=to_delete)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=to_delete)

    elif data == CALLBACK_BUTTON4_BOTTOM:

        to_delete = query.message.message_id

        if message_type == 'text':
          
            inquirer_id = find_user_by_msg_id(admins_msg_id=to_delete)

            published = context.bot.send_message(chat_id=channel, text=current_text)
            context.bot.delete_message(chat_id=admins, message_id=to_delete)
            answer_id = published.message_id
            context.bot.send_message(chat_id=inquirer_id[0], text=f"LINK TO THE ANSWER ON YOUR CHANNEL HERE") #https://t.me/yourchannel/{answer_id}
    
        elif message_type == 'document':

            inquirer_id = find_user_by_msg_id(admins_msg_id=to_delete)
            fileID = query.message['document']['file_id']
            published = context.bot.send_document(chat_id=channel, caption=current_text, document=fileID)
            context.bot.delete_message(chat_id=admins, message_id=to_delete)
            answer_id = published.message_id
            context.bot.send_message(chat_id=inquirer_id[0], text=f"LINK TO THE ANSWER ON YOUR CHANNEL HERE") #https://t.me/yourchannel/{answer_id}
        
        elif message_type == 'photo':

            inquirer_id = find_user_by_msg_id(admins_msg_id=to_delete)
            fileID = query.message['photo'][-1]['file_id']
            published = context.bot.send_photo(chat_id=channel, caption=current_text, photo=fileID)
            context.bot.delete_message(chat_id=admins, message_id=to_delete)
            answer_id = published.message_id
            context.bot.send_message(chat_id=inquirer_id[0], text=f"LINK TO THE ANSWER ON YOUR CHANNEL HERE") #https://t.me/yourchannel/{answer_id}

    elif data == 'Готово':
        
        if message_type == 'text': query.edit_message_text(text = current_text, reply_markup=get_base_inline_keyboard())    
        else: query.edit_message_caption(caption=current_text, reply_markup=get_base_inline_keyboard())

    elif data == button_list[0]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[0]['text']
        else: modified_text = current_text + '\n' + button_list[0]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())
        
    elif data == button_list[1]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[1]['text']
        else: modified_text = current_text + '\n' + button_list[1]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[2]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[2]['text']
        else: modified_text = current_text + '\n' + button_list[2]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[3]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[3]['text']
        else: modified_text = current_text + '\n' + button_list[3]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[4]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[4]['text']
        else: modified_text = current_text + '\n' + button_list[4]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[5]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[5]['text']
        else: modified_text = current_text + '\n' + button_list[5]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[6]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[6]['text']
        else: modified_text = current_text + '\n' + button_list[6]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[7]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[7]['text']
        else: modified_text = current_text + '\n' + button_list[7]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[8]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[8]['text']
        else: modified_text = current_text + '\n' + button_list[8]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[9]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[9]['text']
        else: modified_text = current_text + '\n' + button_list[9]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[10]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[10]['text']
        else: modified_text = current_text + '\n' + button_list[10]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[11]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[11]['text']
        else: modified_text = current_text + '\n' + button_list[11]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[12]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[12]['text']
        else: modified_text = current_text + '\n' + button_list[12]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())

    elif data == button_list[13]['text']:

        if '#' in current_text: modified_text = current_text + ' ' + button_list[13]['text']
        else: modified_text = current_text + '\n' + button_list[13]['text']

        if message_type == 'text': query.edit_message_text(text = modified_text, reply_markup=dynamic_inline_keyboard())
        else: query.edit_message_caption(caption=modified_text, reply_markup=dynamic_inline_keyboard())


@debug_requests

def do_start(update, context):
    '''Greets a new user'''

    user = update.message.from_user
    local_chat_id=update.effective_chat.id

    if not context.bot.get_chat_member(chat_id=local_chat_id, user_id = update.message.from_user.id) in context.bot.get_chat_administrators(chat_id=admins):

        actual_name = user.first_name #should be used for greeting
        context.bot.send_message(chat_id=local_chat_id, 
            text=f"YOUR GREETING HERE",
            parse_mode=ParseMode.HTML,
            reply_markup=base_user_keyboard()
        )

    else: context.bot.send_message(chat_id=local_chat_id, text='Эта команда не работает в канале для администраторов')


@debug_requests

def user_reply_keyboard_data(update, context):

    msg = update.message.text

    if msg == BASE_USER_BUTTON1_INSTRUCTION:

        return do_start(update=update, context=context)

    elif msg == BASE_USER_BUTTON2_ASK_TEXT: pass
    
    elif msg == BASE_USER_BUTTON3_ASK_WITH_ATTACHMENT: pass

    else: pass


@debug_requests

def do_question(update, context):
    '''Sends question with text only to admin for processing'''

    context.bot.send_message(chat_id=update.effective_chat.id, text="Что бы вы хотели спросить? Просьба по возможности продумать ваш вопрос и уместить его в одном сообщении, а не разбивать на несколько частей! Для вопросов с вложением используйте команду /attachment")

    return write_question


@debug_requests

def user_writes_question(update, context):

    msg = update.message.text

    try:

        actual_name = update.message.from_user.first_name
        user_id=update.message.from_user.id
        update.message.reply_text("Спасибо за вопрос, как только мы его обработаем, пришлем вам ссылку на пост с ответом на нашем канале YOUR CHANNEL HERE")

        sent = context.bot.send_message(chat_id=admins, text=f'Вопрос от {actual_name}:\n' + msg, reply_markup=get_base_inline_keyboard())
        message_id = sent.message_id
        register_questions(user_id=user_id, message=msg, actual_name=actual_name, admins_msg_id=message_id)

        return ConversationHandler.END
    
    except TypeError:

        invalid_input(update, context)


@debug_requests

def do_send_attachment(update, context):

    context.bot.send_message(chat_id=update.effective_chat.id, text="Это команда для пересылки фото или документов администраторам, если вы хотите проиллюстрировать ваш вопрос")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста, напишите сначала ваш вопрос, я прикреплю его к документу. Максимальная длина сообщения - 900 символов") # to reserve space for admin hashtags

    return user_caption


@debug_requests

def store_attachment_caption(update, context):

    caption = update.message.text

    # Store value
    context.user_data['user_caption'] = caption

    context.bot.send_message(chat_id=update.effective_chat.id, text="Спасибо, а теперь перетащите фото или документ в это окно. Ограничение по размеру файла: 10 Мб")

    return user_attachment


# ограничение caption = 0-1240 символов; ограничение размера для фото - 10 Мб; ограничение ширины и высоты - 10000
# user_data is a unique dict per user, erased when script terminates.

@debug_requests

def user_sends_attachment(update, context):

    value = context.user_data.get('user_caption', 'Not found')
    actual_name = update.message.from_user.first_name
    user_id=update.message.from_user.id

    if update.message['photo'] == []:
        fileID = update.message['document']['file_id']
        fileName = update.message['document']['file_name']
        sent = context.bot.send_document(chat_id=admins, caption=f'Вопрос от {actual_name}:\n' + value, document=fileID, reply_markup=get_base_inline_keyboard())
    
    else:

        fileID = update.message['photo'][-1]['file_id']
        sent = context.bot.send_photo(chat_id=admins, caption=f'Вопрос от {actual_name}:\n' + value, photo=fileID, reply_markup=get_base_inline_keyboard())

    admins_msg_id = sent.message_id
    register_questions(user_id=user_id, message=value, actual_name=actual_name, admins_msg_id=admins_msg_id)
    context.bot.send_message(chat_id=user_id, text="Спасибо за вопрос, как только мы его обработаем, пришлем вам ссылку на пост с ответом на нашем канале YOUR CHANNEL HERE")

    return ConversationHandler.END


@debug_requests

def invalid_input(update, context):
    update.message.reply_text("Неправильный ввод, отменяю операцию")

    return ConversationHandler.END


@debug_requests

def do_admin_add_hashtag(update,context):
    '''Adds or removes hashtags from user input in TG client, to be used for dynamically created keyboard'''

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id == admins:

        if context.bot.get_chat_member(chat_id=admins, user_id=user_id)['status'] == 'administator' or 'creator':

            context.bot.send_message(chat_id=chat_id, text='Удалить или добавить хэштэг?')

            return add_or_delete_hashtag
        
        else: print(f"Unauthorized access denied for {user_id}.")
    
    else: print(f"Unauthorized access denied for {user_id}.")


@debug_requests

def admin_add_or_delete_hashtag(update, context):

    chat_id=update.effective_chat.id

    if update.message.text == 'добавить':
            
        context.bot.send_message(chat_id=chat_id, text='Пишем')

        return add_hashtag

    elif update.message.text == 'удалить':

        context.bot.send_message(chat_id=chat_id, text='Какой хэштэг удалить?')

        return delete_hashtag


@debug_requests

def admin_adding(update, context):

    hashtag = update.message.text
    result = add_to_hashtag_list(hashtag=hashtag)

    if result[1] <= 15:

        if result[0] is False:

            context.bot.send_message(chat_id=update.effective_chat.id, text='Такой хэштэг уже есть')

            return ConversationHandler.END

        else:

            context.bot.send_message(chat_id=update.effective_chat.id, text='Добавил')

            return ConversationHandler.END
    
    else:

        context.bot.send_message(chat_id=update.effective_chat.id, text='Можно добавить максимум 15 хэштэгов (включая кнопку "Готово")')

        return ConversationHandler.END


@debug_requests

def admin_deleting(update, context):

    hashtag = update.message.text
    result = delete_hashtag_from_list(hashtag=hashtag)

    if result is False:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Такого хэштэга в у меня в списке нет')

        return ConversationHandler.END
    
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Удалил')

        return ConversationHandler.END


@debug_requests

def main():
    logger.info("Starting the bot")

    req = Request(
        connect_timeout=1.0, # 0.5
        read_timeout=2.0,    # 1.0
    )

    # Pre-initialized bot is used, so we have to create it using a Request instance with a large enough connection pool.
    # Add base_url param if you need to use a proxy (base_url=config.TG_API_URL)

    bot = Bot(
        token=config.TG_API_TOKEN,
        request=req,
    )

    updater = Updater(bot=bot, use_context=True)

    # Проверка, подключились или нет

    info = bot.get_me()
    logger.info(f'Bot info: {info}')

    init_db()

    dp = updater.dispatcher

    user_question_conv = ConversationHandler(
        entry_points=[CommandHandler('question', do_question)],
        states={
            write_question: [MessageHandler(Filters.text & ~Filters.command, user_writes_question)]
        },
        fallbacks=[MessageHandler(Filters.command, invalid_input)]
    )

    user_sends_photo = ConversationHandler(
        entry_points=[CommandHandler('attachment', do_send_attachment)],
        states={
            user_caption: [MessageHandler(Filters.text & ~Filters.command, store_attachment_caption)],
            user_attachment: [MessageHandler(Filters.photo | Filters.document, user_sends_attachment)],
        },
        fallbacks=[MessageHandler(Filters.command, invalid_input)]
    )

    working_with_hashtags = ConversationHandler(
        entry_points=[CommandHandler('hashtag', do_admin_add_hashtag)],
        states={
            add_or_delete_hashtag: [MessageHandler(Filters.text & ~Filters.command, admin_add_or_delete_hashtag)],
            add_hashtag: [MessageHandler(Filters.text & ~Filters.command, admin_adding)],
            delete_hashtag: [MessageHandler(Filters.text & ~Filters.command, admin_deleting)],
        },
        fallbacks=[MessageHandler(Filters.command, invalid_input)]
    )


    dp.add_handler(working_with_hashtags)
    dp.add_handler(user_question_conv)
    dp.add_handler(user_sends_photo)

    dp.add_handler(CommandHandler('start', do_start))
    dp.add_handler(MessageHandler(Filters.text, user_reply_keyboard_data))

    buttons_handler = CallbackQueryHandler(callback=keyboard_callback_handler, pass_chat_data=True)
    dp.add_handler(buttons_handler)

    # Начать обработку всех входящих сообщений
    updater.start_polling()

    # Не прерывать скрипт до обработки всех сообщений
    updater.idle()
    logger.info('Bot has been stopped')


if __name__ == "__main__": main()