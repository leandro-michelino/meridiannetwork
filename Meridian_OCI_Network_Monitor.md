# Meridian - OCI Network Monitor
> Unified OCI Network Observability Dashboard  
> Versão: 1.2 | Status: In Design  
> Autor: Leandro | Data: Maio 2026

---

## 1. Visão Geral

### Problema
As ferramentas de observabilidade de rede do OCI estão fragmentadas em múltiplas consolas:
- Network Command Center (Network Visualizer, Path Analyzer)
- Metrics Explorer
- Logging Analytics
- OCI Console (VPN, FastConnect, DRG)
- Alarms & Notifications

Um operador precisa de navegar entre 4 a 6 ecrãs diferentes para ter uma visão completa da rede.

### Solução
**Meridian** - um dashboard web unificado e self-hosted que agrega todas as métricas, logs e estados de rede do OCI num único ecrã, com suporte a múltiplos compartimentos e regiões.

### Casos de uso principais
- Operações diárias de rede (NOC view)
- Pre-sales / demos para clientes
- Monitorização de ambientes DR (validação de readiness)
- Troubleshooting acelerado de conectividade

---

## 2. Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────┐
│                  OCI Tenancy                        │
│  ┌────────────┐  ┌───────────┐  ┌────────────────┐  │
│  │ Monitoring │  │  Logging  │  │  VCN / Network │  │
│  │   Service  │  │ Analytics │  │  Command Center│  │
│  └─────┬──────┘  └─────┬─────┘  └───────┬────────┘  │
└────────┼───────────────┼────────────────┼────────────┘
         │               │                │
         └───────────────┼────────────────┘
                         │ OCI SDK / REST APIs
                         ▼
              ┌──────────────────────┐
              │   Backend (Python)   │
              │  FastAPI + Scheduler │
              │  OCI SDK calls       │
              └──────────┬───────────┘
                         │ JSON REST
                         ▼
              ┌──────────────────────┐
              │  Frontend (React)    │
              │  Dashboard UI        │
              │  Charts, Topology    │
              └──────────────────────┘
```

### Componentes
| Componente | Tecnologia | Função |
|---|---|---|
| Backend API | Python + FastAPI | Agrega dados das OCI APIs |
| Scheduler | APScheduler ou Celery | Polling periódico de métricas |
| Cache | Redis (opcional) | Reduz chamadas à API OCI |
| Frontend | React + Recharts | UI do dashboard |
| Auth | OCI Instance Principal ou API Key | Autenticação com OCI |
| Deploy | OCI Compute (VM) ou Container (OKE) | Self-hosted |

---

## 3. Módulos do Dashboard

### 3.1 VCN Overview
- Lista de VCNs por compartimento e região
- CIDR, status, número de subnets
- Gateways associados (IGW, NAT, SGW, LPG, DRG)

### 3.2 Gateway Status Panel
Monitoriza em tempo real:
- **Internet Gateway** - packets in/out, errors
- **NAT Gateway** - connections, dropped packets
- **Service Gateway** - traffic by service
- **DRG** - estado de attachments, rotas propagadas
- **FastConnect** - estado do circuit (UP/DOWN), bandwidth utilization
- **VPN Site-to-Site** - estado dos tunnels, packets in/out

### 3.3 VCN Flow Logs Viewer
- Tráfego aceite vs rejeitado por subnet
- Top 10 IPs de origem e destino
- Gráfico de evolução temporal de fluxos
- Filtros por protocolo, porta, action (ACCEPT/REJECT)

### 3.4 Network Alarms Center
- Alarmes ativos de rede agregados de todas as regiões
- Severidade, recurso afetado, tempo decorrido
- Link direto para o recurso na OCI Console

### 3.5 Inter-Region Latency
- Mapa de latência entre regiões OCI configuradas
- Histórico de 24h / 7 dias
- Alertas automáticos quando latência excede threshold

### 3.6 VNICs & Compute Network - Top Consumers

Painel dedicado a identificar quais instâncias estão a consumir mais largura de banda de rede - a pergunta mais frequente em operações que hoje obriga a navegar instância a instância no OCI Metrics Explorer.

**Vista principal - Top Consumers:**
- Tabela ranqueada de instâncias por consumo de rede (bytes in + out combinados)
- Colunas: rank, nome da instância, shape, compartimento, região, bytes in, bytes out, total, drops
- Período configurável: última 1h / 6h / 24h / 7 dias
- Filtros: por compartimento, região, shape, VCN
- Ordenação por qualquer coluna
- Atualização automática a cada refresh do dashboard

**Métricas por instância (via VNIC):**
- `VnicFromNetworkBytes` - bytes recebidos (ingress)
- `VnicToNetworkBytes` - bytes enviados (egress)
- `VnicFromNetworkPackets` - pacotes recebidos
- `VnicToNetworkPackets` - pacotes enviados
- `VnicIngressDrops` - pacotes descartados na entrada
- `VnicEgressDrops` - pacotes descartados na saída
- Taxa de drops (%) = drops / total packets - alerta automático quando > 0.5%

**Visualizações:**
- Barra horizontal de bandwidth por instância (top 10)
- Sparkline de evolução nas últimas 24h por instância
- Heatmap de consumo por compartimento (opcional, view secundária)
- Badge de anomalia quando uma instância ultrapassa 2x a sua média histórica

**Detalhes por instância (drill-down):**
- Click na instância abre painel lateral com:
  - Gráfico de linha in/out nas últimas 24h
  - VNICs associadas (instâncias multi-VNIC)
  - Security Lists e NSGs aplicados
  - Link direto para a instância na OCI Console
  - Botão "Explain with AI" - GenAI analisa o padrão de tráfego e sugere se é normal ou anómalo

**Alertas automáticos:**
- Instância entra no top 3 repentinamente (spike detection)
- Taxa de drops > 0.5% por mais de 5 minutos
- Egress de uma instância excede threshold configurável ($/h estimado)

**Endpoints:**
- `GET /api/vnics/top-consumers?period=24h&limit=20&compartment=` - ranking de instâncias
- `GET /api/vnics/instance/{instance_id}/metrics?period=` - métricas detalhadas por instância
- `GET /api/vnics/anomalies` - instâncias com comportamento anómalo detetado

### 3.7 DR Readiness Panel (bonus)
- Estado das rotas de failover
- Validação de regras de Security Lists/NSGs entre regiões
- Status de replicação (se aplicável)

### 3.8 Seletor de Regiões - Especificação de UI

#### Comportamento
- **Home Region** - sempre fixada no lado esquerdo do topbar, não removível
  - Badge laranja com label "home" integrado na pill
  - Indicador visual (dot laranja) para distinguir das demais
  - Corresponde à região principal do tenancy OCI
- **Regiões adicionais** - adicionadas pelo utilizador, aparecem à direita da Home Region, separadas por divisor vertical
  - Cada pill tem botão "✕" para remover
  - A remoção não afeta a Home Region
- **Botão "+"** - abre dropdown para adicionar regiões
  - Label: "adicionar região" com ícone de mais
  - Borda tracejada para distinguir das pills ativas
- **Dropdown de seleção**
  - Campo de pesquisa/filtro por nome ou geo
  - Lista com todas as regiões OCI disponíveis (19 regiões suportadas)
  - Cada item mostra: region ID + geo (Europe, Africa, Asia Pacific, etc.)
  - Regiões já adicionadas mostram checkmark e ficam desativadas (não clicáveis)
  - Fecha automaticamente ao clicar fora
- **Persistência** - lista de regiões ativas guardada em localStorage (sessão)

#### Regiões OCI suportadas (v1)
| Region ID | Geo |
|---|---|
| eu-frankfurt-1 | Europe (Home padrão) |
| eu-amsterdam-1 | Europe |
| eu-london-1 | Europe |
| eu-paris-1 | Europe |
| eu-milan-1 | Europe |
| eu-stockholm-1 | Europe |
| eu-madrid-1 | Europe |
| us-ashburn-1 | North America |
| us-phoenix-1 | North America |
| us-chicago-1 | North America |
| ca-toronto-1 | North America |
| af-johannesburg-1 | Africa |
| me-dubai-1 | Middle East |
| me-jeddah-1 | Middle East |
| ap-tokyo-1 | Asia Pacific |
| ap-singapore-1 | Asia Pacific |
| ap-sydney-1 | Asia Pacific |
| ap-mumbai-1 | Asia Pacific |
| sa-saopaulo-1 | South America |
| sa-vinhedo-1 | South America |

#### Impacto no backend
- Cada região selecionada gera chamadas paralelas às OCI APIs (asyncio)
- O endpoint `/api/vcns` aceita parâmetro `regions=fra,ams,jnb` (lista separada por vírgula)
- KPIs do dashboard agregam dados de todas as regiões ativas simultaneamente

---

### 3.9 Compartment Switcher

- Seletor hierárquico de compartimentos em tree-view (pai > filho > neto)
- Multi-seleção: o utilizador ativa/desativa compartimentos individualmente
- "Selecionar todos" e "limpar seleção" como atalhos
- Compartimentos selecionados persistem em localStorage
- Todos os painéis do dashboard filtram dados pelos compartimentos ativos
- Badge no topbar indica quantos compartimentos estão ativos (ex: "4 compartments")
- Endpoint backend: `GET /api/compartments?tenancy_id=` retorna árvore de compartimentos

### 3.10 Security Posture Panel

Análise de exposição de rede sem depender do OCI Cloud Guard:

- Varredura de todas as Security Lists e NSGs ativos nas regiões/compartimentos selecionados
- Deteção de regras de alto risco:
  - Porta 22 (SSH) aberta para 0.0.0.0/0
  - Porta 3389 (RDP) aberta para 0.0.0.0/0
  - Protocolo ALL aberto para 0.0.0.0/0
  - Ranges CIDR excessivamente permissivos (/8, /16)
- Score de risco por VCN (Low / Medium / High / Critical)
- Lista de regras problemáticas com link direto para edição na OCI Console
- Historial de alterações (via OCI Audit API) para auditoria
- Endpoints:
  - `GET /api/security/posture` - score geral
  - `GET /api/security/risky-rules` - lista de regras de risco

### 3.11 OKE Network Health

Monitorização de conectividade específica para clusters Kubernetes no OCI:

- Estado dos node pools: IP allocation, subnet disponibilidade
- Status do CNI (Flannel / OCI VCN-Native CNI)
- Load Balancers provisionados por Services do tipo LoadBalancer
- Estado dos Ingress Controllers (NGINX, OCI Native Ingress)
- Conectividade API Server (endpoint público vs privado)
- Bandwidth in/out por node pool (via VNIC metrics)
- Alerta de esgotamento de IPs na subnet do node pool
- Endpoints:
  - `GET /api/oke/clusters` - lista de clusters por região
  - `GET /api/oke/network-health?cluster_id=` - health por cluster

### 3.12 Cost-Aware Egress

Correlação de tráfego de saída com estimativa de custo em tempo real:

- Egress bytes por IGW e NAT Gateway (últimas 1h / 24h / 7 dias)
- Custo estimado calculado com OCI price list (egress = $0.0085/GB para regiões standard)
- Top 5 instâncias por volume de egress
- Projeção de custo mensal baseada na média atual
- Alerta configurável quando custo projetado ultrapassa threshold definido pelo utilizador
- Comparação custo-egress entre regiões ativas
- Endpoints:
  - `GET /api/cost/egress?region=&period=` - custo estimado por período
  - `GET /api/cost/top-consumers` - top instâncias por egress

### 3.13 Change Feed (Audit Log)

Registo de alterações recentes na topologia e configuração de rede via OCI Audit API:

- Feed cronológico de eventos de rede (últimas 24h por padrão)
- Tipos de eventos monitorizados:
  - Criação/eliminação de VCN, subnet, gateway
  - Alteração de Security List ou NSG
  - Modificação de Route Table
  - Attach/detach de DRG
  - Criação/eliminação de VPN ou FastConnect
- Filtros por: tipo de evento, compartimento, utilizador responsável
- Integração com IAM para mostrar o utilizador/service que fez a alteração
- Endpoint: `GET /api/audit/network-changes?hours=24&compartment=`

### 3.14 Healthcheck Sintético

Validação ativa de conectividade end-to-end entre regiões e VCNs:

- Pings periódicos configuráveis (intervalo: 30s / 1min / 5min)
- Targets configuráveis: IP privado, IP público, hostname
- Métricas por check: latência média, packet loss %, uptime %
- Estado visual por par origem-destino (verde/amarelo/vermelho)
- Histórico de disponibilidade nas últimas 24h por healthcheck
- Modo DR: conjunto pré-definido de checks para validar readiness de failover
- Alertas automáticos quando check falha N vezes consecutivas
- Endpoints:
  - `GET /api/healthchecks` - lista de checks configurados
  - `POST /api/healthchecks` - criar novo check
  - `GET /api/healthchecks/{id}/history` - histórico de resultados

### 3.15 Modo NOC (Full-Screen Operations View)

Layout dedicado para ecrãs de sala de operações:

- Ativação por botão no topbar ou URL `/noc`
- Layout full-screen sem sidebar, otimizado para TV/monitor grande
- Fonte aumentada, contraste elevado, elementos essenciais apenas
- Auto-refresh configurável: 15s / 30s / 60s com countdown visual
- Painel principal: KPIs + Alarmes ativos + Gateway Status
- Painel secundário: Tráfego VCN + Latência inter-região
- Indicador de última atualização sempre visível
- Suporte a rotação automática entre regiões (carrossel)

### 3.16 Export & Notificações

**Export:**
- Snapshot do estado atual em PDF (via print-to-PDF do browser ou Puppeteer no backend)
- Export de métricas para CSV (período configurável: 1h / 24h / 7 dias / 30 dias)
- Export de Flow Logs filtrados para CSV
- Export do Security Posture Report em PDF com score e lista de riscos

**Notificações:**
- Integração com OCI Notifications Service (SNS-like) para alarmes críticos
- Webhook configurável para Slack (mensagem com severity, recurso, região)
- Webhook configurável para Microsoft Teams
- Email via OCI Email Delivery quando alarme de nível Critical dispara
- Configuração de thresholds por utilizador (ex: "alertar quando latência FRA→JNB > 200ms")
- Endpoints:
  - `POST /api/notifications/webhook` - configurar webhook
  - `GET /api/notifications/config` - listar configurações ativas

### 3.17 Load Balancer Health Panel

O Load Balancer é um dos recursos de rede mais críticos do OCI e não tem visibilidade consolidada nativa. Uma cert expirada ou um backend degradado pode derrubar produção sem disparar nenhum alarme óbvio no OCI Console.

**Vista principal:**
- Lista de todos os Load Balancers (Flexible LB + Network LB) por região e compartimento
- Estado geral por LB: HEALTHY / DEGRADED / CRITICAL / UNKNOWN
- Colunas: nome, tipo (Flex/NLB), shape, VCN, região, backends totais, backends saudáveis, request rate, error rate

**Backend Sets & Health:**
- Para cada LB: lista de backend sets com estado individual por backend (IP:port)
- Health check protocol, intervalo e threshold configurados
- Backends em estado CRITICAL ou UNKNOWN destacados com badge vermelho
- Histórico de saúde: quantas vezes cada backend entrou em CRITICAL nas últimas 24h

**Métricas de tráfego (via OCI Monitoring):**
```
Namespace: oci_lbaas
  - HttpRequests            # request rate total
  - HttpResponses2xx/3xx/4xx/5xx  # por código de resposta
  - ActiveConnections       # conexões ativas
  - BytesProcessed          # throughput
  - ResponseTime            # latência de resposta (p50, p95, p99)

Namespace: oci_nlb
  - ActiveConnections
  - BytesProcessed
  - NewConnections
  - DroppedConnections
```

**SSL/TLS Certificate Expiry Monitor:**
- Extrai certificados de todos os LBs via OCI LB API
- Mostra: nome do cert, LB associado, data de expiração, dias restantes
- Alertas automáticos:
  - 🟡 Amarelo: cert expira em menos de 30 dias
  - 🔴 Vermelho: cert expira em menos de 7 dias
  - ⛔ Crítico: cert já expirado
- Ordenação por proximidade de expiração (mais urgente no topo)

**Drill-down por LB:**
- Gráfico de request rate + error rate nas últimas 24h
- Tabela de backends com status, response time individual, connections
- Regras de listener (porta, protocolo, routing policies)
- Botão "Explain with AI" quando error rate ultrapassa threshold

**Endpoints:**
- `GET /api/lb/list?region=&compartment=` - todos os LBs com estado agregado
- `GET /api/lb/{lb_id}/backends` - backend sets e saúde dos backends
- `GET /api/lb/{lb_id}/metrics?period=` - métricas de tráfego
- `GET /api/lb/certificates` - todos os certs com data de expiração
- `GET /api/lb/alerts` - LBs com backends em CRITICAL ou certs a expirar

**OCI APIs utilizadas:**
```
GET /20170115/loadBalancers                  # lista LBs (Flexible)
GET /20170115/loadBalancers/{id}/backendSets # backend sets
GET /20170115/loadBalancers/{id}/certificates # certificados SSL
GET /20200501/networkLoadBalancers           # lista NLBs
```

---

### 3.18 Private DNS Visibility

O DNS é a causa silenciosa de muitos problemas de conectividade no OCI - uma resolução falhada entre VCNs não dispara alarmes e é difícil de diagnosticar sem CLI. Este módulo dá visibilidade completa sobre a infraestrutura DNS privada do tenancy.

**Vista principal - DNS Overview:**
- Lista de todas as Private DNS Zones por compartimento e região
- Para cada zone: nome, tipo (Primary/Secondary), número de records, VCN views associadas
- Estado de sincronização entre regiões (para zones replicadas)
- Zonas sem nenhuma VCN view associada (potencial misconfiguration)

**DNS Resolvers:**
- Lista de resolvers por VCN
- Regras de forwarding configuradas (conditional forwarding para on-premises ou outras VCNs)
- Endpoints de resolver (IP, subnet, estado)
- Deteção de VCNs sem resolver configurado (blind spot de DNS)

**DNS Views:**
- Mapeamento view → zone → VCN
- Identificação de sobreposições ou conflitos entre views
- VCNs que partilham views vs VCNs isoladas

**Problemas comuns detetados automaticamente:**
- Zone sem records (vazia - provavelmente misconfiguration)
- Resolver sem regras de forwarding configuradas quando esperado
- VCN com peering ativo mas sem DNS forwarding configurado entre pares
- Records com TTL muito baixo (< 60s) que podem causar instabilidade
- Records do tipo A apontando para IPs fora dos CIDRs do tenancy

**DNS Query Visibility (via VCN Flow Logs + Logging Analytics):**
- Volume de queries DNS por VCN (porta 53, UDP/TCP)
- Top 10 domínios mais consultados
- Queries com falha de resolução (NXDOMAIN) - indica possíveis misconfigurations ou tentativas de acesso indevido
- Filtro: queries para domínios externos vs internos

**Endpoints:**
- `GET /api/dns/zones?compartment=` - lista de private DNS zones
- `GET /api/dns/resolvers?vcn_id=` - resolvers e regras de forwarding por VCN
- `GET /api/dns/views?compartment=` - DNS views e mapeamento para VCNs
- `GET /api/dns/issues` - problemas detetados automaticamente
- `GET /api/dns/query-stats?period=` - estatísticas de queries (via flow logs)

**OCI APIs utilizadas:**
```
GET /20180115/zones?scope=PRIVATE           # private DNS zones
GET /20180115/resolvers                     # DNS resolvers por VCN
GET /20180115/resolverEndpoints             # endpoints de cada resolver
GET /20180115/views                         # DNS views
GET /20180115/rrsets/{zone}/{domain}/{type} # DNS records
```

---

### 3.19 DRG Route Inspector

O módulo de DR Readiness dá um score geral, mas não mostra o detalhe das routing tables do DRG. É exatamente aqui que os problemas de failover aparecem - rotas em falta, políticas de import/export incorretas, prefixos BGP mal anunciados - e a troubleshoot hoje obriga a CLI ou múltiplos cliques no OCI Console.

**Vista principal - DRG Overview:**
- Lista de todos os DRGs por região com número de attachments ativos
- Tipos de attachment: VCN, IPSec VPN, FastConnect, RPC (Remote Peering)
- Estado de cada attachment: ATTACHED / DETACHING / DETACHED
- Total de rotas por DRG e percentagem de utilização do limite (máx 300 rotas estáticas)

**Route Tables Inspector:**
- Tabela completa de todas as route tables do DRG com rotas individuais
- Colunas por rota: prefixo CIDR, next hop type, attachment de origem, tipo (STATIC/BGP/STATIC_VCN)
- Filtro por: tipo de rota, attachment, prefixo CIDR
- Deteção de rotas sobrepostas (overlapping prefixes) - causa silenciosa de tráfego mal encaminhado
- Deteção de rotas órfãs (next hop que já não existe)
- Comparação de route tables entre regiões (para DR: primary vs standby devem ter simetria)

**BGP & FastConnect:**
- Prefixos BGP anunciados e recebidos por FastConnect virtual circuit
- AS path e local preference por prefixo
- Estado das sessões BGP (UP/DOWN, uptime, prefixos recebidos/anunciados)
- Alertas quando prefixos BGP esperados deixam de ser anunciados

**Import/Export Policies:**
- Visualização das políticas de import/export por route table
- Deteção de políticas que bloqueiam rotas necessárias para DR
- Comparação de políticas entre attachments do mesmo tipo

**DR Route Validation:**
- Check automático: "as rotas necessárias para failover estão presentes em todas as regiões DR?"
- Define-se um conjunto de prefixos CIDR críticos e o Meridian verifica se estão propagados corretamente
- Resultado: ✅ rota presente / ⚠️ rota parcialmente propagada / ❌ rota ausente
- Integrado com o DR Readiness Summary do GenAI (módulo 3.17.5)

**Endpoints:**
- `GET /api/drg/list?region=` - todos os DRGs com attachments
- `GET /api/drg/{drg_id}/routes` - todas as rotas com filtros
- `GET /api/drg/{drg_id}/bgp` - estado BGP e prefixos por FastConnect
- `GET /api/drg/{drg_id}/policies` - import/export policies
- `GET /api/drg/validation?critical_cidrs=` - validação de rotas DR críticas
- `GET /api/drg/issues` - problemas detetados automaticamente (sobreposições, órfãs)

**OCI APIs utilizadas:**
```
GET /20160918/drgs                           # lista DRGs
GET /20160918/drgAttachments                 # attachments por DRG
GET /20160918/drgs/{id}/drgRouteTables       # route tables
GET /20160918/drgRouteTables/{id}/drgRouteRules  # rotas individuais
GET /20160918/virtualCircuits                # FastConnect circuits (BGP)
GET /20160918/ipsecConnections               # VPN connections por DRG
```

---

### 3.20 OCI GenAI - Meridian Intelligence Layer

Integração com **OCI Generative AI Service** para adicionar capacidades de linguagem natural ao dashboard. Os dados já presentes no Meridian são enviados como contexto para o modelo - sem RAG, sem infraestrutura adicional. Modelo recomendado: **Cohere Command R+** ou **Meta Llama 3** via OCI GenAI Service (endpoint regional, dados permanecem dentro do tenancy).

#### 3.20.1 Alarm Explainer

Quando um alarme dispara, o utilizador clica em "Explain" e o GenAI explica em linguagem natural o que significa, o impacto provável e os próximos passos recomendados.

**Comportamento:**
- Botão "Explain with AI" em cada alarme no Alarms Center
- Payload enviado ao GenAI: tipo de alarme, recurso afetado, região, severidade, métricas recentes do recurso
- Resposta em prosa: explicação do alarme + impacto operacional + 3 ações recomendadas
- Resposta apresentada num drawer lateral, sem sair do dashboard
- Exemplo de output para "DRG route limit exceeded em drg-attach-02":
  > "O DRG drg-attach-02 atingiu o limite máximo de rotas propagadas (142/150). Isto significa que novos prefixos de rede não podem ser anunciados, o que pode causar falhas de conectividade entre VCNs ou para on-premises. Ações recomendadas: 1) Rever e remover rotas estáticas redundantes, 2) Aumentar o limite via OCI Support Request, 3) Verificar se o peering BGP está a anunciar prefixos desnecessariamente."

**Endpoints:**
- `POST /api/genai/alarm/explain` - body: `{ alarm_id, context_metrics }`

#### 3.20.2 Natural Language Query - Flow Logs

O utilizador escreve em linguagem natural (PT/EN) e o GenAI traduz para uma query OCI Logging Analytics, que é executada e os resultados apresentados no painel.

**Comportamento:**
- Caixa de texto no Flow Logs Panel: "Pesquisar em linguagem natural..."
- Exemplos suportados:
  - "mostra-me todo o tráfego rejeitado da subnet prod nas últimas 2 horas"
  - "quais os IPs externos que mais acederam ao port 443 hoje"
  - "show me all traffic between 10.0.1.0/24 and 10.0.2.0/24 yesterday"
- GenAI recebe: query em linguagem natural + schema dos flow logs disponíveis
- GenAI responde: query OCI Logging Analytics formatada
- Backend executa a query gerada e devolve resultados
- Query gerada é sempre visível ao utilizador (modo "mostrar query") para auditoria
- Histórico das últimas 10 queries guardado em localStorage

**Endpoints:**
- `POST /api/genai/flowlogs/nl-query` - body: `{ natural_language_query, regions, time_range }`
- Resposta: `{ generated_query, results }`

#### 3.20.3 Security Risk Narrative

O Security Posture Panel mostra scores e regras. O GenAI gera um relatório executivo em prosa - pronto para enviar a um cliente ou manager sem edição adicional.

**Comportamento:**
- Botão "Generate Executive Report" no Security Posture Panel
- Payload enviado ao GenAI: lista de regras de risco, score por VCN, região, compartimento, data
- Resposta em formato de relatório executivo (~300-500 palavras):
  - Sumário executivo do estado de segurança
  - Riscos críticos identificados com contexto técnico acessível
  - Riscos médios e baixos agrupados
  - Recomendações priorizadas por impacto
  - Nota de conformidade (ex: boas práticas OCI Well-Architected)
- Export direto do relatório para PDF (integrado com módulo 3.16)
- Idioma configurável: PT / EN / ES

**Endpoints:**
- `POST /api/genai/security/narrative` - body: `{ posture_data, language, compartments }`

#### 3.20.4 Change Feed Impact Analysis

Quando uma alteração de rede é detetada no Audit Log, o GenAI analisa automaticamente se a mudança pode ter impacto em conectividade, segurança ou DR readiness.

**Comportamento:**
- Cada evento no Change Feed tem um ícone de análise AI clicável
- Análise automática (background) para eventos de alta criticidade (ex: alteração de Security List, remoção de rota)
- Payload enviado ao GenAI: evento de audit (tipo, recurso, utilizador, antes/depois), topologia atual do tenancy
- Resposta estruturada em 3 dimensões:
  - **Conectividade:** esta alteração pode quebrar alguma comunicação existente?
  - **Segurança:** esta alteração abre ou fecha superfície de ataque?
  - **DR Readiness:** esta alteração afeta a capacidade de failover?
- Badge de impacto no feed: 🟢 Sem impacto / 🟡 Verificar / 🔴 Ação necessária
- Análise automática de eventos críticos via scheduler (não requer clique manual)

**Endpoints:**
- `POST /api/genai/audit/impact` - body: `{ audit_event, topology_snapshot }`

#### 3.20.5 DR Readiness Summary

Dado o estado atual da topologia, gateways e healthchecks, o GenAI produz um resumo executivo do estado de prontidão para DR.

**Comportamento:**
- Painel dedicado "DR Readiness" com botão "Generate AI Summary"
- Inputs para o GenAI: estado dos healthchecks, gateways de todas as regiões, latência inter-região, alarmes ativos, VPN/FastConnect status, rotas DRG
- Output: parágrafo de sumário + score de readiness (0-100%) + lista de riscos bloqueantes
- Exemplo de output:
  > "A infraestrutura Meridian apresenta um score de DR readiness de 73%. Os gateways FastConnect e VPN estão operacionais em todas as regiões monitorizadas. No entanto, o DRG drg-attach-02 em eu-amsterdam-1 está próximo do limite de rotas (95%), o que pode comprometer o failover automático. A latência FRA→JNB de 142ms está dentro dos parâmetros aceitáveis para workloads não-críticos. Ações bloqueantes: resolver o limite de rotas no DRG antes de qualquer teste de failover."
- Score atualizado automaticamente a cada refresh do dashboard
- Histórico de scores guardado para trending (últimas 7 avaliações)

**Endpoints:**
- `POST /api/genai/dr/readiness-summary` - body: `{ gateways, healthchecks, latency, alarms }`

#### Stack OCI GenAI - Abordagem

**Princípio:** OCI GenAI Service direto via API - sem RAG, sem vector stores, sem embeddings. Cada chamada inclui o contexto necessário já disponível no dashboard como parte do prompt. Simples, sem infraestrutura adicional, sem latência de retrieval.

```
┌─────────────────────────────────────────────┐
│              Meridian Backend               │
│                                             │
│  dados OCI já coletados (metrics, alarms,  │
│  posture, audit, topology)                  │
│              │                              │
│              ▼                              │
│  prompt builder (context + instrução)       │
│              │                              │
│              ▼                              │
│  OCI GenAI Service (direct API call)        │
│  modelo: Cohere Command R+                  │
│              │                              │
│              ▼                              │
│  resposta em texto → frontend               │
└─────────────────────────────────────────────┘

SEM: RAG / vector DB / embeddings / fine-tuning
SEM: dados a sair do tenancy OCI
SEM: infraestrutura adicional além da VM do Meridian
```

```python
# OCI Generative AI Service - Instance Principal, chamada direta
import oci

genai_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config={}, signer=signer
)

def call_genai(prompt: str, max_tokens: int = 1024) -> str:
    response = genai_client.chat(
        oci.generative_ai_inference.models.ChatDetails(
            compartment_id=COMPARTMENT_ID,
            serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                model_id="cohere.command-r-plus"
            ),
            chat_request=oci.generative_ai_inference.models.CohereChatRequest(
                message=prompt,
                max_tokens=max_tokens,
                temperature=0.3      # baixo para outputs determinísticos
            )
        )
    )
    return response.data.chat_response.text

# Exemplo - Alarm Explainer
def build_alarm_prompt(alarm: dict, metrics: dict) -> str:
    return f"""
És um especialista em OCI networking. Explica este alarme em linguagem clara para um operador de cloud.

Alarme: {alarm['name']}
Recurso: {alarm['resource']} ({alarm['region']})
Severidade: {alarm['severity']}
Métricas recentes: {metrics}

Responde com:
1. O que significa este alarme
2. Impacto operacional provável
3. Três ações recomendadas (por ordem de prioridade)
"""
```

**Modelo único recomendado: `cohere.command-r-plus`**
- Cobre todos os 5 casos de uso do Meridian
- Contexto de 128K tokens - suficiente para incluir topologia completa no prompt
- Regiões OCI GenAI disponíveis: `us-chicago-1`, `eu-frankfurt-1`
- Usar `eu-frankfurt-1` para tenancies europeus (dados permanecem na Europa)

**Considerações:**
- Prompts stateless - cada chamada inclui todo o contexto, sem estado entre chamadas
- Cache de respostas no Redis (TTL 5min) para evitar chamadas repetidas ao mesmo alarme
- Rate limits OCI GenAI On-Demand: ~60 req/min - adequado para uso interativo
- Custo estimado: ~$0.003/1K tokens input, ~$0.015/1K tokens output (Cohere Command R+)
- Toggle global "AI Features" nas settings - desativa todos os 5 módulos de uma vez
- GenAI é sempre aditivo - todos os painéis funcionam na totalidade sem ele

---

## 4. Fontes de Dados (OCI APIs)

### OCI Monitoring Service
```
Namespace: oci_vcn
Métricas:
  - VnicFromNetworkBytes
  - VnicToNetworkBytes
  - VnicFromNetworkPackets
  - VnicToNetworkPackets
  - VnicIngressDrops
  - VnicEgressDrops

Namespace: oci_nat_gateway
  - BytesFrom / BytesTo
  - PacketsFrom / PacketsTo
  - DroppedPackets

Namespace: oci_vpn
  - TunnelState
  - PacketsReceived / PacketsSent

Namespace: oci_fast_connect
  - BitsReceived / BitsSent

Namespace: oci_lbaas
  - HttpRequests / HttpResponses2xx / HttpResponses4xx / HttpResponses5xx
  - ActiveConnections / BytesProcessed / ResponseTime

Namespace: oci_nlb
  - ActiveConnections / BytesProcessed / NewConnections / DroppedConnections
```

### OCI Network APIs
```
GET /20160918/vcns
GET /20160918/drgs
GET /20160918/ipsecConnections
GET /20160918/crossConnects
GET /20160918/internetGateways
GET /20160918/natGateways
GET /20160918/serviceGateways
GET /20160918/networkSecurityGroups
GET /20160918/securityLists
GET /20160918/routeTables
GET /20200430/clusters                    # OKE clusters
GET /20200430/nodePools                   # OKE node pools
GET /20160918/compartments               # Compartment tree

### OCI Load Balancer APIs
```
GET /20170115/loadBalancers              # Flexible Load Balancers
GET /20170115/loadBalancers/{id}/backendSets   # Backend sets + saúde
GET /20170115/loadBalancers/{id}/certificates  # Certificados SSL/TLS
GET /20500501/networkLoadBalancers       # Network Load Balancers
```

### OCI Private DNS APIs
```
GET /20180115/zones?scope=PRIVATE        # Private DNS zones
GET /20180115/resolvers                  # DNS resolvers por VCN
GET /20180115/resolverEndpoints          # Endpoints de resolver
GET /20180115/views                      # DNS views
GET /20180115/rrsets/{zone}/{domain}/{type}  # DNS records
```

### OCI DRG Route APIs
```
GET /20160918/drgs                       # Lista de DRGs
GET /20160918/drgAttachments             # Attachments por DRG
GET /20160918/drgs/{id}/drgRouteTables   # Route tables
GET /20160918/drgRouteTables/{id}/drgRouteRules  # Rotas individuais
GET /20160918/virtualCircuits            # FastConnect / BGP circuits
```

### OCI Audit API (Change Feed)
```
GET /20190901/auditEvents
  ?compartmentId=...
  &startTime=...
  &endTime=...
  Filtrar por: eventType contains "network" OR "vcn" OR "subnet" OR "securityList"
```

### OCI Price List API (Cost-Aware Egress)
```
GET /20190111/products
  ?serviceCode=OCINetworking
  Extrai: egress pricing por região ($/GB)
```

### OCI Generative AI Service
```
POST /20231130/actions/chat
  model_id: cohere.command-r-plus | cohere.command-r | meta.llama-3-70b-instruct
  Regiões disponíveis: us-chicago-1, eu-frankfurt-1
  Auth: Instance Principal (mesmo signer do resto do Meridian)
  Parâmetros relevantes:
    - max_tokens: 1024 (Alarm Explainer) / 2048 (Security Narrative)
    - temperature: 0.3 (outputs determinísticos)
    - compartment_id: compartimento onde o Meridian está deployado
```
```
Query exemplo:
'Log Source' = 'OCI VCN Flow Unified Schema Logs'
| stats count as logrecords by 'Action', 'Source IP', 'Destination IP'
| sort -logrecords
| head 10
```

---

## 5. Stack Técnico

### Backend
```
Python 3.11+
├── fastapi          # REST API
├── oci              # OCI Python SDK (inclui GenerativeAiInferenceClient)
├── apscheduler      # Polling scheduler
├── pydantic         # Data models
├── uvicorn          # ASGI server
├── httpx            # Async HTTP (healthchecks sintéticos)
├── reportlab        # Geração de PDF (export)
├── pandas           # Manipulação de dados CSV
└── redis (opcional) # Cache de métricas + cache de respostas GenAI
```

### Frontend
```
React 18+
├── recharts         # Gráficos de métricas
├── react-flow       # Topologia de rede (nodes/edges)
├── tailwindcss      # Estilo
├── axios            # HTTP client
├── react-query      # Data fetching + cache
├── react-toastify   # Notificações inline (alertas)
└── jspdf            # Export PDF no browser (alternativa ao Puppeteer)
```

### Infraestrutura (Deploy no OCI)
```
OCI Compute VM (VM.Standard.E4.Flex - 1 OCPU, 8GB RAM)
├── Ubuntu 22.04
├── Docker + Docker Compose
│   ├── backend (FastAPI)
│   ├── frontend (Nginx + React build)
│   └── redis (cache)
└── OCI Load Balancer (opcional para HA)
```

---

## 6. Autenticação com OCI

### Opção 1 - API Key (desenvolvimento)
```python
import oci

config = oci.config.from_file("~/.oci/config")
monitoring_client = oci.monitoring.MonitoringClient(config)
```

### Opção 2 - Instance Principal (produção recomendada)
```python
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
monitoring_client = oci.monitoring.MonitoringClient(
    config={}, signer=signer
)
```

### Política IAM necessária
```hcl
# Dynamic Group
matching_rule = "ANY {instance.compartment.id = 'ocid1.compartment...'}"

# Policy
allow dynamic-group meridian-dg to read metrics in tenancy
allow dynamic-group meridian-dg to read vcns in tenancy
allow dynamic-group meridian-dg to read drgs in tenancy
allow dynamic-group meridian-dg to read alarms in tenancy
allow dynamic-group meridian-dg to read log-groups in tenancy
allow dynamic-group meridian-dg to read audit-events in tenancy
allow dynamic-group meridian-dg to read network-security-groups in tenancy
allow dynamic-group meridian-dg to read security-lists in tenancy
allow dynamic-group meridian-dg to read clusters in tenancy
allow dynamic-group meridian-dg to read node-pools in tenancy
allow dynamic-group meridian-dg to read compartments in tenancy
allow dynamic-group meridian-dg to use ons-topics in tenancy
allow dynamic-group meridian-dg to use generative-ai-family in tenancy
```

---

## 7. Etapas de Desenvolvimento

### Fase 1 - Setup & Backend Base (Semana 1)
- [ ] Criar repositório Git (estrutura de projeto)
- [ ] Setup ambiente local (Python venv, OCI SDK)
- [ ] Configurar autenticação OCI (API Key para dev)
- [ ] Implementar endpoints base FastAPI
- [ ] Testar chamadas às OCI APIs (VCNs, Gateways)
- [ ] Estruturar modelos Pydantic de resposta

### Fase 2 - Coleta de Métricas (Semana 2)
- [ ] Implementar polling de métricas via OCI Monitoring API
- [ ] Gateway status (VPN tunnels, FastConnect, NAT, IGW)
- [ ] VNIC metrics por compartimento
- [ ] Alarmes ativos de rede
- [ ] APScheduler para refresh automático (ex: 60s)
- [ ] Cache Redis para reduzir chamadas (opcional)

### Fase 3 - VCN Flow Logs (Semana 3)
- [ ] Ativar VCN Flow Logs no ambiente de teste
- [ ] Implementar query via Logging Analytics API
- [ ] Parser de logs para formato dashboard
- [ ] Endpoint REST `/api/flowlogs/summary`
- [ ] Endpoint REST `/api/flowlogs/top-sources`

### Fase 4 - Frontend Base (Semana 3-4)
- [ ] Setup projeto React + Tailwind + Recharts
- [ ] Layout do dashboard (sidebar + main area)
- [ ] Componente: VCN Overview card
- [ ] Componente: Gateway Status panel (UP/DOWN indicators)
- [ ] Componente: Alarms Center (tabela com severidade)
- [ ] Componente: Métricas de tráfego (line charts)

### Fase 5 - Topologia Visual (Semana 4-5)
- [ ] Integrar react-flow para topologia de rede
- [ ] Nodes: VCN, Subnets, Gateways, DRG
- [ ] Edges: conexões e sentido do tráfego
- [ ] Tooltips com métricas ao hover
- [ ] Auto-layout baseado nos dados reais da API

### Fase 6 - Multi-região & Compartment Switcher (Semana 5)
- [ ] Suporte a múltiplas regiões no backend (asyncio paralelo)
- [ ] Region selector com Home Region fixa + regiões adicionais
- [ ] Compartment tree-view com multi-seleção
- [ ] Agregação de dados cross-region e cross-compartment
- [ ] Inter-region latency panel

### Fase 7 - Security Posture & Change Feed (Semana 6)
- [ ] Varredura de Security Lists e NSGs
- [ ] Deteção de regras de risco (SSH/RDP/ALL open)
- [ ] Score de risco por VCN
- [ ] Change Feed via OCI Audit API
- [ ] Feed de eventos filtrado por tipo de recurso de rede

### Fase 8 - OKE Network Health & Cost Egress (Semana 7)
- [ ] Integração com OKE API (clusters, node pools)
- [ ] Estado de CNI, LBs e Ingress Controllers
- [ ] Alerta de esgotamento de IPs em subnet OKE
- [ ] Cost-aware egress: bytes + custo estimado por gateway
- [ ] Top consumidores de egress por instância
- [ ] Projeção de custo mensal

### Fase 9 - Healthcheck Sintético (Semana 7-8)
- [ ] Motor de healthchecks com asyncio + httpx
- [ ] CRUD de checks via API REST
- [ ] Dashboard de disponibilidade por check
- [ ] Modo DR: conjunto pré-definido de checks críticos
- [ ] Alertas quando check falha N vezes consecutivas

### Fase 10 - Load Balancer Health Panel (Semana 8-9)
- [ ] Integração com OCI LB API (Flexible LB + Network LB)
- [ ] Backend sets e health check status por backend
- [ ] Métricas de tráfego: request rate, error rate (2xx/4xx/5xx), response time
- [ ] SSL/TLS Certificate Expiry Monitor com alertas 30/7 dias
- [ ] Drill-down por LB com gráficos 24h

### Fase 11 - Private DNS Visibility (Semana 9)
- [ ] Integração com OCI Private DNS API
- [ ] Lista de zones, resolvers, views e mapeamento para VCNs
- [ ] Deteção automática de misconfigurations (zones vazias, resolvers sem regras, peering sem forwarding)
- [ ] DNS query stats via VCN Flow Logs (porta 53)
- [ ] Top domínios + NXDOMAIN failures

### Fase 12 - DRG Route Inspector (Semana 9-10)
- [ ] Integração com OCI DRG Route Tables API
- [ ] Vista completa de rotas por DRG com filtros
- [ ] Deteção de overlapping prefixes e rotas órfãs
- [ ] Estado BGP e prefixos FastConnect
- [ ] DR Route Validation: check de CIDRs críticos em todas as regiões
- [ ] Comparação de route tables entre regiões primary/standby

### Fase 13 - Modo NOC & Export (Semana 10)
- [ ] Layout NOC full-screen (`/noc` route)
- [ ] Auto-refresh com countdown visual
- [ ] Rotação automática entre regiões
- [ ] Export PDF (Security Posture Report + snapshot geral)
- [ ] Export CSV de métricas e flow logs por período

### Fase 14 - Notificações & Deploy (Semana 11)
- [ ] Integração OCI Notifications Service
- [ ] Webhook Slack + Microsoft Teams
- [ ] Email via OCI Email Delivery
- [ ] Configuração de thresholds por utilizador
- [ ] Dockerizar stack completo (backend + frontend + redis)
- [ ] Terraform para provisionar infra no OCI
- [ ] Configurar Instance Principal + IAM policies completas
- [ ] Nginx reverse proxy + TLS

### Fase 15 - OCI GenAI - Intelligence Layer (Semana 12)
- [ ] Configurar OCI GenerativeAiInferenceClient com Instance Principal
- [ ] Adicionar IAM policy `use generative-ai-family in tenancy`
- [ ] Implementar `oci_genai.py` service com wrapper para Cohere Command R+
- [ ] Alarm Explainer: prompt engineering + drawer UI no frontend
- [ ] NL Flow Logs Query: parser de linguagem natural → Logging Analytics query
- [ ] Security Risk Narrative: prompt com dados de posture + export PDF integrado
- [ ] Change Feed Impact Analysis: análise automática de eventos críticos via scheduler
- [ ] DR Readiness Summary: agregação de inputs + score calculation + histórico
- [ ] Cache de respostas GenAI no Redis (TTL 5min)
- [ ] Toggle global "AI Features" nas settings

### Fase 16 - Polimento & Documentação (Semana 13)
- [ ] Dark mode toggle
- [ ] Testes de carga e otimização de chamadas API
- [ ] README completo com guia de instalação
- [ ] Documentação de endpoints (OpenAPI/Swagger auto-gerado)
- [ ] Changelog e versionamento semântico

---

## 8. Estrutura de Pastas do Projeto

```
meridian/
├── backend/
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                    # OCI config & settings
│   ├── requirements.txt
│   ├── routers/
│   │   ├── vcn.py                   # VCN endpoints
│   │   ├── gateways.py              # Gateway metrics
│   │   ├── flowlogs.py              # VCN Flow Logs
│   │   ├── alarms.py                # OCI Alarms
│   │   ├── metrics.py               # Monitoring metrics
│   │   ├── vnics.py                 # VNIC top consumers + instance drill-down
│   │   ├── latency.py               # Inter-region latency
│   │   ├── compartments.py          # Compartment tree
│   │   ├── security.py              # Security posture + risky rules
│   │   ├── audit.py                 # Change feed (Audit API)
│   │   ├── oke.py                   # OKE network health
│   │   ├── cost.py                  # Cost-aware egress
│   │   ├── healthchecks.py          # Synthetic healthchecks
│   │   ├── lb.py                    # Load Balancer health + cert expiry
│   │   ├── dns.py                   # Private DNS visibility
│   │   ├── drg_routes.py            # DRG Route Inspector
│   │   ├── export.py                # PDF + CSV export
│   │   ├── notifications.py         # Webhook + OCI Notifications
│   │   └── genai.py                 # OCI GenAI - todos os endpoints de AI
│   ├── services/
│   │   ├── oci_monitoring.py        # OCI Monitoring SDK calls
│   │   ├── oci_network.py           # OCI Network SDK calls
│   │   ├── oci_logging.py           # Logging Analytics calls
│   │   ├── oci_audit.py             # OCI Audit API calls
│   │   ├── oci_oke.py               # OCI Container Engine calls
│   │   ├── oci_pricing.py           # OCI Price List API
│   │   ├── oci_notifications.py     # OCI ONS integration
│   │   ├── oci_genai.py             # OCI Generative AI Service calls
│   │   ├── oci_lb.py                # OCI Load Balancer SDK calls
│   │   ├── oci_dns.py               # OCI Private DNS SDK calls
│   │   ├── oci_drg.py               # OCI DRG Route Tables SDK calls
│   │   ├── synthetic.py             # Healthcheck engine (httpx async)
│   │   └── scheduler.py             # APScheduler jobs
│   └── models/
│       ├── vcn.py
│       ├── gateway.py
│       ├── alarm.py
│       ├── security.py
│       ├── audit.py
│       ├── oke.py
│       ├── cost.py
│       └── healthcheck.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── VCNOverview.jsx
│   │   │   ├── GatewayStatus.jsx
│   │   │   ├── FlowLogsPanel.jsx
│   │   │   ├── AlarmsCenter.jsx
│   │   │   ├── NetworkTopology.jsx
│   │   │   ├── LatencyMap.jsx
│   │   │   ├── MetricsChart.jsx
│   │   │   ├── VNICTopConsumers.jsx      # Top instâncias por bandwidth + drill-down
│   │   │   ├── LBHealthPanel.jsx         # Load Balancer health + cert expiry
│   │   │   ├── PrivateDNSPanel.jsx       # Private DNS zones, resolvers, issues
│   │   │   ├── DRGRouteInspector.jsx     # DRG route tables + BGP + DR validation
│   │   │   ├── CompartmentSwitcher.jsx
│   │   │   ├── RegionSelector.jsx
│   │   │   ├── SecurityPosture.jsx
│   │   │   ├── ChangeFeed.jsx
│   │   │   ├── OKENetworkHealth.jsx
│   │   │   ├── CostEgress.jsx
│   │   │   ├── HealthcheckPanel.jsx
│   │   │   ├── NOCView.jsx
│   │   │   ├── ExportButton.jsx
│   │   │   ├── NotificationConfig.jsx
│   │   │   ├── AlarmExplainer.jsx       # GenAI: drawer de explicação de alarme
│   │   │   ├── NLFlowQuery.jsx          # GenAI: caixa de query em linguagem natural
│   │   │   ├── SecurityNarrative.jsx    # GenAI: relatório executivo de segurança
│   │   │   ├── ChangeFeedImpact.jsx     # GenAI: análise de impacto por evento
│   │   │   └── DRReadinessSummary.jsx   # GenAI: sumário de prontidão DR
│   │   ├── hooks/
│   │   │   ├── useOCIData.js
│   │   │   ├── useRegions.js
│   │   │   └── useCompartments.js
│   │   └── api/
│   │       └── client.js
│   ├── package.json
│   └── tailwind.config.js
├── infra/
│   ├── terraform/
│   │   ├── main.tf                  # VM + LB no OCI
│   │   ├── iam.tf                   # Dynamic Group + Policy (completo)
│   │   └── variables.tf
│   └── docker-compose.yml
├── .env.example
└── README.md
```

---

## 9. Endpoints REST (Backend)

```
GET  /api/health                              # Status do backend

# Regiões & Compartimentos
GET  /api/compartments?tenancy_id=            # Árvore de compartimentos
GET  /api/regions/available                   # Lista de regiões OCI suportadas

# Rede
GET  /api/vcns?regions=&compartments=         # Lista VCNs (multi-região)
GET  /api/gateways/status                     # Status de todos os gateways
GET  /api/gateways/metrics?type=nat&...       # Métricas por gateway
GET  /api/vpn/tunnels                         # Estado dos tunnels VPN
GET  /api/fastconnect/circuits                # Estado FastConnect
GET  /api/flowlogs/summary                    # Resumo de flow logs
GET  /api/flowlogs/top-sources                # Top IPs de origem
GET  /api/alarms/active                       # Alarmes ativos de rede
GET  /api/latency/interregion                 # Latência entre regiões
GET  /api/vnics/metrics                       # Métricas de VNICs (agregado)
GET  /api/vnics/top-consumers?period=&limit=  # Ranking de instâncias por bandwidth
GET  /api/vnics/instance/{id}/metrics         # Detalhes por instância (drill-down)
GET  /api/vnics/anomalies                     # Instâncias com comportamento anómalo
GET  /api/topology?vcn_id=                    # Dados de topologia

# Security Posture
GET  /api/security/posture                    # Score de risco por VCN
GET  /api/security/risky-rules                # Regras de alto risco

# Audit / Change Feed
GET  /api/audit/network-changes?hours=24      # Alterações recentes de rede

# OKE
GET  /api/oke/clusters                        # Clusters por região
GET  /api/oke/network-health?cluster_id=      # Health de rede por cluster

# Cost Egress
GET  /api/cost/egress?region=&period=         # Custo estimado por período
GET  /api/cost/top-consumers                  # Top instâncias por egress

# Healthchecks Sintéticos
GET  /api/healthchecks                        # Lista de checks configurados
POST /api/healthchecks                        # Criar novo check
GET  /api/healthchecks/{id}/history           # Histórico de resultados
DELETE /api/healthchecks/{id}                 # Remover check

# Export
GET  /api/export/pdf                          # Snapshot geral em PDF
GET  /api/export/csv?dataset=metrics&period=  # Export CSV de métricas
GET  /api/export/security-report              # Security Posture Report PDF

# Notificações
GET  /api/notifications/config                # Configurações ativas
POST /api/notifications/webhook               # Configurar webhook Slack/Teams
POST /api/notifications/threshold             # Configurar threshold de alerta

# Load Balancer
GET  /api/lb/list?region=&compartment=        # Todos os LBs com estado
GET  /api/lb/{lb_id}/backends                 # Backend sets e saúde
GET  /api/lb/{lb_id}/metrics?period=          # Métricas de tráfego
GET  /api/lb/certificates                     # Certs SSL com data de expiração
GET  /api/lb/alerts                           # LBs críticos ou certs a expirar

# Private DNS
GET  /api/dns/zones?compartment=              # Private DNS zones
GET  /api/dns/resolvers?vcn_id=              # Resolvers e forwarding rules
GET  /api/dns/views?compartment=             # DNS views e mapeamento VCN
GET  /api/dns/issues                         # Problemas detetados automaticamente
GET  /api/dns/query-stats?period=            # Estatísticas de queries DNS

# DRG Route Inspector
GET  /api/drg/list?region=                   # DRGs com attachments
GET  /api/drg/{drg_id}/routes                # Rotas com filtros
GET  /api/drg/{drg_id}/bgp                   # Estado BGP e prefixos FastConnect
GET  /api/drg/{drg_id}/policies              # Import/export policies
GET  /api/drg/validation?critical_cidrs=     # Validação de rotas DR críticas
GET  /api/drg/issues                         # Sobreposições, rotas órfãs

# GenAI - Meridian Intelligence
POST /api/genai/alarm/explain                 # Explicação de alarme em linguagem natural
POST /api/genai/flowlogs/nl-query             # NL → OCI Logging Analytics query
POST /api/genai/security/narrative            # Relatório executivo de segurança
POST /api/genai/audit/impact                  # Análise de impacto de alteração de rede
POST /api/genai/dr/readiness-summary          # Sumário de DR readiness
```

---

## 10. Estimativa de Esforço

| Fase | Descrição | Esforço estimado |
|---|---|---|
| 1 | Setup & Backend Base | 3-4 dias |
| 2 | Coleta de Métricas | 4-5 dias |
| 3 | VCN Flow Logs | 3-4 dias |
| 4 | Frontend Base | 4-5 dias |
| 5 | Topologia Visual | 4-5 dias |
| 6 | Multi-região & Compartment Switcher | 3-4 dias |
| 7 | Security Posture & Change Feed | 4-5 dias |
| 8 | OKE Network Health & Cost Egress | 4-5 dias |
| 9 | Healthcheck Sintético | 3-4 dias |
| 10 | Load Balancer Health Panel | 4-5 dias |
| 11 | Private DNS Visibility | 3-4 dias |
| 12 | DRG Route Inspector | 4-5 dias |
| 13 | Modo NOC & Export | 3-4 dias |
| 14 | Notificações & Deploy | 4-5 dias |
| 15 | OCI GenAI - Intelligence Layer | 5-6 dias |
| 16 | Polimento & Documentação | 3-4 dias |
| **Total** | | **~15-17 semanas** |

> Estimativa para desenvolvimento a tempo parcial (evenings/weekends).  
> A tempo inteiro: 6-7 semanas.

---

## 11. Próximos Passos Imediatos

1. **Validar acesso às APIs** - testar OCI SDK localmente com API Key num compartimento de teste
2. **Definir regiões e compartimentos alvo** - quais serão monitorizados na v1
3. **Protótipo do frontend** - mockup do dashboard (pode ser feito como Artifact aqui)
4. **Decidir deploy target** - VM standalone vs container no OKE
5. **Criar repositório Git** - estrutura inicial do projeto

---

*Documento gerado em Maio 2026 - Meridian v1.5*
