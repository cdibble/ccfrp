# import pandas as pd
from flask import Flask, render_template, request, Blueprint, jsonify
# from flask_bootstrap import Bootstrap
# from flask_datepicker import datepicker

from datetime import datetime, timedelta
# from tinyflux import TinyFlux
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from ccfrp.angler import Angler
from wtforms.fields import DateField, SubmitField, SelectField
from wtforms.validators import InputRequired
from flask_wtf import FlaskForm
import plotly_express as px
import plotly
import geojson
from geojson import Polygon, FeatureCollection, dumps, Feature
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
def create_features(df: pd.DataFrame, id_column: str, feat_properties: list = ['Area', 'MPA_Status'], **kwargs):
    features=[]
    for grid_cell in df[id_column].unique():
        gdf = df.loc[df[id_column] == grid_cell]
        properties={x: gdf[x].unique()[0] for x in feat_properties}
        all_lats = gdf['value_x'].to_list()
        all_lons = gdf['value_y'].tolist()
        feat_i = Feature(
            id = grid_cell,
            geometry =
                Polygon(
                    coordinates = [[*list(zip(all_lats,all_lons)), *[(all_lats[0], all_lons[0])]]]
                ),
            properties=properties
            )
        features.append(feat_i)
    return features


def fish_length_map_prep(df: pd.DataFrame = None, common_name: str = None, start_time:str = None, end_time: str = None, id_column: str = 'Grid_Cell_ID', **kwargs):
    angler = Angler()
    if df is None:
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
    if id_column == 'Area_MPA_Status':
        print('getting area sumary')
        gdf = angler.melt_df_area(df, **kwargs)
    else:
        gdf = angler.melt_df(df, **kwargs)
    geo = FeatureCollection(create_features(gdf, id_column=id_column, **kwargs))
    df = df[[id_column, 'Length_cm']].groupby(id_column).mean().reset_index()
    return df, geo


def make_chloropleth_length(df: pd.DataFrame, geo: geojson, locations_column:str='Grid_Cell_ID'):
    fig = px.choropleth_mapbox(
        data_frame=df,
        geojson=geo,
        color="Length_cm",
        locations=locations_column,
        featureidkey="id",
        # opacity=0.9,
        color_continuous_scale='Viridis',
        center={"lat": 33, "lon": -123},
        mapbox_style="carto-positron",
        hover_data=[locations_column, "Length_cm"],
        zoom=7
        )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    # graphJSON = json.dumps([fig], cls=plotly.utils.PlotlyJSONEncoder)
    return fig
###############
# Routes
###############
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
            'select_fish_gridcell.html',
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
            'select_fish_gridcell.html',
            form=form,
            table = df.sort_values('Date').to_html(),
            # graphJSON = graphJSON,
            plt_html=plot.to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )

@app.route("/fish/length/map/gridcell", methods = ['POST'])
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
        id_column='Grid_Cell_ID'
    )
    fig = make_chloropleth_length(map_df, geo)
    graphJSON = json.dumps([fig], cls=plotly.utils.PlotlyJSONEncoder)
    # return fig.to_html(full_html=False, include_plotlyjs=False)
    # return jsonify(fig.to_json())
    return render_template(
        'select_fish_gridcell.html',
        form=form,
        # table = df.sort_values('Date').to_html(),
        # graphJSON = graphJSON,
        plt_html=fig.to_html(),
        default_start = form.data.get('start_date'),
        default_end = form.data.get('end_date'),
        )

@app.route("/fish/length/map/area", methods = ['POST'])
def fish_length_map_area_post():
    # from geojson import Polygon, FeatureCollection, dumps, Feature
    angler = Angler()
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    # Get a second version with Area_MPA_Status as a grouping
    fishdf = angler.get_df(
        'length',
        common_name=form.data.get('fish_name'),
        start_time=form.data.get('start_date'),
        end_time=form.data.get('end_date')
    )
    fishdf['Area_MPA_Status'] = fishdf['Area'].str.cat(fishdf['MPA_Status'], sep = ' ')
    area_df, area_geo = fish_length_map_prep(
        df = fishdf,
        id_column='Area_MPA_Status',
        grouping_vars=['Area_MPA_Status'],
        feat_properties=['Area_MPA_Status']
    )
    # kwargs = {"grouping_vars":['Area_MPA_Status'],'feat_properties':['Area_MPA_Status']}
    print(area_df.head())
    print(area_geo)
    fig = make_chloropleth_length(area_df, area_geo, 'Area_MPA_Status')
    graphJSON = json.dumps([fig], cls=plotly.utils.PlotlyJSONEncoder)
    return render_template(
        'select_fish_area.html',
        form=form,
        # table = df.sort_values('Date').to_html(),
        # graphJSON = graphJSON,
        plt_html=fig.to_html(),
        default_start = form.data.get('start_date'),
        default_end = form.data.get('end_date'),
        )

@app.route("/fish/length/map/gridcell", methods = ['GET'])
def fish_length_map_get():
    from geojson import Polygon, FeatureCollection, dumps, Feature
    angler = Angler()
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    default_start = angler.length.Date.min().date().isoformat()
    default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
    return render_template(
        'select_fish_gridcell.html',
        form = form,
        default_start = default_start,
        default_end = default_end
        )

@app.route("/fish/length/map/area", methods = ['GET'])
def fish_length_map_area_get():
    from geojson import Polygon, FeatureCollection, dumps, Feature
    angler = Angler()
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    default_start = angler.length.Date.min().date().isoformat()
    default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
    return render_template(
        'select_fish_area.html',
        form = form,
        default_start = default_start,
        default_end = default_end
        )

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)