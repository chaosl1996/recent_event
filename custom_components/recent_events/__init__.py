import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .sensor import RecentEventSensor

_LOGGER = logging.getLogger(__name__)

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the recent event integration."""
    _LOGGER.info("Setting up recent event integration")

    # Register the sensor platform
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "integration"}
        )
    )

    return True
