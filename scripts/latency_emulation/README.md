# Docker Network Emulation

- This dir contains scripts and config files to set up network latencies accross differet containers.

## Config file
- Take a look at ```tn-latency.json```
- It stores different container properties and inter-AWS AZ latencies

## Scripts
### tn-latency-set.sh
- Reads the config file and applies it to the containers
- Under the hood, it uses tc with IP based filtering to apply latencies on the traffic
- The script takes the json config file as its argument
```bash
sudo ./tn-latency-set.sh tn-latency.json
```

### tn-latency-reset.sh
- Reads the config file and resets tc config to its defaults
- - The script takes the json config file as its argument
```bash
sudo ./tn-latency-reset.sh tn-latency.json
```
