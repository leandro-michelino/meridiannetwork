# Deployment Strategy

Meridian is currently targeting a small OCI Compute VM. This is the recommended path for the first deployable milestone because it is the simplest fit for a dashboard, Nginx, a long-running FastAPI service, local logs, and future scheduler/cache components.

## Selected Path - OCI Compute VM

Best for:

- First working deployment.
- Demos.
- Long-running FastAPI backend.
- Nginx reverse proxy.
- Local operational troubleshooting.
- Future Redis or background scheduler on the same host.

Required OCI resources:

- Compartment.
- VCN.
- Public or private subnet.
- Internet Gateway for public ingress, or NAT Gateway/Bastion/private access for private deployments.
- Route table.
- Security List or NSGs.
- Compute instance.
- Boot volume.
- Public IP if exposed directly.
- Dynamic group and IAM policy for instance principal access.

Optional OCI resources:

- Load Balancer.
- DNS zone and record.
- TLS certificate.
- OCI Logging.
- OCI Monitoring alarms.
- OCI Vault.
- Object Storage backend for Terraform state.

## Why Not Serverless First

Function-based serverless would force the main API into a different execution model before the product shape is stable. Meridian currently needs a normal web API, built dashboard hosting, future background polling, and likely cache/stateful operational behavior.

## Future Revisit - OCI Container Instances

If the application is containerized later, OCI Container Instances can be evaluated as a serverless-container target.

Potential shape:

- Static frontend in Object Storage or served by the same container.
- FastAPI container in Container Instances.
- API Gateway or Load Balancer in front.
- OCI Logging for container logs.

Required OCI resources:

- Compartment.
- VCN and subnet.
- Container image in OCI Container Registry or another reachable registry.
- Container Instance.
- IAM policy for Container Instances and image pulls.
- API Gateway or Load Balancer if a stable public entry point is needed.
- Dynamic group and IAM policy for resource principal access, if supported by the selected runtime pattern.

## Future Revisit - OCI Functions

OCI Functions is not the recommended primary runtime for the main dashboard API. It may be useful later for:

- Small event-driven collectors.
- Scheduled jobs.
- Lightweight API operations.
- Specific tasks such as refreshing inventory snapshots or exporting reports.

Tradeoffs:

- The current FastAPI service would need adaptation into function handlers.
- Long-running requests and large responses are not a good fit.
- A dashboard API with many endpoints is usually easier to operate as a containerized service.

Recommended use inside Meridian:

- Use Functions later for asynchronous collectors, scheduled refreshes, and notifications.
- Keep the main API as a VM or container service unless the API surface is intentionally redesigned around functions.

## Future Revisit - OKE

Best for:

- Production environments that already run Kubernetes.
- Multiple services.
- Horizontal scaling.
- Separate frontend, backend, cache, and worker deployments.

Tradeoffs:

- More moving parts.
- Higher operational overhead than the current stage needs.

## Current Recommendation

Use the small VM path now. Revisit Container Instances only after the backend and frontend are containerized and stable. Use OCI Functions only for background jobs, not as the first main API runtime.
