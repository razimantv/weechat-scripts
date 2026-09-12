# weechat-scripts

Scripts I use with [WeeChat](https://weechat.org/), particularly with the [wee-slack](https://github.com/wee-slack/wee-slack/) plugin

- [persistent_autohide](persistent_autohide.py) - The plugin allows channels to be individually marked for auto-hiding when they are not active or in the hotlist. Changes persist across WeeChat restarts by storing the list of channels in the plugin's configuration
- [buffer_rename](buffer_rename.py) - The plugin watches WeeChat buffer names and applies persistent substitutions to the buffer's short_name (the name displayed in the buflist). Designed to be used with wee-slack, particularly to rename people, but should work with any buffer.
- [prepare_upload](prepare_upload.py) - The plugin uses [yazi](https://github.com/sxyazi/yazi) to choose files for upload to Slack, and prepares a message to be used with `/slack upload`. **Warning**: multifile slack uploads and uploads with messages only work with [the all_features branch in my fork](https://github.com/razimantv/wee-slack/tree/all_features) of wee-slack.
