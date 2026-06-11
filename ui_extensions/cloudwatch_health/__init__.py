"""CloudWatch AWS Health Check dashboard XUI.

Adds an admin dashboard card that mirrors the Aerocloud monitoring dashboard
(CPU, memory, disk, status checks, network, EBS, RDS) by pulling CloudWatch
metrics for the EC2 servers the signed-in user is allowed to see in CloudBolt.

See README.md for setup and ../../infosys/ROADMAP.md for the full design.
"""
