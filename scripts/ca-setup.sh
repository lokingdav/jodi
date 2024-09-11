#!/bin/bash

# Delete certs folder if it exists
rm -rf certs

# Default number of providers
DEFAULT_PROVIDERS=10

# Root CA certificate details
CA_KEY=ca.key
CA_CERT=ca.crt
CA_SUBJECT="/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=Root CA"
CA_EXPIRY_DAYS=3650
CA_KEY_ALGORITHM=ec # ECDSA algorithm

# Parse command line arguments
if [ $# -eq 0 ]; then
    NUM_PROVIDERS=$DEFAULT_PROVIDERS
elif [ $# -eq 1 ]; then
    NUM_PROVIDERS=$1
else
    echo "Usage: $0 [NUM_PROVIDERS]"
    exit 1
fi

# Carrier details
declare -A CARRIERS
for ((i=1; i<=$NUM_PROVIDERS; i++))
do
    CARRIERS["sp$i"]="sp$i"
done

# Other certificate details
CERT_EXPIRY_DAYS=365
CERT_KEY_ALGORITHM=ec # ECDSA algorithm

# Create certs folder
mkdir -p certs

# Create Root CA key and certificate
openssl ecparam -name prime256v1 -genkey -out "certs/$CA_KEY"
openssl req -new -x509 -key "certs/$CA_KEY" -out "certs/$CA_CERT" -subj "$CA_SUBJECT" -days "$CA_EXPIRY_DAYS"

# Create certificates signed by the CA for each carrier
for CARRIER in "${!CARRIERS[@]}"
do
    CARRIER_FOLDER="certs/${CARRIERS[$CARRIER]}"
    mkdir -p "$CARRIER_FOLDER"

    CERT_KEY="$CARRIER_FOLDER/key.pem"
    CERT_CSR="$CARRIER_FOLDER/csr.pem"
    CERT_CERT="$CARRIER_FOLDER/cert.pem"
    CERT_SUBJECT="/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=${CARRIERS[$CARRIER]}"

    # Generate key
    openssl ecparam -name prime256v1 -genkey -out "$CERT_KEY"

    # Generate CSR with required STIR/SHAKEN fields
    openssl req -new -key "$CERT_KEY" -out "$CERT_CSR" -subj "$CERT_SUBJECT"

    # Sign CSR with CA
    openssl x509 -req -in "$CERT_CSR" -CA "certs/$CA_CERT" -CAkey "certs/$CA_KEY" -CAcreateserial -out "$CERT_CERT" -days "$CERT_EXPIRY_DAYS"

    # Cleanup CSR
    rm "$CERT_CSR"
done

echo "Certificates created successfully."
