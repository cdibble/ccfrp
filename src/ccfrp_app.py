# import pandas as pd
from flask import Flask, render_template, request
# from flask_bootstrap import Bootstrap
# from flask_datepicker import datepicker

from datetime import datetime, timedelta
# from tinyflux import TinyFlux
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from api import Api
from wtforms.fields import DateField, SubmitField, SelectField
from wtforms.validators import InputRequired
from flask_wtf import FlaskForm


def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config['SECRET_KEY'] = 'poopypants'
    from . import auth
    app.register_blueprint(auth.bp)
    return app

app = create_app()

class TimeForm(FlaskForm):
    start_date = DateField('start_date')
    end_date = DateField('end_date')
    submit = SubmitField('Submit')
    

@app.route("/")
def index():
    return render_template('base.html')


@app.route("/home")
def home_page():
    return f"hello. it is {datetime.utcnow()}."


@app.route("/fish/length", methods = ['GET', 'POST'])
def fish_length():
    api = Api()
    all_species=api.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    if not form.is_submitted():
        default_start = api.length.Date.min().date().isoformat()
        default_end = (api.length.Date.max() + timedelta(days=1)).date().isoformat()
        return render_template(
            'select_fish.html',
            form = form,
            default_start = default_start,
            default_end = default_end
            )
    else:
        df = api.get_df(
            'length',
            common_name=form.data.get('fish_name'),
            start_time=form.data.get('start_date'),
            end_time=form.data.get('end_date'),
            )
        return render_template(
            'select_fish.html',
            form=form,
            table = df.sort_values('Date').to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )
