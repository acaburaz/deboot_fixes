# 05 — Moving files on/off the robot over LAN

Pasting binaries over UART is impractical. The robot and your PC are on the same
LAN, so use HTTP (robot → PC) and `nc` (PC → robot). Both servers below are
**manual and non-persistent** — they vanish on reboot, which is fine.

Assume the robot is `192.168.0.223` and your PC is `192.168.0.215` — adjust.

## Robot → PC (pull files off)

On the **robot**, serve the whole filesystem over HTTP:

```
busybox httpd -p 8080 -h /
```

On the **PC**, fetch by exact path (busybox httpd has no directory listing):

```
curl http://192.168.0.223:8080/usr/lib/node/liberos_node_alert.so -o liberos_node_alert.so
curl http://192.168.0.223:8080/etc/fw.manifest
```

To "list" a directory, write a listing to a file the server can serve:

```
ls -la /usr/lib/node > /tmp/ls.txt     # on the robot
curl http://192.168.0.223:8080/tmp/ls.txt   # on the PC
```

## PC → robot (push files on)

The robot's `vsftpd` chroots to `/tmp` and often isn't running, so use `nc`:
the **robot listens**, the **PC connects** (your PC never opens a server port).

On the **robot**:

```
nc -l -p 9999 > /data/patch/liberos_node_alert.so
```

On the **PC** (needs `ncat` from Nmap, or any `nc` client):

```
ncat --send-only --wait 15s 192.168.0.223 9999 < liberos_node_alert.patched.so
```

Then **verify the transfer** by md5 on both ends:

```
md5sum /data/patch/liberos_node_alert.so        # on the robot
```

## Tips

- Prefer `md5sum` to confirm integrity after every transfer.
- Make shell scripts executable (`chmod +x`) and syntax-check before reboot
  (`sh -n file.sh && echo OK`).
- If `httpd`/`nc` die, just start them again — they're disposable.
