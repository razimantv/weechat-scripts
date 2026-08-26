# -*- coding: utf-8 -*-
#
# WeeChat plugin for auto-hiding channels when inactive.
#
# The plugin allows channels to be marked for auto-hiding when they are not
# active or in the hotlist. Changes persist across WeeChat restarts by storing
# the list of channels in the plugin's configuration. This is useful for Slack
# channels that are noisy but not important.
#
# Commands:
#   /persistent_autohide
#
# Author: T. V. Raziman
# Supported by: Gemini 3 Pro
# Date: 2026-08-26
# License: MIT

import weechat

SCRIPT_NAME = "persistent_autohide"
SCRIPT_AUTHOR = "T. V. Raziman"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Toggle auto-hide for current channel"

CONFIG_OPTION = "channels"


def get_target_channels() -> set[str]:
    """Read configured channels from WeeChat plugin options."""
    config_val = weechat.config_get_plugin(CONFIG_OPTION)
    if not config_val:
        return set()
    return {c.strip() for c in config_val.split(", ") if c.strip()}


def set_target_channels(channels: set[str]) -> None:
    """Save target channels back to WeeChat plugin options."""
    weechat.config_set_plugin(CONFIG_OPTION, ", ".join(sorted(channels)))


def get_active_buffers() -> set[str]:
    """Return pointers of buffers currently in the hotlist."""
    active = set()
    infolist = weechat.infolist_get("hotlist", "", "")
    if infolist:
        while weechat.infolist_next(infolist):
            active.add(weechat.infolist_pointer(infolist, "buffer_pointer"))
        weechat.infolist_free(infolist)
    return active


def update_visibilities() -> None:
    """Update hidden state for all target buffers."""
    targets = get_target_channels()
    active_buffers = get_active_buffers()
    current_buffer = weechat.current_buffer()

    infolist = weechat.infolist_get("buffer", "", "")
    if infolist:
        while weechat.infolist_next(infolist):
            buf_ptr = weechat.infolist_pointer(infolist, "pointer")
            full_name = weechat.buffer_get_string(buf_ptr, "full_name")
            short_name = weechat.buffer_get_string(buf_ptr, "short_name")

            # Match on full buffer name or short name
            if full_name in targets or short_name in targets:
                if buf_ptr == current_buffer or buf_ptr in active_buffers:
                    weechat.buffer_set(buf_ptr, "hidden", "0")
                else:
                    weechat.buffer_set(buf_ptr, "hidden", "1")

        weechat.infolist_free(infolist)


def command_cb(data: str, buffer: str, args: str) -> int:
    """Callback for /persistent_autohide command."""
    if not buffer:
        buffer = weechat.current_buffer()

    full_name = weechat.buffer_get_string(buffer, "full_name")
    short_name = weechat.buffer_get_string(buffer, "short_name") or full_name

    targets = get_target_channels()

    # Identify existing match (prefer full_name, fall back to short_name)
    target_id = full_name if full_name in targets else (
        short_name if short_name in targets else full_name
    )

    if target_id in targets:
        targets.remove(target_id)
        weechat.buffer_set(buffer, "hidden", "0")
        weechat.prnt(
            "", f"{weechat.prefix('action')}persistent_autohide: "
            f"Disabled auto-hide for {short_name}"
        )
    else:
        targets.add(target_id)
        weechat.prnt(
            "", f"{weechat.prefix('action')}persistent_autohide: "
            f"Enabled auto-hide for {short_name}"
        )

    set_target_channels(targets)
    update_visibilities()
    return weechat.WEECHAT_RC_OK


def signal_cb(data: str, signal: str, signal_data: str) -> int:
    """Trigger visibility update on hotlist or buffer switch events."""
    update_visibilities()
    return weechat.WEECHAT_RC_OK


def config_cb(data: str, option: str, value: str) -> int:
    """Trigger visibility updates when configuration variable changes."""
    update_visibilities()
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__":
    if weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "",
        "",
    ):
        if not weechat.config_is_set_plugin(CONFIG_OPTION):
            weechat.config_set_plugin(CONFIG_OPTION, "")

        weechat.hook_command(
            "persistent_autohide",
            "Toggle auto-hide status for the current channel",
            "",
            "Run /persistent_autohide in any channel to toggle auto-hiding "
            "when inactive.",
            "",
            "command_cb",
            "",
        )

        weechat.hook_signal("hotlist_changed", "signal_cb", "")
        weechat.hook_signal("buffer_switch", "signal_cb", "")
        weechat.hook_signal("buffer_opened", "signal_cb", "")
        weechat.hook_config(
            f"plugins.var.python.{SCRIPT_NAME}.{CONFIG_OPTION}", "config_cb",
            ""
        )

        update_visibilities()
