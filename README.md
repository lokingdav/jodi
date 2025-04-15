# Control Plane Extension For Telephony

- This repository contains the code for setting up
    - Jodi Evaluators (EV) and Message Stores (MS) on the cloud
    - ATIS OOB STIR/SHAKEN CPSes on the cloud
    - Jodi and OOB STIR/SHAKEN proxy on the providers infrastructure
- All of the components are Dockerized for easy and scalable deployment

## Jodi Evaluators and Message Stores
- The current setup uses Terraform and Ansible to set up multiple instances of EV and MS on AWS over different zones in the US
- Once the setup is done, ```automation/hosts.yml``` and ```.env``` files are created, which will be used by the proxy
- Command for the setup TODO
```bash
./prototype.sh up
```

## ATIS OOB STIR/SHAKEN CPS
- The current setup uses Terraform and Ansible to set up multiple instances of CPSes on AWS over different zones in the US
- Once the setup is done, ```automation/hosts.yml``` and ```.env``` files are created, which will be used by the proxy
- Command for the setup TODO
```bash
./prototype.sh up
```

## Jodi and OOB STIR/SHAKEN proxy
- The proxy is run within a provider's infrastructure
- Clone the repository and copy the ```automation/hosts.yml``` and ```.env``` files over from the cloud setup
- To run the Jodi proxy, run
```bash
docker compose --profile jodi_proxy up -d
```
- To run the OOB SS proxy, run
```bash
docker compose --profile oobss_proxy up -d
```
- Once either of the proxies is running, get the URL of it and provide it to the JIWF.



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
