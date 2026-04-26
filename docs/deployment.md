# Deployment Guide

## Kubernetes / OKE (recommended)

The `k8s/` directory contains production-ready manifests. The default setup uses InstancePrincipal auth — no API keys or secrets in the cluster.

### Prerequisites

- Kubernetes cluster (OKE or any cluster with OCI credentials)
- Prometheus Operator / kube-prometheus-stack (for ServiceMonitor)
- `monitoring` namespace exists: `kubectl create namespace monitoring`

### 1. OCI IAM — allow the node to read metrics

Create a Dynamic Group that matches your OKE worker nodes:

```
All {instance.compartment.id = 'ocid1.compartment.oc1..example', tag.oke-cluster-id.value = 'your-cluster-id'}
```

Then attach a policy:

```
Allow dynamic-group <oke-nodes-dg> to read metrics in compartment <your-compartment>
```

Or tenancy-wide:

```
Allow dynamic-group <oke-nodes-dg> to read metrics in tenancy
```

### 2. Customize the config

Edit `k8s/configmap.yaml` — replace the placeholder OCID and region:

```yaml
compartmentIds:
  - "ocid1.tenancy.oc1..your-real-ocid"
region: "eu-frankfurt-2"
```

For OC19 (EU Sovereign Cloud), uncomment the `telemetryEndpoint` line:

```yaml
telemetryEndpoint: "https://telemetry.eu-frankfurt-2.oraclecloud.eu"
```

### 3. Set the image

Edit `k8s/deployment.yaml` — replace the image placeholder:

```yaml
image: <your-registry>/oci-prometheus-exporter:latest
```

Or use Kustomize image override in `k8s/kustomization.yaml`:

```yaml
images:
  - name: <your-registry>/oci-prometheus-exporter
    newTag: "0.1.0"
```

### 4. Apply

```bash
kubectl apply -k k8s/
```

### 5. Validate before deploying

Run the validator from inside the cluster (or locally with ApiKey) against the real OCI API:

```bash
kubectl run oci-validate --rm -it --restart=Never \
  --image=<your-registry>/oci-prometheus-exporter:latest \
  --overrides='{"spec":{"serviceAccountName":"oci-exporter"}}' \
  -- oci-exporter --config /etc/oci-exporter/config.yaml --validate
```

Or locally:

```bash
oci-exporter --config k8s/config.yaml --validate
```

### 6. Verify

```bash
# Pod is running
kubectl get pod -n monitoring -l app=oci-exporter

# Logs
kubectl logs -n monitoring -l app=oci-exporter

# Metrics endpoint
kubectl port-forward -n monitoring svc/oci-exporter 9090:9090
curl http://localhost:9090/metrics | grep oci_
```

### ServiceMonitor label

The `servicemonitor.yaml` has `release: prometheus` — the default label for kube-prometheus-stack. If your Prometheus Operator uses a different `serviceMonitorSelector`, update the label:

```yaml
kubectl get prometheus -n monitoring -o jsonpath='{.items[0].spec.serviceMonitorSelector}'
```

---

## ApiKey auth (non-OKE / local k8s)

Use `k8s/deployment-apikey.yaml` instead of `deployment.yaml`, and apply the API key secret first.

### 1. Create the secret

```bash
kubectl create secret generic oci-apikey \
  --namespace monitoring \
  --from-file=config=$HOME/.oci/config \
  --from-file=oci_api_key.pem=$HOME/.oci/oci_api_key.pem
```

The OCI config file must reference the key by its in-pod path:

```ini
[DEFAULT]
user=ocid1.user.oc1..example
fingerprint=xx:xx:xx:...
tenancy=ocid1.tenancy.oc1..example
region=eu-frankfurt-2
key_file=/home/exporter/.oci/oci_api_key.pem
```

The exporter container runs as UID 10001 (`exporter`), home directory `/home/exporter`.

### 2. Apply

```bash
kubectl apply -n monitoring -f k8s/secret-apikey.yaml   # or use kubectl create above
kubectl apply -k k8s/
# Override the deployment:
kubectl apply -n monitoring -f k8s/deployment-apikey.yaml
```

---

## Docker (standalone)

```bash
docker run --rm \
  -v /path/to/config.yaml:/etc/oci-exporter/config.yaml:ro \
  -p 9090:9090 \
  <your-registry>/oci-prometheus-exporter:latest
```

With ApiKey:

```bash
docker run --rm \
  -v /path/to/config.yaml:/etc/oci-exporter/config.yaml:ro \
  -v $HOME/.oci:/home/exporter/.oci:ro \
  -p 9090:9090 \
  <your-registry>/oci-prometheus-exporter:latest
```