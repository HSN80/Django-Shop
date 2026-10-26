FROM python:3.12-slim
RUN mkdir /app
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 
RUN pip install --upgrade pip
COPY requirements.txt /app
RUN pip install -r requirements.txt
COPY ./core /app
EXPOSE 8000