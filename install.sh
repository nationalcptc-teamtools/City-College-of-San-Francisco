#!/bin/bash

git clone https://github.com/zoeyg/cptc.git ~/tools
chmod +x ~/tools/setup-kali.sh
sudo ~/tools/setup-kali.sh $(whoami)
