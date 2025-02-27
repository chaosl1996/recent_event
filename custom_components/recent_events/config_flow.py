import voluptuous as vol 
from homeassistant import config_entries 
from homeassistant.core  import callback 
from homeassistant.helpers  import selector 
from.const  import DOMAIN, CONF_ENTITY_ID, CONF_EVENT_COUNT, DEFAULT_NAME 
 
 
class RecentEventsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN): 
    """Handle a config flow for Recent Calendar Events.""" 
 
    VERSION = 1 
 
    async def async_step_user(self, user_input=None): 
        """Handle the initial step.""" 
        errors = {} 
        if user_input is not None: 
            # Check if the entity ID already exists in the config entries 
            await self.async_set_unique_id(user_input[CONF_ENTITY_ID])  
            self._abort_if_unique_id_configured() 
 
            return self.async_create_entry(  
                title=user_input.get(CONF_NAME,  DEFAULT_NAME), 
                data=user_input 
            ) 
 
        return self.async_show_form(  
            step_id="user", 
            data_schema=vol.Schema({ 
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str, 
                vol.Required(CONF_ENTITY_ID): selector.EntitySelector( 
                    selector.EntitySelectorConfig(domain="calendar") 
                ), 
                vol.Required(CONF_EVENT_COUNT, default=3): vol.All( 
                    vol.Coerce(int), 
                    vol.Range(min=1) 
                ) 
            }), 
            errors=errors 
        ) 
 
    @staticmethod 
    @callback 
    def async_get_options_flow(config_entry): 
        """Get the options flow for this handler.""" 
        return RecentEventsOptionsFlow(config_entry) 
 
 
class RecentEventsOptionsFlow(config_entries.OptionsFlow): 
    """Handle options flow for Recent Calendar Events.""" 
 
    def __init__(self, config_entry): 
        """Initialize options flow.""" 
        self.config_entry  = config_entry 
 
    async def async_step_init(self, user_input=None): 
        """Manage the options.""" 
        errors = {} 
        if user_input is not None: 
            return self.async_create_entry(title="",  data=user_input) 
 
        return self.async_show_form(  
            step_id="init", 
            data_schema=vol.Schema({ 
                vol.Required( 
                    CONF_ENTITY_ID, 
                    default=self.config_entry.data.get(CONF_ENTITY_ID)  
                ): selector.EntitySelector( 
                    selector.EntitySelectorConfig(domain="calendar") 
                ), 
                vol.Required( 
                    CONF_EVENT_COUNT, 
                    default=self.config_entry.data.get(CONF_EVENT_COUNT)  
                ): vol.All( 
                    vol.Coerce(int), 
                    vol.Range(min=1) 
                ) 
            }), 
            errors=errors 
        ) 
 
