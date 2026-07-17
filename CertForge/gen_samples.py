#!/usr/bin/env python3
"""Generate script_samples.js — 100 full Cisco IOS config examples
spanning CCNA -> CCNP -> CCIE. Emits window.SCRIPT_SAMPLES = [...]."""
import json

S = []  # each: {id,title,level,cat,purpose,config(list of lines)}

def add(title, level, cat, purpose, cfg):
    S.append({"id": len(S)+1, "title": title, "level": level,
              "cat": cat, "purpose": purpose, "config": cfg})

# helper prologue
def L3(lines): return lines

# ============================ CCNA (1-40) ============================
add("Set hostname & banners", "CCNA", "Device Basics",
    "Name the device and set a login banner.",
    ["enable","configure terminal","hostname R1",
     "banner motd # Authorized access only #","end","show running-config"])

add("Console & VTY passwords", "CCNA", "Device Basics",
    "Secure console and remote VTY lines with passwords.",
    ["enable","configure terminal","line console 0"," password cisco"," login","exit",
     "line vty 0 4"," password cisco"," login"," transport input ssh","end"])

add("Enable secret vs enable password", "CCNA", "Device Basics",
    "Protect privileged EXEC mode with an encrypted secret.",
    ["enable","configure terminal","enable secret Str0ngP@ss",
     "service password-encryption","end","show running-config"])

add("Create a local user for SSH", "CCNA", "Device Basics",
    "Local username with privilege level for SSH login.",
    ["enable","configure terminal","username admin privilege 15 secret Adm1nP@ss",
     "line vty 0 4"," login local"," transport input ssh","end"])

add("Enable SSH v2", "CCNA", "Management Access",
    "Generate RSA keys and enable SSH version 2.",
    ["enable","configure terminal","ip domain-name lab.local",
     "crypto key generate rsa modulus 2048","ip ssh version 2",
     "line vty 0 4"," transport input ssh"," login local","end"])

add("Assign an interface IP", "CCNA", "Interfaces",
    "Configure an IPv4 address and bring the interface up.",
    ["enable","configure terminal","interface gi0/0",
     " ip address 192.168.1.1 255.255.255.0"," description LAN"," no shutdown","end",
     "show ip interface brief"])

add("Loopback interface", "CCNA", "Interfaces",
    "Create a stable loopback used as a router-id / test address.",
    ["enable","configure terminal","interface Loopback0",
     " ip address 1.1.1.1 255.255.255.255","end","show ip interface brief"])

add("Description & speed/duplex", "CCNA", "Interfaces",
    "Document and hard-set interface parameters.",
    ["enable","configure terminal","interface gi0/1",
     " description ** Server Farm **"," speed 1000"," duplex full"," no shutdown","end"])

add("Create VLANs with names", "CCNA", "Switching",
    "Define VLANs 10/20/30 and name them.",
    ["enable","configure terminal","vlan 10"," name SALES","exit",
     "vlan 20"," name ENG","exit","vlan 30"," name VOICE","end","show vlan brief"])

add("Access port assignment", "CCNA", "Switching",
    "Place an access port into VLAN 10.",
    ["enable","configure terminal","interface gi0/2",
     " switchport mode access"," switchport access vlan 10","end","show vlan brief"])

add("Voice + data on one port", "CCNA", "Switching",
    "Data VLAN plus a voice VLAN on an access port.",
    ["enable","configure terminal","interface gi0/3",
     " switchport mode access"," switchport access vlan 10"," switchport voice vlan 30",
     " spanning-tree portfast","end"])

add("802.1Q trunk", "CCNA", "Switching",
    "Configure a dot1q trunk carrying selected VLANs.",
    ["enable","configure terminal","interface gi0/24",
     " switchport trunk encapsulation dot1q"," switchport mode trunk",
     " switchport trunk allowed vlan 10,20,30","end","show interfaces trunk"])

add("Native VLAN change", "CCNA", "Switching",
    "Move the trunk native VLAN off VLAN 1.",
    ["enable","configure terminal","interface gi0/24",
     " switchport mode trunk"," switchport trunk native vlan 99","end"])

add("PortFast + BPDU Guard", "CCNA", "Switching",
    "Speed up access ports and protect the edge.",
    ["enable","configure terminal","interface range gi0/2 - 10",
     " switchport mode access"," spanning-tree portfast"," spanning-tree bpduguard enable","end"])

add("Set STP root bridge", "CCNA", "Switching",
    "Force this switch to be root for a VLAN.",
    ["enable","configure terminal","spanning-tree vlan 10 root primary",
     "spanning-tree vlan 10 priority 4096","end","show spanning-tree vlan 10"])

add("Rapid-PVST+ mode", "CCNA", "Switching",
    "Switch spanning-tree mode to rapid-pvst.",
    ["enable","configure terminal","spanning-tree mode rapid-pvst","end","show spanning-tree summary"])

add("EtherChannel (LACP)", "CCNA", "Switching",
    "Bundle two links into a Port-channel with LACP.",
    ["enable","configure terminal","interface range gi0/1 - 2",
     " channel-group 1 mode active","exit","interface port-channel 1",
     " switchport mode trunk","end","show etherchannel summary"])

add("SVI for inter-VLAN (router-on-a-stick alt)", "CCNA", "Switching",
    "Layer-3 switch SVI providing a VLAN gateway.",
    ["enable","configure terminal","ip routing","interface vlan 10",
     " ip address 10.10.10.1 255.255.255.0"," no shutdown","end"])

add("Router-on-a-stick subinterfaces", "CCNA", "Routing",
    "Sub-interfaces provide inter-VLAN routing on a router.",
    ["enable","configure terminal","interface gi0/0.10",
     " encapsulation dot1Q 10"," ip address 10.10.10.1 255.255.255.0","exit",
     "interface gi0/0.20"," encapsulation dot1Q 20"," ip address 10.20.20.1 255.255.255.0","end"])

add("Default static route", "CCNA", "Routing",
    "Point unknown traffic at the next hop.",
    ["enable","configure terminal","ip route 0.0.0.0 0.0.0.0 203.0.113.1","end","show ip route"])

add("Specific static route", "CCNA", "Routing",
    "Reach a remote subnet via a next hop.",
    ["enable","configure terminal","ip route 192.168.50.0 255.255.255.0 10.0.0.2","end","show ip route static"])

add("Floating static (backup)", "CCNA", "Routing",
    "Backup route with a higher administrative distance.",
    ["enable","configure terminal","ip route 192.168.50.0 255.255.255.0 10.0.0.2",
     "ip route 192.168.50.0 255.255.255.0 10.0.1.2 200","end"])

add("Single-area OSPF", "CCNA", "Routing",
    "Advertise networks into OSPF area 0.",
    ["enable","configure terminal","router ospf 1"," router-id 1.1.1.1",
     " network 10.0.0.0 0.0.0.255 area 0"," network 192.168.1.0 0.0.0.255 area 0","end","show ip ospf neighbor"])

add("OSPF passive interface", "CCNA", "Routing",
    "Stop OSPF hellos on a LAN edge.",
    ["enable","configure terminal","router ospf 1",
     " passive-interface gi0/1"," network 10.0.0.0 0.0.0.255 area 0","end"])

add("OSPF default-route injection", "CCNA", "Routing",
    "Advertise a default route into OSPF.",
    ["enable","configure terminal","ip route 0.0.0.0 0.0.0.0 203.0.113.1",
     "router ospf 1"," default-information originate","end"])

add("Basic EIGRP", "CCNA", "Routing",
    "Enable EIGRP AS 100 on connected networks.",
    ["enable","configure terminal","router eigrp 100",
     " network 10.0.0.0 0.0.0.255"," network 192.168.1.0 0.0.0.255"," no auto-summary","end","show ip eigrp neighbors"])

add("RIPv2", "CCNA", "Routing",
    "Classless RIP with no auto-summary.",
    ["enable","configure terminal","router rip"," version 2",
     " network 10.0.0.0"," no auto-summary","end","show ip protocols"])

add("DHCP server pool", "CCNA", "Services",
    "Hand out addresses from an excluded range.",
    ["enable","configure terminal","ip dhcp excluded-address 10.10.10.1 10.10.10.10",
     "ip dhcp pool LAN"," network 10.10.10.0 255.255.255.0"," default-router 10.10.10.1",
     " dns-server 8.8.8.8","end"])

add("DHCP relay (helper-address)", "CCNA", "Services",
    "Forward DHCP requests to a central server.",
    ["enable","configure terminal","interface gi0/1",
     " ip helper-address 10.0.0.53","end"])

add("Static NAT", "CCNA", "NAT",
    "Map an inside host to a public address.",
    ["enable","configure terminal","interface gi0/0"," ip nat inside","exit",
     "interface gi0/1"," ip nat outside","exit",
     "ip nat inside source static 10.10.10.5 203.0.113.5","end","show ip nat translations"])

add("PAT (NAT overload)", "CCNA", "NAT",
    "Many inside hosts share one public IP.",
    ["enable","configure terminal","access-list 1 permit 10.10.10.0 0.0.0.255",
     "interface gi0/0"," ip nat inside","exit","interface gi0/1"," ip nat outside","exit",
     "ip nat inside source list 1 interface gi0/1 overload","end"])

add("Standard numbered ACL", "CCNA", "Security",
    "Permit one subnet, deny the rest, apply inbound.",
    ["enable","configure terminal","access-list 10 permit 10.10.10.0 0.0.0.255",
     "interface gi0/1"," ip access-group 10 in","end","show access-lists"])

add("Extended named ACL", "CCNA", "Security",
    "Allow web + SSH to a server, deny other IP.",
    ["enable","configure terminal","ip access-list extended WEB",
     " permit tcp any host 10.10.10.80 eq 80"," permit tcp any host 10.10.10.80 eq 22",
     " deny ip any any","end","show ip access-lists WEB"])

add("Port security", "CCNA", "Security",
    "Limit MAC addresses on an access port.",
    ["enable","configure terminal","interface gi0/5"," switchport mode access",
     " switchport port-security"," switchport port-security maximum 2",
     " switchport port-security violation restrict"," switchport port-security mac-address sticky","end"])

add("NTP client", "CCNA", "Services",
    "Sync the clock to an NTP server.",
    ["enable","configure terminal","ntp server 129.6.15.28","end","show ntp associations"])

add("CDP/LLDP toggle", "CCNA", "Services",
    "Enable LLDP globally for discovery.",
    ["enable","configure terminal","lldp run","cdp run","end","show cdp neighbors"])

add("Save & verify config", "CCNA", "Device Basics",
    "Copy running to startup and verify.",
    ["enable","configure terminal","hostname EDGE","end",
     "copy running-config startup-config","show running-config"])

add("IPv6 addressing", "CCNA", "IPv6",
    "Enable IPv6 routing and assign a global address.",
    ["enable","configure terminal","ipv6 unicast-routing","interface gi0/0",
     " ipv6 address 2001:db8:acad:1::1/64"," no shutdown","end","show ipv6 interface brief"])

add("IPv6 static + default route", "CCNA", "IPv6",
    "Static IPv6 route plus a default.",
    ["enable","configure terminal","ipv6 unicast-routing",
     "ipv6 route 2001:db8:acad:2::/64 2001:db8:acad:1::2",
     "ipv6 route ::/0 2001:db8:acad:1::2","end","show ipv6 route"])

# ============================ CCNP (41-75) ============================
add("OSPF multi-area", "CCNP", "OSPF",
    "Split networks across area 0 and area 1.",
    ["enable","configure terminal","router ospf 1"," router-id 2.2.2.2",
     " network 10.1.0.0 0.0.255.255 area 0"," network 10.2.0.0 0.0.255.255 area 1","end","show ip ospf"])

add("OSPF stub area", "CCNP", "OSPF",
    "Reduce LSAs by making an area stub.",
    ["enable","configure terminal","router ospf 1",
     " area 1 stub"," network 10.2.0.0 0.0.255.255 area 1","end"])

add("OSPF totally stubby area", "CCNP", "OSPF",
    "ABR blocks inter-area + external LSAs.",
    ["enable","configure terminal","router ospf 1",
     " area 1 stub no-summary","end"])

add("OSPF NSSA", "CCNP", "OSPF",
    "Allow external routes into a stub-like area.",
    ["enable","configure terminal","router ospf 1"," area 2 nssa","end"])

add("OSPF cost / reference-bandwidth", "CCNP", "OSPF",
    "Tune path selection with cost and ref-bw.",
    ["enable","configure terminal","router ospf 1"," auto-cost reference-bandwidth 10000","exit",
     "interface gi0/0"," ip ospf cost 5","end"])

add("OSPF authentication (MD5)", "CCNP", "OSPF",
    "Authenticate OSPF adjacencies per-interface.",
    ["enable","configure terminal","interface gi0/0",
     " ip ospf authentication message-digest"," ip ospf message-digest-key 1 md5 S3cret","end"])

add("OSPF virtual-link", "CCNP", "OSPF",
    "Repair a discontiguous area 0 via a transit area.",
    ["enable","configure terminal","router ospf 1"," area 1 virtual-link 3.3.3.3","end"])

add("OSPFv3 for IPv6", "CCNP", "OSPF",
    "Enable OSPFv3 on interfaces for IPv6.",
    ["enable","configure terminal","ipv6 unicast-routing","ipv6 router ospf 1"," router-id 4.4.4.4","exit",
     "interface gi0/0"," ipv6 ospf 1 area 0","end"])

add("EIGRP named mode", "CCNP", "EIGRP",
    "Modern named EIGRP configuration.",
    ["enable","configure terminal","router eigrp CORP"," address-family ipv4 unicast autonomous-system 100",
     "  network 10.0.0.0 0.0.0.255","  af-interface gi0/1","   passive-interface","  exit-af-interface","end"])

add("EIGRP summary route", "CCNP", "EIGRP",
    "Advertise a manual summary out an interface.",
    ["enable","configure terminal","interface gi0/0",
     " ip summary-address eigrp 100 10.0.0.0 255.0.0.0","end"])

add("EIGRP unequal-cost (variance)", "CCNP", "EIGRP",
    "Load-balance across unequal paths.",
    ["enable","configure terminal","router eigrp 100"," variance 2","end"])

add("EIGRP authentication", "CCNP", "EIGRP",
    "Key-chain based MD5 authentication.",
    ["enable","configure terminal","key chain EK"," key 1","  key-string EigrpKey","exit","exit",
     "interface gi0/0"," ip authentication mode eigrp 100 md5"," ip authentication key-chain eigrp 100 EK","end"])

add("iBGP peering", "CCNP", "BGP",
    "Internal BGP session using loopbacks.",
    ["enable","configure terminal","router bgp 65001"," bgp router-id 1.1.1.1",
     " neighbor 2.2.2.2 remote-as 65001"," neighbor 2.2.2.2 update-source Loopback0","end","show ip bgp summary"])

add("eBGP peering + network", "CCNP", "BGP",
    "External BGP and originate a prefix.",
    ["enable","configure terminal","router bgp 65001",
     " neighbor 203.0.113.2 remote-as 65002"," network 10.0.0.0 mask 255.255.255.0","end","show ip bgp"])

add("BGP eBGP-multihop", "CCNP", "BGP",
    "Peer eBGP across loopbacks (multihop).",
    ["enable","configure terminal","router bgp 65001",
     " neighbor 4.4.4.4 remote-as 65002"," neighbor 4.4.4.4 ebgp-multihop 2",
     " neighbor 4.4.4.4 update-source Loopback0","end"])

add("BGP route-reflector", "CCNP", "BGP",
    "Scale iBGP with a route reflector client.",
    ["enable","configure terminal","router bgp 65001",
     " neighbor 2.2.2.2 remote-as 65001"," neighbor 2.2.2.2 route-reflector-client","end"])

add("BGP local-preference (route-map)", "CCNP", "BGP",
    "Prefer one exit with local-preference.",
    ["enable","configure terminal","route-map SET_LP permit 10"," set local-preference 200","exit",
     "router bgp 65001"," neighbor 203.0.113.2 route-map SET_LP in","end"])

add("BGP AS-path prepend", "CCNP", "BGP",
    "Make a path less preferred to neighbors.",
    ["enable","configure terminal","route-map PREPEND permit 10"," set as-path prepend 65001 65001","exit",
     "router bgp 65001"," neighbor 203.0.113.2 route-map PREPEND out","end"])

add("Redistribute static into OSPF", "CCNP", "Redistribution",
    "Inject static routes as external OSPF.",
    ["enable","configure terminal","router ospf 1",
     " redistribute static subnets metric 20","end"])

add("Redistribute OSPF <-> EIGRP", "CCNP", "Redistribution",
    "Mutual redistribution with seed metrics.",
    ["enable","configure terminal","router eigrp 100"," redistribute ospf 1 metric 100000 100 255 1 1500","exit",
     "router ospf 1"," redistribute eigrp 100 subnets","end"])

add("Route-map filter with prefix-list", "CCNP", "Filtering",
    "Match a prefix-list and deny redistribution.",
    ["enable","configure terminal","ip prefix-list P1 seq 5 permit 10.0.0.0/8 le 24",
     "route-map RM deny 10"," match ip address prefix-list P1","route-map RM permit 20","end"])

add("HSRP gateway redundancy", "CCNP", "FHRP",
    "Active/standby virtual gateway with preempt.",
    ["enable","configure terminal","interface vlan 10"," ip address 10.10.10.2 255.255.255.0",
     " standby 1 ip 10.10.10.1"," standby 1 priority 110"," standby 1 preempt","end","show standby brief"])

add("VRRP gateway redundancy", "CCNP", "FHRP",
    "Open-standard first-hop redundancy.",
    ["enable","configure terminal","interface vlan 10"," ip address 10.10.10.2 255.255.255.0",
     " vrrp 1 ip 10.10.10.1"," vrrp 1 priority 120","end"])

add("GLBP load balancing", "CCNP", "FHRP",
    "Load-balance across multiple gateways.",
    ["enable","configure terminal","interface vlan 10"," ip address 10.10.10.2 255.255.255.0",
     " glbp 1 ip 10.10.10.1"," glbp 1 priority 120"," glbp 1 preempt","end"])

add("Layer-3 EtherChannel", "CCNP", "Switching",
    "Routed Port-channel between switches.",
    ["enable","configure terminal","interface range gi0/1 - 2"," no switchport",
     " channel-group 1 mode active","exit","interface port-channel 1",
     " ip address 10.0.0.1 255.255.255.252","end"])

add("SPAN (port mirroring)", "CCNP", "Monitoring",
    "Mirror traffic to an analyzer port.",
    ["enable","configure terminal","monitor session 1 source interface gi0/1",
     "monitor session 1 destination interface gi0/24","end"])

add("DHCP snooping", "CCNP", "Security",
    "Trust the uplink, protect access ports.",
    ["enable","configure terminal","ip dhcp snooping","ip dhcp snooping vlan 10",
     "interface gi0/24"," ip dhcp snooping trust","end"])

add("Dynamic ARP Inspection", "CCNP", "Security",
    "Validate ARP against the snooping DB.",
    ["enable","configure terminal","ip arp inspection vlan 10",
     "interface gi0/24"," ip arp inspection trust","end"])

add("Control-plane SSH ACL", "CCNP", "Security",
    "Restrict VTY access to a mgmt subnet.",
    ["enable","configure terminal","access-list 20 permit 10.0.0.0 0.0.0.255",
     "line vty 0 4"," access-class 20 in"," transport input ssh","end"])

add("QoS classify & mark", "CCNP", "QoS",
    "Class-map + policy-map marking DSCP.",
    ["enable","configure terminal","class-map match-any VOICE"," match protocol rtp","exit",
     "policy-map QOS"," class VOICE","  set dscp ef","exit","interface gi0/0"," service-policy output QOS","end"])

add("SNMPv2 read-only", "CCNP", "Management",
    "Expose read-only SNMP to an NMS.",
    ["enable","configure terminal","snmp-server community R3ad ro 20",
     "snmp-server location DC1","snmp-server contact netops","end"])

add("Syslog to server", "CCNP", "Management",
    "Send logs to a remote collector.",
    ["enable","configure terminal","logging host 10.0.0.50","logging trap informational",
     "service timestamps log datetime msec","end"])

add("NTP authenticated + master", "CCNP", "Management",
    "Authenticated NTP with a local master.",
    ["enable","configure terminal","ntp authenticate","ntp authentication-key 1 md5 NtpKey",
     "ntp trusted-key 1","ntp master 3","end"])

add("IP SLA + track", "CCNP", "HA",
    "Probe a target and track reachability.",
    ["enable","configure terminal","ip sla 1"," icmp-echo 8.8.8.8"," frequency 5","exit",
     "ip sla schedule 1 life forever start-time now","track 1 ip sla 1 reachability","end"])

# ============================ CCIE (76-100) ============================
add("MPLS L3VPN: VRF definition", "CCIE", "MPLS L3VPN",
    "Define a customer VRF with RD/RT.",
    ["enable","configure terminal","vrf definition CUST_A"," rd 65000:1",
     " address-family ipv4","  route-target export 65000:1","  route-target import 65000:1","end","show vrf"])

add("MPLS L3VPN: bind interface to VRF", "CCIE", "MPLS L3VPN",
    "Assign a PE interface to the customer VRF.",
    ["enable","configure terminal","interface gi0/1"," vrf forwarding CUST_A",
     " ip address 10.1.1.1 255.255.255.252"," no shutdown","end"])

add("MPLS core: enable LDP", "CCIE", "MPLS",
    "Turn on MPLS + LDP on core links.",
    ["enable","configure terminal","mpls label protocol ldp","interface gi0/0",
     " mpls ip","end","show mpls interfaces"])

add("MP-BGP VPNv4 session", "CCIE", "MPLS L3VPN",
    "PE-PE VPNv4 address-family peering.",
    ["enable","configure terminal","router bgp 65000",
     " neighbor 2.2.2.2 remote-as 65000"," neighbor 2.2.2.2 update-source Loopback0",
     " address-family vpnv4","  neighbor 2.2.2.2 activate","  neighbor 2.2.2.2 send-community extended","end"])

add("PE-CE OSPF in a VRF", "CCIE", "MPLS L3VPN",
    "Run OSPF per-VRF toward the customer.",
    ["enable","configure terminal","router ospf 10 vrf CUST_A"," router-id 10.1.1.1",
     " network 10.1.1.0 0.0.0.3 area 0","end"])

add("Redistribute VRF BGP<->OSPF", "CCIE", "MPLS L3VPN",
    "Glue PE-CE OSPF into MP-BGP.",
    ["enable","configure terminal","router bgp 65000"," address-family ipv4 vrf CUST_A",
     "  redistribute ospf 10","exit","router ospf 10 vrf CUST_A",
     " redistribute bgp 65000 subnets","end"])

add("DMVPN hub (mGRE + NHRP)", "CCIE", "DMVPN",
    "Phase-3 hub tunnel with NHRP.",
    ["enable","configure terminal","interface Tunnel0"," ip address 172.16.0.1 255.255.255.0",
     " tunnel source gi0/0"," tunnel mode gre multipoint"," ip nhrp network-id 1",
     " ip nhrp map multicast dynamic","end"])

add("DMVPN spoke", "CCIE", "DMVPN",
    "Spoke registering to the NHRP hub.",
    ["enable","configure terminal","interface Tunnel0"," ip address 172.16.0.2 255.255.255.0",
     " tunnel source gi0/0"," tunnel mode gre multipoint"," ip nhrp network-id 1",
     " ip nhrp nhs 172.16.0.1"," ip nhrp map 172.16.0.1 203.0.113.1","end"])

add("IPsec: IKEv2 proposal", "CCIE", "VPN/IPsec",
    "Define an IKEv2 proposal and policy.",
    ["enable","configure terminal","crypto ikev2 proposal PROP"," encryption aes-cbc-256",
     " integrity sha256"," group 14","exit","crypto ikev2 policy POL"," proposal PROP","end"])

add("IPsec: IKEv2 keyring + profile", "CCIE", "VPN/IPsec",
    "Pre-shared key and IKEv2 profile.",
    ["enable","configure terminal","crypto ikev2 keyring KR"," peer PEER",
     "  address 203.0.113.2","  pre-shared-key L0ngKey","exit","exit",
     "crypto ikev2 profile PROF"," match identity remote address 203.0.113.2 255.255.255.255",
     " authentication remote pre-share"," authentication local pre-share"," keyring local KR","end"])

add("IPsec: transform-set + tunnel protection", "CCIE", "VPN/IPsec",
    "IPsec profile applied to a GRE tunnel.",
    ["enable","configure terminal","crypto ipsec transform-set TS esp-aes 256 esp-sha-hmac",
     " mode transport","exit","crypto ipsec profile IPSEC"," set transform-set TS","exit",
     "interface Tunnel0"," tunnel protection ipsec profile IPSEC","end"])

add("BGP confederations", "CCIE", "BGP Advanced",
    "Split an AS into sub-ASes.",
    ["enable","configure terminal","router bgp 65001"," bgp confederation identifier 100",
     " bgp confederation peers 65002"," neighbor 10.0.0.2 remote-as 65002","end"])

add("BGP communities + community-list", "CCIE", "BGP Advanced",
    "Tag routes and match on community.",
    ["enable","configure terminal","ip community-list 1 permit 100:200",
     "route-map SETCOMM permit 10"," set community 100:200","exit",
     "router bgp 65001"," neighbor 203.0.113.2 route-map SETCOMM out",
     " neighbor 203.0.113.2 send-community","end"])

add("BGP peer-group + template", "CCIE", "BGP Advanced",
    "Reuse settings across many peers.",
    ["enable","configure terminal","router bgp 65001",
     " neighbor RRC peer-group"," neighbor RRC remote-as 65001",
     " neighbor RRC route-reflector-client"," neighbor 2.2.2.2 peer-group RRC","end"])

add("BGP conditional advertisement", "CCIE", "BGP Advanced",
    "Advertise a prefix only if another is missing.",
    ["enable","configure terminal","router bgp 65001",
     " neighbor 203.0.113.2 advertise-map ADV non-exist-map NEM","end"])

add("PfR / performance routing stub", "CCIE", "WAN",
    "Master controller definition (concept).",
    ["enable","configure terminal","pfr master"," border 10.0.0.2 key-chain PK",
     "  interface gi0/0 external","  interface gi0/1 internal","end"])

add("QoS hierarchical shaping", "CCIE", "QoS",
    "Parent shaper with a child queueing policy.",
    ["enable","configure terminal","policy-map CHILD"," class VOICE","  priority percent 30","exit",
     "policy-map PARENT"," class class-default","  shape average 10000000","  service-policy CHILD","end"])

add("QoS WRED", "CCIE", "QoS",
    "Congestion avoidance with WRED.",
    ["enable","configure terminal","policy-map WRED_P"," class class-default",
     "  bandwidth percent 75","  random-detect dscp-based","end"])

add("Multicast: PIM sparse-mode", "CCIE", "Multicast",
    "Enable multicast routing + PIM-SM.",
    ["enable","configure terminal","ip multicast-routing","interface gi0/0",
     " ip pim sparse-mode","end","show ip pim interface"])

add("Multicast: static RP", "CCIE", "Multicast",
    "Define a static rendezvous point.",
    ["enable","configure terminal","ip pim rp-address 1.1.1.1","end","show ip pim rp"])

add("Multicast: Auto-RP", "CCIE", "Multicast",
    "Candidate RP + mapping agent.",
    ["enable","configure terminal","ip pim send-rp-announce Loopback0 scope 16",
     "ip pim send-rp-discovery Loopback0 scope 16","end"])

add("IS-IS backbone", "CCIE", "IS-IS",
    "Level-2 IS-IS with a NET address.",
    ["enable","configure terminal","router isis"," net 49.0001.1111.1111.1111.00",
     " is-type level-2-only","exit","interface gi0/0"," ip router isis","end","show isis neighbors"])

add("IS-IS metric-style wide", "CCIE", "IS-IS",
    "Use wide metrics for scalability.",
    ["enable","configure terminal","router isis"," metric-style wide","end"])

add("VXLAN/EVPN NVE (concept)", "CCIE", "Data Center",
    "NVE interface for a VXLAN VNI.",
    ["enable","configure terminal","interface nve1"," source-interface Loopback0",
     " member vni 10010 mcast-group 239.1.1.1","end"])

add("Zone-Based Firewall", "CCIE", "Security",
    "Zones, class, policy and zone-pair.",
    ["enable","configure terminal","zone security INSIDE","zone security OUTSIDE",
     "class-map type inspect match-any CM"," match protocol tcp","exit",
     "policy-map type inspect PM"," class type inspect CM","  inspect","exit",
     "zone-pair security IN_OUT source INSIDE destination OUTSIDE"," service-policy type inspect PM","end"])

add("IPv6 EIGRP (EIGRPv6)", "CCNP", "EIGRP",
    "Enable EIGRP for IPv6 on interfaces.",
    ["enable","configure terminal","ipv6 unicast-routing","ipv6 router eigrp 100"," no shutdown","exit",
     "interface gi0/0"," ipv6 eigrp 100","end"])

add("Segment Routing MPLS (concept)", "CCIE", "MPLS",
    "Enable SR-MPLS and a prefix-SID on a loopback.",
    ["enable","configure terminal","segment-routing mpls"," connected-prefix-sid-map",
     "  address-family ipv4","   1.1.1.1/32 index 100 range 1","end"])

# ============================ Explanations ============================
# id -> "why it works" (mechanics) + common failure mode where useful.
EXPLAIN = {
1:"WHY IT WORKS: 'hostname' renames the device so the prompt and CDP/LLDP show a friendly name; the MOTD banner is displayed to anyone connecting, which is a legal/deterrence requirement in most orgs. The '#' characters are delimiters, not part of the message. WHY A VARIANT FAILS: if you reuse a character inside the banner text that matches the delimiter, IOS ends the banner early and treats the rest as commands.",
2:"WHY IT WORKS: 'line console 0' and 'line vty 0 4' select the physical console and the 5 virtual (Telnet/SSH) sessions; 'password' sets the secret and 'login' tells IOS to actually prompt for it. WHY A VARIANT FAILS: setting a password but omitting 'login' means the line is never challenged; setting 'login' with no password locks you out with '% Login disabled on line'.",
3:"WHY IT WORKS: 'enable secret' stores a hashed (irreversible) password for privileged EXEC, and always overrides the weaker, reversible 'enable password'. 'service password-encryption' obfuscates other plaintext passwords in the config. WHY IT MATTERS: 'enable password' uses trivially reversible Type-7 encoding, so 'enable secret' is the secure choice.",
4:"WHY IT WORKS: a local username with 'privilege 15' plus 'login local' on the VTY lines authenticates SSH users against the device's own database and drops them straight into privileged EXEC. WHY A VARIANT FAILS: 'login local' with no username defined means nobody can log in.",
5:"WHY IT WORKS: SSH needs three things - a hostname (already set), a domain name (to build the RSA key label), and an RSA key pair. Generating a >=768-bit modulus and setting 'ip ssh version 2' enables secure remote access. WHY A VARIANT FAILS: skipping 'ip domain-name' makes 'crypto key generate rsa' refuse with '% Please define a domain-name first'.",
6:"WHY IT WORKS: the IP/mask defines the subnet and 'no shutdown' administratively enables the port; routed interfaces are shut by default on routers. WHY A VARIANT FAILS: forgetting 'no shutdown' leaves the line 'administratively down' and it never forwards traffic.",
7:"WHY IT WORKS: a loopback is a virtual interface that is always up as long as the device is up, making it ideal as an OSPF/BGP router-id or a stable management target. The /32 mask means it represents exactly one host address.",
8:"WHY IT WORKS: 'description' is cosmetic documentation; 'speed' and 'duplex' hard-set the link parameters. WHY A VARIANT FAILS: hard-coding one side but leaving the other on 'auto' causes a duplex mismatch - late collisions and terrible throughput.",
9:"WHY IT WORKS: VLANs are created in the VLAN database; naming is optional but aids operations. Ports later reference these VLAN IDs. WHY A VARIANT FAILS: assigning a port to a VLAN that was never created will auto-create an inactive VLAN in some IOS versions, so the port stays down.",
10:"WHY IT WORKS: 'switchport mode access' forces the port to a single untagged VLAN and 'switchport access vlan 10' places it there. WHY A VARIANT FAILS: leaving the port in default 'dynamic auto' can cause it to negotiate a trunk unexpectedly.",
11:"WHY IT WORKS: an access port carries one data VLAN untagged plus a voice VLAN tagged for IP phones; 'portfast' skips STP listening/learning so phones/PCs get link immediately. WHY IT MATTERS: portfast should only be on edge/access ports, never on trunks to other switches.",
12:"WHY IT WORKS: 'switchport trunk encapsulation dot1q' selects 802.1Q tagging, 'mode trunk' makes it a trunk, and 'allowed vlan' prunes it to only the needed VLANs. WHY A VARIANT FAILS: mismatched allowed-VLAN lists on the two ends silently black-hole those VLANs.",
13:"WHY IT WORKS: moving the native VLAN off VLAN 1 mitigates VLAN-hopping attacks; native-VLAN frames travel untagged. WHY A VARIANT FAILS: the native VLAN must match on BOTH trunk ends or CDP reports a 'native VLAN mismatch' and traffic leaks between VLANs.",
14:"WHY IT WORKS: 'portfast' shortcuts STP convergence on edge ports; 'bpduguard' err-disables the port instantly if a BPDU arrives, protecting against a rogue switch. WHY IT MATTERS: portfast without bpduguard leaves you exposed to accidental switch loops at the edge.",
15:"WHY IT WORKS: STP root election is by lowest bridge-id (priority + MAC). Setting a lower priority (4096, or 'root primary') makes this switch the root so traffic follows the intended paths. WHY A VARIANT FAILS: leaving default priority 32768 lets the oldest/lowest-MAC switch win, often a wiring-closet switch, creating suboptimal paths.",
16:"WHY IT WORKS: rapid-pvst uses 802.1w for sub-second convergence per-VLAN, versus the ~30-50s of classic STP. It is backward-compatible with older STP neighbors.",
17:"WHY IT WORKS: 'channel-group 1 mode active' runs LACP to bundle the members into Port-channel1, which is then configured as one logical trunk. WHY A VARIANT FAILS: the member ports must have identical speed/duplex/VLAN settings or the bundle stays 'suspended'; mixing 'active' with 'on' (no protocol) breaks negotiation.",
18:"WHY IT WORKS: enabling 'ip routing' turns the L3 switch into a router; an SVI ('interface vlan 10') becomes the default gateway for that VLAN, giving inter-VLAN routing in hardware. WHY A VARIANT FAILS: the SVI stays down unless at least one access port in that VLAN is up.",
19:"WHY IT WORKS: on a router with one physical link to a switch trunk, subinterfaces with 'encapsulation dot1Q <vlan>' each act as a gateway for one VLAN - classic router-on-a-stick. WHY A VARIANT FAILS: forgetting the 'encapsulation dot1Q' line means the subinterface can't match tagged frames.",
20:"WHY IT WORKS: 0.0.0.0/0 matches every destination; the router sends anything it has no specific route for to the next hop. WHY A VARIANT FAILS: pointing a default route at a broadcast/multi-access interface instead of a next-hop IP can cause repeated ARP and 'route to null' problems.",
21:"WHY IT WORKS: a static route installs a fixed path to a remote subnet via a next hop; it has a low administrative distance (1) so it is preferred over dynamic routes. WHY IT MATTERS: the mask must exactly describe the destination subnet.",
22:"WHY IT WORKS: two statics to the same subnet - the second has a higher AD (200), so it only installs when the primary next hop disappears, giving automatic failover. WHY A VARIANT FAILS: give both the same AD and the router load-balances instead of failing over.",
23:"WHY IT WORKS: OSPF matches interfaces whose IP falls inside 'network <addr> <wildcard>' and places them in the stated area; the router-id gives a stable identity. WHY A VARIANT FAILS: OSPF 'network' takes a WILDCARD mask (0.0.0.255), not a subnet mask - using 255.255.255.0 is rejected.",
24:"WHY IT WORKS: 'passive-interface' still advertises the subnet but stops sending hellos out that port, so no adjacency forms toward hosts - safer and quieter on LAN edges. WHY A VARIANT FAILS: making a transit link passive silently prevents the neighbor relationship from ever forming.",
25:"WHY IT WORKS: 'default-information originate' tells OSPF to advertise a default route to the area, but only if the router actually has one (here, the static 0.0.0.0/0). WHY A VARIANT FAILS: without an existing default route, this command does nothing unless you add 'always'.",
26:"WHY IT WORKS: EIGRP forms neighbors on matched interfaces and exchanges routes; 'no auto-summary' keeps discontiguous subnets from being wrongly summarized to classful boundaries. WHY A VARIANT FAILS: EIGRP 'network' also uses a WILDCARD mask - a subnet mask is rejected.",
27:"WHY IT WORKS: RIP v2 supports VLSM/CIDR (unlike v1); 'no auto-summary' preserves subnet detail. WHY IT MATTERS: RIP advertises classful networks, so 'network 10.0.0.0' covers all 10.x subnets on the router.",
28:"WHY IT WORKS: the DHCP pool defines the subnet, gateway and DNS; the excluded-address range protects statically-assigned infrastructure IPs from being handed out. WHY A VARIANT FAILS: forgetting to exclude the gateway IP can hand it to a client, causing duplicate-IP outages.",
29:"WHY IT WORKS: 'ip helper-address' converts a client's broadcast DHCP DISCOVER into a unicast forwarded to the central server, so one server serves many subnets. WHY A VARIANT FAILS: the helper must be on the client-facing SVI/interface, not the server side.",
30:"WHY IT WORKS: static NAT creates a permanent 1:1 mapping so an inside host is always reachable at a fixed public IP; 'ip nat inside/outside' tells NAT which direction each interface faces. WHY A VARIANT FAILS: omitting the inside/outside interface tags means NAT never triggers.",
31:"WHY IT WORKS: PAT ('overload') multiplexes many inside hosts onto one public IP using unique source ports; the ACL selects which inside addresses get translated. WHY A VARIANT FAILS: leaving off 'overload' makes it 1:1 dynamic NAT that runs out of addresses instantly.",
32:"WHY IT WORKS: a standard ACL filters by source IP only; applied inbound it permits the listed subnet and the implicit 'deny any' drops the rest. WHY A VARIANT FAILS: standard ACLs should be placed close to the destination, and order matters - a broad permit above a specific deny nullifies the deny.",
33:"WHY IT WORKS: an extended ACL matches protocol, source, destination and port, so you can allow only HTTP/SSH to one server. The final explicit 'deny ip any any' makes intent clear (it's implicit anyway). WHY A VARIANT FAILS: ACL lines are evaluated top-down and stop at first match, so ordering is everything.",
34:"WHY IT WORKS: port-security limits how many MACs a port learns; 'sticky' saves learned MACs to the config, and 'restrict' drops violating frames while logging. WHY A VARIANT FAILS: the default violation action is 'shutdown' (err-disable), which can take a port down unexpectedly.",
35:"WHY IT WORKS: pointing at an NTP server lets the device sync its clock, which is essential for accurate logs, certificates and Kerberos. WHY IT MATTERS: without correct time, TLS/cert validation and log correlation break.",
36:"WHY IT WORKS: CDP (Cisco) and LLDP (standard) let devices discover directly-connected neighbors - handy for mapping and troubleshooting. WHY IT MATTERS: many orgs disable CDP toward untrusted edges to avoid leaking device info.",
37:"WHY IT WORKS: 'copy running-config startup-config' saves the live config to NVRAM so it survives a reload. WHY A VARIANT FAILS: forgetting this means all changes are lost on the next power cycle.",
38:"WHY IT WORKS: 'ipv6 unicast-routing' enables IPv6 forwarding (off by default); a /64 global address is assigned to the interface. WHY A VARIANT FAILS: without 'ipv6 unicast-routing' the router will not forward IPv6 between interfaces.",
39:"WHY IT WORKS: an IPv6 static route to a specific /64 plus a ::/0 default mirror the IPv4 model for IPv6. WHY IT MATTERS: link-local next hops require you to also specify the exit interface.",
40:"WHY IT WORKS: putting different networks in area 0 and area 1 scales OSPF - LSAs are flooded only within an area, and the ABR summarizes between them. WHY A VARIANT FAILS: every non-backbone area must touch area 0 (directly or via a virtual-link) or routing breaks.",
41:"WHY IT WORKS: a stub area blocks Type-5 external LSAs and injects a default route instead, shrinking the LSDB on edge routers. WHY A VARIANT FAILS: ALL routers in the area must agree it's a stub, or adjacencies won't form.",
42:"WHY IT WORKS: 'stub no-summary' (totally stubby) blocks Type-3, 4 AND 5 LSAs, leaving only a default route - maximum LSDB reduction. It is configured only on the ABR. WHY IT MATTERS: internal routers just need plain 'area X stub'.",
43:"WHY IT WORKS: an NSSA allows external routes to be injected (as Type-7, later translated to Type-5 by the ABR) while still behaving like a stub - useful when a stub area also has its own ASBR.",
44:"WHY IT WORKS: raising 'reference-bandwidth' lets OSPF distinguish between fast links (10G vs 1G) since default cost caps at 100Mbps; per-interface 'ip ospf cost' hard-sets a value. WHY A VARIANT FAILS: reference-bandwidth must match on all routers or cost calculations diverge.",
45:"WHY IT WORKS: MD5 authentication ensures only routers sharing the key form adjacencies, preventing rogue OSPF injection. WHY A VARIANT FAILS: mismatched key IDs or strings silently prevent the neighborship.",
46:"WHY IT WORKS: a virtual-link tunnels area 0 across a non-backbone transit area to repair a discontiguous backbone. WHY IT MATTERS: it's a fix, not a design goal - the router-id of the far ABR is the target.",
47:"WHY IT WORKS: OSPFv3 runs OSPF for IPv6, enabled per-interface with 'ipv6 ospf 1 area 0'; it uses link-local addresses for adjacencies. WHY A VARIANT FAILS: OSPFv3 still needs a 32-bit router-id, which it can't auto-derive without an IPv4 address, so set it manually.",
48:"WHY IT WORKS: named EIGRP centralizes all settings under one hierarchy (address-family, af-interface), which is the modern, scalable syntax. WHY IT MATTERS: 'af-interface' settings like passive-interface apply cleanly per interface.",
49:"WHY IT WORKS: 'ip summary-address eigrp' advertises one summary prefix out an interface instead of many specifics, shrinking routing tables. WHY A VARIANT FAILS: an overly-broad summary can black-hole traffic to subnets you don't actually have.",
50:"WHY IT WORKS: EIGRP 'variance N' allows load-balancing over feasible paths whose metric is within N times the best - unequal-cost load balancing, unique to EIGRP. WHY A VARIANT FAILS: a path must pass the feasibility condition or variance won't use it (loop prevention).",
51:"WHY IT WORKS: a key-chain provides the shared secret; per-interface commands bind MD5 auth to EIGRP so only trusted routers peer. WHY A VARIANT FAILS: key-string or key-id mismatch breaks the adjacency silently.",
52:"WHY IT WORKS: iBGP peers inside the same AS; peering to loopbacks with 'update-source Loopback0' keeps the session up as long as any path to the loopback exists. WHY A VARIANT FAILS: iBGP neighbors are not directly connected, so without 'update-source' (and reachability via an IGP) the TCP session never forms.",
53:"WHY IT WORKS: eBGP peers between different AS numbers; 'network ... mask' advertises a prefix that must already exist in the routing table. WHY A VARIANT FAILS: if the exact prefix isn't in the RIB, BGP won't advertise it.",
54:"WHY IT WORKS: eBGP normally requires TTL=1 (directly connected); 'ebgp-multihop 2' plus loopback peering allows the session to survive multiple paths/links. WHY A VARIANT FAILS: without multihop, loopback-based eBGP fails because packets exceed one hop.",
55:"WHY IT WORKS: a route reflector re-advertises iBGP routes to its clients, breaking the full-mesh requirement and scaling iBGP. WHY IT MATTERS: only the RR needs 'route-reflector-client'; clients are unaware.",
56:"WHY IT WORKS: local-preference is the second BGP decision step and is shared inside the AS; higher wins, so setting LP 200 inbound steers all internal traffic toward that exit. WHY A VARIANT FAILS: LP only influences outbound traffic from your AS, not what a neighbor sends you.",
57:"WHY IT WORKS: prepending your own AS lengthens the AS-path, making the route less attractive to neighbors - a common way to make a backup link truly backup. WHY IT MATTERS: apply it OUTbound; AS-path length is compared before MED.",
58:"WHY IT WORKS: 'redistribute static subnets' injects static routes into OSPF as external (E2) routes; 'subnets' is required or only classful networks are redistributed. WHY A VARIANT FAILS: omitting 'subnets' silently drops all non-classful statics.",
59:"WHY IT WORKS: mutual redistribution shares routes both ways; EIGRP needs a full seed metric (bw, delay, reliability, load, MTU) because it has no default. WHY A VARIANT FAILS: forgetting the EIGRP metric means redistributed routes are ignored; two-way redistribution without filtering can cause routing loops.",
60:"WHY IT WORKS: a route-map matched to a prefix-list gives fine-grained control - here it denies specific prefixes during redistribution. WHY IT MATTERS: prefix-lists match ranges precisely with 'le'/'ge' and are faster than ACLs for route filtering.",
61:"WHY IT WORKS: HSRP presents a virtual IP as the gateway; the higher-priority router is active, and 'preempt' lets it reclaim the active role after a failure. WHY A VARIANT FAILS: without 'preempt', a recovered primary stays standby until the current active fails.",
62:"WHY IT WORKS: VRRP is the open-standard equivalent of HSRP; the master owns the virtual IP and higher priority wins. WHY IT MATTERS: VRRP preempts by default (unlike HSRP).",
63:"WHY IT WORKS: GLBP provides load-balancing across multiple gateways via a single virtual IP by handing out different virtual MACs - active/active, unlike HSRP/VRRP active/standby.",
64:"WHY IT WORKS: 'no switchport' turns the members into routed ports, then they're bundled into a L3 Port-channel with an IP - one logical routed link with double bandwidth. WHY A VARIANT FAILS: mixing L2 and L3 members in one channel is invalid.",
65:"WHY IT WORKS: SPAN copies traffic from a source port to a destination analyzer port for packet capture/IDS. WHY A VARIANT FAILS: the destination port stops passing normal traffic, so never use a live uplink as a SPAN destination.",
66:"WHY IT WORKS: DHCP snooping builds a binding table of legitimate leases and only trusts the uplink toward the real server, blocking rogue DHCP servers on access ports. WHY A VARIANT FAILS: forgetting to trust the server-facing port blocks legitimate DHCP offers.",
67:"WHY IT WORKS: Dynamic ARP Inspection validates ARP against the DHCP-snooping binding table, stopping ARP-spoofing/man-in-the-middle. WHY IT MATTERS: DAI depends on DHCP snooping being enabled first.",
68:"WHY IT WORKS: 'access-class' applies an ACL to the VTY lines so only the management subnet can open SSH sessions - control-plane protection. WHY A VARIANT FAILS: applying it as 'out' instead of 'in' restricts where the device can SSH TO, not who can reach it.",
69:"WHY IT WORKS: a class-map identifies traffic (e.g. RTP voice), a policy-map marks it (DSCP EF), and 'service-policy' applies it to an interface - the Modular QoS CLI. WHY IT MATTERS: marking must happen as close to the source as possible so the whole path honors it.",
70:"WHY IT WORKS: an SNMPv2 read-only community with an ACL lets an NMS poll the device while limiting who can query. WHY A VARIANT FAILS: SNMPv2 community strings are sent in clear text - use SNMPv3 for anything sensitive.",
71:"WHY IT WORKS: 'logging host' ships syslog to a collector and 'logging trap informational' sets the severity threshold; timestamps make events correlatable. WHY IT MATTERS: without accurate NTP, timestamps are useless for correlation.",
72:"WHY IT WORKS: authenticated NTP ensures the device only trusts time from a keyed source; 'ntp master' provides a local reference if upstream is lost. WHY A VARIANT FAILS: a mismatched trusted-key means the device rejects the server's time.",
73:"WHY IT WORKS: an IP SLA probe repeatedly tests reachability; a 'track' object turns that result into an up/down signal other features (static routes, HSRP) can react to for fast failover. WHY IT MATTERS: this is how you make a floating static route respond to end-to-end loss, not just local link state.",
74:"WHY IT WORKS: a VRF gives a customer its own private routing table on a shared PE; the Route Distinguisher makes overlapping customer prefixes unique, and Route Targets control which VRFs import/export routes. WHY A VARIANT FAILS: mismatched import/export RTs mean routes never reach the other site.",
75:"WHY IT WORKS: 'vrf forwarding' binds the PE interface into the customer VRF so its traffic uses the customer's private table, not the global one. WHY A VARIANT FAILS: applying the IP before 'vrf forwarding' wipes the IP - always set the VRF first.",
76:"WHY IT WORKS: enabling LDP and 'mpls ip' on core links lets routers exchange labels and build LSPs, so the core switches on labels instead of IP lookups - the foundation for MPLS VPNs. WHY IT MATTERS: the core needs an IGP (OSPF/IS-IS) with loopback reachability for LDP to work.",
77:"WHY IT WORKS: the VPNv4 address-family carries customer routes (RD+prefix) between PEs over MP-BGP; 'send-community extended' is required so Route Targets travel with the routes. WHY A VARIANT FAILS: forgetting 'send-community extended' means RTs are stripped and no VRF imports the routes.",
78:"WHY IT WORKS: running OSPF inside a VRF ('router ospf 10 vrf CUST_A') keeps the customer's IGP isolated per-VRF on the PE. WHY IT MATTERS: each VRF gets its own OSPF process/instance.",
79:"WHY IT WORKS: redistributing between the per-VRF OSPF and MP-BGP glues the PE-CE routing to the MPLS backbone in both directions. WHY A VARIANT FAILS: one-way redistribution leaves half the sites unreachable.",
80:"WHY IT WORKS: DMVPN uses a multipoint GRE tunnel plus NHRP so the hub learns spoke public IPs dynamically and (phase 3) spokes build direct tunnels on demand. WHY IT MATTERS: 'ip nhrp map multicast dynamic' lets routing protocols run over the tunnel.",
81:"WHY IT WORKS: the spoke registers its tunnel-to-public mapping with the NHS (hub); NHRP then resolves other spokes for direct spoke-to-spoke traffic. WHY A VARIANT FAILS: a wrong 'nhrp nhs' or 'nhrp map' to the hub prevents registration and the tunnel stays down.",
82:"WHY IT WORKS: the IKEv2 proposal lists the crypto algorithms and the policy binds them; both peers must have a compatible proposal to negotiate phase 1. WHY A VARIANT FAILS: no overlapping DH group/encryption/integrity means IKE never establishes.",
83:"WHY IT WORKS: the keyring holds the pre-shared key per peer, and the IKEv2 profile ties identity matching to authentication and the keyring. WHY A VARIANT FAILS: an identity mismatch ('match identity remote') means the peer is rejected during auth.",
84:"WHY IT WORKS: the transform-set defines how packets are encrypted/authenticated (ESP-AES/SHA), the IPsec profile wraps it, and 'tunnel protection' applies it to the GRE tunnel - GRE-over-IPsec. WHY A VARIANT FAILS: transform-set mismatch between peers drops phase 2.",
85:"WHY IT WORKS: a confederation splits one big AS into smaller sub-ASes that use eBGP-like rules internally while appearing as a single AS externally - an alternative to route reflectors. WHY IT MATTERS: 'confederation peers' lists the other sub-ASes.",
86:"WHY IT WORKS: communities tag routes so policy can be applied consistently downstream; the community-list matches the tag and route-maps act on it, and 'send-community' forwards the tags. WHY A VARIANT FAILS: forgetting 'send-community' means the tag is stripped and neighbors can't match it.",
87:"WHY IT WORKS: a peer-group/template applies one set of policies to many neighbors at once, cutting config and improving update efficiency. WHY IT MATTERS: all members share outbound policy, so they must be policy-compatible.",
88:"WHY IT WORKS: conditional advertisement advertises a prefix only when a monitored ('non-exist') prefix is absent - e.g. advertise a backup only when the primary is gone. WHY IT MATTERS: it needs both an advertise-map and a non-exist-map.",
89:"WHY IT WORKS: Performance Routing (PfR/OER) uses a master controller and border routers to pick the best exit based on delay/loss/reachability, beyond static metrics. WHY IT MATTERS: borders must be under the master's control via the key-chain.",
90:"WHY IT WORKS: hierarchical QoS nests a child queuing policy inside a parent shaper, so you shape the aggregate to a rate and prioritize within it - typical for sub-line-rate WAN. WHY A VARIANT FAILS: the child bandwidth percentages are relative to the shaped rate, not the physical link.",
91:"WHY IT WORKS: WRED drops packets probabilistically as queues fill (weighted by DSCP) to prevent TCP global synchronization and manage congestion gracefully. WHY IT MATTERS: WRED is for TCP-heavy traffic; it hurts UDP/voice.",
92:"WHY IT WORKS: 'ip multicast-routing' enables multicast forwarding and 'ip pim sparse-mode' builds shared/shortest-path trees only where receivers exist. WHY A VARIANT FAILS: sparse-mode needs an RP; without one, group state never forms.",
93:"WHY IT WORKS: a static RP tells every router where the shared-tree root is for multicast groups - simple and deterministic for small networks. WHY A VARIANT FAILS: every router must agree on the same RP address or trees fragment.",
94:"WHY IT WORKS: Auto-RP distributes RP info automatically - a candidate-RP announces itself and a mapping agent advertises the elected RP to everyone. WHY IT MATTERS: it removes the need to hard-code the RP on every router.",
95:"WHY IT WORKS: IS-IS uses a NET (area + system-id) instead of IP for its addressing; 'is-type level-2-only' keeps it as a flat backbone. WHY A VARIANT FAILS: mismatched area IDs at L1 or a malformed NET prevents adjacency.",
96:"WHY IT WORKS: 'metric-style wide' enables 24-bit/32-bit metrics instead of the tiny 6-bit default, which is required for large networks and for IS-IS traffic engineering. WHY A VARIANT FAILS: mixing narrow and wide metrics in a domain causes inconsistent path selection.",
97:"WHY IT WORKS: an NVE interface sources VXLAN from a loopback and maps a Layer-2 segment (VNI) to a multicast group for BUM traffic - stretching L2 over an L3 fabric. WHY IT MATTERS: the loopback must be reachable across the underlay.",
98:"WHY IT WORKS: ZBF assigns interfaces to security zones, then a zone-pair with an inspect policy controls and statefully inspects traffic between zones; traffic between zones is denied unless a policy permits it. WHY A VARIANT FAILS: interfaces in the same zone pass freely, and traffic to/from the 'self' zone needs its own zone-pair.",
99:"WHY IT WORKS: EIGRP for IPv6 is enabled per-interface with 'ipv6 eigrp 100' and the process must be 'no shutdown'. WHY A VARIANT FAILS: the IPv6 EIGRP process starts shut down by default, so forgetting 'no shutdown' means no neighbors.",
100:"WHY IT WORKS: SR-MPLS assigns a globally-significant prefix-SID (index) to a loopback; every router derives the same label from the SGGB block, so no LDP is needed for the LSP. WHY IT MATTERS: SIDs must be unique and within the configured label range.",
}
for _s in S:
    _s["explain"] = EXPLAIN.get(_s["id"], "WHY IT WORKS: this is a valid configuration that follows the correct mode, syntax and command dependencies for the feature.")
assert all(s.get("explain") for s in S), "missing explanation"
print("explanations:", sum(1 for s in S if s.get('explain')))

print("total samples:", len(S))
js = "window.SCRIPT_SAMPLES = " + json.dumps(S, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"
with open("/home/user/workspace/certprep_single/script_samples.js", "w", encoding="utf-8") as f:
    f.write(js)
print("wrote script_samples.js", len(js), "bytes")
