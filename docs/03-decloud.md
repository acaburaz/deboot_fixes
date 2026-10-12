# 03 — De-cloud (block the cloud, keep the LAN)

The robot streams camera/telemetry to Ecovacs' cloud (AWS Kinesis / Aliyun
Linkkit) and phones home via MQTT. With root you can cut that off at the network
layer while the robot keeps cleaning (it runs locally via ROS).

## Why routes, not iptables

This firmware ships **no `iptables`** — only `/sbin/ip`. So instead of a
firewall we install two **blackhole routes** that cover the entire internet:

```
ip route add blackhole 0.0.0.0/1     # 0.0.0.0   – 127.255.255.255
ip route add blackhole 128.0.0.0/1   # 128.0.0.0 – 255.255.255.255
```

These `/1` routes are **more specific than the default `/0` route**, so they
win and drop all internet-bound traffic. Your LAN keeps working because the
on-link `/24` route (e.g. `192.168.0.0/24`) is more specific still. `dhcpcd`
only manages the default route, so it can't undo these.

## Install (persistent)

The watchdog restarts crashed daemons, so blocking at the network layer (rather
than killing the cloud processes) avoids fighting it. Put the script in the
`/data/autostart/` hook — it runs on every boot.

[`autostart/00-decloud.sh`](../autostart/00-decloud.sh):

```sh
#!/bin/sh
ip route add blackhole 0.0.0.0/1   2>/dev/null
ip route add blackhole 128.0.0.0/1 2>/dev/null
ip -6 route add blackhole ::/0     2>/dev/null
```

Deploy (adjust the LAN if yours isn't `192.168.0.0/24` — the blackhole lines
don't reference it, so usually no change needed):

```
mkdir -p /data/autostart
# copy the file to /data/autostart/00-decloud.sh (see doc 05 for transfer)
chmod +x /data/autostart/00-decloud.sh
```

> The stock `autostart.sh` runs `/data/autostart/*.sh start`, so write the
> script to respond to a `start` argument, or make it apply unconditionally on
> any invocation. The version in this repo applies on any arg.

## Verify

From another LAN device / your router: the robot still gets a DHCP lease but has
**no internet**, and the Ecovacs app goes **offline**.

## Trade-offs

- **The app stops working** — app control is routed through the cloud. The robot
  still cleans; physical/dock controls still work.
- **No NTP** — the clock won't sync, so timestamps drift (point it at a LAN time
  source if you care). Harmless for cleaning.
- **Narrower block possible** — if you want to keep *some* app function, block
  only the camera-streaming/MQTT endpoints instead of all WAN.

## Rollback

```
rm /data/autostart/00-decloud.sh
reboot
```
