FROM python:3.8
  
ENV GIT_HASH=12345

COPY ./ /

RUN ls -al /

RUN pip3 install -r /requirements.txt

CMD ["/flask_code.py"]

