#!/bin/bash

git clone https://github.com/nationalcptc-teamtools/City-College-of-San-Francisco.git ~/tools
chmod +x ~/tools/setup-kali.sh
sudo ~/tools/setup-kali.sh $(whoami)
