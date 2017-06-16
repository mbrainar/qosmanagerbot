FROM python:3-alpine
MAINTAINER Matthew Brainard <mbrainar@cisco.com>
EXPOSE 5000

# Install basic utilities
RUN apk add -U \
        ca-certificates \
  && rm -rf /var/cache/apk/* \
  && pip install --no-cache-dir \
        setuptools \
        wheel


COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

WORKDIR /app
ADD ./bot /app/bot

CMD [ "python", "bot/bot.py" ]
