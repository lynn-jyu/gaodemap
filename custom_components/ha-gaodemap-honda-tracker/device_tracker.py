"""
Support for gaodemap of honda
# Author:
    lynn
# Created:
    2021/2/8
配置格式：
device_tracker: 
  - platform: ha_gaodemap_honda_tracker
    name: 'Name of Your Car'
    key: 'KO8IbsmkeGDqdNrj7nBFd8htmgOFI3W38zVQYAZLnEEX4KGql41KsRWCAPrqq0g4hjSxiOYBH%2FN2lC6JNMie03tp1HaqiinC87XcXFuTg7ptcHmd5ZgQgKL0vY%2Fqcih86bLlF9RJtkoYzy3vXWbrvYZunEW91%2BJlLN25Vb8dQjnplJ%2B2IHyVmvRiZT%2FM%2BJ84Po3wkKEQB8beyoNup9VbYXjgSCQ%2F1ABvyHtsZ5Ag5w%2FTpMMSxifnGZvkqiZ9J%2FdPEe2LrG4gJSpSiN%2B22JTSIhAV1g0pNzyEjvonkIOAnuMWRJLH088TS3qa2cgaBoNyZLd56Io6%2Fskh4N9CLoCS5ENAGRMq%2Flz%2Fu%2F%2Bu8bkIWJcDL9LoTB1PTf97UTPpU4dbdJN%2Ba0GKnY3ftrgfUINSwyzzAlnqx%2FAU1ngSb79JNVXI4KaNr86X50%2B67uhnS7Aq9H9ZmnXPK0zwC6lC7rS5KKGC94rcbpVoB4Wfq7fB1EsGsSqFVxyx1NK83q4qaCieg3vdWsum8rPH%2B1V8N9dYjQ1Gw6MxZgz5L2n2l%2FW5eMiObJilZmiGL7ObKWfbkr9U2YaViHrhGQSFEmgdZfg0YkOPLLv6y7w%2FA8fKEV%2BEaL4yzg8BBpCIKRX%2B1FXNFjckyAAdVBz4II5t4WMVG6PKZ5Wx00OqsuPVSBEnzpIT7%2BZMg2L7ALP8JyZp2O1%2B6TQkVSh0l%2Fj6NlgEyIuhUiVDYa7%2BFqWqATCmeiRcF5Qls0ollAsxjCeb8VNHehmCxi80UjeW3MTJZ73rso5rYBj%2F9p0toLXMnR2Re0SR0B5asxKusJ%2Bogc%2BkdZgt15nu6EXxSdgHRDFtgcR3yERXIC4g%2FODEJc3uqMf2EZTpxz4E%2XXXXXXXXXXzSvH0iCA7kGXDh4q%2FovQaHKoLW3IO9QjNH8PH%2Bh7Rwcbzkycijv2YX7KteXXXXXXXXXX&csid=25615E59-E54D-4939-9990-XXXXXXXXX'
    sessionid: 'cpuywkud2f0jvhpnigysigXXXXXXXXX'
    paramdata: 'oMYpWPAUpXXXXXXXXX'
"""
import logging
import asyncio
import json
import time, datetime
import requests
import re
from dateutil.relativedelta import relativedelta 
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from bs4 import BeautifulSoup
from requests import ReadTimeout, ConnectTimeout, HTTPError, Timeout, ConnectionError
from datetime import timedelta
from time import strftime
from aiohttp.client_exceptions import ClientConnectorError
from async_timeout import timeout
import homeassistant.util.dt as dt_util
from homeassistant.components import zone
from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.components.device_tracker.const import CONF_SCAN_INTERVAL
from homeassistant.components.device_tracker.legacy import DeviceScanner
from homeassistant.const import (
    CONF_NAME,
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_HOME,
    STATE_NOT_HOME,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify
from homeassistant.util.location import distance


TYPE_GEOFENCE = "Geofence"

__version__ = '0.1.1'
_Log=logging.getLogger(__name__)

COMPONENT_REPO = 'https://github.com/lynn-jyu/ha-gaodemap-honda-tracker'
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
ICON = 'mdi:car'

DEFAULT_NAME = 'gaodemap'
KEY = 'key'
SESSIONID = 'sessionid'

lastofflinetime = "未知"
lastonlinetime = "未知"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(KEY): cv.string,
    vol.Required(SESSIONID): cv.string,
    vol.Optional(CONF_NAME, default= DEFAULT_NAME): cv.string,
})


API_URL = "http://ts.amap.com/ws/tservice/location/getLast?ent=2&keyt=4&in="

async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    sensor_name = config.get(CONF_NAME)
    key = config.get(KEY)
    sessionid = config.get(SESSIONID)
    url = API_URL + key
    """_Log.info("key:" + key + ";sessionid:" + sessionid )"""
    scanner = GaodeDeviceScanner(hass, async_see, sensor_name, url, sessionid)
    await scanner.async_start(hass, interval)
    return True


class GaodeDeviceScanner(DeviceScanner):
    def __init__(self, hass, async_see, sensor_name: str, url: str, sessionid: str):
        """Initialize the scanner."""
        self.hass = hass
        self.async_see = async_see
        self._name = sensor_name
        self._url = url
        self._sessionid = sessionid
        self._state = None
        self.attributes = {}
    
    def get_data(self, url, headerstr):
        json_text = requests.post(url, headers=headerstr).content
        json_text = json_text.decode('utf-8')
        resdata = json.loads(json_text)
        return resdata    
    
    def time_diff (timestamp):
                result = datetime.datetime.now() - datetime.datetime.fromtimestamp(timestamp)
                hours = int(result.seconds / 3600)
                minutes = int(result.seconds % 3600 / 60)
                seconds = result.seconds%3600%60
                if result.days > 0:
                    return("{0}天{1}小时{2}分钟".format(result.days,hours,minutes))
                elif hours > 0:
                    return("{0}小时{1}分钟".format(hours,minutes))
                elif minutes > 0:
                    return("{0}分钟{1}秒".format(minutes,seconds))
                else:
                    return("{0}秒".format(seconds))
                    
    async def async_start(self, hass, interval):
        """Perform a first update and start polling at the given interval."""
        await self.async_update_info()
        interval = max(interval, DEFAULT_SCAN_INTERVAL)
        async_track_time_interval(hass, self.async_update_info, interval)             
            
    
    async def async_update_info(self, now=None):
        """Get the gps info."""
        global lastofflinetime
        global lastonlinetime
        HEADERS = {
            'Host': 'ts.amap.com',
            'Accept': 'application/json',
            'sessionid': self._sessionid,
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'Cookie': 'sessionid=' + self._sessionid,
            }

        def time_diff (timestamp):
            result = datetime.datetime.now() - datetime.datetime.fromtimestamp(timestamp)
            hours = int(result.seconds / 3600)
            minutes = int(result.seconds % 3600 / 60)
            seconds = result.seconds%3600%60
            if result.days > 0:
                return("{0}天{1}小时{2}分钟".format(result.days,hours,minutes))
            elif hours > 0:
                return("{0}小时{1}分钟".format(hours,minutes))
            elif minutes > 0:
                return("{0}分钟{1}秒".format(minutes,seconds))
            else:
                return("{0}秒".format(seconds))
                
        
        try:
            async with timeout(10):                
                ret =  await self.hass.async_add_executor_job(self.get_data, self._url, HEADERS)
                _Log.debug("请求结果: %s", ret)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        _Log.debug("Requests remaining: %s", self._url)

        if ret['result'] == "false":
            _Log.error("抓包信息有误，请检查是否正确或是否过期，服务器反馈信息："+ret['message']) 
        elif ret['result'] == "true":
            _Log.info("请求服务器信息成功.....") 
            
            kwargs = {
                "dev_id": slugify("gaodemap_{}".format(self._name)),
                "host_name": self._name,                
                "attributes": {
                    "icon": ICON,
                    "querytime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                }
            kwargs["gps"] = [
                ret['data']['latitude'] + 0.00240,
                ret['data']['longitude'] - 0.00540,
            ]

            interval = 60
            # TODO make interval configurable in future
            result = await self.async_see(**kwargs)
            return result
            
        else:
            _Log.error("send request error....")       
