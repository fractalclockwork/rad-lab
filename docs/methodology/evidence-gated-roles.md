# Evidence-Gated Roles in Agentic Cyber-Physical Systems

## 1. Theoretical Framework of Actuation-in-the-Loop

The paradigm of continuous integration relies on the premise that an automated agent or pipeline possesses complete authority over its environment. In purely virtual domains, software agents may iteratively invent, test, and validate until constraints are satisfied. However, deploying agentic frameworks into cyber-physical systems introduces a severe epistemic and safety boundary. Autonomous agents are fundamentally incapable of verifying real-world physical compliance, electrical continuity, or regulatory licensing.

**The Epistemic Wall**

Allowing an agent to simulate physical compliance by exporting digital confirmation flags bypasses critical physical controls. To maintain system integrity, repositories and automation pipelines must be strictly partitioned by authorization to act, rather than by sequential workflow stages. A generalized framework must enforce that digital steps close autonomously, while physical steps require machine-readable evidence paired with human-readable reporting prior to energization.

In this document, **HWIL** always means **hardware-in-the-loop** (physical DUT or actuator execution under a test harness). The operator role is **human** / **human-in-the-loop**, always spelled out.

## 2. Structural Role Taxonomy

The core mechanism for preventing agentic hallucination of safety limits is the strict segregation of execution roles. Automation may operate freely within theoretical boundaries but is entirely restricted from self-authorizing physical deployment.

| Role | Operational Domain | Agent Permission Level | Verification Mechanism |
| --- | --- | --- | --- |
| **Human** (human-in-the-loop) | Physical environment, regulatory compliance | Zero. Agents may never invent or simulate assent. | Non-forgeable confirmation tokens; physical path attestation. |
| **Actuator automation** | Hardware-in-the-loop (HWIL), mechanical or RF control | Bound by hardcoded limits. Executes only after human assent and prior evidence. | Immutable policy manifests. |
| **Software** | Mathematical modeling, DSP, logical compilation | Complete autonomy. May invent freely. | CI pipelines, unit testing. |
| **Environment** | Containerization, dependency mapping | Autonomy restricted to virtual boundaries. | Build matrices, checksums. |
| **Consumer** | Curriculum, higher labs, downstream analysis | Content only. Must not re-run actuators to unlock itself. | Evidence artifact presence via harness predicates. |
| **Harness** | Unlock predicates and path roots | Read-only observation of system state. No prompts, no energize. | Evidence artifact presence. |

## 3. The Dual-Loop Execution Model

System progression through a physical deployment pipeline is strictly gated by the Dual-Loop Architecture.

**The Autonomous Loop (including SIL)**

- Agents generate theoretical models, perform numerical simulations (simulation-in-the-loop, **SIL**), and compile software binaries.
- Execution occurs entirely offline or within virtualized sandboxes.
- The state output is a machine-readable artifact (e.g., JSON metrics) that serves as proof of mathematical or simulated safety.

**The Physical Loop (HWIL)**

- The pipeline halts execution at the actuation boundary.
- The system generates a human-readable writeup summarizing predicted limits, simulated margins, and the specific physical checklist required.
- The operator (human-in-the-loop) constructs the physical environment, verifies the path and policy claims, and injects a non-forgeable authorization token.
- Actuator automation then runs HWIL sequences within policy ceilings and writes new evidence.

**Mathematical Formalization of the State Transition**

The progression from a virtual simulation state to a physical actuation state requires the logical conjunction of prior state completion, validated evidence, and human assent.

$$ \Phi_{i+1} = \Phi_i \land \mathbb{E}(\Phi_i) \land \mathbb{H}(W_i) $$

$\Phi_i$, current execution state; $\Phi_{i+1}$, subsequent physical execution state; $\mathbb{E}$, verification function for machine-readable evidence; $\mathbb{H}$, Boolean function for human assent given writeup $W_i$; $W_i$, human-readable writeup required for informed judgment.

## 4. Fidelity Ladder: SIL to HWIL

Agentic workflows climb a fidelity ladder. Each rung must emit evidence before the next is allowed.

1. **Component / software simulation (SIL)** — Models, fixtures, and offline DSP; CI-green.
2. **System or matrix modeling** — Idealized multi-element behavior checked against simulated bounds.
3. **Build / layout / toolchain** — Container images, firmware artifacts, or board layouts produced in the environment role.
4. **Physical HWIL bring-up** — Human constructs the path; actuator automation measures under policy; evidence unlocks consumers.

Specialized domains (high-voltage instrumentation, radiating systems, medical devices) use the same assent, policy-manifest, and evidence gates when those labs exist; they are not specified further here.

## 5. Invariant Policy Ceilings

To prevent optimization algorithms from maliciously or accidentally violating physical limits to achieve a passing programmatic condition, constraints must be encoded as read-only invariants.

**Power and Duration Bounding**

Maximum physical limits (e.g., torque, voltage, duty cycle, RF transmit power) must act as fail-closed clamps. The integral of physical output over the duration of the automated test must strictly obey the energy limits defined in the immutable manifest.

$$ \int_{t_0}^{t_1} P(t) \, dt \leq E_{\text{max}} $$

$P(t)$, instantaneous output power of the physical actuator; $t_0$, start time of automation sequence; $t_1$, termination time; $E_{\text{max}}$, absolute maximum allowable energy deposition defined by the system manifest.

**Regulatory Identity Constraints**

- Legal identities, callsigns, or operator IDs must be explicitly injected by the human operator.
- The harness may validate the string format of the identity.
- The system must fault if an agent synthesizes a nominal identity to satisfy a dependency check.

## 6. Embedded Test Harnesses (Same Pattern, Multiple Domains)

Containerized harnesses instantiate the role taxonomy in different operational domains. The permission model does not change.

| Harness instance | Operational domain | Primary function |
| --- | --- | --- |
| **SDR toolset** (e.g. rad-lab) | RF and signal processing | Host-gated HWIL bring-up; containerized telemetry and DSP evaluation |
| **Modular MCU testbed** | Embedded systems | Multi-MCU experimentation and CI against physical boards |
| **HPC regression system** | High-performance computing | Parallel module validation across clusters |

Telemetry and bench control remain actuator or environment concerns; unlock predicates stay in the harness; human assent remains non-forgeable.

## 7. Master Glossary

| Term | Definition | Primary unit / format |
| --- | --- | --- |
| **HWIL** | Hardware-in-the-loop: physical DUT or actuator execution under a test harness after human assent and prior evidence. | Stages, labs, binaries |
| **SIL** | Simulation-in-the-loop / offline simulation rung on the fidelity ladder. | Models, fixtures, CI |
| **Human** / **human-in-the-loop** | Operator role. Always spelled out; never abbreviated as HIL. | Assent tokens, writeups |
| **Actuator automation** | Scripts that manipulate physical hardware, bound by evidence and human assent. | Code modules, binaries |
| **Assent air-gap** | Logical break where automation halts pending non-forgeable human input. | Boolean env flags, interactive YES |
| **Evidence artifact** | Machine-readable proof that a prior SIL or HWIL step completed within parameters. | JSON, XML, JUnit |
| **Fidelity ladder** | Monotonic progression from pure software simulation to physical HWIL. | Hierarchical stages |
| **Policy manifest** | Read-only config of absolute physical maximums that agents cannot override. | YAML, TOML |
| **Writeup** | Human-facing prose summarizing outcomes and physical requirements before assent. | Markdown, PDF |
| **Consumer** | Curriculum or downstream lab unlocked only by evidence, not by re-running actuators. | Lessons, analysis scripts |

**Naming note (rad-lab):** Human assent environment variables are named `HUMAN_LOOPBACK`, `HUMAN_TX_CONFIRM`, and `HUMAN_FIRMWARE`, clearly distinguishing human operator assent from `HWIL` (hardware-in-the-loop) automation (`make hwil`, `RAD_LAB_HWIL_SIM`).
