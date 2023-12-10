from flask import Flask, redirect, url_for, render_template, request
import requests
import googlemaps
from flask_sqlalchemy import SQLAlchemy
from datetime import date
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer, ChatterBotCorpusTrainer

my_bot = ChatBot(
    name='pybot',
    read_only=True,
    logic_adapters=["chatterbot.logic.BestMatch"]
)

corpus_trainer = ChatterBotCorpusTrainer(my_bot)
corpus_trainer.train('chatterbot.corpus.english.conversations')

# initiating the Flask application
app = Flask(__name__)

db_file = 'weather.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)

class Location(db.Model):
    #__tablename__ = 'location'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    def __repr__(self):
        return f'<Location {self.name}>'

class Weather(db.Model):
    #__tablename__ = 'weather'
    id = db.Column(db.Integer, primary_key=True)
    # Define other columns here
    date = db.Column(db.String(10))
    temp = db.Column(db.Float)
    description = db.Column(db.String(255))  # storing more here as I don't know how long these get
    wind_speed = db.Column(db.Float)

    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    location = db.relationship('Location', backref=db.backref('weathers', lazy=True))
    def __repr__(self):
        return f'<Weather {self.date} {self.temp}, Location: {self.location.name}>'


with app.app_context():
    db.create_all()


# creating an empty dict to store API keys
API_keys = {
    'openweather': '',
    'googlemaps': ''
}

# retrieving API keys from txt file
f = open('./APIkeys/keys.txt')
for line in f:
    # for each line I use splitlines to get rid of /n chars and then split with spaces
    key = line.splitlines()[0].split(' ')
    for dict_key in API_keys.keys():
        # I check if the lines first half matches the names in API_keys and then assign the value/second half
        if key[0] == dict_key:
            API_keys[dict_key] = key[1]

# initiating the googlemaps client
gmaps = googlemaps.Client(key=API_keys['googlemaps'])

# creating a list of default URLs, googlemaps not needed in here due to using the googlemaps library
urls = {
    'openweather': 'https://api.openweathermap.org/data/2.5/weather?',
}

# list of travel locations
locations = [
    'Cumbria',
    'Corfe Castle',
    'The Cotswolds',
    'Cambridge',
    'Bristol',
    'Oxford',
    'Norwich',
    'Stonehenge',
    'Watergate Bay',
    'Birmingham'
]


# this function takes and stores weather data in the sqlite database
def input_weather_data(location_name, data):
    # first checks if the location already exists, if it doesn't it makes an entry, if it does it uses the old one
    existing_loc = Location.query.filter_by(name=location_name).first()
    if existing_loc:
        loc = existing_loc
    else:
        loc = Location(name=location_name)
        db.session.add(loc)
        db.session.commit()

    # here we add the weather data itself
    for entry in data['list']:
        # we only want 1 result per day, I've set the filter to only add results for 12pm
        if '12:00:00' in entry['dt_txt']:
            # we check if we already have a forcast for the days in the data, if we do we skip adding them
            existing_entry = Weather.query.filter_by(date=entry['dt_txt'].split()[0], location_id=loc.id).first()
            if existing_entry:
                continue
            weather_entry = Weather(
                date=entry['dt_txt'].split()[0],
                temp=entry['main']['temp'],
                description=entry['weather'][0]['description'],
                wind_speed=entry['wind']['speed'],
                location_id=loc.id
            )
            db.session.add(weather_entry)
            db.session.commit()


# rendering the default route
@app.route('/', methods=['POST', 'GET'])
def home():
    # we check the method and if post we try and retrieve the address
    if request.method == 'POST':
        address = ''
        geocode_results = False
        # I have 2 ways to get the address, one for the list and one for entering it manually
        if 'manual' not in request.form:
            # here we check for each item, what button was pressed to submit the form
            for i in locations:
                button = request.form.get(i)
                # if the button is an empty string then it was the one pressed, that should mean the address is i
                if button == '':
                    address = i
                    break
            # check database first before going to geocode
            location = Location.query.filter_by(name=address).first()
            if location and Weather.query.filter_by(location_id=location.id, date=date.today().strftime('%Y-%m-%d')).all():
                print('in database')
            else:
                # once address is found we make the api call using the googlemaps library
                geocode_results = gmaps.geocode(address)
        else:
            # the manual method is much more straight forward, we just grab the element named address (text input)
            address = request.form['address']
            # before making the request we first check if address is an empty string and if so, return with error
            if address == '':
                return render_template('index.html', locations=locations, error=True), 400
            # check database first before going to geocode
            location = Location.query.filter_by(name=address).first()
            if location and Weather.query.filter_by(location_id=location.id, date=date.today().strftime('%Y-%m-%d')).all():
                print('in database')
            else:
                geocode_results = gmaps.geocode(address)
        # if the location was found in database, return results directly
        if location and Weather.query.filter_by(location_id=location.id, date=date.today().strftime('%Y-%m-%d')).all():
            return redirect(
                url_for(
                    'results',
                    lat=0,
                    lon=0,
                    name=address
                )
            )
        # if there was an error receiving the data from googlemaps we return the html with an error and a 400 status
        if not geocode_results:
            return render_template('index.html', locations=locations, error=True), 400
        # we get the coordinates from the results and redirect the user to the results page while passing the location
        location = geocode_results[0]['geometry']['location']
        return redirect(
            url_for(
                'results',
                lat=location['lat'],
                lon=location['lng'],
                name=address
            )
        )
    # else if the method doesn't equal POST then we simply render the template while passing the travel locations
    return render_template('index.html', locations=locations)


# rendering the results
@app.route('/results<lat>?<lon>?<name>')
def results(lat, lon, name):
    # query the database first to see if it has already been saved
    location = Location.query.filter_by(name=name).first()
    if location:
        # we check if we have weather data for this day in the specified location
        weather = Weather.query.filter_by(location_id=location.id, date=date.today().strftime('%Y-%m-%d')).first()
        if not weather:
            # if we don't we gather the next 5 days of weather data and save it in the database
            resp = requests.get(url=f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_keys["openweather"]}&units=metric')
            input_weather_data(location.name, resp.json())
            weather = Weather.query.filter_by(location_id=location.id, date=date.today().strftime('%Y-%m-%d')).first()
            # just incase something goes wrong, we return an error page
            if not weather:
                return '<h1>Error, could not find weatherdata</h1>'
        return render_template(
            'results.html',
            name=location.name,
            desc=weather.description,
            temp=weather.temp,
            wspeed=weather.wind_speed
        )

    # we query the openweather api using the lat and lon to return the weather data
    resp = requests.get(url=f'{urls["openweather"]}lat={lat}&lon={lon}&appid={API_keys["openweather"]}&units=metric')

    # we store the next 5 day forcast in order to reduce api calls
    resp2 = requests.get(url=f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_keys["openweather"]}&units=metric')
    input_weather_data(name, resp2.json())

    # in case of error we return an error message
    if resp.status_code != 200:
        return '<h1>Error in retrieving weather data</h1>'
    # using the weather data we render the results
    weather_data = resp.json()
    return render_template(
        'results.html',
        name=name,
        desc=weather_data['weather'][0]['description'],
        temp=weather_data['main']['temp'],
        wspeed=weather_data['wind']['speed']
    )


if __name__ == '__main__':
    app.run()