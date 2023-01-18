FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY convert_scryfall_to_sql.py .
COPY main.py .
COPY html html/
COPY static static/
COPY templates templates/

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:80"]
