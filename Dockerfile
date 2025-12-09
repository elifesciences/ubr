FROM ubuntu:20.04

ARG POSTGRES_VERSION

RUN apt-get update -y && apt-get install -y gpg wget curl ca-certificates rsync postgresql-common && \
    install -dm 755 /etc/apt/keyrings && \
    wget -qO - https://mise.jdx.dev/gpg-key.pub | gpg --dearmor | tee /etc/apt/keyrings/mise-archive-keyring.gpg 1> /dev/null && \
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor | tee /etc/apt/trusted.gpg.d/apt.postgresql.org.gpg >/dev/null && sh -c 'echo "deb http://apt-archive.postgresql.org/pub/repos/apt/ focal-pgdg main" >> /etc/apt/sources.list.d/postgresql.list' && \
    echo "deb [signed-by=/etc/apt/keyrings/mise-archive-keyring.gpg] https://mise.jdx.dev/deb stable main" | tee /etc/apt/sources.list.d/mise.list && \
    apt-get update -y && apt-get install -y mysql-client postgresql-client-${POSTGRES_VERSION} mise

WORKDIR /opt/ubr
COPY . .
RUN chmod 600 .pgpass.test

RUN mise trust . && mise install && mise install-deps

CMD [ "mise", "test" ]
