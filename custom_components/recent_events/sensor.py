import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_CALENDAR_ID, CONF_EVENT_COUNT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    calendar_id = config_entry.data[CONF_CALENDAR_ID]
    event_count = config_entry.data[CONF_EVENT_COUNT]
    
    sensors = [
        RecentCalendarEventSensor(hass, config_entry, index)
        for index in range(event_count)
    ]
    
    async_add_entities(sensors, True)

class RecentCalendarEventSensor(SensorEntity):
    _attr_icon = "mdi:calendar"
    _attr_should_poll = False

    def __init__(self, hass, config_entry, index):
        self._hass = hass
        self._config_entry = config_entry
        self._index = index
        self._events = []
        
        self._attr_name = f"Recent Event {index + 1}"
        self._attr_unique_id = f"{config_entry.entry_id}_event_{index}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"{config_entry.data[CONF_CALENDAR_ID]} Events",
            "manufacturer": "Recent Events"
        }

    @property
    def extra_state_attributes(self):
        if self._index < len(self._events):
            event = self._events[self._index]
            return {
                "summary": event.get("summary"),
                "start": self._parse_datetime(event.get("start")),
                "end": self._parse_datetime(event.get("end")),
                "description": event.get("description"),
                "location": event.get("location")
            }
        return {}

    @property
    def state(self):
        if self._index < len(self._events):
            return self._events[self._index].get("summary", "No event")
        return "No event"

    async def async_update(self, now=None):
        try:
            calendar_id = self._config_entry.data[CONF_CALENDAR_ID]
            event_count = self._config_entry.data[CONF_EVENT_COUNT]

            events = await self._hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": calendar_id,
                    "start_date_time": dt_util.now().isoformat(),
                    "end_date_time": (dt_util.now() + timedelta(days=365)).isoformat()
                },
                return_response=True
            )

            if events and calendar_id in events:
                valid_events = [
                    event for event in events[calendar_id]
                    if event.get("start") and event.get("start").get("dateTime")
                ]
                sorted_events = sorted(
                    valid_events,
                    key=lambda x: x["start"]["dateTime"]
                )
                self._events = sorted_events[:event_count]
            else:
                self._events = []

            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Error updating events: %s", str(e))

    def _parse_datetime(self, dt_dict):
        """Parse datetime from calendar event format"""
        if not dt_dict:
            return None
        return dt_dict.get("dateTime") or dt_dict.get("date")

    async def async_added_to_hass(self):
        """Set up update listener."""
        self.async_on_remove(
            async_track_time_interval(
                self._hass,
                self.async_update,
                timedelta(minutes=5)
            )
        )
        await self.async_update()
