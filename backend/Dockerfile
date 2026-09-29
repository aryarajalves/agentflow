FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    ffmpeg \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configuração de timezone padrão para horário de Brasília
ENV TZ=America/Sao_Paulo

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Fix Windows line endings (CRLF -> LF) and make executable
RUN sed -i 's/\r//' entrypoint.sh && chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Run migrations then start the application
ENTRYPOINT ["./entrypoint.sh"]
