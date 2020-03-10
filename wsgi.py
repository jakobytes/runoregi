from flask import Flask
import os

application = Flask(__name__)


@application.route('/')
def hello_world():
    text = 'Hello, World! The DB name is: {}'.format(os.getenv('DB_NAME'))
    return text

if __name__ == '__main__':
    application.run()
