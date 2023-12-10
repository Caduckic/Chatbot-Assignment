import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import date

# in order to get some more use out of my sql database, I will be using it to automate some of the ai training

db_file = 'instance/weather.db'

db_engine = create_engine('sqlite:///' + db_file)

# first I read in the sql data to a pandas dataframe
df = pd.read_sql('SELECT * from weather w JOIN location l ON w.location_id = l.id', con=db_engine)


# not for all of these functions I filter through the dataframe to get the desired item
def hottest_place():
    # on each of them I make sure to filter to only show results for today
    today_df = df.loc[df['date'] == date.today().strftime('%Y-%m-%d')]
    # I use the idxmax/idxmin function to find the row with the highest or lowest value
    hottest = today_df.loc[today_df['temp'].idxmax()]
    # I return a formatted string that can serve as an answer to 'where is the hottest right now?' for example
    return f'{hottest["name"]} is the hottest at {hottest["temp"]} degrees'


def coldest_place():
    today_df = df.loc[df['date'] == date.today().strftime('%Y-%m-%d')]
    coldest = today_df.loc[today_df['temp'].idxmin()]
    return f'{coldest["name"]} is the coldest at {coldest["temp"]} degrees'


def least_windy():
    today_df = df.loc[df['date'] == date.today().strftime('%Y-%m-%d')]
    least_windiest = today_df.loc[today_df['wind_speed'].idxmin()]
    return f'{least_windiest["name"]} is the least windiest at {least_windiest["wind_speed"]} meters/s'


def most_windy():
    today_df = df.loc[df['date'] == date.today().strftime('%Y-%m-%d')]
    most_windiest = today_df.loc[today_df['wind_speed'].idxmax()]
    return f'{most_windiest["name"]} is the most windiest at {most_windiest["wind_speed"]} meters/s'


# print(hottest_place())
# print(coldest_place())
# print(least_windy())
# print(most_windy())

# I make sure to close the dataframe after use
db_engine.dispose()
