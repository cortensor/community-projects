FROM ipfs/kubo:v0.33.2 AS ipfs

FROM ubuntu:24.04

# Install necessary packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    apt-transport-https \
    ca-certificates 

COPY --from=ipfs /usr/local/bin/ipfs /usr/local/bin/ipfs

# Clone the Cortensor installer repository
RUN git clone https://github.com/cortensor/installer.git /opt/cortensor-installer

WORKDIR /opt/cortensor-installer

RUN mkdir /home/deploy && cp -r dist /home/deploy/.cortensor

WORKDIR /home/deploy/.cortensor

COPY run.sh /home/deploy/.cortensor/run.sh

RUN chmod +x cortensord \
  && mkdir logs \
  && mkdir llm-files \
  && cp .env-example .env \
  && cp cortensor.service /etc/systemd/system \
  && touch logs/cortensord.log \
  && touch logs/cortensord-llm.log \
  && chmod +x run.sh

USER root
CMD ["/bin/bash", "-c", "/home/deploy/.cortensor/run.sh"]
