# Use Miniconda base image
FROM continuumio/miniconda3

# Set work directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

COPY jupyter_notebook_config.py /root/.jupyter/jupyter_notebook_config.py

# Create the environment
RUN conda env create -f environment.yml

# Make RUN.sh executable
RUN chmod +x run.sh

# Specify the command to run your app
CMD ["./run.sh"]
