# Copyright © Amazon.com and Affiliates: This deliverable is considered Developed Content as defined in the AWS Service Terms.

FROM public.ecr.aws/docker/library/python:3.11.10-slim
WORKDIR /app

COPY requirements.txt requirements.txt
# Install from requirements file
RUN pip install -r requirements.txt

RUN pip install aws-opentelemetry-distro==0.10.0

# AWS_REGION and credentials should be passed at runtime via task IAM roles
# or container orchestration, not baked into the image (T2/T10).
# Example: docker run -e AWS_REGION=us-east-1 ...

# BDR4: Bedrock Guardrails — pass guardrail ID and version at runtime.
# Example: docker run -e BEDROCK_GUARDRAIL_ID=abc123 -e BEDROCK_GUARDRAIL_VERSION=1 ...

# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

# Copy entire project (respecting .dockerignore)
COPY . .

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=3)" || exit 1

CMD ["opentelemetry-instrument", "python", "-m", "main"]
