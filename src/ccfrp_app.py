# import pandas as pd
from flask import Flask
from datetime import datetime, timedelta
# from tinyflux import TinyFlux
import wrangling

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/home")
def home_page():
    return f"hello. it is {datetime.utcnow()}."

