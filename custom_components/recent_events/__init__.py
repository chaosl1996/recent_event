import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from .sensor import RecentEventSensor
from .const import *

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the recent event integration from a config entry."""
    _LOGGER.info("Setting up recent event integration from config entry")

    # Extract configuration data from the config entry
    config = entry.data

    # Create and add the sensor
    sensor = RecentEventSensor(hass, config)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = sensor
    hass.add_job(sensor.async_refresh)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading recent event integration")
    sensor = hass.data[DOMAIN].pop(entry.entry_id)
    await sensor.async_remove()
    return True
