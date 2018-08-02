# pl-indigo
Indigo for Poland

# Local development

This package uses [pipenv](https://docs.pipenv.org/), which combines virtualenv and pip into a simpler package.

To setup your local environment:

* ensure you have [pipenv](https://docs.pipenv.org/) installed
* clone this repo and move into the repo directory
* setup a virtualenv and install development dependencies: `pipenv install --dev`
* setup the database and other dependencies (TODO: document)
* run the local server: `pipenv run python manage.py runserver`
* visit [http://localhost:8000](http://localhost:8000)

## Running tests

To run tests on your code, use:

    pipenv run python manage.py test

# Updating your Indigo dependency

If you need to update you Indigo version to a certain commit in the [Indigo repo](https://github.com/OpenUpSA/indigo):

* get the SHA-1 hash of the commit you want
* update your install-time dependency: `pipenv install 'git+https://github.com/OpenUpSA/indigo.git@<PUT-SHA1-HERE>#egg=indigo'`
* update your development-time dependency: `pipenv install --dev 'git+https://github.com/OpenUpSA/indigo.git@<PUT-SHA1-HERE>#egg=indigo[dev]'`

Updating the development-time dependency with the extra `[dev]` part ensures that Indigo's dev-time requirements are included. Basically, this
ensures that you can run the tests.
