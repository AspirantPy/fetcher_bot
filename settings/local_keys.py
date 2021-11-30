import logging.config


# str!
TG_API_TOKEN = 'YOUR BOT TOKEN'


#INT!
ADMIN_GROUP = 'INSERT_DESIRED_CHAT_ID'

# int!
CHANNEL = 'INSERT_DESIRED_CHAT_ID'


# This is for when you need to use a proxy, if TG is blocked
#TG_API_URL = "https://<...>"

#'' means default logger

LOGGING = {
    'disable_existing_loggers': True,
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(module)s.%(funcName)s | %(asctime)s | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
logging.config.dictConfig(LOGGING)