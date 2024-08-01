FROM python:3.11
COPY . .
RUN  install -r requirements.txt
ENTRYPOINT [ "python3", "-m"]