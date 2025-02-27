import logging
import asyncio
import re
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN, CONF_CALENDAR_ID, CONF_EVENT_COUNT

_LOGGER = logging.getLogger(__name__)

def sanitize_entity_id(input_str):
    """生成符合规范的entity_id字符串"""
    sanitized = input_str.lower()
    sanitized = re.sub(r"[^a-z0-9_]", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_")

async def async_setup_entry(hass, config_entry, async_add_entities):
    """设置传感器入口"""
    calendar_id = config_entry.data[CONF_CALENDAR_ID]
    
    # 验证事件数量配置
    try:
        event_count = int(config_entry.data[CONF_EVENT_COUNT])
        if not 1 <= event_count <= 10:
            raise ValueError("事件数量需在1-10之间")
    except (TypeError, ValueError) as e:
        _LOGGER.error("配置错误: %s", str(e))
        return False

    # 验证日历实体
    if not (state := hass.states.get(calendar_id)):
        _LOGGER.error("找不到日历实体: %s", calendar_id)
        return False

    if state.domain != "calendar":
        _LOGGER.error("实体不是日历: %s", calendar_id)
        return False

    # 创建传感器实例
    sensors = [
        RecentEventSensor(
            hass=hass,
            config_entry=config_entry,
            index=index,
            max_events=event_count
        ) for index in range(event_count)
    ]
    
    async_add_entities(sensors, True)
    _LOGGER.info("已成功创建 %d 个事件传感器", event_count)

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
        
        # 生成安全的entity_id
        base_id = f"{config_entry.entry_id}_event_{index}"
        safe_id = sanitize_entity_id(f"recent_event_{base_id}")
        self.entity_id = f"sensor.{safe_id}"
        self._attr_unique_id = base_id
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"{config_entry.data[CONF_CALENDAR_ID]} 事件",
            "manufacturer": "Recent Events"
        }

    @property
    def name(self):
        """返回用户友好名称"""
        return f"事件 {self._index + 1}"

    @property
    def state(self):
        """当前状态值"""
        try:
            return self._events[self._index].get("summary", "无事件")
        except IndexError:
            return "无事件"

    @property
    def extra_state_attributes(self):
        """额外属性信息"""
        if self._index >= len(self._events):
            return {}
            
        event = self._events[self._index]
        return {
            "summary": event.get("summary"),
            "start": self._format_time(event["start"]),
            "end": self._format_time(event["end"]),
            "location": event.get("location", ""),
            "description": event.get("description", "")
        }

    async def async_update(self, now=None):
        """更新事件数据"""
        try:
            calendar_id = self._config_entry.data[CONF_CALENDAR_ID]
            _LOGGER.debug("开始更新 %s 的事件数据", self.entity_id)
            
            # 获取日历事件
            raw_events = await self._fetch_events(calendar_id)
            valid_events = self._process_events(raw_events.get(calendar_id, []))
            
            # 过滤和排序事件
            now = dt_util.now()
            future_events = [
                e for e in valid_events
                if self._parse_time(e["end"]) > now
            ]
            sorted_events = sorted(future_events, key=lambda x: self._parse_time(x["start"]))
            
            self._events = sorted_events[:self._max_events]
            _LOGGER.debug("更新后事件列表: %s", [e["summary"] for e in self._events])
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("更新失败: %s", str(e), exc_info=True)

    async def _fetch_events(self, calendar_id):
        """从日历服务获取事件"""
        try:
            today = dt_util.now().replace(hour=0, minute=0, second=0)
            return await self._hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": calendar_id,
                    "start_date_time": today.isoformat(),
                    "end_date_time": (today + timedelta(days=14)).isoformat()
                },
                blocking=True,
                return_response=True
            )
        except (ServiceNotFound, asyncio.TimeoutError) as e:
            _LOGGER.error("服务调用失败: %s", str(e))
            return {}

    def _process_events(self, raw_events):
        """处理原始事件数据"""
        processed = []
        for event in raw_events:
            if not isinstance(event, dict):
                continue
                
            # 解析时间
            start = self._parse_calendar_time(event.get("start", {}))
            end = self._parse_calendar_time(event.get("end", start))
            
            if not start or not end:
                continue
                
            processed.append({
                "summary": event.get("summary", "未命名事件"),
                "start": {"dateTime": start.isoformat()} if isinstance(start, dt_util.datetime) else {"date": start.isoformat()},
                "end": {"dateTime": end.isoformat()} if isinstance(end, dt_util.datetime) else {"date": end.isoformat()},
                "location": event.get("location", ""),
                "description": event.get("description", "")
            })
        
        _LOGGER.debug("有效事件数: %d", len(processed))
        return processed

    def _parse_calendar_time(self, time_dict):
        """解析日历时间结构"""
        if "dateTime" in time_dict:
            return dt_util.parse_datetime(time_dict["dateTime"])
        if "date" in time_dict:
            return dt_util.parse_date(time_dict["date"])
        return None

    def _parse_time(self, time_dict):
        """转换为可比较的时间对象"""
        if "dateTime" in time_dict:
            return dt_util.as_local(dt_util.parse_datetime(time_dict["dateTime"]))
        if "date" in time_dict:
            return dt_util.as_local(dt_util.parse_datetime(time_dict["date"] + "T00:00:00"))
        return None

    def _format_time(self, time_dict):
        """格式化输出时间"""
        if "dateTime" in time_dict:
            return dt_util.parse_datetime(time_dict["dateTime"]).isoformat()
        if "date" in time_dict:
            return dt_util.parse_date(time_dict["date"]).isoformat()
        return None

    async def async_added_to_hass(self):
        """实体注册完成后的初始化"""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self._hass,
                self.async_update,
                timedelta(minutes=15)
            )
        )
        await self.async_update()
