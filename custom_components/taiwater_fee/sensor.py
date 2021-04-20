"""Support for the TaiWater Fee."""
import logging
from typing import Callable
from datetime import timedelta

from aiohttp.hdrs import USER_AGENT
import requests
from bs4 import BeautifulSoup

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.util import Throttle
import homeassistant.util.dt as dt_util
from homeassistant.helpers.event import track_point_in_time
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CURRENCY_DOLLAR,
    HTTP_OK,
    HTTP_FORBIDDEN,
    HTTP_NOT_FOUND,
)
from .const import (
    ATTRIBUTION,
    ATTR_BILLING_MONTH,
    ATTR_BILLING_DATE,
    ATTR_PAYMENT,
    ATTR_WATER_CONSUMPTION,
    ATTR_DURATION,
    ATTR_BILL_AMOUNT,
    ATTR_HTTPS_RESULT,
    ATTR_LIST,
    BASE_URL,
    CONF_WATERID,
    CONF_COOKIE,
    CONF_CSRF,
    CONF_VERIFYTOKEN1,
    CONF_VERIFYTOKEN2,
    DATA_KEY,
    HA_USER_AGENT,
    REQUEST_TIMEOUT
)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_FORCED_UPDATES = timedelta(minutes=25)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=45)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_devices: Callable
) -> None:
    """Set up the TaiWater Fee Sensor from config."""
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    if config.data.get(CONF_WATERID, None):
        waterid = config.data[CONF_WATERID]
        cookie = config.data[CONF_COOKIE]
        csrf = config.data[CONF_CSRF]
        verifytoken1 = config.data[CONF_VERIFYTOKEN1]
        verifytoken2 = config.data[CONF_VERIFYTOKEN2]
    else:
        waterid = config.options[CONF_WATERID]
        cookie = config.options[CONF_COOKIE]
        csrf = config.options[CONF_CSRF]
        verifytoken1 = config.options[CONF_VERIFYTOKEN1]
        verifytoken2 = config.options[CONF_VERIFYTOKEN2]

    data = TaiWaterFeeData(waterid, cookie, csrf, verifytoken1, verifytoken2)
    data.expired = False
    device = TaiWaterFeeSensor(data, waterid)

    hass.data[DATA_KEY][config.entry_id] = device
    async_add_devices([device], update_before_add=True)


class TaiWaterFeeData():
    """Class for handling the data retrieval."""

    def __init__(self, waterid, cookie, csrf, verifytoken1, verifytoken2):
        """Initialize the data object."""
        self.data = {}
        self._waterid = waterid
        self._cookie = cookie
        self._csrf = csrf
        self._verifytoken1 = verifytoken1
        self._verifytoken2 = verifytoken2
        self.expired = False
        self.uri = BASE_URL

    def _parser_html(self, text):
        """ parser html """
        data = {}
        soup = BeautifulSoup(text, 'html.parser')
        billdetail = soup.find(class_="inquiry_main_content")
        if billdetail:
            inquiry = billdetail.find(class_="block_table inquiry_table view")
            if inquiry:
                results = inquiry.find_all(["td"], limit=13)
                if results:
                    for i in results:
                        data[i.get("data-title")] = i.string
        return data

    def update_no_throttle(self):
        """Get the data for a specific water id."""
        self.update(no_throttle=True)

    @Throttle(MIN_TIME_BETWEEN_UPDATES, MIN_TIME_BETWEEN_FORCED_UPDATES)
    def update(self, **kwargs):
        """Get the latest data for water id from REST service."""
        self._cookie = "__RequestVerificationToken={}; TS01689f3b={}".format(
            self._verifytoken1,
            self._cookie)
        headers = {USER_AGENT: HA_USER_AGENT, "Cookie": self._cookie}
        payload = {
            "__RequestVerificationToken": self._verifytoken2,
            "model.Index": self._csrf,
            "model[{}].SiteNo".format(self._csrf): self._waterid[:2],
            "model[{}].UserNo".format(self._csrf): self._waterid[2:-1],
            "model[{}].CheckNo".format(self._csrf): self._waterid[-1]}

        self.data = {}
        self.data[self._waterid] = {}

        if not self.expired:
            try:
                req = requests.post(
                    self.uri,
                    headers=headers,
                    data=payload,
                    timeout=REQUEST_TIMEOUT)

            except requests.exceptions.RequestException:
                _LOGGER.error("Failed fetching data for %s", self._waterid)
                return

            if req.status_code == HTTP_OK:
                self.data[self._waterid] = self._parser_html(req.text)
                if len(self.data[self._waterid]) >= 1:
                    self.data[self._waterid]['result'] = HTTP_OK
                else:
                    self.data[self._waterid]['result'] = HTTP_NOT_FOUND
                self.expired = False
            elif req.status_code == HTTP_NOT_FOUND:
                self.data[self._waterid]['result'] = HTTP_NOT_FOUND
                self.expired = True
            else:
                info = ""
                self.data[self._waterid]['result'] = req.status_code
                if req.status_code == HTTP_FORBIDDEN:
                    info = " Token or Cookie is expired"
                _LOGGER.error(
                    "Failed fetching data for %s (HTTP Status_code = %d).%s",
                    self._waterid,
                    req.status_code,
                    info
                )
                self.expired = True
        else:
            self.data[self._waterid]['result'] = 'sessions_expired'
            _LOGGER.warning(
                "Failed fetching data for %s (Sessions expired)",
                self._waterid,
            )


class TaiWaterFeeSensor(SensorEntity):
    """Implementation of a TaiWater Fee sensor."""

    def __init__(self, data, waterid):
        """Initialize the sensor."""
        self._state = None
        self._data = data
        self._attributes = {}
        self._attr_value = {}
        self._name = "taiwater_fee_{}".format(waterid)
        self._waterid = waterid

        self.uri = BASE_URL
        for i in ATTR_LIST:
            self._attr_value[i] = None
        self._data.data[self._waterid] = {}
        self._data.data[self._waterid]['result'] = None

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self._name

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:currency-twd"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return CURRENCY_DOLLAR

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        self._attributes[ATTR_ATTRIBUTION] = ATTRIBUTION
        for i in ATTR_LIST:
            self._attributes[i] = self._attr_value[i]
        return self._attributes

    async def async_added_to_hass(self):
        """Get initial data."""
        # To make sure we get initial data for the sensors ignoring the normal
        # throttle of 45 mintunes but using an update throttle of 15 mintunes
        self.hass.async_add_executor_job(self.update_nothrottle)

    def update_nothrottle(self, dummy=None):
        """Update sensor without throttle."""
        self._data.update_no_throttle()

        # Schedule a forced update 15 mintunes in the future if the update above
        # returned no data for this sensors power number.
        if not self._data.expired:
            track_point_in_time(
                self.hass,
                self.update_nothrottle,
                dt_util.now() + MIN_TIME_BETWEEN_FORCED_UPDATES,
            )
            return

        self.schedule_update_ha_state()

    async def async_update(self):
        """Update state."""
#        self._data.update()
        self.hass.async_add_executor_job(self._data.update)
        if self._waterid in self._data.data:
            for i, j in self._data.data[self._waterid].items():
                if i is None:
                    continue
                if "\u61c9\u7e73\u91d1\u984d" in i:
                    self._state = ''.join(k for k in j if k.isdigit() or k == ".")
                    self._attr_value[ATTR_BILL_AMOUNT] = j
                if "\u7e73\u8cbb\u5e74\u6708" in i:
                    self._attr_value[ATTR_BILLING_MONTH] = j
                if "\u92b7\u5e33\u65e5\u671f" in i:
                    self._attr_value[ATTR_BILLING_DATE] = j
                if "\u92b7\u5e33\u65e5\u671f" in i:
                    self._attr_value[ATTR_PAYMENT] = j
                if "\u7528\u6c34\u5ea6\u6578(\u4e0d\u542b\u5206\u6524\u5ea6\u6578)" in i:
                    self._attr_value[ATTR_WATER_CONSUMPTION] = j
                if "\u8a08\u8cbb\u6642\u9593" in i:
                    self._attr_value[ATTR_DURATION] = j
            self._attr_value[ATTR_HTTPS_RESULT] = self._data.data[self._waterid].get(
                'result', 'Unknow')
            if self._attr_value[ATTR_HTTPS_RESULT] == HTTP_FORBIDDEN:
                self._state = None
