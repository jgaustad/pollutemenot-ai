#!/bin/bash

#FROM nvcr.io/nvidia/l4t-tensorflow:r32.4.3-tf2.2-py3
#FROM tensorflow/tensorflow
#FROM nvidia/k8s-device-plugin
# 
# 
#
# JupyterLab
#
#

apt-get update
apt-get -y upgrade
apt-get install python3
apt-get install -y python3-pip
#pip3 install --upgrade pip
# install gdal
apt-get install -y gdal-bin libgdal-dev
CPLUS_INCLUDE_PATH=/usr/include/gdal
C_INCLUDE_PATH=/usr/include/gdal
pip3 install GDAL==2.2.3 #version == might be needed here.
pip3 install keras


#RUN pip3 install --upgrade pip3
pip3 install --upgrade setuptools pip
#RUN apt install -y libzmq3-dev
pip3 install earthengine-api
#RUN pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
apt-get install -y screen
apt-get install -y vim
apt-get install -y curl
#RUN pip3 install gcloud #added
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-sdk -y
      

#RUN apt install -y libffi-dev
#RUN apt install -y python3-cffi
# RUN apt install -y python3-zmq
# RUN apt install -y python3-tornado
# RUN apt install -y python3-argon2
#RUN apt install -y python3-pandocfilters
pip3 install jupyter jupyterlab --verbose
pip3 install matplotlib
pip3 install pandas
pip3 install folium

#
pip3 install tensorflow-hub
pip3 install tensorflow-datasets
#RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager@2
#RUN jupyter lab --generate-config
#RUN python3 -c "from notebook.auth.security import set_password; set_password('nvidia', '/root/.jupyter/jupyter_notebook_config.json')" 
#CMD /bin/bash -c "jupyter lab --ip 0.0.0.0 --port 8888 --allow-root"

