nginx:
    pkg:
        - installed
        - name: nginx

    service:
        - running
        - watch:
            - pkg: nginx
            - file: /etc/nginx/nginx.conf

/etc/nginx/nginx.conf:
    file.managed:
        - source: salt://webserver/nginx.conf
        - user: root
        - group: root
        - mode: 644
        - template: jinja
