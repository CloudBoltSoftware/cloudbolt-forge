#!/usr/bin/env python
import pika
import sys

from common.methods import set_progress
from jobs.models import Job

def run(job, logger=None, **kwargs):
    status = job.status
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='<rabbitmq ip>'))
    for server in job.server_set.all():
        hostname = server.hostname
	mem_size = server.mem_size
	cpu = server.cpu_cnt
        channel = connection.channel()
        channel.queue_declare(queue='<queuename>', durable=True)
        job.set_progress("Sending Message that %s resources changed..." % server.hostname)
        channel.basic_publish(exchange='<exchangename>',
                      routing_key='<routingkey>',
                      body="Server:{}\nMem:{}\nCpu:{}\nStatus:{}".format(hostname, mem_size, cpu, status),
                      properties=pika.BasicProperties(
                         delivery_mode = 2, # make message persistent
                      ))
        job.set_progress("Message Sent to Queue")
        connection.close()
    return '', '', ''

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <Job ID>\n" % sys.argv[0])
        sys.exit(2)

    job_id = sys.argv[1]
    run(Job.objects.get(id=job_id))
