from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol
from homeassistant.core import callback
from .const import DOMAIN, CONF_CALENDAR_ID, CONF_EVENT_COUNT, DEFAULT_EVENT_COUNT

class RecentEventsFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        
        if user_input:
            try:
                await self._validate_input(user_input, errors)
                if not errors:
                    return self._create_entry(user_input)
            except Exception as e:
                _LOGGER.error("Configuration error: %s", str(e))
                errors["base"] = "unknown_error"

        return self._show_config_form(errors)

    async def _validate_input(self, user_input, errors):
        """Validate user input."""
        # Validate calendar entity
        if not self.hass.states.get(user_input[CONF_CALENDAR_ID]):
            errors[CONF_CALENDAR_ID] = "entity_not_found"
        
        # Validate event count
        event_count = int(user_input[CONF_EVENT_COUNT])
        if not 1 <= event_count <= 10:
            errors[CONF_EVENT_COUNT] = "invalid_count"

    def _create_entry(self, user_input):
        """Create config entry."""
        return self.async_create_entry(
            title=f"{user_input[CONF_CALENDAR_ID]} Events",
            data=user_input
        )

    def _show_config_form(self, errors):
        """Show configuration form."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CALENDAR_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
                vol.Required(CONF_EVENT_COUNT, default=DEFAULT_EVENT_COUNT): 
                    selector.NumberSelector(selector.NumberSelectorConfig(
                        min=1, max=10, step=1))
            }),
            errors=errors,
            description_placeholders={
                "error_info": ", ".join(errors.values()) if errors else ""
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input:
            if 1 <= int(user_input[CONF_EVENT_COUNT]) <= 10:
                return self.async_create_entry(title="", data=user_input)
            errors[CONF_EVENT_COUNT] = "invalid_count"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_EVENT_COUNT, 
                    default=self.config_entry.options.get(CONF_EVENT_COUNT, 
                        self.config_entry.data[CONF_EVENT_COUNT])): 
                        selector.NumberSelector(selector.NumberSelectorConfig(
                            min=1, max=10, step=1))
            }),
            errors=errors
        )
