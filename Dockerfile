FROM python:3.9.16-slim as python

ENV PYTHONUNBUFFERED=true
WORKDIR /app


FROM python as poetry

ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN python -c 'from urllib.request import urlopen; print(urlopen("https://install.python-poetry.org").read().decode())' | python -
COPY . ./
RUN poetry install --no-interaction --no-ansi -vvv



FROM python as runtime
LABEL org.opencontainers.image.source=https://github.com/ziyixi/Job-Finder

ENV PATH="/app/.venv/bin:$PATH"
ENV NOTION_TOKEN="NOTION_TOKEN"
ENV NOTION_PAGE_ID="NOTION_PAGE_ID"

COPY --from=poetry /app /app
WORKDIR /app/job_finder

CMD ["sh", "-c", "playwright install chromium; playwright install-deps; sh run_job.sh; tail -f /dev/null"]