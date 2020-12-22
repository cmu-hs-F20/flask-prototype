## Prerequisites
1. Install python3
2. Install the required python libraries specified in `requirements.txt`. To install prerequisites: Open a terminal in this folder and run:
```
python3 -m pip install -r requirements.txt
```
3. Create a secrets file, using secrets_template.py as a template:
   1. Request a census.gov API key [here](https://duckduckgo.com/?t=canonical&q=census.gov+api+key&ia=web). Store the key you receive as `secrets_template.census_key`
   2. Generate a random string to be used as your flask [`SECRET_KEY`](https://flask.palletsprojects.com/en/1.1.x/config/#SECRET_KEY). This should be a long random string of bytes. Store this as `secrets_template.census_key`.
## Basic usage
1. Copy this repository to your computer
2. Start a new terminal in this folder
3. (with python 3 and required libraries installed) Run `python app.py`
4. Open a browser window, browse to https://127.0.0.1:5000