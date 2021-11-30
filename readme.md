# Educhannel_bot

<div style="text-align: justify"> Бот работает с группой администраторов, каналом и группой для обсуждений постов с канала. Основной фунционал для админов доступен только в админской группе.

Бот пересылает сообщения пользователей администраторам, которые могут 1) группировать несколько сообщений (включая фото и видео) от одного и того же пользователя, 2) добавить к сообщению хэштэги (без ограничения), 3) удалить и 4) опубликовать на канале. После публикации пользователям, задавшим вопрос, приходит ссылка с оповещением.

Администраторы также могут добавлять к подстрочной клавиатуре новые кнопки с хэштэгами прямо в клиенте Телеграма, и удалять их. Максимальное количество хэштэгов – 14. Этим функционалом можно воспользоваться с помощью команды `/hashtag` и ключевых слов `добавить` и `удалить`.

Вся информация о пользователях удаляется из базы данных после обработки их вопросов администраторами.

Для удобства пользователей, в личном чате с ботом есть простой интерфейс с клавиатурой. На ней три кнопки для быстрого вызова команд `/start` (инструкция/приветствие и вызов пользовательской клавиатуры), `/question` (задать вопрос администраторам) и `/attachment` (задать вопрос с вложением фото или документа).

### Ограничения:

- Отреагировать на сообщения пользователей нужно в течение 48 часов, после этого манипуляции с ними могут быть невозможны из-за ограничений Телеграма.

- Сообщения от пользователей, которые бот транслирует администраторам, нужно удалять кнопкой "удалить" в меню сообщения, иначе в базе останется лишняя информация, что может привести к некорректной работе.

- Когда группируете несколько сообщений от пользователя, и если одно из них с фото или документом, жмите на кнопку "сгруппировать" конкретно под фото, иначе сгруппируется только текст, а вложение пропадет.

Бот подойдет для образовательных каналов.</div>