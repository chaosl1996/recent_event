import logging
import asyncio
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import ServiceNotFound
from .const import DOMAIN, CONF_CALENDAR_ID, CONF_EVENT_COUNT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    calendar_id = config_entry.data[CONF_CALENDAR_ID]
    event_count = int(config_entry.data[CONF_EVENT_COUNT])
    
    if not hass.states.get(calendar_id):
        _LOGGER.error("Calendar entity %s not found during setup", calendar_id)
        return False

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
            event_count = int(self._config_entry.data[CONF_EVENT_COUNT])

            if not self._hass.states.get(calendar_id):
                _LOGGER.error("Calendar entity %s not found", calendar_id)
                self._events = []
                self.async_write_ha_state()
                return

            try:
                events = await self._hass.services.async_call(
                    "calendar",
                    "get_events",
                    {
                        "entity_id": calendar_id,
                        "start_date_time": dt_util.now().isoformat(),
                        "end_date_time": (dt_util.now() + timedelta(days=365)).isoformat()
                    },
                    blocking=True,
                    return_response=True
                )
            except ServiceNotFound as e:
                _LOGGER.error("Calendar service not available: %s", str(e))
                return
            except asyncio.TimeoutError:
                _LOGGER.warning("Calendar service call timed out")
                return

            if not isinstance(events, dict):
                _LOGGER.error("Invalid response format: %s", type(events))
                self._events = []
                self.async_write_ha_state()
                return

            calendar_events = events.get(calendar_id, [])
            if not isinstance(calendar_events, list):
                _LOGGER.error("Expected list of events, got %s", type(calendar_events))
                self._events = []
                self.async_write_ha_state()
                return

            valid_events = []
            for event in calendar_events:
                if isinstance(event, dict) and event.get("start"):
                    start = event["start"]
                    if isinstance(start, dict) and (start.get("dateTime") or start.get("date")):
                        valid_events.append(event)
                else:
                    _LOGGER.debug("Invalid event format: %s", type(event))

            sorted_events = sorted(
                valid_events,
                key=lambda x: (
                    x.get("start", {}).get("dateTime") or 
                    x.get("start", {}).get("date") or 
                    ""
                )
            )

            self._events = sorted_events[:event_count]
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("Error updating events: %s", str(e), exc_info=True)

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
