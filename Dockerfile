FROM python
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT [ "python3", "-m" , "src.fetch.transfer_file"]
