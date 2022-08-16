# import pandas as pd
from flask import Flask, render_template, request, Blueprint, jsonify
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
import json
from api import api
import pandas as pd

def create_app():
    app = Flask('ccfrp_app', template_folder='templates')
    app.config['SECRET_KEY'] = 'poopypants'
    from . import auth
    app.register_blueprint(auth.bp)
    app.register_blueprint(api)
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

# -----------
# Fish Length
# -----------

def melt_df(df):
    mdf = df[['Grid_Cell_ID', 'Area', 'Site', 'lat_1_dd', 'lon_1_dd', 'lat_2_dd','lon_2_dd', 'lat_3_dd', 'lon_3_dd', 'lat_4_dd', 'lon_4_dd']].melt(
        id_vars = ['Grid_Cell_ID', 'Area', 'Site'])
    mdf['point_no'] = mdf.variable.str[4]
    mdf = mdf.groupby(['Grid_Cell_ID', 'Area', 'Site', 'point_no', 'variable']).mean().reset_index()
    lats = mdf.loc[mdf.variable.str.startswith('lat')]
    lons = mdf.loc[mdf.variable.str.startswith('lon')]
    df = pd.merge(lats,lons,on=['Grid_Cell_ID', 'Area', 'Site', 'point_no']).drop(columns=['variable_x', 'variable_y'])
    return df

def fish_length_map_prep(common_name: str, start_time:str, end_time: str):
    from geojson import Polygon, FeatureCollection, dumps, Feature
    angler = Angler()
    df = angler.get_df(
        'length',
        common_name=common_name,
        start_time=start_time,
        end_time=end_time,
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
    gdf = melt_df(df)
    features=[]
    for grid_cell in gdf.Grid_Cell_ID.unique():
        df_gc = gdf.loc[gdf['Grid_Cell_ID'] == grid_cell]
        Area = df_gc.Area.unique()[0]
        Site = df_gc.Site.unique()[0]
        all_lats = df_gc['value_y'].to_list()
        all_lons = df_gc['value_x'].tolist()
        feat_i = Feature(
            id = grid_cell,
            geometry =
                Polygon(
                    coordinates = [[*list(zip(all_lats,all_lons)), *[(all_lats[0], all_lons[0])]]]
                ),
            properties={'Area': Area, 'Site': Site}
            )
        features.append(feat_i)
    geo = FeatureCollection(features)
    df = df[['Grid_Cell_ID', 'Length_cm']].groupby('Grid_Cell_ID').mean().reset_index()
    return df, geo

def make_chloropleth_length(df, geo):
    fig = px.choropleth_mapbox(
        data_frame=df,
        geojson=geo,
        color="Length_cm",
        locations="Grid_Cell_ID",
        featureidkey="id",
        # opacity=0.9,
        color_continuous_scale='Viridis',
        center={"lat": 33, "lon": -123},
        mapbox_style="carto-positron",
        zoom=7
        )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    # graphJSON = json.dumps([fig], cls=plotly.utils.PlotlyJSONEncoder)
    return fig

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
    map_df, geo = fish_length_map_prep(
        common_name=form.data.get('fish_name'),
        start_time=form.data.get('start_date'),
        end_time=form.data.get('end_date'),
    )
    df = angler.get_df(
            'length',
            common_name=form.data.get('fish_name'),
            start_time=form.data.get('start_date'),
            end_time=form.data.get('end_date'),
            )
    # dumps(geo)
    fig = make_chloropleth_length(map_df, geo)
    graphJSON = json.dumps([fig], cls=plotly.utils.PlotlyJSONEncoder)
    # return fig.to_html(full_html=False, include_plotlyjs=False)
    # return jsonify(fig.to_json())
    return render_template(
        'select_fish.html',
        form=form,
        # table = df.sort_values('Date').to_html(),
        # graphJSON = graphJSON,
        plt_html=fig.to_html(),
        default_start = form.data.get('start_date'),
        default_end = form.data.get('end_date'),
        )


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


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)