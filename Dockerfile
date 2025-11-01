FROM python:3.11-slim

# Instalar Java y herramientas necesarias
RUN apt-get update && \
    apt-get install -y openjdk-11-jre-headless wget unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Descargar EPUBCheck
RUN wget https://github.com/w3c/epubcheck/releases/download/v5.1.0/epubcheck-5.1.0.zip && \
    unzip epubcheck-5.1.0.zip && \
    mv epubcheck-5.1.0/epubcheck.jar /app/epubcheck.jar && \
    rm -rf epubcheck-5.1.0 epubcheck-5.1.0.zip

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY app.py .

# Exponer puerto
EXPOSE 8080

# Comando de inicio
CMD ["python", "app.py"]
