FROM python:3.11-slim
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install pytest \
    && pip install -r requirements.txt

# Copy source and test code to the container
COPY src/ src/
COPY tests/ tests/
COPY utils/ utils/
COPY pytest.ini .

# Just runs tests for now, will be updated in the future
CMD ["pytest", "tests/"]
