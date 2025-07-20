#!/bin/bash

sudo echo "Installing FileShare..."
mkdir FileShare
cd FileShare
curl https://quanthai.net/fileshare.py -o fileshare.py
echo "Requires pyinstaller to work"
pyinstaller --onefile fileshare.py
echo -e "===\n\n\nStep 1 done\n\n\n==="
cd dist
sudo cp fileshare /usr/bin/
sudo cp fileshare /usr/local/bin/
sudo mkdir /usr/share/fileshare
sudo cp fileshare /usr/share/fileshare/
rm -rf build
rm *.spec
rm -rf dist

echo "installation of FileShare complete!"