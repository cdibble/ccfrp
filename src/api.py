from flask import Flask, render_template, request, jsonify, Blueprint
from angler import Angler

api = Blueprint('api', __name__, template_folder='templates')
# ----------
# Species
# ----------
@api.route("/api/v1/species/common")
def species_common():
    angler = Angler()
    return {'species': angler.species.Common_Name.unique().tolist()}

@api.route("/api/v1/species/scientific")
def species_scientific():
    angler = Angler()
    return {'species': angler.species.Species.unique().tolist()}

@api.route("/api/v1/species/full")
def species_full():
    angler = Angler()
    return {'species': angler.species.to_dict('records')}

# ----------
# Locations
# ----------
@api.route("/api/v1/location/area")
def location_area():
    angler = Angler()
    return {'location': angler.location.Area.unique().tolist()}

@api.route("/api/v1/location/mpa_names")
def location_mpa_names():
    angler = Angler()
    return {'location': angler.location.MPA_names.unique().tolist()}

@api.route("/api/v1/location/full")
def location_full():
    angler = Angler()
    return {'location': angler.location.to_dict('records')}

# ----------
# Fish Length
# ----------
@api.route("/api/v1/fish/length")
def species():
    angler = Angler()
    return {'location': angler.location.Area.unique().tolist()}
