# --- Base image -------------------------------------------------------------
FROM ubuntu:22.04

# --- Non‑interactive frontend -----------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive

# --- Install system deps ----------------------------------------------------
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
          python3 \
          python3-pip \
          rsyslog \
          jq \
          ca-certificates \
          iproute2 \
          curl \
          tzdata \
          tcpdump \
          iptables \
          sudo \
          tini \
     && rm -rf /var/lib/apt/lists/*



# --- disable rsyslog at boot--------------------------------------------------

RUN rm -f /etc/init.d/rsyslog
   

# --- Create app directory ---------------------------------------------------
WORKDIR /app

# --- Copy & install Python requirements -------------------------------------
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# --- Copy Streamlit app & entrypoint ----------------------------------------
COPY app/ /opt/streamlit
COPY app/.streamlit /opt/streamlit/.streamlit
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
RUN chmod +x /opt/streamlit/*.sh


# --- Entrypoint -------------------------------------------------------------

ENTRYPOINT ["tini","-g","--"]

CMD ["/usr/local/bin/entrypoint.sh"]
     
