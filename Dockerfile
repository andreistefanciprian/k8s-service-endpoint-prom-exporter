FROM python:3.7-slim

RUN groupadd nonroot && useradd -m -r -g nonroot nonroot

USER nonroot

WORKDIR /home/nonroot

ADD --chown=nonroot:nonroot requirements.txt  .
ADD --chown=nonroot:nonroot main.py  .

RUN pip install -r requirements.txt

CMD ["python", "main.py"]