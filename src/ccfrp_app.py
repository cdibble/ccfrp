# import pandas as pd
from flask import Flask, render_template, request
# from flask_bootstrap import Bootstrap
# from flask_datepicker import datepicker

from datetime import datetime, timedelta
# from tinyflux import TinyFlux
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from angler import Angler
from wtforms.fields import DateField, SubmitField, SelectField
from wtforms.validators import InputRequired
from flask_wtf import FlaskForm
import plotly_express as px
import plotly
import geojson

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
    angler = Angler()
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    if not form.is_submitted():
        default_start = angler.length.Date.min().date().isoformat()
        default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
        return render_template(
            'select_fish.html',
            form = form,
            default_start = default_start,
            default_end = default_end
            )
    else:
        df = angler.get_df(
            'length',
            common_name=form.data.get('fish_name'),
            start_time=form.data.get('start_date'),
            end_time=form.data.get('end_date'),
            )
        plot =  px.scatter(df, x="Date", y="Length_cm", color="Area", facet_col='Site')
        # graphJSON = json.dumps([plot], cls=plotly.utils.PlotlyJSONEncoder)
        return render_template(
            'select_fish.html',
            form=form,
            table = df.sort_values('Date').to_html(),
            # graphJSON = graphJSON,
            plt_html=plot.to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )



@app.route("/fish/length/map", methods = ['POST'])
def fish_length_map_post():
    from geojson import Polygon, FeatureCollection, dumps, Feature
    angler = Angler()
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    df = angler.get_df(
        'length',
        common_name=form.data.get('fish_name'),
        start_time=form.data.get('start_date'),
        end_time=form.data.get('end_date'),
        )
    # have to filter out nas for geojson
    df = df[~(
        df['lon_1_dd'].isna() |
        df['lon_2_dd'].isna() |
        df['lon_3_dd'].isna() |
        df['lon_4_dd'].isna() |
        df['lat_1_dd'].isna() |
        df['lat_2_dd'].isna() |
        df['lat_3_dd'].isna() |
        df['lat_4_dd'].isna()
    )]
    polys = [
        Feature(
            Polygon([[
                (round(x.get('lon_1_dd'), 5), round(x.get('lat_1_dd'), 5)),
                (round(x.get('lon_2_dd'), 5), round(x.get('lat_2_dd'), 5)),
                (round(x.get('lon_3_dd'), 5), round(x.get('lat_3_dd'), 5)),
                (round(x.get('lon_4_dd'), 5), round(x.get('lat_4_dd'), 5))
                ]],
                ),
            properties={'Area': x.get('Area'), 'Site': x.get('Site')}
            )
            for x in df.to_dict('records')
    ]
    geo = FeatureCollection(polys)
    # dumps(geo)
    fig = px.choropleth_mapbox(
        data_frame=df,
        geojson=dumps(geo), 
        color="Length_cm",
        locations="Area", 
        featureidkey="properties.Site",
        opacity=0.9,
        color_continuous_scale='Viridis',
        center={"lat": df.lat_1_dd.mean(), "lon": df.lon_1_dd.mean()},
        mapbox_style="carto-positron", 
        zoom=9)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    # graphJSON = json.dumps([plot], cls=plotly.utils.PlotlyJSONEncoder)
    return fig.to_html()
    # render_template(
    #     'select_fish.html',
    #     form=form,
    #     table = df.sort_values('Date').to_html(),
    #     # graphJSON = graphJSON,
    #     plt_html=fig.to_html(),
    #     default_start = form.data.get('start_date'),
    #     default_end = form.data.get('end_date'),
    #     )

@app.route("/fish/length/map", methods = ['GET'])
def fish_length_map_get():
    from geojson import Polygon, FeatureCollection, dumps, Feature
    angler = Angler()
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    default_start = angler.length.Date.min().date().isoformat()
    default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
    return render_template(
        'select_fish.html',
        form = form,
        default_start = default_start,
        default_end = default_end
        )