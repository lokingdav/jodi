# Control Plane Extension For Telephony
Implementation of the CPeX paper

Run experiment in background

```bash
nohup ./prototype.sh runexp 1 > output.log 2>&1 & echo $! > exp1.pid
```
This runs the experiment in the background and saves the output to `output.log`. The process ID is saved to `exp1.pid`.

To Kill the experiment, run:

```bash
kill -9 $(cat exp1.pid)
```

Run Grafana k6 load test
```bash
k6 run --config cpex/prototype/experiments/k6/options.json cpex/prototype/experiments/k6/<protocol>.js # replace <protocol> with cpex or atis
```
