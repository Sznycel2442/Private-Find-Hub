from __future__ import annotations

import base64
from typing import Any
from uuid import uuid4

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import async_lock_entry, async_unlock_entry, vault_path
from .api.mock import MOCK_DEVICES, create_mock_keys
from .const import (
    ADAPTER_MOCK,
    CONF_ACCOUNT_LABEL,
    CONF_ADAPTER,
    CONF_AGING_MINUTES,
    CONF_FRESH_MINUTES,
    CONF_MAX_ACCURACY_M,
    CONF_RECORDER_ACKNOWLEDGED,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SELECTED_TAGS,
    CONF_VAULT_ID,
    DEFAULT_AGING_MINUTES,
    DEFAULT_FRESH_MINUTES,
    DEFAULT_MAX_ACCURACY_M,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
    RECORDER_EXAMPLE,
)
from .security.vault import (
    MIN_PASSPHRASE_LENGTH,
    SecretVault,
    VaultAuthenticationError,
    VaultCorruptedError,
    VaultError,
)

CONF_PASSPHRASE = "passphrase"
CONF_OLD_PASSPHRASE = "old_passphrase"
CONF_NEW_PASSPHRASE = "new_passphrase"
CONF_CONFIRM = "confirm"


def password_selector() -> TextSelector:
    return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def tags_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                {"value": device.device_id, "label": device.name} for device in MOCK_DEVICES
            ],
            multiple=True,
            mode="list",
        )
    )


class PrivateFindHubConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._account_label = ""
        self._passphrase = ""
        self._selected_tags: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            passphrase = str(user_input[CONF_PASSPHRASE])
            if len(passphrase) < MIN_PASSPHRASE_LENGTH:
                errors[CONF_PASSPHRASE] = "passphrase_too_short"
            else:
                await self.async_set_unique_id("private-find-hub-mock-prototype")
                self._abort_if_unique_id_configured()
                self._account_label = str(user_input[CONF_ACCOUNT_LABEL]).strip()
                self._passphrase = passphrase
                return await self.async_step_tags()
        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_ACCOUNT_LABEL, default="Private Find Hub"): str,
                    probatio.Required(CONF_PASSPHRASE): password_selector(),
                }
            ),
            errors=errors,
        )

    async def async_step_tags(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = list(user_input[CONF_SELECTED_TAGS])
            if not selected:
                errors[CONF_SELECTED_TAGS] = "select_at_least_one"
            else:
                self._selected_tags = selected
                return await self.async_step_privacy()
        return self.async_show_form(
            step_id="tags",
            data_schema=probatio.Schema(
                {probatio.Required(CONF_SELECTED_TAGS): tags_selector()}
            ),
            errors=errors,
        )

    async def async_step_privacy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            acknowledged = bool(user_input[CONF_RECORDER_ACKNOWLEDGED])
            if not acknowledged:
                errors[CONF_RECORDER_ACKNOWLEDGED] = "recorder_ack_required"
            else:
                vault_id = uuid4().hex
                keys = create_mock_keys()
                payload = {
                    "adapter": ADAPTER_MOCK,
                    "device_keys": {
                        device_id: base64.b64encode(key).decode("ascii")
                        for device_id, key in keys.items()
                    },
                }
                vault = SecretVault(vault_path(self.hass, vault_id))
                try:
                    await self.hass.async_add_executor_job(
                        vault.create, self._passphrase, vault_id, payload
                    )
                except VaultError:
                    errors["base"] = "vault_create_failed"
                else:
                    self._passphrase = ""
                    return self.async_create_entry(
                        title=self._account_label,
                        data={
                            CONF_ACCOUNT_LABEL: self._account_label,
                            CONF_ADAPTER: ADAPTER_MOCK,
                            CONF_VAULT_ID: vault_id,
                        },
                        options={
                            CONF_SELECTED_TAGS: self._selected_tags,
                            CONF_SCAN_INTERVAL_MINUTES: DEFAULT_SCAN_INTERVAL_MINUTES,
                            CONF_FRESH_MINUTES: DEFAULT_FRESH_MINUTES,
                            CONF_AGING_MINUTES: DEFAULT_AGING_MINUTES,
                            CONF_MAX_ACCURACY_M: DEFAULT_MAX_ACCURACY_M,
                            CONF_RECORDER_ACKNOWLEDGED: True,
                        },
                    )
        return self.async_show_form(
            step_id="privacy",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_RECORDER_ACKNOWLEDGED, default=False
                    ): BooleanSelector()
                }
            ),
            description_placeholders={"recorder_config": RECORDER_EXAMPLE},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            entry = self._get_reauth_entry()
            try:
                await async_unlock_entry(self.hass, entry, str(user_input[CONF_PASSPHRASE]))
            except VaultAuthenticationError:
                errors[CONF_PASSPHRASE] = "invalid_passphrase"
            except VaultCorruptedError:
                errors["base"] = "vault_corrupted"
            else:
                return self.async_abort(reason="reauth_successful")
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=probatio.Schema(
                {probatio.Required(CONF_PASSPHRASE): password_selector()}
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return PrivateFindHubOptionsFlow()


class PrivateFindHubOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=("unlock", "lock", "settings", "privacy", "rotate"),
        )

    async def async_step_unlock(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await async_unlock_entry(
                    self.hass,
                    self.config_entry,
                    str(user_input[CONF_PASSPHRASE]),
                )
            except VaultAuthenticationError:
                errors[CONF_PASSPHRASE] = "invalid_passphrase"
            except VaultCorruptedError:
                errors["base"] = "vault_corrupted"
            else:
                return self.async_create_entry(title="", data=self.config_entry.options)
        return self.async_show_form(
            step_id="unlock",
            data_schema=probatio.Schema(
                {probatio.Required(CONF_PASSPHRASE): password_selector()}
            ),
            errors=errors,
        )

    async def async_step_lock(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None and bool(user_input[CONF_CONFIRM]):
            await async_lock_entry(self.hass, self.config_entry)
            return self.async_create_entry(title="", data=self.config_entry.options)
        return self.async_show_form(
            step_id="lock",
            data_schema=probatio.Schema(
                {probatio.Required(CONF_CONFIRM, default=False): BooleanSelector()}
            ),
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        options = self.config_entry.options
        if user_input is not None:
            fresh = int(user_input[CONF_FRESH_MINUTES])
            aging = int(user_input[CONF_AGING_MINUTES])
            selected = list(user_input[CONF_SELECTED_TAGS])
            if not selected:
                errors[CONF_SELECTED_TAGS] = "select_at_least_one"
            elif fresh > aging:
                errors[CONF_AGING_MINUTES] = "aging_before_fresh"
            else:
                updated = dict(options)
                updated.update(user_input)
                updated[CONF_SELECTED_TAGS] = selected
                return self.async_create_entry(title="", data=updated)
        return self.async_show_form(
            step_id="settings",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_SELECTED_TAGS,
                        default=list(options.get(CONF_SELECTED_TAGS, ())),
                    ): tags_selector(),
                    probatio.Required(
                        CONF_SCAN_INTERVAL_MINUTES,
                        default=options.get(
                            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_MINUTES,
                            max=MAX_SCAN_INTERVAL_MINUTES,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    probatio.Required(
                        CONF_FRESH_MINUTES,
                        default=options.get(CONF_FRESH_MINUTES, DEFAULT_FRESH_MINUTES),
                    ): NumberSelector(NumberSelectorConfig(min=1, max=1440, step=1)),
                    probatio.Required(
                        CONF_AGING_MINUTES,
                        default=options.get(CONF_AGING_MINUTES, DEFAULT_AGING_MINUTES),
                    ): NumberSelector(NumberSelectorConfig(min=1, max=10080, step=1)),
                    probatio.Required(
                        CONF_MAX_ACCURACY_M,
                        default=options.get(CONF_MAX_ACCURACY_M, DEFAULT_MAX_ACCURACY_M),
                    ): NumberSelector(NumberSelectorConfig(min=1, max=100000, step=1)),
                }
            ),
            errors=errors,
        )

    async def async_step_privacy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        options = self.config_entry.options
        if user_input is not None:
            updated = dict(options)
            updated[CONF_RECORDER_ACKNOWLEDGED] = bool(
                user_input[CONF_RECORDER_ACKNOWLEDGED]
            )
            return self.async_create_entry(title="", data=updated)
        return self.async_show_form(
            step_id="privacy",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_RECORDER_ACKNOWLEDGED,
                        default=options.get(CONF_RECORDER_ACKNOWLEDGED, False),
                    ): BooleanSelector()
                }
            ),
            description_placeholders={"recorder_config": RECORDER_EXAMPLE},
        )

    async def async_step_rotate(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            new_passphrase = str(user_input[CONF_NEW_PASSPHRASE])
            if len(new_passphrase) < MIN_PASSPHRASE_LENGTH:
                errors[CONF_NEW_PASSPHRASE] = "passphrase_too_short"
            else:
                vault = self.config_entry.runtime_data.vault
                try:
                    await self.hass.async_add_executor_job(
                        vault.rotate,
                        str(user_input[CONF_OLD_PASSPHRASE]),
                        new_passphrase,
                    )
                except VaultAuthenticationError:
                    errors[CONF_OLD_PASSPHRASE] = "invalid_passphrase"
                except VaultError:
                    errors["base"] = "vault_rotation_failed"
                else:
                    await async_lock_entry(self.hass, self.config_entry)
                    return self.async_create_entry(title="", data=self.config_entry.options)
        return self.async_show_form(
            step_id="rotate",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_OLD_PASSPHRASE): password_selector(),
                    probatio.Required(CONF_NEW_PASSPHRASE): password_selector(),
                }
            ),
            errors=errors,
        )

