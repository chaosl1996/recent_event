from datetime import timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, CONF_CALENDAR_ENTITY, CONF_EVENT_COUNT

class RecentEventSensor(Entity):
    _attr_icon = "mdi:calendar-text"
    _attr_should_poll = False

    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._events = []
        self._attr_name = f"Recent Events - {config[CONF_CALENDAR_ENTITY].split('.')}"
        self._attr_unique_id = f"recent_events_{config[CONF_CALENDAR_ENTITY]}"

    async def async_added_to_hass(self):
        await self.async_update()
        async_track_time_interval(
            self.hass,
            self.async_update,
            timedelta(minutes=15)
        )

    async def async_update(self, now=None):
        try:
            events = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {"entity_id": self._config[CONF_CALENDAR_ENTITY]},
                return_result=True
            )
            
            now = dt_util.now()
            self._events = sorted(
                [e for e in events if e.start >= now],
                key=lambda x: x.start
            )[:self._config[CONF_EVENT_COUNT]]
            
        except Exception as e:
            self.hass.components.persistent_notification.create(
                f"Calendar update error: {str(e)}",
                title="Recent Events Error"
            )

    @property
    def state(self):
        return len(self._events)

    @property
    def extra_state_attributes(self):
        return {
            "events": [
                {
                    "start": event.start.isoformat(),
                    "end": event.end.isoformat(),
                    "summary": event.summary,
                    "location": event.location or "",
                    "description": event.description or ""
                } for event in self._events
            ]
        }
