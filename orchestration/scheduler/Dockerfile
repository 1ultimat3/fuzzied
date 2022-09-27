FROM python:3.9

RUN apt update
RUN apt install git

RUN git clone https://github.com/1ultimat3/fuzzied.git /opt/fuzzied
RUN pip3 install -r /opt/fuzzied/orchestration/bot/requirements.txt

COPY env.conf /opt/fuzzied/orchestration/scheduler/

CMD cd /opt/fuzzied/orchestration/scheduler && python3 scheduler.py
