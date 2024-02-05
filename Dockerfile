FROM python:3.11.6-slim-bookworm
RUN apt update && apt autoremove -y && apt upgrade -y
RUN apt install -y openssh-server nginx redis-server
RUN ssh-keygen -A
RUN mkdir /run/sshd
# for user-specific sshd_config
RUN mkdir /etc/ssh/sshd_config.d/user.d 
ENV HTTP_HOST=demo.q2k.dev
ENV SECRET_KEY=secretkeyyyyyyyyyyyyyyyyy
COPY nginx.conf /etc/nginx/nginx.conf
RUN mkdir /etc/nginx/sites
COPY sshd_config.conf /etc/ssh/sshd_config
WORKDIR /srv/http-server
COPY . .
RUN pip install -r requirements.txt
RUN python manage.py collectstatic --noinput
CMD nginx && redis-server --daemonize yes && gunicorn -w 5 src.wsgi:application -b 0.0.0.0:8000 --daemon && /usr/sbin/sshd -D

