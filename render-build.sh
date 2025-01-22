#!/usr/bin/env bash
set -x

# Instalar Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome-stable_current_amd64.deb

# Limpiar archivos innecesarios
rm google-chrome-stable_current_amd64.deb
