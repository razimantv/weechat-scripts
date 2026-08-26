# -*- coding: utf-8 -*-
#
# WeeChat plugin for locally renaming buffers.
#
# The plugin watches WeeChat buffer names and applies persistent substitutions
# to the buffer's short_name (the name displayed in the buflist).
# Designed to be used with wee-slack, particularly to rename people, but should
# work with any buffer.
#
# Rules are stored as JSON in WeeChat's config directory:
#   <weechat_config_dir>/buffer_rename.json
#
# Example:
# {
#   "substitutions": [
#     ["very-long-channel-name-that-i-dont-like", "memorable-name"],
#     ["LongFullName", "Nick"]
#   ],
#   "removals": ["UserThatLeftTheTeamButShowsUpInGroupChat"]
# }
#
# Commands:
#   /buffer_rename list
#   /buffer_rename rename <old> <new>
#   /buffer_rename ignore <old>
#   /buffer_rename clear <old>
#   /buffer_rename clear-all
#   /buffer_rename reload
#
# The JSON file is the source of truth, so changes survive WeeChat restarts.
#
# Author: T. V. Raziman
# Supported by: ChatGPT
# Date: 2026-08-26
# License: MIT

from __future__ import print_function, unicode_literals

import json
import os

try:
    import weechat
except ImportError:
    raise RuntimeError("This script must be run under WeeChat.")


SCRIPT_NAME = "buffer_rename"
SCRIPT_AUTHOR = "T. V. Raziman"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Persistently rename buffers in the buflist"

CONFIG_FILENAME = "buffer_rename.json"

# We deliberately keep these empty: put your personal rules in the JSON file.
DEFAULT_CONFIG = { "substitutions": [], "removals": [] }

config = None
config_path = None
processing = set()


def get_config_path():
    data_dir = weechat.info_get("weechat_data_dir", "")
    if not data_dir:
        data_dir = weechat.info_get("weechat_dir", "")
    return os.path.join(data_dir, CONFIG_FILENAME)


def save_config():
    tmp_path = config_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, config_path)


def load_config():
    global config

    try:
        with open(config_path, "r") as f:
            loaded = json.load(f)
    except (IOError, OSError, ValueError):
        config = {
            "substitutions": list(DEFAULT_CONFIG["substitutions"]),
            "removals": list(DEFAULT_CONFIG["removals"]),
        }
        save_config()
        return

    config = {
        "substitutions": loaded.get("substitutions", []),
        "removals": loaded.get("removals", []),
    }


def transform(name):
    """Return the local display name for a WeeChat buffer name."""

    # Comma-separated members can be removed, then textual substitutions apply.
    parts = [
        part for part in name.split(",")
        if part not in config["removals"]
    ]
    name = ",".join(parts)

    for before, after in config["substitutions"]:
        name = name.replace(before, after)

    return name


def rename_buffer(buffer):
    if not buffer or buffer in processing:
        return

    current = weechat.buffer_get_string(buffer, "short_name")
    if not current:
        return

    new_name = transform(current)
    if new_name == current:
        return

    processing.add(buffer)
    try:
        weechat.buffer_set(buffer, "short_name", new_name)
    finally:
        processing.discard(buffer)


def rename_all_buffers():
    infolist = weechat.infolist_get("buffer", "", "")
    while weechat.infolist_next(infolist):
        buffer = weechat.infolist_pointer(infolist, "pointer")
        rename_buffer(buffer)
    weechat.infolist_free(infolist)


def buffer_name_changed(data, modifier, modifier_data, string):
    # Only alter the buffer's displayed short name. Do not alter canonical
    # buffer identity.
    buffer = modifier_data
    if buffer:
        rename_buffer(buffer)
    return string


def signal_buffer_opened(data, signal, signal_data):
    # WeeChat gives us the buffer pointer as signal_data on buffer_opened.
    rename_buffer(signal_data)
    return weechat.WEECHAT_RC_OK


def signal_buffer_renamed(data, signal, signal_data):
    rename_buffer(signal_data)
    return weechat.WEECHAT_RC_OK


def command_cb(data, buffer, args):
    argv = args.split(None, 2) if args else []
    command = argv[0] if argv else "list"

    if command == "list":
        if not config["substitutions"] and not config["removals"]:
            weechat.prnt("", "buffer_rename: no rules configured")
            return weechat.WEECHAT_RC_OK

        for old, new in config["substitutions"]:
            weechat.prnt("", "  {!r} -> {!r}".format(old, new))
        for old in config["removals"]:
            weechat.prnt("", "  {!r} -> ''".format(old))
        return weechat.WEECHAT_RC_OK
    elif command == "rename":
        if len(argv) < 3:
            weechat.prnt("", "Usage: /buffer_rename rename <old> <new>")
            return weechat.WEECHAT_RC_ERROR

        old, new = argv[1], argv[2]
        config["substitutions"].append([old, new])
        save_config()
        rename_all_buffers()
        return weechat.WEECHAT_RC_OK
    elif command == "ignore":
        if len(argv) < 2:
            weechat.prnt("", "Usage: /buffer_rename ignore <old>")
            return weechat.WEECHAT_RC_ERROR

        old = argv[1]
        config["removals"].append(old)
        save_config()
        rename_all_buffers()
        return weechat.WEECHAT_RC_OK
    elif command == "clear":
        if len(argv) != 2:
            weechat.prnt("", "Usage: /buffer_rename clear <old>")
            return weechat.WEECHAT_RC_ERROR

        old = argv[1]
        before = len(config["substitutions"])
        config["substitutions"] = [
            pair for pair in config["substitutions"] if pair[0] != old
        ]
        config["removals"] = [
            value for value in config["removals"] if value != old
        ]

        if len(config["substitutions"]) == before:
            weechat.prnt(
                "", "buffer_rename: no substitution for {!r}".format(old)
            )

        save_config()
        rename_all_buffers()
        return weechat.WEECHAT_RC_OK
    elif command == "clear-all":
        config["substitutions"] = []
        config["removals"] = []
        save_config()
        rename_all_buffers()
        return weechat.WEECHAT_RC_OK
    elif command == "reload":
        load_config()
        rename_all_buffers()
        return weechat.WEECHAT_RC_OK
    elif command == "save":
        save_config()
        return weechat.WEECHAT_RC_OK

    weechat.prnt(
        "",
        "Usage: /buffer_rename "
        "[list|rename|ignore|clear|clear-all|reload|save]"
    )
    return weechat.WEECHAT_RC_ERROR


if weechat is not None:
    # WeeChat must register the Python script before calling its API
    if weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "",
        "",
    ):
        config_path = get_config_path()
        load_config()

    weechat.hook_command(
        SCRIPT_NAME,
        SCRIPT_DESC,
        "list|rename|ignore|clear|clear-all|reload|save",
        "list: show all rules\n"
        "rename <old> <new>: add a substitution rule\n"
        "ignore <old>: add a removal rule\n"
        "clear <old>: remove any rule for <old>\n"
        "clear-all: remove all rules\n"
        "reload: reload rules from the JSON file\n"
        "save: save rules to the JSON file\n",
        "list|rename|ignore|clear|clear-all|reload|save",
        "command_cb",
        ""
    )

    # buffer_opened catches buffers created after the plugin loads.
    weechat.hook_signal("buffer_opened", "signal_buffer_opened", "")

    # buffer_renamed catches changes made by other plugins.
    weechat.hook_signal("buffer_renamed", "signal_buffer_renamed", "")

    rename_all_buffers()
