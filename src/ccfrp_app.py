# import pandas as pd
from flask import Flask, render_template, request
from datetime import datetime, timedelta
# from tinyflux import TinyFlux
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from api import Api
# from . import app


def create_app():
    app = Flask(__name__, template_folder='templates')
    from . import auth
    app.register_blueprint(auth.bp)
    return app

app = create_app()

@app.route("/")
def index():
    return render_template('base.html')


@app.route("/home")
def home_page():
    return f"hello. it is {datetime.utcnow()}."


@app.route("/fish/length", methods = ['GET', 'POST'])
def fish_length():
    api = Api()
    if request.method == 'GET':
        return render_template(
            'select_fish.html',
            fishes = (api.species.Common_Name.unique(), api.species.Common_Name.unique()[0]),
            dates = (sorted(api.length.Date.unique()), api.length.Date.min())
            )
    elif request.method == 'POST':
        df = api.get_df(
            'length',
            common_name=request.form.get('fish'),
            start_date =request.form.get('start_date'),
            )
        print(request.form)
        return render_template(
            'select_fish.html',
            fishes = (api.species.Common_Name.unique(), request.form.get('fish')),
            table = df.to_html(),
            dates = (sorted(api.length.Date.unique()), request.form.get('start_date'))
            )
