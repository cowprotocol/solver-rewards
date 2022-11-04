FROM python:3.10.8
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT [ "python3", "-m"]