FROM python:3.12
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT [ "python", "-m"]
