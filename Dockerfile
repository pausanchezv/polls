FROM python:3.9
WORKDIR /polls
COPY . /polls
RUN pip install --no-cache-dir --upgrade -r /polls/requirements.txt
EXPOSE 80

# Only kubernetes
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]