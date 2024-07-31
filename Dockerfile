FROM python:3.11
COPY . .
RUN pip3 install -r requirements.txt
ENTRYPOINT [ "python3", "-m"]