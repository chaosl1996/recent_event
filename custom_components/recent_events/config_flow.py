from homeassistant import config_entries 
from homeassistant.core  import callback 
from homeassistant.helpers  import selector 
from .const import DOMAIN, CONF_ENTITY_ID, CONF_EVENT_COUNT, DEFAULT_NAME 
 
class RecentEventsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry( 
                title=user_input.get(CONF_NAME,  DEFAULT_NAME),
                data=user_input 
            )
 
        return self.async_show_form( 
            step_id="user",
            data_schema=config_entries.ConfigSchema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="calendar")
                    ),
                    vol.Required(CONF_EVENT_COUNT, default=3): int 
                }
            ),
            errors=errors 
        )
 
    @staticmethod 
    @callback 
    def async_get_options_flow(config_entry):
        return RecentEventsOptionsFlow(config_entry)
 
class RecentEventsOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry  = config_entry 
 
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="",  data=user_input)
 
        return self.async_show_form( 
            step_id="init",
            data_schema=config_entries.ConfigSchema(
                {
                    vol.Required(
                        CONF_ENTITY_ID,
                        default=self.config_entry.data.get(CONF_ENTITY_ID) 
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="calendar")
                    ),
                    vol.Required(
                        CONF_EVENT_COUNT,
                        default=self.config_entry.data.get(CONF_EVENT_COUNT) 
                    ): int 
                }
            ),
            errors=errors 
        )
