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
    """Set up sensors from config entry."""
    calendar_id = config_entry.data[CONF_CALENDAR_ID]
    event_count = config_entry.data[CONF_EVENT_COUNT]
    
    # Validate calendar entity
    if not (state := hass.states.get(calendar_id)):
        _LOGGER.error("Calendar entity %s not found", calendar_id)
        return False

    if state.domain != "calendar":
        _LOGGER.error("Entity %s is not a calendar", calendar_id)
        return False

    # Create sensor instances
    sensors = [
        RecentEventSensor(hass, config_entry, index)
        for index in range(event_count)
    ]
    
    async_add_entities(sensors, True)

class RecentEventSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar"
    _attr_should_poll = False

    def __init__(self, hass, config_entry, index):
        self._hass = hass
        self._config_entry = config_entry
        self._index = index
        self._events = []
        
        self._attr_unique_id = f"{config_entry.entry_id}_event_{index}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"{config_entry.data[CONF_CALENDAR_ID]} Events",
            "manufacturer": "Recent Events"
        }

    @property
    def name(self):
        return f"Event {self._index + 1}"

    @property
    def state(self):
        return self._events[self._index].get("summary", "No event") if self._index < len(self._events) else "No event"

    @property
    def extra_state_attributes(self):
        if self._index >= len(self._events):
            return {}
            
        event = self._events[self._index]
        return {
            "summary": event.get("summary"),
            "start": self._parse_datetime(event.get("start")),
            "end": self._parse_datetime(event.get("end")),
            "location": event.get("location", ""),
            "description": event.get("description", "")
        }

    async def async_update(self, now=None):
        try:
            calendar_id = self._config_entry.data[CONF_CALENDAR_ID]
            
            # Fetch events
            events = await self._fetch_events(calendar_id)
            valid_events = self._validate_events(events.get(calendar_id, []))
            
            self._events = sorted(valid_events, 
                key=lambda x: x["start"].get("dateTime", x["start"].get("date")))[:self._config_entry.data[CONF_EVENT_COUNT]]
                
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Update failed: %s", str(e))

    async def _fetch_events(self, calendar_id):
        """Retrieve events from calendar service."""
        try:
            return await self._hass.services.async_call(
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
        except (ServiceNotFound, asyncio.TimeoutError) as e:
            _LOGGER.error("Service error: %s", str(e))
            return {}

    def _validate_events(self, events):
        """Filter valid calendar events."""
        return [e for e in events if isinstance(e, dict) and e.get("start")]

    def _parse_datetime(self, dt_dict):
        return dt_dict.get("dateTime") or dt_dict.get("date") if dt_dict else None

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_track_time_interval(
                self._hass,
                self.async_update,
                timedelta(minutes=5)
            )
        )
        await self.async_update()
