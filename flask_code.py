#!/usr/bin/env python3

from flask import Flask
from os import getenv
 
app = Flask(__name__)
 
 
@app.route('/')
def hello_world():
    return {'git_hash': getenv('GIT_HASH')}


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)

