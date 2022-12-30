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
import json
from api import api
import pandas as pd
import logging
module_logger=logging.getLogger('ccfrp_app')


def create_app():
    app = Flask('ccfrp_app', template_folder='templates')
    app.config['SECRET_KEY'] = 'poopypants'
    from . import auth
    app.register_blueprint(auth.bp)
    app.register_blueprint(api)
    return app

app = create_app()
angler = Angler()

class TimeForm(FlaskForm):
    start_date = DateField('start_date')
    end_date = DateField('end_date')
    submit = SubmitField('Submit')

@app.route("/")
def index():
    return render_template('base.html')

@app.route("/home")
def home_page():
    return render_template(
        'base.html'
    )

# -----------
# Fish Length
# -----------
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
# Fish Length: Grid Cell
# ## MAPS
@app.route("/length/gridcell/map", methods = ['GET', 'POST'])
def fish_length_map_get():
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    if request.method == 'GET':
        default_start = angler.length.Date.min().date().isoformat()
        default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
        return render_template(
            'select_fish_gridcell.html',
            form = form,
            default_start = default_start,
            default_end = default_end
            )
    elif request.method == 'POST':
        map_df, geo = angler.fish_length_map_prep(
            common_name=form.data.get('fish_name'),
            start_time=form.data.get('start_date'),
            end_time=form.data.get('end_date'),
            id_column='Grid_Cell_ID'
        )
        fig = make_chloropleth_length(map_df, geo)
        # graphJSON = json.dumps([fig], cls=plotly.utils.PlotlyJSONEncoder)
        return render_template(
            'select_fish_gridcell.html',
            form=form,
            # table = df.sort_values('Date').to_html(),
            # graphJSON = graphJSON,
            plt_html=fig.to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )

# ## TABLES
@app.route("/length/gridcell/table", methods = ['GET', 'POST'])
def fish_length_table_get():
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    if request.method == 'GET':
        default_start = angler.length.Date.min().date().isoformat()
        default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
        return render_template(
            'select_fish_gridcell.html',
            form = form,
            default_start = default_start,
            default_end = default_end
            )
    elif request.method == 'POST':
        map_df, _ = angler.fish_length_map_prep(
            common_name=form.data.get('fish_name'),
            start_time=form.data.get('start_date'),
            end_time=form.data.get('end_date'),
            id_column='Grid_Cell_ID'
        )
        return render_template(
            'select_fish_gridcell.html',
            form=form,
            table = map_df.to_html(),
            # graphJSON = graphJSON,
            # plt_html=fig.to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )

#
# Fish Length: MPA Area
# ## MAPS
@app.route("/length/area/map", methods = ['GET', 'POST'])
def fish_length_map_area_get():
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    if request.method == 'GET':
        default_start = angler.length.Date.min().date().isoformat()
        default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
        return render_template(
            'select_fish_area.html',
            form = form,
            default_start = default_start,
            default_end = default_end
            )
    elif request.method == 'POST':
        # Get a second version with Area_MPA_Status as a grouping
        fishdf = angler.get_df(
            'length',
            common_name=form.data.get('fish_name'),
            start_time=form.data.get('start_date'),
            end_time=form.data.get('end_date')
        )
        fishdf['Area_MPA_Status'] = fishdf['Area'].str.cat(fishdf['MPA_Status'], sep = ' ')
        area_df, area_geo = angler.fish_length_map_prep(
            df = fishdf,
            id_column='Area_MPA_Status',
            feat_properties=['Area_MPA_Status']
        )
        # kwargs = {"grouping_vars":['Area_MPA_Status'],'feat_properties':['Area_MPA_Status']}
        module_logger.debug('Area DF- the summarized data to be mapped')
        module_logger.debug(area_df.head())
        module_logger.debug('Area Geo- the geometries for the mapped data')
        module_logger.debug(area_geo)
        fig = make_chloropleth_length(area_df, area_geo, 'Area_MPA_Status')
        # graphJSON = json.dumps([fig], cls=plotly.utils.PlotlyJSONEncoder)
        return render_template(
            'select_fish_area.html',
            form=form,
            # table = df.sort_values('Date').to_html(),
            # graphJSON = graphJSON,
            plt_html=fig.to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )

# ## TABLES
@app.route("/length/area/table", methods = ['GET', 'POST'])
def fish_length_table_area_get():
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    if request.method == 'GET':
        default_start = angler.length.Date.min().date().isoformat()
        default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
        return render_template(
            'select_fish_area.html',
            form = form,
            default_start = default_start,
            default_end = default_end
            )
    elif request.method == 'POST':
        # Get a second version with Area_MPA_Status as a grouping
        fishdf = angler.get_df(
            'length',
            common_name=form.data.get('fish_name'),
            start_time=form.data.get('start_date'),
            end_time=form.data.get('end_date')
        )
        fishdf['Area_MPA_Status'] = fishdf['Area'].str.cat(fishdf['MPA_Status'], sep = ' ')
        area_df, _ = angler.fish_length_map_prep(
            df = fishdf,
            id_column='Area_MPA_Status',
            feat_properties=['Area_MPA_Status']
        )
        return render_template(
            'select_fish_area.html',
            form=form,
            table = area_df.to_html(),
            # graphJSON = graphJSON,
            # plt_html=fig.to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )

@app.route("/length/gridcell/table_detail", methods = ['GET', 'POST'])
def get_table_gridcell():
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    if request.method == 'GET':
        default_start = angler.length.Date.min().date().isoformat()
        default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
        return render_template(
            'select_fish_gridcell.html',
            form = form,
            default_start = default_start,
            default_end = default_end
            )
    elif request.method == 'POST':
        df = angler.get_df(
                type = 'length',
                common_name=form.data.get('fish_name'),
                start_time=form.data.get('start_date'),
                end_time=form.data.get('end_date')
            ).drop(
                columns = [
                    'Year',
                    'Month',
                    'Day',
                    'ID_Cell_per_Trip',
                    'LTM_project_short_code'
                ],
                errors='ignore'
            )
        df = pd.merge(
            df,
            angler.get_location_summary(df)
        ).drop(
            columns = [
                'lat_1_dd', 'lon_1_dd', 'lat_2_dd','lon_2_dd', 'lat_3_dd', 'lon_3_dd', 'lat_4_dd', 'lon_4_dd', 'lat_center_point_dd', 'lon_center_point_dd', 'species_definition', 'CA_MPA_name_short'
            ]
        )
        return render_template(
            'select_fish_gridcell.html',
            form=form,
            table = df.to_html(),
            # graphJSON = graphJSON,
            # plt_html=fig.to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )

@app.route("/length/area/table_detal", methods = ['GET', 'POST'])
def get_table_area():
    all_species=angler.species.Common_Name.unique()
    TimeForm.fish_name = SelectField(u'Field name', choices = all_species, validators = [InputRequired()])
    form = TimeForm()
    if request.method == 'GET':
        default_start = angler.length.Date.min().date().isoformat()
        default_end = (angler.length.Date.max() + timedelta(days=1)).date().isoformat()
        return render_template(
            'select_fish_area.html',
            form = form,
            default_start = default_start,
            default_end = default_end
            )
    elif request.method == 'POST':
        # Get filtered dataframe
        df = angler.get_df(
            type = 'length',
            common_name=form.data.get('fish_name'),
            start_time=form.data.get('start_date'),
            end_time=form.data.get('end_date'),
            join_locations=False,
            join_species=False
        ).drop(
            columns = [
                'Year',
                'Month',
                'Day',
                'ID_Cell_per_Trip',
                'LTM_project_short_code'
            ],
            errors='ignore'
        )
        # Aggregate
        print('aggregating')
        df = df.groupby(
            [x for x in df.columns if x not in ['Date', 'Length_cm']],
            dropna=False
            ).mean().reset_index()
        # Add meta data
        df = angler._join_location(df)
        df = angler._join_species(df)
        # summarize location data
        df = pd.merge(
            df,
            angler.get_location_summary(df)
        ).drop(
            columns = [
                'lat_1_dd', 'lon_1_dd', 'lat_2_dd','lon_2_dd', 'lat_3_dd', 'lon_3_dd', 'lat_4_dd', 'lon_4_dd', 'lat_center_point_dd', 'lon_center_point_dd', 'species_definition', 'CA_MPA_name_short', 'LTM_project_short_code'
            ]
        )
        return render_template(
            'select_fish_area.html',
            form=form,
            table = df.to_html(),
            # graphJSON = graphJSON,
            # plt_html=fig.to_html(),
            default_start = form.data.get('start_date'),
            default_end = form.data.get('end_date'),
            )


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)