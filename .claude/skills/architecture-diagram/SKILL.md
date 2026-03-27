---
name: architecture-diagram
description: Create or update AWS architecture diagrams using diagram-as-code (awsdac). Use when the user asks to create, modify, or regenerate an architecture diagram.
user-invocable: true
argument-hint: "[describe the system or changes you want]"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Agent
effort: high
---

# Architecture Diagram Generator

You are an expert at creating clear, well-structured AWS architecture diagrams using the `awsdac` (diagram-as-code) CLI tool. You produce YAML definitions that render into professional PNG diagrams.

## Your Task

Create or update an architecture diagram based on: **$ARGUMENTS**

If no arguments are provided, analyze the codebase to auto-generate an architecture diagram.

## Process

### Step 1: Understand the System

- If updating an existing diagram, read `architecture-diagram.yaml` first
- If creating from scratch, explore the codebase to identify:
  - Services, APIs, and entry points
  - Databases, queues, and storage
  - External integrations
  - Data flow between components
  - Cloud resources (AWS services)

### Step 2: Design the Diagram Layout

- **Direction**: Use `horizontal` (left-to-right) for request flows, `vertical` (top-to-bottom) for layered architectures
- **Grouping**: Use Cloud/Region/Stack containers to logically group related components
- **Columns/Rows**: Use `HorizontalStack` and `VerticalStack` to arrange items in rows or columns

### Step 3: Write the YAML

Generate a valid `awsdac` YAML file. Follow this structure:

```yaml
Diagram:
  DefinitionFiles:
    - Type: URL
      Url: "https://raw.githubusercontent.com/awslabs/diagram-as-code/main/definitions/definition-for-aws-icons-light.yaml"

  Resources:
    Canvas:
      Type: AWS::Diagram::Canvas
      Direction: horizontal   # or vertical
      Children:
        - ComponentA
        - ComponentB

    ComponentA:
      Type: AWS::Diagram::Resource
      Preset: "Amazon SageMaker AI"    # Choose appropriate icon
      Title: "My Component"

  Links:
    - Source: ComponentA
      SourcePosition: E
      Target: ComponentB
      TargetPosition: W
      TargetArrowHead:
        Type: Open
```

### Step 4: Render the Diagram

```bash
awsdac architecture-diagram.yaml -o architecture-diagram.png -f
```

Then read the generated PNG to verify it looks correct.

## YAML Reference

### Container Types

| Type | Use For |
|------|---------|
| `AWS::Diagram::Canvas` | Root container (required) |
| `AWS::Diagram::Cloud` | AWS Cloud boundary. Use `Preset: AWSCloudNoLogo` |
| `AWS::Region` | AWS Region grouping (e.g., us-east-1) |
| `AWS::Diagram::VerticalStack` | Stack children top-to-bottom |
| `AWS::Diagram::HorizontalStack` | Stack children left-to-right |
| `AWS::Diagram::Resource` | Individual resource with icon |

### Direction & Layout

- `Direction: horizontal` — left-to-right flow
- `Direction: vertical` — top-to-bottom flow
- `Align: center` — center-align children
- Use `Children: [...]` to nest resources inside containers

### Link Positions

Use compass positions for source/target attachment points:
`N`, `NNE`, `NE`, `ENE`, `E`, `ESE`, `SE`, `SSE`, `S`, `SSW`, `SW`, `WSW`, `W`, `WNW`, `NW`, `NNW`

### Link Styles

```yaml
Links:
  - Source: A
    SourcePosition: E
    Target: B
    TargetPosition: W
    TargetArrowHead:
      Type: Open          # Arrow type
    LineStyle: dashed      # Optional: solid (default) or dashed
```

### Icon Selection Guide — Presets

Choose icons based on component role. Use distinct icons for different categories so the diagram is easy to read at a glance.

#### AI Agents & Orchestrators
| Preset | Best For |
|--------|----------|
| `"Amazon SageMaker AI"` | AI agents, orchestrators, ML-powered components |
| `"Amazon Bedrock"` | Foundation models, LLM inference |
| `"Amazon Q"` | AI assistants, Q-based features |
| `"Amazon Nova"` | Nova model components |

#### Tools & External Services
| Preset | Best For |
|--------|----------|
| `"AWS Tools and SDKs"` | Generic tools, utilities, SDK integrations |
| `"Amazon API Gateway"` | External APIs, REST endpoints |
| `"Toolkit"` | Tool collections, helper utilities |
| `"Gear"` | Configuration, processing components |
| `"Generic application"` | Generic external applications |

#### Compute & Containers
| Preset | Best For |
|--------|----------|
| `"AWS Lambda"` | Serverless functions |
| `"Amazon Elastic Container Service (Amazon ECS)"` | Container services |
| `"AWS Fargate"` | Serverless containers |
| `"AWS Step Functions"` | Workflow orchestration, state machines |
| `"Amazon Elastic Compute Cloud (Amazon EC2)"` | Virtual machines |

#### Networking & Routing
| Preset | Best For |
|--------|----------|
| `"Elastic Load Balancing"` | Load balancers |
| `"Amazon CloudFront"` | CDN, edge distribution |
| `"Amazon Route 53"` | DNS routing |
| `"Amazon VPC Lattice"` | Service-to-service networking |

#### Storage & Databases
| Preset | Best For |
|--------|----------|
| `"Amazon Simple Storage Service (Amazon S3)"` | Object storage |
| `"Amazon DynamoDB"` | NoSQL database |
| `"Amazon Relational Database Service (Amazon RDS)"` | SQL databases |
| `"Amazon ElastiCache"` | In-memory caching |
| `"Amazon Aurora"` | Aurora database |

#### Security & Identity
| Preset | Best For |
|--------|----------|
| `"AWS Identity and Access Management (IAM)"` | IAM roles, policies |
| `"AWS Secrets Manager"` | Secrets, credentials |
| `"AWS Certificate Manager (ACM)"` | TLS certificates |
| `"AWS WAF"` | Web application firewall |

#### Monitoring & Observability
| Preset | Best For |
|--------|----------|
| `"Amazon CloudWatch"` | Logging, monitoring, metrics |
| `"AWS X-Ray"` | Distributed tracing |
| `"AWS CloudTrail"` | Audit logging |

#### Messaging & Integration
| Preset | Best For |
|--------|----------|
| `"Amazon Simple Queue Service (Amazon SQS)"` | Message queues |
| `"Amazon Simple Notification Service (Amazon SNS)"` | Pub/sub notifications |
| `"Amazon EventBridge"` | Event bus, event routing |
| `"Amazon Kinesis"` | Real-time data streaming |

#### CI/CD & Developer Tools
| Preset | Best For |
|--------|----------|
| `"Amazon Elastic Container Registry (Amazon ECR)"` | Container image registry |
| `"AWS CodePipeline"` | CI/CD pipelines |
| `"AWS CodeBuild"` | Build service |

#### Users & Clients
| Preset | Best For |
|--------|----------|
| `User` | End user / person |
| `"Client"` | Client application |
| `"Mobile client"` | Mobile app |
| `"Developer"` | Developer persona |

## Design Guidelines

1. **Left-to-right flow** for request/data pipelines (User -> Client -> Backend -> Tools)
2. **Top-to-bottom flow** for layered architectures (Frontend -> API -> Services -> Data)
3. **Use distinct icon categories** so the diagram is scannable:
   - `"Amazon SageMaker AI"` for AI agents/orchestrators
   - `"AWS Tools and SDKs"` or `"Toolkit"` for tools
   - `"Amazon Bedrock"` for foundation models
   - `"AWS Step Functions"` for workflow routers
4. **Group related components** inside VerticalStack/HorizontalStack with a Title
5. **Use dashed lines** for infrastructure/config connections (IAM, logging, ECR)
6. **Use solid lines** for data/request flow
7. **Keep titles concise** — use `\n` for multi-line labels
8. **Validate** by rendering and visually inspecting the PNG output

## Output

1. Save the YAML to `architecture-diagram.yaml`
2. Run `awsdac architecture-diagram.yaml -o architecture-diagram.png -f` to render
3. Read and display the generated PNG to the user for verification
4. Briefly describe the diagram layout and key components
