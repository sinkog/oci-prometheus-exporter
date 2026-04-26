# OCI Monitoring Namespaces

## Provider-side vs agent-side metrics

OCI Monitoring exposes two categories of compute metrics:

| Category | Namespace | Source | Analogy |
|----------|-----------|--------|---------|
| **Provider-side** | `oci_compute_infrastructure_health`, `oci_vcn`, `oci_blockstore` | OCI hypervisor / control plane — measured externally | VMware host metrics, Proxmox node metrics |
| **Agent-side** | `oci_computeagent` | Oracle Cloud Agent running inside the VM | VMware Tools / guest metrics |

For infrastructure observability (SLA monitoring, noisy-neighbour detection, platform health), prefer provider-side namespaces. Agent-side metrics require the Oracle Cloud Agent to be installed and running in each VM.

## Provider-side namespaces

### `oci_compute_infrastructure_health`

Hypervisor-level VM health. Available for all compute instances including OKE worker nodes.

| Metric | Description | Recommended aggregation |
|--------|-------------|------------------------|
| `instance_status` | `0` = healthy, `1` = hardware/software fault | `mean()` |
| `maintenance_status` | `0` = no maintenance, `1` = scheduled/in-progress | `mean()` |

These metrics disappear when an instance is stopped. Use stale cleanup (3-cycle default) to detect termination.

### `oci_vcn`

Virtual NIC metrics from the OCI hypervisor — **not** the OS network stack. Covers all instances including OKE nodes.

| Metric | Description | Recommended aggregation |
|--------|-------------|------------------------|
| `VnicFromNetworkBytes` | Ingress bytes to the VNIC | `sum()` |
| `VnicToNetworkBytes` | Egress bytes from the VNIC | `sum()` |
| `VnicFromNetworkPackets` | Ingress packet count | `sum()` |
| `VnicToNetworkPackets` | Egress packet count | `sum()` |
| `VnicIngressDropsThrottle` | Ingress drops due to rate limiting | `sum()` |
| `VnicEgressDropsThrottle` | Egress drops due to rate limiting | `sum()` |
| `VnicIngressDropsSecurityList` | Ingress drops from security list rules | `sum()` |
| `VnicEgressDropsSecurityList` | Egress drops from security list rules | `sum()` |
| `VnicConntrackUtilPercent` | Connection tracking table utilisation % | `mean()` |
| `VnicConntrackIsFull` | `1` when conntrack table is full | `mean()` |
| `VnicIngressDropsConntrackFull` | Ingress drops due to conntrack exhaustion | `sum()` |
| `VnicEgressDropsConntrackFull` | Egress drops due to conntrack exhaustion | `sum()` |
| `VnicIngressDropsZpr` | Ingress drops from Zero Trust Packet Routing | `sum()` |
| `VnicEgressDropsZpr` | Egress drops from Zero Trust Packet Routing | `sum()` |

Mirror metrics (`VnicFromNetworkMirrorBytes`, etc.) are for VTAP-based traffic mirroring and rarely needed for standard monitoring.

### `oci_blockstore`

Block volume performance as seen by the OCI storage service.

| Metric | Description | Recommended aggregation |
|--------|-------------|------------------------|
| `VolumeReadOps` | Read operations per interval | `sum()` |
| `VolumeWriteOps` | Write operations per interval | `sum()` |
| `VolumeReadThroughput` | Read throughput (bytes) | `mean()` |
| `VolumeWriteThroughput` | Write throughput (bytes) | `mean()` |
| `VolumeThrottledIOs` | I/O operations throttled by OCI | `sum()` |
| `VolumeGuaranteedIOPS` | Provisioned IOPS for the volume | `mean()` |
| `VolumeGuaranteedThroughput` | Provisioned throughput for the volume | `mean()` |
| `VolumeGuaranteedVPUsPerGB` | Volume performance units per GB | `mean()` |

`VolumeThrottledIOs` is the key signal for storage saturation — a non-zero value means the workload exceeds the provisioned performance tier.

**Note:** OCI Block Storage does not expose read/write latency metrics. This is a known gap compared to on-prem storage monitoring.

### `oci_lbaas` — Load Balancer

| Metric | Description |
|--------|-------------|
| `AcceptedConnections` | New connections accepted |
| `ActiveConnections` | Current active connections |
| `ClosedConnections` | Connections closed |
| `HttpRequests` | HTTP request count |
| `BytesReceived` / `BytesSent` | Traffic volume |
| `BackendServers` | Total backend count |
| `UnHealthyBackendServers` | Backends failing health checks |
| `BackendTimeouts` | Backend connection timeouts |
| `ResponseTimeFirstByte` | Time to first byte from backend |
| `AcceptedSSLHandshake` / `FailedSSLHandshake` | TLS handshake stats |
| `PeakBandwidth` | Peak bandwidth usage |

### `oci_nlb` — Network Load Balancer

| Metric | Description |
|--------|-------------|
| `ActiveConnections` / `ActiveConnectionsTCP` / `ActiveConnectionsUDP` | Active connections by protocol |
| `NewConnections` / `NewConnectionsTCP` / `NewConnectionsUDP` | New connection rate |
| `ProcessedBytes` / `ProcessedPackets` | Traffic volume |
| `HealthyBackends` / `UnhealthyBackends` | Backend health counts |
| `HealthyBackendsPerNlb` / `UnhealthyBackendsPerNlb` | Per-NLB backend health |
| `IngressPacketsDroppedBySL` / `EgressPacketsDroppedBySL` | Security list drops |
| `IngressPacketsDroppedByZPR` / `EgressPacketsDroppedByZPR` | ZPR drops |

### `oci_objectstorage`

| Metric | Description |
|--------|-------------|
| `StoredBytes` | Total bytes stored in the bucket |
| `ObjectCount` | Number of objects |
| `AllRequests` | Total request count |
| `GetRequests` / `PutRequests` / `DeleteRequests` / `CopyRequests` / `HeadRequests` / `ListRequests` | Requests by type |
| `ClientErrors` | 4xx error count |
| `FirstByteLatency` | Time to first byte (ms) |
| `TotalRequestLatency` | End-to-end request latency (ms) |
| `EnabledOLM` | Object Lifecycle Management enabled flag |

## Agent-side namespace

### `oci_computeagent`

In-VM metrics collected by Oracle Cloud Agent. Requires the agent installed and running in the guest.

| Metric | Description |
|--------|-------------|
| `CpuUtilization` | vCPU utilisation % |
| `MemoryUtilization` | RAM utilisation % |
| `NetworksBytesIn` / `NetworksBytesOut` | OS-level network throughput |
| `DiskBytesRead` / `DiskBytesWritten` | OS-level disk throughput |

## Known gaps vs on-premises hypervisors

The following metrics are standard in VMware vSphere, Proxmox, and OpenStack Nova but have **no OCI Monitoring equivalent**:

| Metric | On-prem source | OCI status |
|--------|---------------|------------|
| CPU ready / CPU steal time | vSphere, KVM steal | Not exposed. No way to know if vCPUs are waiting for physical cores. |
| Memory balloon / memory swap | vSphere balloon driver, KVM balloon | Not exposed. OCI does not reveal hypervisor memory pressure. |
| Storage I/O latency (ms) | vSphere, Proxmox, Cinder | Not exposed. `oci_blockstore` has IOPS/throughput but no latency metric. |
| Live migration / vMotion events | vSphere vMotion, Nova live migrate | `maintenance_status` changes but there is no migration-specific event or counter. |
| Host hardware (power, thermal, fan) | vSphere, IPMI, iDRAC | Fully opaque — OCI is a public cloud, physical host metrics are not exposed. |
| NUMA topology / CPU pinning | vSphere, libvirt | Not exposed. |

These gaps are inherent to OCI's shared-responsibility model and are unlikely to be filled for standard compute shapes.