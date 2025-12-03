# Server
## CA Creation
```
openssl genrsa -out /etc/ipsec.d/private/root.pem 4096
openssl req -x509 -new -key /etc/ipsec.d/private/root.pem \
    -out /etc/ipsec.d/certs/root.crt -days 3650
echo 01 > /etc/ipsec.d/root.srl
touch /etc/ipsec.d/ca.db.index
```

## VPN server cert request
```
openssl genrsa -out /etc/ipsec.d/private/key.pem 2048
openssl req -new -key /etc/ipsec.d/private/key.pem \
    -out /etc/ipsec.d/reqs/vpn.csr -config /etc/ipsec.d/openssl-server.cnf
```

## Server Cert signature
```
openssl ca -config /etc/ipsec.d/openssl.cnf -in /etc/ipsec.d/reqs/vpn.csr \
    -out /etc/ipsec.d/certs/vpn.crt -policy generic_policy -days 365
```

# Client
## Client cert request
```
openssl req -new -key /etc/ipsec.d/private/key.pem \
    -out /etc/ipsec.d/reqs/fabianb.csr -config /etc/ipsec.d/openssl.cnf
```
Copy the request from client to server

# Server
## Client Cert signature
```
openssl ca -config /etc/ipsec.d/openssl.cnf -in /etc/ipsec.d/reqs/fabianb.csr \
    -out /etc/ipsec.d/certs/fabianb.crt -policy generic_policy -days 365

```
Copy the signed certificate back to the client