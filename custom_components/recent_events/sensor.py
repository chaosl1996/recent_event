from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_CALENDAR_ENTITY, CONF_EVENT_COUNT

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities
) -> bool:
    """设置传感器平台"""
    config = config_entry.data
    sensor = RecentEventSensor(hass, config)
    async_add_entities([sensor], update_before_add=True)
    return True

class RecentEventSensor(SensorEntity):
    _attr_icon = "mdi:calendar-text"
    _attr_should_poll = False

    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._events = []
        self._attr_name = f"Recent Events - {config[CONF_CALENDAR_ENTITY].split('.')}"
        self._attr_unique_id = f"recent_events_{config[CONF_CALENDAR_ENTITY]}"

    async def async_added_to_hass(self):
        """注册自动更新"""
        await self.async_update()
        async_track_time_interval(
            self.hass,
            self.async_update,
            timedelta(minutes=15)
        )

    async def async_update(self, now=None):
        """更新事件数据"""
        try:
            events = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {"entity_id": self._config[CONF_CALENDAR_ENTITY]},
                blocking=True,
                return_response=True
            )
            
            now = dt_util.now()
            self._events = sorted(
                [e for e in events if e.end >= now],  # 包含进行中的事件
                key=lambda x: x.start
            )[:self._config[CONF_EVENT_COUNT]]
            
        except Exception as e:
            self.hass.components.persistent_notification.create(
                f"Calendar update error: {str(e)}",
                title="Recent Events Error"
            )

    @property
    def state(self):
        """当前状态值"""
        return len(self._events)

    @property
    def extra_state_attributes(self):
        """扩展属性"""
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
