# Prepare an upload listfor wee-slack
# Open yazi to choose files and add them to the input buffer
# Built from the edit-weechat.py script by Keith Smiley
#
# Usage:
# /prepare_upload

VERSION = "0.1"

import json
import os
import shlex
import tempfile

import weechat

upload_command = "/slack upload"


def filechooser_process_cb(data, command, return_code, out, err):
    buf, path = json.loads(data)

    if return_code != 0:
        cleanup(path, buf)
        weechat.prnt("", f"{err.strip()}: {return_code}")
        return weechat.WEECHAT_RC_ERROR

    update_input(path, buf)
    cleanup(path, buf)

    return weechat.WEECHAT_RC_OK


def cleanup(path, buf):
    try:
        os.remove(path)
    except OSError:
        pass

    weechat.command(buf, "/window refresh")


def update_input(path, buf):
    try:
        with open(path) as f:
            text = f.read().strip()

        # If text is empty, don't do anything
        if not text.strip():
            return

        text = f"{upload_command}\n" + text

        previous_input = weechat.buffer_get_string(buf, "input")
        if previous_input.startswith(upload_command):
            previous_input = previous_input[len(upload_command):].strip()
        if previous_input:
            text += "\n--\n" + previous_input

        weechat.buffer_set(buf, "input", text)
        weechat.buffer_set(buf, "input_pos", str(len(text)))

    except OSError:
        pass

    weechat.command(buf, "/window refresh")


def hook_filechooser_process(path, buf):
    data = json.dumps([buf, path])
    weechat.hook_process(
        shlex.join(
            [
                "zellij",
                "run",
                "-c",
                "-f",
                "--blocking",
                "--",
                "yazi",
                "--chooser-file",
                path,
            ]
        ),
        0,
        "filechooser_process_cb",
        data,
    )


def prepare_upload(data, buf, args):
    f, path = tempfile.mkstemp(prefix="weechat-yazi-")
    os.close(f)

    hook_filechooser_process(path, buf)
    return weechat.WEECHAT_RC_OK


def main():
    if not weechat.register(
        "prepare_upload",
        "T V Raziman",
        VERSION,
        "MIT",
        "Prepare files for /slack upload using yazi",
        "",
        "",
    ):
        return weechat.WEECHAT_RC_ERROR

    weechat.hook_command(
        "prepare_upload",
        "Open yazi to choose files and add them to the input buffer",
        "",
        "",
        "",
        "prepare_upload",
        "",
    )


if __name__ == "__main__":
    main()
