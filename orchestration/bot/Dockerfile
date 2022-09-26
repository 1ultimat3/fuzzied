FROM trailofbits/echidna

RUN apt update
RUN apt install git python3-pip -y

RUN git clone https://github.com/1ultimat3/fuzzied.git /opt/fuzzied
RUN pip3 install -r /opt/fuzzied/orchestration/bot/requirements.txt

RUN find /opt/fuzzied -name "compile.sh" |xargs chmod a+x

CMD cd /opt/fuzzied/orchestration/bot && python3 bot.py
