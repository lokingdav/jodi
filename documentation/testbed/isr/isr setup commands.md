## Admin
Get into privileged mode
```
en
```

Get into configuration terminal \
Need this to change any setting.
```
conf t
```

Set hostname
```
(config) hostname <new hostname>
```

Time related (run these after network setup)
```
clock timezone EST -5 0
ntp server time.google.com
```

## Network Setup
Get into configuration terminal and run the commands below

The commands below set up ethernet port 0/0/0. Replace it with he one you need.

Show interfaces
```
sh ip int
sh ip int bri
sh int 0/0/0
```

Set up an interface with VLAN tag 43
```
interface GigabitEthernet0/0/0.43
encapsulation dot1Q 10
ip address 192.168.43.10 255.255.255.0
```

Turn on interface
```
interface GigabitEthernet0/0/0
no shutdown
```

Set up route and DNS
```
ip route 0.0.0.0 0.0.0.0 192.168.43.1
ip name-server 1.1.1.1 8.8.8.8
```

Set up DHCP
```
interface gigabitethernet 0/0/0
ip address dhcp
```


## SSH
Get into configuration terminal and run the commands below


create user will full privilege
```
username <username> privilege 15 password <password>
```

set domain
```
ip domain name wspr.ncsu.edu
```

Enable local login
```
Router(config)# line vty 0 4
Router(config-line)# login local
Router(config-line)# transport input ssh
```
to check
```
show running-config | section line vty
show running-config | include username
```

create RSA key pair
```
crypto key generate rsa
```

# Telco setup
look into the latest configs configs isr/latest_configs/isrX.txt for exact configs.

Get into configuration terminal and run the commands below

The commands below set up ethernet port 0/1. Replace it with he one you need.

## T1 setup

the following config shows t1 set up for 1 port
```
card type t1 0 1
isdn switch-type primary-ni
!
controller T1 0/1/0
 framing esf
 clock source network
 linecode b8zs
 cablelength short 110
 pri-group timeslots 1-24
!
interface Serial0/1/0:23 ! we have setup 24 channel. the last one - 23 is the control channel
 encapsulation hdlc
 isdn switch-type primary-ni
 isdn protocol-emulate network
 isdn incoming-voice voice
 no cdp enable
```

## VoIP Setup
enable voip processing
```
voice service voip
 ip address trusted list
  ipv4 192.168.43.0 255.255.255.0
 allow-connections h323 to sip
 allow-connections sip to h323
 allow-connections sip to sip
 sip
  bind control source-interface GigabitEthernet0/0/0.43
  bind media source-interface GigabitEthernet0/0/0.43
!
voice class codec 1
 codec preference 1 g711ulaw
 codec preference 2 g711alaw
```

## Configure Dial-Peers

Outbound Dial-Peer
```
ISR(config)# dial-peer voice 1 voip
ISR(config-dial-peer)# destination-pattern 302...   ! Matches the dialed number (e.g., starts with 9)
ISR(config-dial-peer)# session protocol sipv2
ISR(config-dial-peer)# session target ipv4:192.168.43.102  ! Replace with IP address or domain
ISR(config-dial-peer)# dtmf-relay rtp-nte         ! DTMF relay method (adjust as needed)
ISR(config-dial-peer)# codec g711ulaw             ! Select codec
ISR(config-dial-peer)# no vad                     ! Disable Voice Activity Detection
ISR(config-dial-peer)# exit
```

Inbound Dial-Peer
```
ISR(config)# dial-peer voice 2 voip
ISR(config-dial-peer)# incoming called-number .   ! Matches all incoming calls
ISR(config-dial-peer)# session protocol sipv2
ISR(config-dial-peer)# dtmf-relay rtp-nte
ISR(config-dial-peer)# exit
```

Dial peer summary
```
show dial-peer voice summary
```

Example config
```
dial-peer voice 1001 pots
 destination-pattern 3[(01)(12)]...
 port 0/1/0:23
 forward-digits all
!
dial-peer voice 2012 voip
 destination-pattern 3[(02)(11)]...
 session protocol sipv2
 session target ipv4:192.168.43.142
 voice-class codec 1  
 voice-class sip bind control source-interface GigabitEthernet0/0/0.43
 voice-class sip bind media source-interface GigabitEthernet0/0/0.43
 dtmf-relay rtp-nte sip-info
```

<!-- ### Configure SIP-UA settings
ISR(config)# sip-ua
ISR(config-sip-ua)# registrar ipv4:192.168.43.102 expires 3600
ISR(config-sip-ua)# sip-server ipv4:192.168.43.102
ISR(config-sip-ua)# exit -->

# Debugging calls
```
debug isdn q931
debug isdn q921
debug voip ccapi inout
debug ccsip messages

term len 0
logging buffered 2000000
sh log

clear log
undebug all
```


# Status checks
```
sh isdn status
sh call activ voice bri
```

# Other cmds
```
dir
cd <>
more <filename>
copy <filename> running-config

do sh run | s dial
```