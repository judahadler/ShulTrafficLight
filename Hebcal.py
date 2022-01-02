'''
Created on Dec 10, 2018

@author: elliott
'''

import argparse
import datetime
import ssl
import urllib.request
import json
        
def getShabbosTimes(yr, zp):

    # Create a dictionary (times) to hold on/off times, keyed by the dates which need to be programmed    
    times = dict()

    # Call the hebcal API with the requested year and zip-code as parameters
    ssl._create_default_https_context = ssl._create_unverified_context
    url = "https://www.hebcal.com/hebcal/?v=1&cfg=json&year={0}&month=x&maj=on&c=on&m=50&geo=zip&zip={1}".format(yr, zp)
    print(url)
    response = urllib.request.urlopen(url)
    
    # Read the result from the API call, and load the JSON-formatted results into a dictionary item (jdat)
    data = response.read()
    jdat = json.loads(data)

    # iterate through the date entries returned by the hebcal API
    for d in jdat['items']:

        # Convert the date string into a dateime object
        dt = datetime.datetime.strptime(d['date'][0:10], "%Y-%m-%d").date()

        # If the 'times' dictionary does not yet have an entry for the date, 
        # then set up a blank dictionary to hold the data for that date
        if dt not in times:
            times[dt] = dict()

        # If the date is a holiday, capture the title of the holiday,
        # which will be used in the next loop to decide how to set the lights
        # The 'category' field will either be 'candles', 'havdalah', or 'holiday'
        # The 'holiday' information is used to decide how to set the daytime lights
        if d['category'] == 'holiday':
            field = 'title'
        else:
            field = 'date'

        times[dt][d['category']] = d[field]
                    
    for didx, d in enumerate(sorted( times.keys() )):

        # If there is not candlelighting or havdalah time, skip to the next item
        if 'candles' not in times[d] and 'havdalah' not in times[d]:
            continue

        # The amOn/amOff variables will hold the times to start/end the daytime schedule
        amOn = None
        amOff = None

        # Get the name of the holiday, or empty-string if not a holiday
        hlday = times[d].get('holiday', '')

        # Get the prior day, in case we need to adjust those times based on the holiday
        priorDay = d - datetime.timedelta(days=1)

        # Check if candle-lighting is in the prior day, or if this is Jan-1 (and shabbos!)
        # Thge Jan-1 code was just put in for the 2022 special-case, and may still need to be perfected
        # In 2022, the first day was Saturday - but the logic assumes that Friday night data is also in our dictionary
        daytime = (priorDay in times and 'candles' in times[priorDay]) or (didx == 0)

        # If 'daytime' is true, then it means we need to generate on/off times for the daytime for that date
        if daytime:
            hlday1st = hlday.split(' ')[0]

            # For the first night of Shavuot, start the sechedule at midnight and keep it going until 1pm
            if hlday == 'Shavuot I':
                amOn= datetime.time(0,0)
                amOff = datetime.time(13,0)

            # For Pesach, Shavuot II, Sukkot and Shmini Atezeret, run the dayime schedule from 8:50am - 1pm
            elif hlday1st in ( 'Pesach', 'Shavuot', 'Sukkot', 'Shmini' ):
                amOn = datetime.time(8,50)     
                amOff = datetime.time(13,0)

            # For Rosh Hashanah, Yom Kippur and Simchat Torah, we start davening earlier, so run schedule from 7am - 2pm
            elif hlday1st in ( 'Rosh', 'Yom', 'Simchat' ):
                amOn = datetime.time(7,0)
                amOff = datetime.time(14,0)

            # For a normal Shabbos, run the daytimne schedule from 8:50am - 12:30pm
            else:
                amOn = datetime.time(8,50)
                amOff = datetime.time(12,30)
                 
        # If there is candle-lighting for the day, then set the pmOn/pmOff values
        if 'candles' in times[d]:

            # Grab the candlighting time
            canTime = datetime.datetime.strptime(times[d]['candles'][0:16], "%Y-%m-%dT%H:%M")

            # If there is already a daytime schedule (e.g., 2nd day YomTov),
            # then start the evening schedule at 2pm (for play-dates, etc)
            if daytime:
                pmOn = datetime.time(14,0) # canTime - datetime.timedelta(minutes = 240) 

            # Otherwise, set the start time for the nightl schedule to candle-lighting time
            # When shabbos starts after 7:45pm, start the schedule at 7:45pm to account for the early minyan
            else:
                pmOn = canTime.time()
                if canTime.time() > datetime.time(19, 45):
                    pmOn = datetime.time(19, 45)

            # For a normal nightime, stop the schedule 95 minutes after it starts
            postCandles = 95
            
            # If it is a holiday, then possibly change the stop time
            if len(hlday) > 0:

                # Rosh Hashanah night davening takes longer, so give it 125 minutes
                if 'Rosh' in hlday:
                    postCandles = 125

                # Yom Kippur takes even longer, so give it 185 minutes
                elif 'Kippur' in hlday:
                    postCandles = 185

                # For Shmini Azteret, the night is Simchat Torah so run the lights until 11pm
                elif 'Shmini' in hlday:
                    canTime = canTime.replace(hour=23, minute=0)
                    postCandles = 0

                # On the 1st night of Shavuot run the night schedule until 11:59pm
                # After that, the dayime schedule for the 1st day of Shavuot will take over at 12am
                elif 'Erev Shavuot' in hlday:
                    canTime = canTime.replace(hour=23, minute=59)
                    postCandles = 0

            # Calculate the stop-time (pmOff) by adding 'postCandles' minutes to the candle-lighting time
            pmOff = (canTime + datetime.timedelta(minutes = postCandles)).time() # or havdalah

        # If there is havdalah for the day, then start the evening scehdule at 2pm (playdates)
        # and end the evening schedule 30 minutes after the havdalah time
        elif 'havdalah' in times[d]:
            havTime = datetime.datetime.strptime(times[d]['havdalah'][0:16], "%Y-%m-%dT%H:%M")
            pmOn = datetime.time(14,0) # havTime - datetime.timedelta(minutes = 270)
            pmOff = havTime.time() # + datetime.timedelta(minutes = 30)
        else:
            havTime = None
        
        # When the AM off-time is after the PM on-time, combine them
        # This happens when Shabbos is very short
        if not amOff is None and amOff >= pmOn:
            pmOn = pmOn.replace(hour = amOn.hour, minute = amOn.minute)
            amOn = None
            amOff = None
        
        # Print either one or two pairs of on/off times
        # When it is an Erev Shabbos/Chag, there is just a PM time
        if amOn is None:
            print("{}|{}|{}|{}".format(d, hlday, pmOn, pmOff))
        else:
            print("{}|{}|{}|{}|{}|{}".format(d, hlday, amOn, amOff, pmOn, pmOff))
    return times

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate on/off times for the Keter Torah stoplight")
    parser.add_argument("-Y", "--year", help="The 4-digit year to use for generating the reports", required=True)
    parser.add_argument("-Z", "--zipcode", help="The 0-padded 5-digit Zip Code to use for generating the reports", required=True)
    args = parser.parse_args()

    getShabbosTimes(args.year, args.zipcode)

    exit()
    
    
