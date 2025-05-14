# Commands used to restart DAHDI when drivers randomly fail

DAHDI failing is a common issue I faced while modifying Asterisk configuration. The best solution would be to not touch the FPBX running T1 once it is set up.

## Restart wanrouter (this would restart DAHDI as well).
```
sudo /usr/sbin/wanrouter start
sudo /usr/sbin/wanrouter stop

OR

sudo /usr/sbin/wanrouter restart (this did not work all the time, so I wouldn't prefer it)
```
- When wanrouter is restarted, it cannot complete the process without killing asterisk, so Asterisk must be started back up manually.

### Kill asterisk (in case wanrouter fails to kill Asterisk)
```
`core stop gracefully` in asterisk CLI

OR

`fwconsole stop` in terminal. This kills FreePBX.
```

## Start Asterisk
- Wait a minute after wanrouter restarts and run this command as root.

```
/bin/sh /usr/sbin/safe_asterisk -U asterisk -G asterisk
```