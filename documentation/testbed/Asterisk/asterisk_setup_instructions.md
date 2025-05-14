# Jodi Enhanced Asterisk (JAsterisk)

- This document explains how to set up Asterisk with JIWF. 
- We developed the JIWF and integrated it with Asterisk version 21.4.3 running on Debian 12.7.0.

## Setup
- Please read the file fully before starting the setup process

### OS
- Download and Install [Debain 12.7.0](https://cloud.debian.org/images/archive/12.7.0/amd64/iso-dvd/debian-12.7.0-amd64-DVD-1.iso)

### Building Asterisk
- Download [Asterisk version 21.4.3](https://github.com/asterisk/asterisk/releases/tag/21.4.3) (Commit hash: 489a05f269e005242027ab47d37fb6b6a1651989)
    - Or download the patched source from [Jasterisk](https://github.com/nithinshyam13/Jasterisk-21.4.3)
- Go to the source directory.
- Run `contrib/scripts/install_prereq install`, this will install all the necessary packages.
- Update the files as described in the next subsection (JAsterisk files) if working with original source.
- Next configure using `./configure --with-pjproject-bundled --with-jansson-bundled --with-libjwt-bundled`
- Run `make menuselect` and make sure all the necessary packages are selected for the build (make sure `res_stir_shaken` and `res_pjsip_stir_shaken` are selected)
- Save and exit out of menuselect.
- Run `make` to build (A copy of the built Asterisk software is provided in the file ```artifact-asterisk-21.4.3.tar.xz```).
- Run `sudo make install` to install Asterisk
- If you already have Asterisk installed, then simply replace the following files in the appropriate locations
    - res/res_stir_shaken.so        -> \<your Asterisk modules location\>/res_stir_shaken.so      
    - res/res_pjsip_stir_shaken.so  -> \<your Asterisk modules location\>/res_pjsip_stir_shaken.so
    - channels/chan_dahdi.so        -> \<your Asterisk modules location\>/chan_dahdi.so
    - NOTE: Common locations for Asterisk modules: ```/usr/lib/x86_64-linux-gnu/asterisk/modules/```, ```/usr/lib/asterisk/modules/```
    - NOTE: Don't forget to make the .so files executable

#### JAsterisk files
- The files in ```JAsterisk_files``` folder have to be copied into their locations
```
asterisk-21.4.3/include/asterisk/res_stir_shaken_oob.h - JIWF functions
asterisk-21.4.3/res/res_pjsip_stir_shaken.c            - The STIR SHAKEN module for PJSIP

asterisk-21.4.3/channels/sig_pri.c                     - The main module handling PRI signals
```

### Setting up Asterisk
- Install JAsterisk in multiple hosts to simulate a real world telco network
- Create new subscribers (extensions) for each Asterisk instance and also connect the Asterisk instances to each other using SIP or TDM trunks (this might be a daunting task for beginners, so install FreePBX on top of our Asterisk installation for easier configurations)

#### STIR/SHAKEN
- Follow this guide - [Generate Self-Signed STIR/SHAKEN Certificates](https://blog.opensips.org/2022/10/31/how-to-generate-self-signed-stir-shaken-certificates/) to generate self-signed certificates for each provider.
- Follow this guide - [Asterisk STIR-SHAKEN Deployment](https://docs.asterisk.org/Deployment/STIR-SHAKEN/) to create STIR-SHAKEN configuration file for each provider and place the file in ```/etc/asterisk/stir_shaken.conf```.
    - Private keys and root CA certificates must be stored in each provider's host and the path to the files have to be provided in ```private_key_file``` and ```ca_file```
    - Public certificates have to be uploaded to location on the internet, and the URL must be used for ```public_cert_url```
- Sample ```stir_shaken.conf``` file looks like this
```
[attestation]
global_disable = no
private_key_file = /home/asterisk/ss_vault/sp-312/sp-key-312.pem
public_cert_url = https://anywhere.com/ss/cert-312.pem
attest_level = A

[312001]
type = tn

[verification]
global_disable = no
load_system_certs = no
ca_file = /home/asterisk/ss_vault/root-ca/root-ca-cert.pem
cert_cache_dir = /home/asterisk/ss_vcache
failure_action = continue_return_reason
curl_timeout=5
max_iat_age=60
max_date_header_age=60
max_cache_entry_age = 300

[ssprfl_trunk]
type = profile
endpoint_behavior = attest
failure_action = continue_return_reason

[ssprfl_subscriber]
type = profile
endpoint_behavior = verify
failure_action = continue_return_reason
```

- Set the ```stir_shaken_profile``` for endpoints (trunks and extensions) in the ```pjsip.endpoint.conf``` file. Instructions for this should be available on the "Asterisk STIR-SHAKEN Deployment" website.
    - For trunks use ssprfl_trunk
    - For extensions use ssprfl_subscriber
    - Add this line to the extesntions config to separate them from trunks ```set_var=EP_TYPE=sub```

- Create a new JSON file ```/etc/asterisk/stir_shaken.oob.conf``` (sample below)
    - ```pri_ss_enable``` is used to enable STIR/SHAKEN operations in the TDM trunks.
    - ```pri_ss_profile_name``` is used to the set the name of the profile from the ```stir_shaken.conf``` file.
    - ```oob_proxy_url``` is used to set the URL for Jodi/OOBSS proxy
```
{
        "pri_ss_enable": true,
        "pri_ss_profile_name": "ssprfl_trunk",
        "oob_proxy_url": "http://192.168.50.99"
}
```

## Design of our modified Asterisk
- Will be explained through a scenario

### Scenario
- A call is made from 312 to 311
- 312's SIP S/S module's "incoming" function receives a call from one of its subscribers. It does nothing as its behavior is set to verify-only (ssprfl_subscriber). The call is then put on the SIP trunk to 301. Now, 312's SIP S/S module's "outgoing" function doesn't find an existing PASSPorT, so it creates a new one and attaches it to the call.
- 301's SIP S/S module's "incoming" function receives the call, retrieves the PASSPorT and puts it into channel variables. It doesn't verify because its behavior is attest-only (ssprfl_trunk). The call is then put on the T1 trunk to 302. The PRI module retrieves the PASSPorT from channel vars and uploads it to Jodi. Even though, it's behavior is set to attest, the trunk doesn't attest because it found existing an PASSPorT.
- 302's PRI module receives the call, retrieves the PASSPorT from Jodi and puts it into the channel vars. Verification is skipped. 302's SIP S/S module's "outgoing" function receives the call, retrieves the PASSPorT from the channel variables, and attaches it to the SIP INVITE. Attestation is skipped.
- 311's SIP S/S module's "incoming" function receives the call, retrieves the PASSPorT and puts it into channel variables. Verification is skipped. 311's SIP S/S module's "outgoing" function receives the call, retrieves the PASSPorT from the channel variables. It checks what type of endpoint is next; if it is of type "sub", only then verification is done. This is the first time verification is done in the whole process. Verification result is logged and call is delivered.

---
TL;DR
- Verification is done only on the trunk going out to the subscriber. Intermediary providers skip verification by checking the endpoint type they are routing the call to. ```EP_TYPE=sub``` marks a subscriber/extension.
- Attestation is done only on the trunk extending from the originating provider to the 1st intermediate provider in the chain. Intermediary providers skip attestation because they are not the owners of the source TN.
- PASSPorTs are shared between channels within a provider using *channel variables*

# Misc
- ```jasterisk.diff``` is a diff file comparing the patched asterisk 21.4.3 source vs original asterisk 21.4.3 source.