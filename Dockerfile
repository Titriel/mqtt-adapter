FROM python:3.11-slim

RUN useradd worker
USER worker
WORKDIR /home/worker
RUN mkdir /home/worker/.local
RUN mkdir -m 755 /home/worker/.local/bin
ENV PATH "$PATH:/home/worker/.local/bin"

COPY ./requirements.txt /home/worker/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /home/worker/requirements.txt
 
COPY ./script /home/worker/script
COPY ./config /home/worker/config
COPY ./devices /home/worker/devices

RUN cd /home/worker
WORKDIR /home/worker
CMD ["python", "script/main.py"]