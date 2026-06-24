# Architecture Lens

Use this reference when DD needs architecture or AWS/system design depth.

For the short cross-skill operating guide on custom HTML, Python `diagrams`,
Graphviz/DOT, Kiro/QW scratch use, and the five-block presentation rule, read:
`docs/ARCH_DESIGN_DIAGRAM_GUIDE.md`.

## Architecture modes

Choose based on availability and user intent:

| Mode | When to use | Output |
|------|-------------|--------|
| Inline SVG (default) | Always available, offline-safe | Embedded in HTML |
| Python `diagrams` library | User asks for "proper AWS diagrams", "AWS icons", or "architecture PNG" | PNG embedded as base64 |
| Mermaid | Only if vendored locally or explicitly requested | Inline or separate |

---

## Python `diagrams` library (best practice for AWS)

When to use: user says "Python diagram", "AWS icons", "proper architecture diagram", or "diagrams.py".

Check availability first:
```bash
python3 -c "import diagrams; print('ok')"
which dot   # graphviz backend
```

If not installed:
```bash
pip install diagrams
# macOS: brew install graphviz
# Ubuntu: sudo apt install graphviz
```

Write diagram source to `scripts/portal/<name>.py` in the repo (version-controlled, reproducible).
Generate PNG, then embed as base64 in HTML:
```bash
python3 scripts/portal/arch-account-boundary.py   # outputs arch-account-boundary.png
python3 scripts/portal/embed_png_base64.py arch-account-boundary.png >> architecture.html
```

Example — AMI Factory account boundary:
```python
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2ImageBuilder, EC2
from diagrams.aws.storage import S3
from diagrams.aws.management import SystemsManagerParameterStore as SSM
from diagrams.aws.security import KMS
from diagrams.aws.devtools import Codebuild

with Diagram("AMI Factory — Account Boundary", filename="arch-account-boundary",
             show=False, direction="LR"):
    with Cluster("DEV Account 672172129528"):
        cb = Codebuild("CodeBuild")
        s3 = S3("Artifacts S3")
        ib = EC2ImageBuilder("Image Builder")
        kms = KMS("KMS Key")
        ec2 = EC2("Ref EC2\n(SOP proof)")
        ssm_dev = SSM("SSM PS\n/ami-factory/dev/...")
        cb >> ib >> ec2
        s3 >> ib
        kms >> ib

    with Cluster("PROD Account 021577063369"):
        ssm_prod = SSM("SSM PS\n/hcr/prod/ami/.../\napproved-latest")

    ib >> Edge(label="promote\n(Amit approval)", style="dashed", color="green") >> ssm_prod
```

---

## Inline SVG pattern library

Use these skeletons when Python `diagrams` is not available.

### Account boundary box

```html
<svg width="860" height="220" viewBox="0 0 860 220">
  <defs>
    <marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L0,6 L8,3 z" fill="#8892a4"/>
    </marker>
  </defs>
  <!-- DEV account -->
  <rect x="10" y="10" width="500" height="200" rx="12"
        fill="rgba(79,142,247,0.05)" stroke="#4f8ef7" stroke-width="1.5" stroke-dasharray="6,3"/>
  <text x="26" y="32" fill="#4f8ef7" font-size="12" font-weight="700">DEV Account — 672172129528</text>
  <!-- PROD account -->
  <rect x="540" y="10" width="300" height="200" rx="12"
        fill="rgba(62,207,142,0.04)" stroke="#3ecf8e" stroke-width="1.5" stroke-dasharray="6,3"/>
  <text x="556" y="32" fill="#3ecf8e" font-size="12" font-weight="700">PROD Account — 021577063369</text>
  <!-- cross-account arrow -->
  <line x1="510" y1="110" x2="540" y2="110" stroke="#3ecf8e" stroke-width="1.5"
        stroke-dasharray="6,3" marker-end="url(#arr)"/>
  <text x="515" y="105" fill="#3ecf8e" font-size="9">promote</text>
  <!-- Add service boxes inside each cluster as needed -->
</svg>
```

### E2E swimlane skeleton (5 actors)

```html
<svg width="900" height="380" viewBox="0 0 900 380">
  <!-- Lane backgrounds (alternating) -->
  <rect x="0" y="40"  width="900" height="60" fill="rgba(255,255,255,0.02)"/>
  <rect x="0" y="100" width="900" height="60" fill="none"/>
  <rect x="0" y="160" width="900" height="60" fill="rgba(255,255,255,0.02)"/>
  <rect x="0" y="220" width="900" height="60" fill="none"/>
  <rect x="0" y="280" width="900" height="60" fill="rgba(255,255,255,0.02)"/>
  <!-- Actor labels (left column) -->
  <rect x="0" y="0" width="130" height="380" fill="rgba(79,142,247,0.04)"/>
  <text x="65" y="75"  fill="#8892a4" font-size="11" text-anchor="middle">Actor 1</text>
  <text x="65" y="135" fill="#8892a4" font-size="11" text-anchor="middle">Actor 2</text>
  <text x="65" y="195" fill="#8892a4" font-size="11" text-anchor="middle">Actor 3</text>
  <text x="65" y="255" fill="#8892a4" font-size="11" text-anchor="middle">Actor 4</text>
  <text x="65" y="315" fill="#8892a4" font-size="11" text-anchor="middle">Actor 5</text>
  <line x1="130" y1="0" x2="130" y2="380" stroke="#2a2d3e" stroke-width="1"/>
  <!-- Add step boxes and arrows inside lanes as needed -->
</svg>
```

### AMI lineage fork

```html
<svg width="700" height="110" viewBox="0 0 700 110">
  <defs>
    <marker id="la" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L0,6 L8,3 z" fill="#8892a4"/>
    </marker>
  </defs>
  <!-- Source -->
  <rect x="10" y="30" width="130" height="50" rx="8" fill="#1e2130" stroke="#f5a623" stroke-width="1.5"/>
  <text x="75" y="52" fill="#f5a623" font-size="11" text-anchor="middle" font-weight="700">GCC Golden AMI</text>
  <text x="75" y="72" fill="#8892a4" font-size="10" text-anchor="middle">ami-xxx (parent)</text>
  <line x1="140" y1="55" x2="180" y2="55" stroke="#8892a4" stroke-width="1.5" marker-end="url(#la)"/>
  <!-- Middle -->
  <rect x="180" y="20" width="140" height="70" rx="8" fill="#1e2130" stroke="#4f8ef7" stroke-width="1.5"/>
  <text x="250" y="48" fill="#4f8ef7" font-size="11" text-anchor="middle" font-weight="700">CloudOS-Core</text>
  <text x="250" y="62" fill="#8892a4" font-size="10" text-anchor="middle">recipe 0.1.12</text>
  <text x="250" y="78" fill="#3ecf8e" font-size="9" text-anchor="middle">ami-06c721cbbcfb8f81e</text>
  <!-- Fork arrows -->
  <line x1="320" y1="45" x2="360" y2="28" stroke="#8892a4" stroke-width="1.5" marker-end="url(#la)"/>
  <line x1="320" y1="65" x2="360" y2="82" stroke="#8892a4" stroke-width="1.5" marker-end="url(#la)"/>
  <!-- Child 1 -->
  <rect x="360" y="10" width="140" height="40" rx="8" fill="#1e2130" stroke="#7c5cbf" stroke-width="1.5"/>
  <text x="430" y="28" fill="#7c5cbf" font-size="11" text-anchor="middle" font-weight="700">Child Lane A</text>
  <text x="430" y="44" fill="#3ecf8e" font-size="9" text-anchor="middle">ami-yyy</text>
  <!-- Child 2 -->
  <rect x="360" y="68" width="140" height="36" rx="8" fill="#1e2130" stroke="#3ecf8e" stroke-width="1.5"/>
  <text x="430" y="84" fill="#3ecf8e" font-size="11" text-anchor="middle" font-weight="700">Child Lane B</text>
  <text x="430" y="98" fill="#3ecf8e" font-size="9" text-anchor="middle">ami-zzz</text>
</svg>
```

---

## Architecture components

- Environment boundary board: DEV, TEST, PROD, shared services, external systems.
- Resource lineage: source → transformation → artifact → consumer.
- Security overlay: identity, encryption, network, logging, secrets, compliance.
- Lifecycle timeline: build, test, promote, deploy, operate, rollback, cleanup.
- Failure-mode bank: permissions, region, sharing, KMS, SSM, TTL, rollback.
- Validation matrix: check, evidence, confidence, owner.

---

## AMI Factory recipe (canonical steps)

1. Source AMI selected (GCC Golden / parent).
2. CodeBuild triggers Terraform + Image Builder pipeline.
3. Build EC2 launched (private subnet, no public IP).
4. Component YAML steps run: install packages, configure agents, harden OS.
5. Custom workflow remounts `/tmp exec` if CIS `/tmp noexec` hardening is present.
6. AMI created (AVAILABLE), snapshots encrypted with DEV KMS key.
7. KMS grant issued to PROD account for cross-account launch proof.
8. Validation EC2 launched (SOP reference, DEV account, no public IP).
9. Inspector CIS scan run — accept only COMPLETED + totalChecks > 0.
10. GCC agent check via SSM Run Document.
11. SSM DEV approved-ami pointer updated.
12. PROD canonical SSM promoted (Amit approval required).
13. KMS grant revoked, validation EC2 terminated after TTL.
