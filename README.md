# Jodi - Jodi’s Out-of-band Dial Intelligence

The STIR/SHAKEN caller attestation framework to combat pervasive telephone abuse. This initiative has not achieved its goals, partly because legacy non-VoIP infrastructure could not participate. The industry solution to extend STIR/SHAKEN broadcasts sensitive metadata of every non-VoIP call in plaintext to every third party required to facilitate the system. It has no mechanism to determine if a provider's request for call data is appropriate, nor can it ensure that every copy of that call data is unavailable after its specified expiration. It threatens both individual privacy and industry trade secrets.

Jodi (pronounced “YOH-dee"), is a distributed system that securely extends STIR/SHAKEN across telephone network technologies. It provides secure out-of-band signaling for transmitting STIR/SHAKEN PASSPorTs even with non-VoIP infrastructure and protects confidentiality of subscriber identity. Not only is Jodi a superior approach, it provides a transformative tool for future improvements, such as stronger call authentication or features like Branded Calling.

Jodi makes use of Oblivious Pseudorandom Functions (OPRFs), Threshold Group Signatures (TGS) and Symmetric Key Encryption to ensure its security guarantees. Jodi distributes secrets in a T-out of-N scheme. So, at least T members of the group have to collude to leak any secrets as compared to 1 in the original OOB SS design.

- The code repository contains the source code for setting up
    - Jodi Evaluators (EV) and Message Stores (MS) on the cloud
    - OOB STIR/SHAKEN CPSes on the cloud
    - Jodi and OOB STIR/SHAKEN proxy on the providers infrastructure
- All of the components are Dockerized for easy and scalable deployment


## Setup Instructions
- Install Docker and Docker Compose
- Run ```sudo chmod +x ./prototype && sudo chmod +x -R scripts/``` to make the scripts executable
- Create a copy of ```.env``` file and update the values as per your setup.
- Run ```./prototype.sh build``` to build the Docker images
- Run ```./prototype.sh up``` to start the services


## Jodi Evaluators and Message Stores
- The current setup uses Terraform and Ansible to set up multiple instances of EV and MS on AWS over different zones in the US
- Once the setup is done, ```automation/hosts.yml``` and ```.env``` files are created, which will be used by the proxy
- Command for the setup TODO
```bash
./prototype.sh up
```

## OOB STIR/SHAKEN CPS
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



## Other Useful Commands

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
k6 run --config jodi/prototype/experiments/k6/options.json jodi/prototype/experiments/k6/<protocol>.js # replace <protocol> with jodi or oobss
```
