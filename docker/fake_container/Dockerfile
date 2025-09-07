FROM busybox:stable

COPY rename.sh /usr/local/bin/rename.sh
RUN chmod +x /usr/local/bin/rename.sh

# Default mount points (you'll bind these at runtime)
VOLUME ["/input", "/output"]

ENTRYPOINT ["/usr/local/bin/rename.sh"]