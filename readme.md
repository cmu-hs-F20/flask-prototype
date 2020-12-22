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

## Census Variables Config File
Selection of Census API variables is controlled by a config file, called `vars.json`. One item in this file defines a single variable. Each variable includes five fields:
- `name` (required): The variable name
- `vars` (required): A list of the data.census.gov API variable ids required in this variable's definition. Accepts multiple ids to allow specification of fields that are aggregations of several variables. Find the list of available census API variable IDs for detailed, subject, data profile, and comparison profile tables [here](https://www.census.gov/data/developers/data-sets/acs-5year.html)
- `definition` (required):  A string containing a python expression that defines the column contents, in terms of the available census variables. 
  - Can use mathematical symbols (`+ - / *`), or Python operators like `sum()`, to calculate row-wise operations between the specified columns. 
  - To apply no operation, and assign the value of a single census api variable, assign this to the variable id.
- `category` (required): The category of this variable. Variables in the same category will be displayed under the same heading.
- `description` (optional): A text description of the content and purpose of the variable.

`vars.json` is automatically validated when the app is launched. If an invalid entry is specified, the app will fail to launch, and an error message will be displayed, indicating which variable was improperly specified.
### Examples:


1. To create a variable that displays the total population of a county, add the following item to the config file:
```json
{
        "name": "Total Population",
        "vars": [
            "B01003_001E"
        ],
        "definition": "B01003_001E",
        "category": "Total population",
        "description": "The total population in a county"
}
```
- This variable id (`B01003_001E`) represents the total number of residents in a county.
- No operation is calculated: The column is assigned to take the raw value of the variable.
- This variable is assigned to the `Total Population` category.

2. To create a variable that calculates the percentage of population of a county who are not white, add the following item to the config file:
```json
{
    "name": "Percentage non-white population",
    "vars": [
        "B02001_002E",
        "B01003_001E"
    ],
    "definition": "(B01003_001E - B02001_002E) / B01003_001E",
    "category": "Total population",
    "description": "The percentage of a county's residents who are not white"
}
```
- These variable ids query the number of white residents (`B02001_002E`) and the total residents (`B01003_001E`) in a county.
- This definition calculates the total number of non-white residents, divided by the total number of residents.
- This variable is assigned to the "Total population" category, and will be grouped with the other variables in that category in the dashboard.