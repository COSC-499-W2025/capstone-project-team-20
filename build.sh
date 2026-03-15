#!/bin/bash
cd src/ui/react-app
npm install
npm run build
cd ../../../
pip install -r requirements.txt