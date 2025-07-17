FROM ubuntu:20.04

RUN apt update -y && apt install -y gpg wget curl postgresql-client mysql-client rsync && \
    install -dm 755 /etc/apt/keyrings && \
    wget -qO - https://mise.jdx.dev/gpg-key.pub | gpg --dearmor | tee /etc/apt/keyrings/mise-archive-keyring.gpg 1> /dev/null && \
    echo "deb [signed-by=/etc/apt/keyrings/mise-archive-keyring.gpg] https://mise.jdx.dev/deb stable main" | tee /etc/apt/sources.list.d/mise.list && \
    apt update && \
    apt install -y mise

WORKDIR /opt/ubr
COPY . .
RUN chmod 600 .pgpass.test

RUN mise trust . && mise install && mise install-deps

CMD [ "mise", "exec", "--", "./test.sh" ]
