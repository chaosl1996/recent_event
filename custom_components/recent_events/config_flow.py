import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from .const import DOMAIN, DEFAULT_EVENT_COUNT, CONF_CALENDAR_ENTITY, CONF_EVENT_COUNT

class RecentEventConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        calendars = self.hass.states.async_entity_ids(CALENDAR_DOMAIN)
        
        if not calendars:
            return self.async_abort(reason="no_calendars")
        
        if user_input is not None:
            return self.async_create_entry(
                title=f"Recent Events - {user_input[CONF_CALENDAR_ENTITY]}",
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CALENDAR_ENTITY): vol.In(
                    {eid: eid.split('.')[1] for eid in calendars}
                ),
                vol.Required(
                    CONF_EVENT_COUNT, 
                    default=DEFAULT_EVENT_COUNT
                ): vol.All(int, vol.Range(min=1, max=20))
            }),
            errors=errors
        )
