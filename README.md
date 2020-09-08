eis
==============================

Data collection and analysis for exploratory paper about Digital Skills in the European Innovation Scoreboard

After cloning the repo, do the following:

* Run `make create_environment` to install required packages and the scripts in the `eis folder`.
* Run `python eis/data/make_eurostat.py` to download relevant and process relevant Eurostat indicators. These will be saved in `data/raw/selected_tables` together with the data dictionaries.

Provisionally, the analysis that we have conducted is contained in `notebooks/dev/data_analysis`.

This includes:

* `01_eter_eda.ipynb`: Collection and EDA of ETER data               
* `02_eurostat_eda.ipynb`: EDA of Eurostat data
* `02b_normalisation_factors.ipynb`: Collection of Eurostat normalisation indicators
* `03_other_official_eda.ipynb`: Collection and EDA of other official data
* `04_web_sources.ipynb`: Collection and EDA of other web sources
* `05_synthesis.ipynb`: Synthesis of indicators for validation
* `06_study_portals.ipynb`: EDA of Study Portals data

Future updates of the repo will involve the refactoring and repackaging of the code.

Note that the collection and analysis of web data requires

* Meetup analysis: Access to Nesta Data Production system (currently not available)
* GitHub, Python Downloads and Stack Overflow Q&A: Registration with Google big query (save credentials as `gbq_eis_credentials.json` in the main project directory)

To produce the figures, install chrome driver ([link](https://chromedriver.chromium.org/)) and add the path to an `.env` file in the project directory. 

--------

<p><small>Project based on the <a target="_blank" href="https://github.com/nestauk/cookiecutter-data-science-nesta">Nesta cookiecutter data science project template</a>.</small></p>
