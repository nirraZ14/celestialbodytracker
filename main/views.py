from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse

import argparse, time
from skyfield.api import load,Topos
from datetime import datetime,timedelta
from time import strftime, gmtime, localtime
from skyfield import almanac
from tzlocal import get_localzone
import pytz
from .forms import ProjectForm
from skyfield.nutationlib import iau2000b
from .models import PlanetData
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from io import BytesIO
import base64
matplotlib.use("Agg")



def targetDistance(observer, target):
    station=observer.at
    # Planet at time t
    def planet_at(t):
        t._nutation_angles=iau2000b(t.tt)
        # Altitude Azimuth
        return station(t).observe(target).apparent().altaz()[0].degrees > -0.8333 # Index value=0
    # how much it happens a day
    planet_at.rough_period = 0.5  # twice a day
    return planet_at


def doppler_shift(frequency, relativeVelocity):
    """
    Doppler Shift is the apparent change in frequency of a wave in relation to an observer moving relative to the wave source.
    How fast things are moving away or toward of us
    Frequency will never change for source but there will be shift in frequency for stationary.
    So shift in frequency for observer,
    f0 = f{(v+-v0)/v}, where,
    f0 = observed frequency,
    f =  provided frequecy or source frequency,
    v = speed of light
    
    Simplifying the equation,
    we get,
    f0= f+- f*(v0/v)           [ positive or negative depends on velocity moving away or moving towards ]

    Input:
    frequency           = satellite's frequecy in Hz
    relativeVelocity    = satellite is moving at velocity in m/s

    return shift in frequency due to doppler effect or shift
    """
    return (frequency - frequency * (relativeVelocity/3e8))  # velocity of light in m/s


"""
from https://github.com/skyfielders/python-skyfield.git

def iau2000b(jd_tt):
    Compute Earth nutation based on the faster IAU 2000B nutation model.

    `jd_tt` - Terrestrial Time: Julian date float, or NumPy array of floats

    Returns a tuple ``(delta_psi, delta_epsilon)`` measured in tenths of
    a micro-arcsecond.  Each is either a float, or a NumPy array with
    the same dimensions as the input argument.  The result will not take
    as long to compute as the full IAU 2000A series, but should still
    agree with ``iau2000a()`` to within a milliarcsecond between the
    years 1995 and 2020.

    
    dpsi, deps = iau2000a(jd_tt, 2, 77, 0)
    dpsi += -0.000135e7
    deps +=  0.000388e7
    return dpsi, deps
"""

"""
from https://github.com/skyfielders/python-skyfield.git

class Topos(GeographicPosition):
    #Deprecated: use ``wgs84.latlon()`` or ``iers2010.latlon()`` instead.

    def __init__(self, latitude=None, longitude=None, latitude_degrees=None,
                 longitude_degrees=None, elevation_m=0.0, x=0.0, y=0.0):

        if latitude_degrees is not None:
            pass
        elif isinstance(latitude, Angle):
            latitude_degrees = latitude.degrees
        elif isinstance(latitude, (str, float, tuple)):
            latitude_degrees = _ltude(latitude, 'latitude', 'N', 'S')
        else:
            raise TypeError('please provide either latitude_degrees=<float>'
                            ' or latitude=<skyfield.units.Angle object>'
                            ' with north being positive')

        if longitude_degrees is not None:
            pass
        elif isinstance(longitude, Angle):
            longitude_degrees = longitude.degrees
        elif isinstance(longitude, (str, float, tuple)):
            longitude_degrees = _ltude(longitude, 'longitude', 'E', 'W')
        else:
            raise TypeError('please provide either longitude_degrees=<float>'
                            ' or longitude=<skyfield.units.Angle object>'
                            ' with east being positive')

        # Sneaky: the model thinks it's creating an object when really
        # it's just calling our superclass __init__() for us.  Alas, the
        # crimes committed to avoid duplicating code!  (This is actually
        # quite clean compared to the other alternatives I tried.)
        iers2010.latlon(latitude_degrees, longitude_degrees, elevation_m,
                        super(Topos, self).__init__)

        self.R_lat = self._R_lat  # On this old class, it was public.

    def itrf_xyz(self):
        return self.itrs_xyz
"""


def data(body):
     # Ephemeris file
    planets=load('de421.bsp')
    ts=load.timescale()

    earth=planets['earth']
    try:
         target=planets[body]
    except Exception as e:
        try:
             body=body + ' barycenter'
             target=planets[body]
        except:
             pass


    topog=Topos(latitude_degrees=23.8041, longitude_degrees=90.4152)
    observer= earth + topog

    first=True
    try:
      while (first):
            first=False
            t=ts.now()   # Auto Time Series (Auto-TS) is an open-source Python library to automate time series analysis and forecasting
            td=datetime.utcnow()

            local=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            delta=datetime.now()-td
            delta=str(delta).strip(":")[0]
            offset=timedelta(hours=int(delta))

 

            aU=observer.at(t).observe(target)

            azimuth, elevation, distance=aU.apparent().altaz()

            azi=azimuth.to('deg').value
            ele=elevation.to('deg').value
            distanceInM=distance.to('m').value # To find velocity
            distanceInKm=distanceInM/1000.0
            distanceInMiles=distanceInKm*0.621371  # Converting km to miles

            futuret=t.utc_datetime()
            futuret=futuret+timedelta(seconds=int(delta))

            futureT=ts.utc(futuret.year, futuret.month, futuret.day, futuret.hour, futuret.minute, futuret.second)
            futureaU=observer.at(futureT).observe(target)
            azimuth, elevation, distance=futureaU.apparent().altaz()

            futureDistance=distance.to('m').value
            relativeVelocity=(futureDistance - distanceInM)/ float(delta)
            iluminate=almanac.fraction_illuminated(planets,body,t)*100.0  # Return the fraction of the target’s disc that is illuminated.



            

            # local zone
            local_zone = get_localzone()
            
            # time in that zone
            local_t = datetime.now(local_zone)
            
            # Rise time Fall time 
            # predicts rise time and fall time of the target
            riseTime=local_t - timedelta(hours=local_t.hour) - timedelta(minutes=local_t.minute) - timedelta(seconds=local_t.second)
            fallTime=riseTime + timedelta(hours=23) +  timedelta(minutes=59) + timedelta(seconds=59)

            # convert to UTC
            utcRise=riseTime.astimezone(pytz.utc) # return a DateTime instance according to the specified time zone parameter tz. 
            utcFall=fallTime.astimezone(pytz.utc) # pytz.utc returns a timezone object for the UTC timezone
            

            rise = ts.utc(utcRise.year, utcRise.month, utcRise.day, utcRise.hour,  utcRise.minute,  utcRise.second)
            fall = ts.utc(utcFall.year, utcFall.month, utcFall.day, utcFall.hour,  utcFall.minute,  utcFall.second)


            # Find the times at which a discrete function of time changes value.
            t, y = almanac.find_discrete(rise, fall,targetDistance(observer,target))  # returns an array

            rise_t = None
            fall_t = None
                
            if len(y) > 0:
                if y[0] == True:
                    rise_t = t[0]
                    if len(t) > 1:
                        fall_t = t[1]
                    else:
                        fall_t = None
                else:
                    if len(t) > 1:
                        rise_t = t[1]
                    else:
                        rise_t = None
                            
                    fall_t = t[0]

            if rise_t is not None:
                    rise_time=(rise_t.astimezone(local_zone).strftime('%d/%m/%Y %H:%M:%S'))
                    
            if fall_t is not None:
                    fall_time=(fall_t.astimezone(local_zone).strftime('%d/%m/%Y %H:%M:%S'))
     
    except KeyboardInterrupt:
              pass
    return local,offset,azi,ele,distanceInM,distanceInKm,relativeVelocity,iluminate,rise_time, fall_time,local_zone



def plot_planet_graph(newDatas):
     alts=[planet.azim for planet in newDatas]
     dates=[planet.date for planet in newDatas]
     plt.figure(figsize=(6,4))
     plt.plot(dates, alts, label="Elevation")
     plt.xlabel("Date")
     plt.ylabel("Elevation")
     plt.title("Elevation")
     plt.legend()
     plt.grid(True)
     plt.gca().xaxis.set_major_formatter(DateFormatter("%d"))

     img=BytesIO()
     plt.savefig(img, format="png")
     img.seek(0)
     plt.close()

     img_64=base64.b64encode(img.read()).decode("utf-8")
     return img_64

def index(request):
    if request.method=="POST":
        form=ProjectForm(request.POST)
        if form.is_valid():
            body=form.cleaned_data['planet']
    
            # Ephemeris file
            planets=load('de421.bsp')

            local_time,offs,az,el,distanceM,distanceKm,relative,ilumin,rise_t,fall_t,local_z=data(body)
            newData=PlanetData(body=body,date=local_time,utc=offs,azim=az, elev=el,inM=distanceM,inKm=distanceKm,rv=relative,ilumn=ilumin,rise=rise_t,fall=fall_t,zone=local_z)
            newData.save()
            newDatas=PlanetData.objects.filter(body=body).order_by('date')
            body_image_url=newData.body_image_url()
            plot_graph=plot_planet_graph(newDatas)
            return render(request,"main/result.html",{
                    "newData":newData,
                    "plot_graph":plot_graph,
                    "body_image_url":body_image_url
                    })
                      
                 
    else:
        form=ProjectForm()
        return render(request,"main/index.html",{
            "form":form,
            "error":False
        })
                