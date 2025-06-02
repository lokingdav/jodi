# FreePBX Routes and Extension setup

## Extensions
- Extensions are the end users of the PBX
- Configure users for the PBX by adding a new extension at Connectivity->Extensions
- For this project, only chan_pjsip extensions are used

Steps to set up an extension
```
1. Go to the chan_pjsip extension creation window
2. Enter the following fields: User Extension, Display Name, Secret, Username (check Use Custom Username), Password
3. Use the username and secret to login in your SIP client (Zoiper for example)
```

### Extensions Already Set Up
- Each FPBX is set up with an extension as follows
    - Username = \<VMID\>001
    - Password = \<Username\>s

## Trunks
- Trunks are used to establish a connection between two nodes in a network
- Configure trunks for the PBX by adding a new extension at Connectivity->Trunks
- 2 types of trunks can be created - DAHDi (ISDN) and SIP (chan_pjsip)

DAHDi trunk
```
1. Go to the DAHDI trunk creation window
2. In general, enter the trunk name and for DAHDI Trunks - select the group set for the T1 port in Connectivity->DAHDI Config
```

PJSIP Trunk
```
1. Go to the chan_pjsip trunk creation window
2. In general, enter the trunk name
3. In pjsip settings, set the IP address for the SIP Server. Change authentication and registration as necessary. Leave default if connecting to another FPBX instance. Set Auth and Reg both to None if connecting to ISR
```

## Outbound Routes
- This option is used to handle routing of outgoing calls based on the destination number
- Found in Connectivity->Outbound Routes

Steps to set up
```
1. Go to "Add Route" window
2. In Route Settings, enter the Route name and select the trunk (Trunk Sequence for Matched Routes) to use.
3. In Dial Patters, enter the pattern to match in "Match pattern". Help is available on the same page for creating match patterns.
```

## Inbound routes
- This option is used to handle routing of incoming calls based on the caller and callee number
- Found in Connectivity->Inbound Routes
- Pattern matching help - [link](https://sangomakb.atlassian.net/wiki/spaces/Phones/pages/19562848/Dial+Patterns)

Steps to set up
```
1. Go to "Add Incoming Route" window
2. In General, enter the Route description, DID Number (callee), CallerID Number (caller), and select the destination. The destination could be a trunk also (Select "Trunks" in the drop down). The phone numbers can be pattern matched (make sure to add an underscore "_" at the beginning of the string if using pattern matching).
```

---

NOTE: Look at the network diagram for understanding the trunks and inbound/outbound routes.