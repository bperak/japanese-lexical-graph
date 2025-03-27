#!/bin/bash
# Check SSL certificate status for Japanese Lexical Graph

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# SSL Certificate Configuration (default paths)
CERT_DIR="/home/Liks/certs"
CERT_FILE="$CERT_DIR/liks.cer"
KEY_FILE="$CERT_DIR/liks.key"

# Allow custom paths
if [ "$1" != "" ]; then
  CERT_FILE="$1"
fi

if [ "$2" != "" ]; then
  KEY_FILE="$2"
fi

echo -e "${GREEN}=== SSL Certificate Check ===${NC}"

# Check if certificate file exists
if [ ! -f "$CERT_FILE" ]; then
  echo -e "${RED}Certificate file not found at: $CERT_FILE${NC}"
  exit 1
else
  echo -e "${GREEN}Certificate file found at: $CERT_FILE${NC}"
fi

# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
  echo -e "${RED}Key file not found at: $KEY_FILE${NC}"
  exit 1
else
  echo -e "${GREEN}Key file found at: $KEY_FILE${NC}"
fi

# Check certificate expiration date
echo -e "\n${YELLOW}Certificate Information:${NC}"
CERT_END_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f 2)
CERT_START_DATE=$(openssl x509 -startdate -noout -in "$CERT_FILE" | cut -d= -f 2)
CURRENT_DATE=$(date)
CERT_SUBJECT=$(openssl x509 -subject -noout -in "$CERT_FILE")
CERT_ISSUER=$(openssl x509 -issuer -noout -in "$CERT_FILE")

echo -e "Subject: ${GREEN}$CERT_SUBJECT${NC}"
echo -e "Issuer:  ${GREEN}$CERT_ISSUER${NC}"
echo -e "Valid From: ${GREEN}$CERT_START_DATE${NC}"
echo -e "Valid Until: ${GREEN}$CERT_END_DATE${NC}"
echo -e "Current Date: ${YELLOW}$CURRENT_DATE${NC}"

# Check if certificate matches private key
KEY_MOD=$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)
CERT_MOD=$(openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5)

if [ "$KEY_MOD" = "$CERT_MOD" ]; then
  echo -e "\n${GREEN}✓ Private key matches certificate${NC}"
else
  echo -e "\n${RED}✗ Private key does NOT match certificate!${NC}"
fi

# Check if the certificate is self-signed
if [ "$(openssl x509 -noout -issuer -in "$CERT_FILE")" = "$(openssl x509 -noout -subject -in "$CERT_FILE")" ]; then
  echo -e "${YELLOW}⚠ This is a self-signed certificate${NC}"
fi

# Check days until expiration
EXPIRE_DATE=$(date -d "$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f 2)" +%s)
CURRENT_DATE=$(date +%s)
DAYS_LEFT=$(( (EXPIRE_DATE - CURRENT_DATE) / 86400 ))

if [ $DAYS_LEFT -lt 0 ]; then
  echo -e "${RED}✗ Certificate has EXPIRED!${NC}"
elif [ $DAYS_LEFT -lt 30 ]; then
  echo -e "${RED}⚠ Certificate will expire in $DAYS_LEFT days!${NC}"
else
  echo -e "${GREEN}✓ Certificate valid for $DAYS_LEFT more days${NC}"
fi

echo -e "\n${YELLOW}To check your SSL configuration from the web, try:${NC}"
echo -e "https://www.ssllabs.com/ssltest/analyze.html?d=$(hostname -f)&latest"

echo -e "\n${YELLOW}To test the SSL connection directly:${NC}"
echo -e "openssl s_client -connect $(hostname -f):8003" 