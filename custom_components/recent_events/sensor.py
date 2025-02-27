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
    
    # 类型转换和验证
    try:
        raw_value = config_entry.data[CONF_EVENT_COUNT]
        event_count = int(float(raw_value))
        if not 1 <= event_count <= 10:
            raise ValueError(f"Invalid event count: {event_count}")
    except (TypeError, ValueError) as e:
        _LOGGER.error(
            "Invalid event count configuration: Value '%s' error: %s",
            raw_value,
            str(e)
        )
        return False

    # 验证日历实体
    if not (state := hass.states.get(calendar_id)):
        _LOGGER.error("Calendar entity %s not found", calendar_id)
        return False

    if state.domain != "calendar":
        _LOGGER.error("Entity %s is not a calendar", calendar_id)
        return False

    # 创建传感器实例时传递转换后的整数值
    sensors = [
        RecentEventSensor(
            hass=hass,
            config_entry=config_entry,
            index=index,
            max_events=event_count
        )
        for index in range(event_count)
    ]
    
    async_add_entities(sensors, True)
    _LOGGER.debug("Successfully created %d event sensors", event_count)

class RecentEventSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar"
    _attr_should_poll = False

    def __init__(self, hass, config_entry, index, max_events):
        self._hass = hass
        self._config_entry = config_entry
        self._index = index
        self._max_events = max_events
        self._events = []
        
        # 显式设置实体唯一标识
        self._attr_unique_id = f"{config_entry.entry_id}_event_{index}"
        # 生成符合规范的entity_id
        self.entity_id = f"sensor.recent_event_{config_entry.entry_id}_{index}"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"{config_entry.data[CONF_CALENDAR_ID]} Events",
            "manufacturer": "Recent Events"
        }

    @property
    def name(self):
        """返回用户可见的名称"""
        return f"Event {self._index + 1}"

    @property
    def state(self):
        """返回当前状态"""
        if self._index < len(self._events):
            return self._events[self._index].get("summary", "No event")
        return "No event"

    @property
    def extra_state_attributes(self):
        """返回额外属性"""
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
        """更新传感器数据"""
        try:
            calendar_id = self._config_entry.data[CONF_CALENDAR_ID]
            
            # 获取事件
            events = await self._fetch_events(calendar_id)
            valid_events = self._validate_events(events.get(calendar_id, []))
            
            # 使用存储的整数进行切片
            self._events = sorted(
                valid_events,
                key=lambda x: x["start"].get("dateTime", x["start"].get("date"))
            )[:self._max_events]
            
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Update failed: %s", str(e))

    async def _fetch_events(self, calendar_id):
        """从日历服务获取事件"""
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
            _LOGGER.error("服务错误: %s", str(e))
            return {}

    def _validate_events(self, events):
        """验证日历事件有效性"""
        return [e for e in events if isinstance(e, dict) and e.get("start")]

    def _parse_datetime(self, dt_dict):
        """解析日期时间数据"""
        return dt_dict.get("dateTime") or dt_dict.get("date") if dt_dict else None

    async def async_added_to_hass(self):
        """实体被添加到Home Assistant时调用"""
        await super().async_added_to_hass()  # 添加父类调用
        self.async_on_remove(
            async_track_time_interval(
                self._hass,
                self.async_update,
                timedelta(minutes=5)
            )
        )
        # 延迟首次更新确保实体完全注册
        self.hass.async_create_task(self.async_update())
