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
    ssl._create_default_https_context = ssl._create_unverified_context
    url = "https://www.hebcal.com/hebcal/?v=1&cfg=json&year={0}&month=x&maj=on&c=on&m=50&geo=zip&zip={1}".format(yr, zp)
    print(url)
    response = urllib.request.urlopen(url)
    
    data = response.read()
    jdat = json.loads(data)
    
    times = dict()
    for d in jdat['items']:
        dt = datetime.datetime.strptime(d['date'][0:10], "%Y-%m-%d").date()
        if dt not in times:
            times[dt] = dict()
        if d['category'] == 'holiday':
            field = 'title'
        else:
            field = 'date'
        times[dt][d['category']] = d[field]
                    
    for didx, d in enumerate(sorted( times.keys() )):
        if 'candles' not in times[d] and 'havdalah' not in times[d]:
            continue

        amOn = None
        amOff = None
        hlday = times[d].get('holiday', '')
        priorDay = d - datetime.timedelta(days=1)

        # Check if candle-lighting is in the prior day, or if this is Jan-1 (and shabbos!)
        daytime = (priorDay in times and 'candles' in times[priorDay]) or (didx == 0)
        if daytime:
            hlday1st = hlday.split(' ')[0]
            if hlday == 'Shavuot I':
                amOn= datetime.time(0,0)
                amOff = datetime.time(13,0)
            elif hlday1st in ( 'Pesach', 'Shavuot', 'Sukkot', 'Shmini' ):
                amOn = datetime.time(8,50)     
                amOff = datetime.time(13,0)
            elif hlday1st in ( 'Rosh', 'Yom', 'Simchat' ):
                amOn = datetime.time(7,0)
                amOff = datetime.time(14,0)
            else:
                amOn = datetime.time(8,50)
                amOff = datetime.time(12,30)
                   
        if 'candles' in times[d]:
            canTime = datetime.datetime.strptime(times[d]['candles'][0:16], "%Y-%m-%dT%H:%M")
            if daytime:
                pmOn = datetime.time(14,0) # canTime - datetime.timedelta(minutes = 240) 
            else:
                pmOn = canTime.time()
                if canTime.time() > datetime.time(19, 45):
                    pmOn = datetime.time(19, 45)
            postCandles = 95
            if len(hlday) > 0:
                if 'Rosh' in hlday:
                    postCandles = 125
                elif 'Kippur' in hlday:
                    postCandles = 185
                elif 'Shmini' in hlday:
                    canTime = canTime.replace(hour=23, minute=0)
                    postCandles = 0
                elif 'Erev Shavuot' in hlday:
                    canTime = canTime.replace(hour=23, minute=59)
                    postCandles = 0
            pmOff = (canTime + datetime.timedelta(minutes = postCandles)).time() # or havdalah
        elif 'havdalah' in times[d]:
            havTime = datetime.datetime.strptime(times[d]['havdalah'][0:16], "%Y-%m-%dT%H:%M")
            pmOn = datetime.time(14,0) # havTime - datetime.timedelta(minutes = 270)
            pmOff = havTime.time() # + datetime.timedelta(minutes = 30)
        else:
            havTime = None
        
        if not amOff is None and amOff >= pmOn:
            pmOn = pmOn.replace(hour = amOn.hour, minute = amOn.minute)
            amOn = None
            amOff = None
            
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
    
    
