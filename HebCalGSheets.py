'''
Created on Dec 10, 2018

@author: elliott
@author: judah
'''

import argparse
import datetime
import ssl
import urllib.request
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import gspread_formatting as gsf
from gspread_formatting import Color, TextFormat, CellFormat


def cleanSchedule(schedule):
    # Final formatted schedule
    formatted_schedule = []

    # Iterate over the list to format it
    for entry in schedule:
        date, holiday, candles_time, havdalah_time = entry

        # If no holiday, leave the holiday field blank
        holiday = holiday if holiday else ''

        # Convert the date object to a string
        date = date.strftime("%Y-%m-%d") if isinstance(date, datetime.date) else date

        # Convert the time objects to string if they are not None
        candles_time = candles_time.strftime("%H:%M") if isinstance(candles_time, datetime.time) else candles_time
        havdalah_time = havdalah_time.strftime("%H:%M") if isinstance(havdalah_time, datetime.time) else havdalah_time

        # Add the formatted row to the list
        formatted_schedule.append([date, holiday, candles_time, havdalah_time])

    return formatted_schedule


def writeToSheets(data, yr):
    # Authorize and open the spreadsheet
    scope = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/drive.file'
    ]
    # Replace file name with relevant file path
    file_name = '/Users/elliottadler/Desktop/Coding/HebCal/hebcal-times-12302024-v1-6acf86968087.json'
    creds = ServiceAccountCredentials.from_json_keyfile_name(file_name, scope)
    gc = gspread.authorize(creds)

    # If google sheet changes, make sure to update key
    sh = gc.open_by_key('1fXwskKZXBd16FfpTeE46fUQdZ1mQ-z5FmVpq72fyGMU')

    # Check if the worksheet already exists
    worksheet_title = "Times for " + yr + " Automated"
    try:
        wk = sh.worksheet(worksheet_title)  # Try to open the existing worksheet
    except gspread.exceptions.WorksheetNotFound:
        wk = sh.add_worksheet(title=worksheet_title, rows=100, cols=20, index=0)  # Create if it doesn't exist

    # Merge A1 and B1
    wk.merge_cells('A1:B1')

    # Merge C1 and D1
    wk.merge_cells('C1:D1')

    # Set text in merged cells (using 2D lists)
    wk.update(range_name='A1', values=[[yr]])  # Set year in A1 (merged with B1)
    wk.update(range_name='C1', values=[['Times']])  # Set "Times" in C1 (merged with D1)

    # Define the new background color (light blue)
    light_blue = Color(217 / 255, 234 / 255, 247 / 255)

    # Apply formatting for A1:B1 (2027 in red)
    format_a1_b1 = CellFormat(
        backgroundColor=light_blue,
        textFormat=TextFormat(
            foregroundColor=Color(1, 0, 0),  # Red color for year
            bold=True
        ),
        horizontalAlignment='CENTER',
        verticalAlignment='MIDDLE'
    )
    gsf.format_cell_range(wk, 'A1:B1', format_a1_b1)

    # Apply formatting for C1:D1 (Times in black)
    format_c1_d1 = CellFormat(
        backgroundColor=light_blue,
        textFormat=TextFormat(
            foregroundColor=Color(0, 0, 0),
            bold=True
        ),
        horizontalAlignment='CENTER',
        verticalAlignment='MIDDLE'
    )
    gsf.format_cell_range(wk, 'C1:D1', format_c1_d1)

    # Set values for A2, B2, C2, D2
    wk.update(range_name='A2', values=[['Date']])
    wk.update(range_name='B2', values=[['Holiday']])
    wk.update(range_name='C2', values=[['On']])
    wk.update(range_name='D2', values=[['Off']])

    # Apply the same formatting as C1:D1 to A2:D2
    format_a2_d2 = CellFormat(
        backgroundColor=light_blue,
        textFormat=TextFormat(
            foregroundColor=Color(0, 0, 0),
            bold=True
        ),
        horizontalAlignment='CENTER',
        verticalAlignment='MIDDLE'
    )
    gsf.format_cell_range(wk, 'A2:D2', format_a2_d2)

    # Convert dictionary to a list of values
    row_values = cleanSchedule(data)

    # Calculate the range based on the number of rows
    num_rows = len(row_values)
    range_name = f"A3:D{2 + num_rows}"

    # Update the sheet with the calculated range
    wk.update(range_name=range_name, values=row_values)

    # Define default formatting for the data (no bold, right aligned, white background)
    default_format = CellFormat(
        backgroundColor=Color(1, 1, 1),
        textFormat=TextFormat(
            foregroundColor=Color(0, 0, 0),
            bold=False
        ),
        horizontalAlignment='RIGHT',
        verticalAlignment='MIDDLE'
    )

    # Apply the default formatting to the updated range
    gsf.format_cell_range(wk, range_name, default_format)



def getShabbosTimes(yr, zp):
    # Create a dictionary (times) to hold on/off times, keyed by the dates which need to be programmed
    times = dict()
    formatted_times = []

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

    for didx, d in enumerate(sorted(times.keys())):

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
            if 'havdalah' in times[d]:
                offTime = datetime.datetime.strptime(times[d]['havdalah'][0:16], "%Y-%m-%dT%H:%M")
            elif 'candles' in times[d]:
                offTime = datetime.datetime.strptime(times[d]['candles'][0:16], "%Y-%m-%dT%H:%M")

            # For the first night of Shavuot, start the sechedule at midnight and keep it going until EOD
            if hlday == 'Shavuot I':
                amOn = datetime.time(0, 0)
                amOff = offTime.time()

            # For Pesach, Shavuot II, Sukkot and Shmini Atezeret, run the dayime schedule from 8:50am - EOD
            elif hlday1st in ('Pesach', 'Shavuot', 'Sukkot', 'Shmini'):
                amOn = datetime.time(8, 50)
                amOff = offTime.time()

            # For Rosh Hashanah, Yom Kippur and Simchat Torah, we start davening earlier, so run schedule from 7am - EOD
            elif hlday1st in ('Rosh', 'Yom', 'Simchat'):
                amOn = datetime.time(7, 0)
                amOff = offTime.time()

            # For a normal Shabbos, run the daytimne schedule from 8:50am - 12:30pm
            else:
                amOn = datetime.time(8, 50)
                amOff = offTime.time()


        # If there is candle-lighting for the day, then set the pmOn/pmOff values
        if 'candles' in times[d]:

            # Grab the candlighting time
            canTime = datetime.datetime.strptime(times[d]['candles'][0:16], "%Y-%m-%dT%H:%M")

            # If there is already a daytime schedule (e.g., 2nd day YomTov),
            # then start the evening schedule at 2pm (for play-dates, etc)
            if daytime:
                pmOn = datetime.time(14, 0)  # canTime - datetime.timedelta(minutes = 240)

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
            pmOff = (canTime + datetime.timedelta(minutes=postCandles)).time()  # or havdalah

        # If there is havdalah for the day, then start the evening scehdule at 2pm (playdates)
        # and end the evening schedule 30 minutes after the havdalah time
        elif 'havdalah' in times[d]:
            havTime = datetime.datetime.strptime(times[d]['havdalah'][0:16], "%Y-%m-%dT%H:%M")
            pmOn = datetime.time(14, 0)  # havTime - datetime.timedelta(minutes = 270)
            pmOff = havTime.time()  # + datetime.timedelta(minutes = 30)
        else:
            havTime = None

        # When the AM off-time is after the PM on-time, combine them
        # This happens when Shabbos is very short
        if not amOff is None and amOff >= pmOn:
            pmOn = pmOn.replace(hour=amOn.hour, minute=amOn.minute)
            amOn = None
            amOff = None

        # Print either one or two pairs of on/off times
        # When it is an Erev Shabbos/Chag, there is just a PM time
        if amOn is None:
            #print("{}|{}|{}|{}".format(d, hlday, pmOn, pmOff))
            formatted_times.append([d, hlday, pmOn, pmOff])
        else:
            #print("{}|{}|{}|{}|{}|{}".format(d, hlday, amOn, amOff, pmOn, pmOff))
            formatted_times.append([d, hlday, amOn, amOff, pmOn, pmOff])
    return formatted_times


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate on/off times for the Keter Torah stoplight")
    parser.add_argument("-Y", "--year", help="The 4-digit year to use for generating the reports", required=True)
    parser.add_argument("-Z", "--zipcode", help="The 0-padded 5-digit Zip Code to use for generating the reports",
                        required=True)
    args = parser.parse_args()

    times = getShabbosTimes(args.year, args.zipcode)
    #print(times)
    writeToSheets(times, args.year)

    exit()

