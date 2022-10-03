# ccfrp
Python API and Flask App for CA Collaborative Fisheries Research Program Data Exploration

## To Do
- [ ] For sampling Areas, aggregate based on the maximum boundaries of each area, rather than on the mean lat/lon
- [ ] Allow multiple-select on species
- [ ] Allow time slider widget on chloropleth plots if possible

## Installation
The repo includes a python module and a Flask app.

### Python module: ccfrp
`ccfrp` can be installed by cloning the repo and running from the root of the repo

```bash
pip install .
```

### Flask app
Run the Flask app with
```bash
flask --app src/ccfrp_app.py run
```

then visit [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser.