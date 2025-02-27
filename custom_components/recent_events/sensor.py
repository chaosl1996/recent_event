from datetime import timedelta 
import logging 
from homeassistant.helpers.entity  import Entity 
from homeassistant.components.calendar  import CalendarEntity 
from homeassistant.helpers.update_coordinator  import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from .const import DOMAIN, CONF_ENTITY_ID, CONF_EVENT_COUNT 
 
_LOGGER = logging.getLogger(__name__) 
 
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = RecentEventsCoordinator(
        hass,
        config_entry.data[CONF_ENTITY_ID], 
        config_entry.data[CONF_EVENT_COUNT] 
    )
    
    await coordinator.async_config_entry_first_refresh() 
    
    entities = []
    for i in range(config_entry.data[CONF_EVENT_COUNT]): 
        entities.append(RecentEventSensor(coordinator,  i, config_entry))
    
    async_add_entities(entities)
 
class RecentEventsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, calendar_entity_id, event_count):
        """Initialize coordinator"""
        super().__init__(
            hass,
            _LOGGER,
            name="Recent Events Coordinator",
            update_interval=timedelta(minutes=1)
        )
        self.calendar_entity_id  = calendar_entity_id 
        self.event_count  = event_count 
        self.events  = []
 
    async def _async_update_data(self):
        """Fetch calendar events"""
        calendar = self.hass.states.get(self.calendar_entity_id) 
        if not calendar:
            return 
 
        now = self.hass.config.util.utcnow() 
        end = now + timedelta(days=365)  # 1 year lookahead 
        
        events = await self.hass.components.calendar.async_get_events( 
            self.hass, 
            self.calendar_entity_id, 
            start_datetime=now,
            end_datetime=end 
        )
 
        # Sort and limit events 
        sorted_events = sorted(events, key=lambda x: x.start) 
        self.events  = sorted_events[:self.event_count] 
        return self.events  
 
class RecentEventSensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator, index, config_entry):
        """Initialize sensor"""
        super().__init__(coordinator)
        self._index = index 
        self._config_entry = config_entry 
        self._attr_unique_id = f"{config_entry.entry_id}_{index}" 
        self._attr_name = f"{config_entry.data.get('name')}  {index+1}"
 
    @property 
    def state(self):
        """Return the state of the sensor."""
        events = self.coordinator.data  or []
        if len(events) > self._index:
            return events[self._index].summary 
        return "No event"
 
    @property 
    def extra_state_attributes(self):
        """Return additional attributes"""
        if len(self.coordinator.data)  > self._index:
            event = self.coordinator.data[self._index] 
            return {
                "start": event.start.isoformat(), 
                "end": event.end.isoformat(), 
                "description": event.description, 
                "location": event.location, 
                "all_day": event.all_day  
            }
        return {}
