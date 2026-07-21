FROM frangoteam/fuxa:1.3.1@sha256:96cc065acb82db99943142a2ba12760b4d48440d96e263744acb706188420e22

WORKDIR /usr/src/app/FUXA/server

COPY services/fuxa/project.json /opt/rivermark-fuxa/project.json
COPY services/fuxa/line4.svg /opt/rivermark-fuxa/line4.svg
COPY services/fuxa/seed.js /opt/rivermark-fuxa/seed.js
COPY services/fuxa/entrypoint.sh /opt/rivermark-fuxa/entrypoint.sh

RUN chmod 0555 /opt/rivermark-fuxa/entrypoint.sh \
    && chmod 0444 /opt/rivermark-fuxa/project.json \
        /opt/rivermark-fuxa/line4.svg \
        /opt/rivermark-fuxa/seed.js

ENTRYPOINT ["/opt/rivermark-fuxa/entrypoint.sh"]
CMD ["node", "main.js"]
