# Plano: Migracao Dashboard Financeiro -> Next.js + FastAPI

## Objetivo
Migrar o dashboard Streamlit atual para uma aplicacao moderna com **Next.js 14+ (App Router)** no frontend e **FastAPI** no backend, criando o projeto na pasta `dashboard-rebranding/`.

---

## Arquitetura Geral

```
dashboard-rebranding/
├── backend/          (FastAPI - Python)
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS
│   │   ├── auth/                # JWT auth (httponly cookies)
│   │   │   ├── router.py        # POST /login, /logout, /me
│   │   │   ├── security.py      # hash, verify, create_token
│   │   │   └── dependencies.py  # get_current_user
│   │   ├── routers/
│   │   │   ├── contas_pagar.py  # /api/pagar/*
│   │   │   ├── contas_receber.py # /api/receber/*
│   │   │   └── intercompany.py  # /api/intercompany/*
│   │   ├── services/            # Logica de negocio (pandas)
│   │   │   ├── pagar.py
│   │   │   ├── receber.py
│   │   │   └── intercompany.py
│   │   ├── schemas/             # Pydantic models (request/response)
│   │   │   ├── auth.py
│   │   │   ├── pagar.py
│   │   │   ├── receber.py
│   │   │   └── common.py        # ChartData, KPIData, TableData
│   │   ├── data/                # Data processors
│   │   │   ├── loader.py        # Carrega Excel + cache
│   │   │   └── processors.py    # Filtros, agrupamentos, ABC
│   │   └── config.py            # Settings (porta do Streamlit)
│   ├── data/                    # Arquivos Excel (symlink ou copia)
│   ├── requirements.txt
│   └── .env
│
├── frontend/         (Next.js 14 - TypeScript)
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx        # Root layout + providers
│   │   │   ├── page.tsx          # Redirect -> /pagar
│   │   │   ├── login/page.tsx    # Login page
│   │   │   ├── pagar/
│   │   │   │   ├── layout.tsx    # Sidebar + filtros
│   │   │   │   └── page.tsx      # Tabs: Visao Geral, Vencimentos, etc.
│   │   │   ├── receber/
│   │   │   │   ├── layout.tsx
│   │   │   │   └── page.tsx
│   │   │   └── intercompany/
│   │   │       ├── layout.tsx
│   │   │       └── page.tsx
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui components
│   │   │   ├── charts/          # Recharts wrappers
│   │   │   │   ├── BarChart.tsx
│   │   │   │   ├── LineChart.tsx
│   │   │   │   ├── PieChart.tsx
│   │   │   │   ├── TreemapChart.tsx
│   │   │   │   └── HeatmapChart.tsx
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── PageHeader.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── KPICard.tsx
│   │   │   │   ├── DataTable.tsx  # TanStack Table
│   │   │   │   ├── FilterBar.tsx
│   │   │   │   └── ExportButton.tsx
│   │   │   └── auth/
│   │   │       └── AuthGuard.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useFilters.ts
│   │   │   └── useDashboardData.ts
│   │   ├── lib/
│   │   │   ├── api.ts            # Axios/fetch client
│   │   │   ├── formatters.ts     # formatar_moeda, etc.
│   │   │   └── constants.ts      # Cores, labels, configs
│   │   ├── store/
│   │   │   └── filters.ts        # Zustand store
│   │   └── types/
│   │       ├── api.ts            # Response types
│   │       └── dashboard.ts      # ChartData, KPI, etc.
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── .env.local
│
└── README.md
```

---

## Stack Tecnologico

### Backend
- **FastAPI** - API REST async
- **Pandas** - Processamento de dados (reutiliza logica existente)
- **Pydantic v2** - Validacao de schemas
- **python-jose** - JWT tokens
- **passlib[bcrypt]** - Hash de senhas
- **openpyxl** - Leitura Excel
- **uvicorn** - Server ASGI
- **python-dotenv** - Variaveis de ambiente

### Frontend
- **Next.js 14+** - App Router, SSR/CSR
- **TypeScript** - Tipagem estatica
- **Tailwind CSS** - Estilizacao utility-first
- **shadcn/ui** - Componentes UI (Card, Table, Select, Tabs, Dialog, etc.)
- **Recharts** - Graficos (Bar, Line, Pie, Treemap, Scatter)
- **TanStack Table** - Tabelas com sort, filter, pagination
- **TanStack Query** - Cache de dados da API
- **Zustand** - Estado global (filtros, tema)
- **Lucide React** - Icones
- **date-fns** - Manipulacao de datas

---

## Contrato de Dados (API)

### Schemas Padronizados

```typescript
// ChartData - Usado por todos os graficos
interface ChartData {
  labels: string[];
  series: {
    name: string;
    data: number[];
    color?: string;
  }[];
  chart_type: 'bar' | 'line' | 'pie' | 'treemap' | 'scatter' | 'heatmap';
}

// KPIData - Cards de metricas
interface KPIData {
  label: string;
  value: string;        // Ja formatado
  raw_value: number;    // Para calculos
  delta?: string;       // Variacao
  delta_type?: 'positive' | 'negative' | 'neutral';
  icon?: string;
}

// TableData - Tabelas de detalhes
interface TableData {
  columns: { key: string; label: string; type: 'text' | 'currency' | 'date' | 'number' }[];
  rows: Record<string, any>[];
  total_rows: number;
  page: number;
  page_size: number;
}

// FilterOptions - Opcoes de filtros
interface FilterOptions {
  filiais: { grupo: string; filiais: string[] }[];
  categorias: string[];
  status: string[];
  tipos_documento: string[];
  date_range: { min: string; max: string };
}
```

### Endpoints Principais

```
# Auth
POST   /api/auth/login          -> { token, user }
POST   /api/auth/logout         -> { ok }
GET    /api/auth/me             -> { user }

# Contas a Pagar
GET    /api/pagar/filters       -> FilterOptions
GET    /api/pagar/kpis          -> KPIData[]
GET    /api/pagar/visao-geral   -> { kpis, charts }
GET    /api/pagar/vencimentos   -> { aging, charts, table }
GET    /api/pagar/fornecedores  -> { top, abc, ranking, charts }
GET    /api/pagar/categorias    -> { pareto, treemap, table }
GET    /api/pagar/evolucao      -> { chart_mensal }
GET    /api/pagar/detalhes      -> TableData (paginado)
GET    /api/pagar/adiantamentos -> { kpis, charts, table }
GET    /api/pagar/bancos        -> { charts, table }
GET    /api/pagar/tipos         -> { charts, table }

# Contas a Receber (espelho do Pagar com ajustes)
GET    /api/receber/filters     -> FilterOptions
GET    /api/receber/kpis        -> KPIData[]
GET    /api/receber/visao-geral -> { kpis, charts }
GET    /api/receber/vencimentos -> { aging, charts, table }
GET    /api/receber/clientes    -> { top, abc, ranking, charts }
GET    /api/receber/categorias  -> { pareto, treemap, table }
GET    /api/receber/detalhes    -> TableData (paginado)
GET    /api/receber/adiantamentos -> { kpis, charts, table }
GET    /api/receber/tipos       -> { charts, table }

# Intercompany
GET    /api/intercompany/conciliacao -> { kpis, matrix, pairs, charts }
GET    /api/intercompany/detalhes-pagar -> TableData
GET    /api/intercompany/detalhes-receber -> TableData

# Todos endpoints aceitam query params de filtros:
# ?data_inicio=2024-01-01&data_fim=2024-12-31&filiais=F1,F2&status=vencido&categoria=X
```

---

## Mapeamento de Funcionalidades (Streamlit -> Next.js)

### Contas a Pagar (app.py + tabs/)
| Tab Streamlit | Endpoint API | Componente Frontend |
|---|---|---|
| Visao Geral | `/api/pagar/visao-geral` | `pagar/page.tsx` (tab default) |
| Vencimentos | `/api/pagar/vencimentos` | Tab Vencimentos |
| Fornecedores | `/api/pagar/fornecedores` | Tab Fornecedores |
| Categorias | `/api/pagar/categorias` | Tab Categorias |
| Evolucao | `/api/pagar/evolucao` | Tab Evolucao |
| Tipos Doc | `/api/pagar/tipos` | Tab Tipos |
| Adiantamentos | `/api/pagar/adiantamentos` | Tab Adiantamentos |
| Bancos | `/api/pagar/bancos` | Tab Bancos |
| Juros/Cambio | `/api/pagar/juros-cambio` | Tab JurosCambio |
| Detalhes | `/api/pagar/detalhes` | Tab Detalhes |

### Contas a Receber (pages/2_Contas_a_Receber.py + tabs_receber/)
| Tab Streamlit | Endpoint API | Componente Frontend |
|---|---|---|
| Visao Geral | `/api/receber/visao-geral` | `receber/page.tsx` (tab default) |
| Vencimentos | `/api/receber/vencimentos` | Tab Vencimentos |
| Clientes | `/api/receber/clientes` | Tab Clientes |
| Categorias | `/api/receber/categorias` | Tab Categorias |
| Tipos Doc | `/api/receber/tipos` | Tab Tipos |
| Adiantamentos | `/api/receber/adiantamentos` | Tab Adiantamentos |
| Detalhes | `/api/receber/detalhes` | Tab Detalhes |

### Intercompany (pages/1_Intercompany.py + tabs/intercompany_unified.py)
| Secao | Endpoint API | Componente Frontend |
|---|---|---|
| KPIs + Conciliacao | `/api/intercompany/conciliacao` | `intercompany/page.tsx` |
| Detalhes Pagar | `/api/intercompany/detalhes-pagar` | Tab Detalhes Pagar |
| Detalhes Receber | `/api/intercompany/detalhes-receber` | Tab Detalhes Receber |

---

## Tema e Design

### Paleta de Cores (Dark Theme padrao)
Reutilizar do `config/theme.py`:
```typescript
const darkTheme = {
  background: '#0f172a',
  card: '#1e293b',
  cardHover: '#334155',
  border: '#334155',
  text: '#f1f5f9',
  textSecondary: '#94a3b8',
  primary: '#3b82f6',
  success: '#10b981',
  danger: '#ef4444',
  warning: '#f59e0b',
  info: '#06b6d4',
  accent: '#8b5cf6',
};

const lightTheme = {
  background: '#f8fafc',
  card: '#ffffff',
  // ...
};
```

### Componentes shadcn/ui a Instalar
`card`, `button`, `input`, `select`, `tabs`, `table`, `dialog`, `dropdown-menu`, `badge`, `tooltip`, `separator`, `skeleton`, `sheet` (sidebar mobile), `toggle`, `popover`, `calendar`, `command`

---

## Fases de Implementacao

### Fase 1: Scaffolding + Auth
**Arquivos a criar:**
- `dashboard-rebranding/backend/` - FastAPI base com auth JWT
- `dashboard-rebranding/frontend/` - Next.js com shadcn/ui + Tailwind
- Login page funcional
- Layout base (Navbar + Sidebar + Content area)
- Tema escuro/claro

**Resultado:** Login funciona, layout base renderiza, sem dados ainda.

### Fase 2: Data Layer + Contas a Pagar
**Backend:**
- Data loader (Excel -> Pandas) com cache
- Services de processamento (filtros, aging, ABC, agrupamentos)
- Endpoints /api/pagar/* com todos os filtros
- Schemas Pydantic para todas as respostas

**Frontend:**
- Componentes chart reutilizaveis (BarChart, LineChart, PieChart, etc.)
- KPICard, DataTable, FilterBar
- Pagina Contas a Pagar completa com todas as tabs
- Zustand store para filtros
- TanStack Query para cache

**Resultado:** Dashboard Contas a Pagar 100% funcional.

### Fase 3: Contas a Receber + Intercompany
**Backend:**
- Endpoints /api/receber/* e /api/intercompany/*
- Services espelhados do Pagar com ajustes

**Frontend:**
- Paginas Receber e Intercompany
- Reutilizacao maxima de componentes da Fase 2

**Resultado:** Dashboard completo, todas as 3 paginas funcionando.

### Fase 4: Polish + Deploy
- Animacoes com Framer Motion
- Responsividade mobile
- Loading skeletons
- Error boundaries
- Docker compose (backend + frontend)
- Deploy config

---

## Arquivos Criticos do Projeto Atual (referencia)

### Logica de Negocio (portar para services/)
- `data/loader.py` - Carregamento + padronizacao de dados
- `data/loader_receber.py` - Loader especifico receber
- `config/settings.py` - Constantes, patterns intercompany, grupos filiais
- `tabs/visao_geral.py` - KPIs e graficos overview
- `tabs/vencimentos.py` - Aging buckets, analise vencimentos
- `tabs/fornecedores.py` - ABC/Pareto, ranking, ticket medio
- `tabs/categorias.py` - Pareto categorias, treemap
- `tabs/intercompany_unified.py` - Conciliacao intercompany

### Auth (portar para auth/)
- `auth/database.py` - Conexao Neon PostgreSQL + autenticar_usuario
- `auth/security.py` - Hash bcrypt
- `auth/login.py` - UI login (recriar em React)

### Formatadores (portar para lib/formatters.ts)
- `utils/formatters.py` - formatar_moeda (R$ com Bi/M/K), formatar_numero, to_excel, to_csv

---

## Verificacao

1. **Backend:** `cd dashboard-rebranding/backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
   - Testar `POST /api/auth/login` com credenciais
   - Testar `GET /api/pagar/visao-geral` com token
   - Verificar que filtros funcionam nos endpoints

2. **Frontend:** `cd dashboard-rebranding/frontend && npm install && npm run dev`
   - Login funcional
   - Navegacao entre Pagar/Receber/Intercompany
   - Todos os graficos renderizam com dados reais
   - Filtros (data, filial, status) atualizam os dados
   - Tema escuro/claro funciona
   - Export Excel/CSV funciona

3. **Integracao:** Frontend consome API do backend corretamente, auth protege rotas
