#!/bin/bash
set -e

# Update package information
apt-get update

# Install Chrome dependencies
apt-get install -y wget gnupg unzip

# Install Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list
apt-get update
apt-get install -y google-chrome-stable

# Download ChromeDriver
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1)
wget -q https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION} -O chrome_version
CHROMEDRIVER_VERSION=$(cat chrome_version)
rm chrome_version
wget -q https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/chromedriver
chown root:root /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver

# Install Selenium
pip install selenium

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -f chromedriver_linux64.zip

echo "Selenium and Chrome installed successfully!"
