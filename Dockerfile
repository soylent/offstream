FROM python:3.10
ENV PORT=8000
ENV HOST=0.0.0.0
EXPOSE 8000
VOLUME /root/.offstream
RUN pip install offstream && \
  echo '#!/bin/sh\nexec offstream --host $HOST --port $PORT' > /init.sh && \
  chmod +x /init.sh
CMD ["/init.sh"]