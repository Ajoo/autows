#!/bin/bash

apt-get update
apt-get install htop

USER="ubuntu"
USER_HOME="/home/$USER"

cd $USER_HOME
mkdir .ssl
cd .ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout "cert.key" -out "cert.pem" -batch
cd ..

#jupyter notebook --generate-config
cat >> $USER_HOME/.jupyter/jupyter_notebook_config.py << EOF
c.NotebookApp.certfile = u'$USER_HOME/.ssl/cert.pem'
c.NotebookApp.keyfile = u'$USER_HOME/.ssl/cert.key'

c.NotebookApp.ip = '*'
c.NotebookApp.password = u'{notebook_password}'
c.NotebookApp.open_browser = False

c.NotebookApp.port = {notebook_port}
EOF