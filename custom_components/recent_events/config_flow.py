from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DOMAIN, CONF_CALENDAR_ID, CONF_EVENT_COUNT, DEFAULT_EVENT_COUNT

class RecentEventsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CALENDAR_ID])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"{user_input[CONF_CALENDAR_ID]} Events",
                data={
                    CONF_CALENDAR_ID: user_input[CONF_CALENDAR_ID],
                    CONF_EVENT_COUNT: int(user_input[CONF_EVENT_COUNT])  # 转换为整数
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CALENDAR_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar", multiple=False)
                ),
                vol.Required(
                    CONF_EVENT_COUNT,
                    default=DEFAULT_EVENT_COUNT
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=10,
                        mode="box",
                        step=1  # 强制整数输入
                    )
                )
            }),
            errors=errors
        )

    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    def async_get_options_flow(config_entry):
        return RecentEventsOptionsFlow(config_entry)

class RecentEventsOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={
                CONF_EVENT_COUNT: int(user_input[CONF_EVENT_COUNT])  # 转换为整数
            })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_EVENT_COUNT,
                    default=self.config_entry.data.get(CONF_EVENT_COUNT, DEFAULT_EVENT_COUNT)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=10,
                        mode="box",
                        step=1  # 强制整数输入
                    )
                )
            })
        )
