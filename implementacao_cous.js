const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, Footer, PageBreak
} = require('docx');
const fs = require('fs');

const GRAY_HEADER = "2E4057";
const GRAY_LIGHT = "F2F4F6";
const GRAY_MID = "D0D5DC";
const TEAL = "1D9E75";
const AMBER = "BA7517";
const BLUE = "185FA5";
const RED = "A32D2D";
const WHITE = "FFFFFF";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorders = {
  top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
};

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    children: [new TextRun({ text, font: "Arial", size: 36, bold: true, color: GRAY_HEADER })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: GRAY_MID, space: 4 } },
    children: [new TextRun({ text, font: "Arial", size: 28, bold: true, color: GRAY_HEADER })]
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 24, bold: true, color: GRAY_HEADER })]
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 80, after: 120 },
    children: [new TextRun({ text, font: "Arial", size: 22, color: "333333", ...opts })]
  });
}

function pMixed(runs) {
  return new Paragraph({
    spacing: { before: 80, after: 120 },
    children: runs.map(r => new TextRun({ font: "Arial", size: 22, color: "333333", ...r }))
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, font: "Arial", size: 22, color: "333333" })]
  });
}

function bulletMixed(runs, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: runs.map(r => new TextRun({ font: "Arial", size: 22, color: "333333", ...r }))
  });
}

function code(text) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    indent: { left: 720 },
    children: [new TextRun({ text, font: "Courier New", size: 18, color: "1D3557" })]
  });
}

function label(text, color) {
  return new Paragraph({
    spacing: { before: 0, after: 0 },
    children: [new TextRun({ text, font: "Arial", size: 18, bold: true, color })]
  });
}

function divider() {
  return new Paragraph({
    spacing: { before: 160, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: GRAY_MID, space: 1 } },
    children: []
  });
}

function statusTable(rows) {
  const colW = [3200, 2400, 3760];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: colW,
    rows: [
      new TableRow({
        tableHeader: true,
        children: ["Arquivo", "Status", "O que muda"].map((t, i) =>
          new TableCell({
            borders,
            width: { size: colW[i], type: WidthType.DXA },
            shading: { fill: GRAY_HEADER, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: t, font: "Arial", size: 20, bold: true, color: WHITE })] })]
          })
        )
      }),
      ...rows.map((row, ri) =>
        new TableRow({
          children: row.map((cell, ci) =>
            new TableCell({
              borders,
              width: { size: colW[ci], type: WidthType.DXA },
              shading: { fill: ri % 2 === 0 ? WHITE : GRAY_LIGHT, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({
                children: [new TextRun({
                  text: cell.text,
                  font: ci === 0 ? "Courier New" : "Arial",
                  size: ci === 0 ? 18 : 20,
                  bold: ci === 1,
                  color: cell.color || "333333"
                })]
              })]
            })
          )
        })
      )
    ]
  });
}

function flowTable(rows) {
  const colW = [2600, 560, 2600, 560, 2600];
  const arrow = { text: "→", font: "Arial", size: 22, bold: true, color: GRAY_HEADER };
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: colW,
    rows: rows.map(row =>
      new TableRow({
        children: [
          new TableCell({
            borders: noBorders,
            width: { size: colW[0], type: WidthType.DXA },
            shading: { fill: row[0].fill || GRAY_LIGHT, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 140, right: 140 },
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: row[0].text, font: "Arial", size: 20, bold: row[0].bold, color: row[0].color || GRAY_HEADER })] })]
          }),
          new TableCell({ borders: noBorders, width: { size: colW[1], type: WidthType.DXA }, margins: { top: 100, bottom: 100, left: 60, right: 60 }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun(arrow)] })] }),
          new TableCell({
            borders: noBorders,
            width: { size: colW[2], type: WidthType.DXA },
            shading: { fill: row[1].fill || GRAY_LIGHT, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 140, right: 140 },
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: row[1].text, font: "Arial", size: 20, bold: row[1].bold, color: row[1].color || GRAY_HEADER })] })]
          }),
          new TableCell({ borders: noBorders, width: { size: colW[3], type: WidthType.DXA }, margins: { top: 100, bottom: 100, left: 60, right: 60 }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun(arrow)] })] }),
          new TableCell({
            borders: noBorders,
            width: { size: colW[4], type: WidthType.DXA },
            shading: { fill: row[2].fill || GRAY_LIGHT, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 140, right: 140 },
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: row[2].text, font: "Arial", size: 20, bold: row[2].bold, color: row[2].color || GRAY_HEADER })] })]
          }),
        ]
      })
    )
  });
}

function decisionBox(titulo, decisao, alternativa) {
  const colW = [2200, 3760, 3400];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: colW,
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders,
            width: { size: colW[0], type: WidthType.DXA },
            shading: { fill: GRAY_HEADER, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 140, right: 140 },
            children: [new Paragraph({ children: [new TextRun({ text: titulo, font: "Arial", size: 20, bold: true, color: WHITE })] })]
          }),
          new TableCell({
            borders,
            width: { size: colW[1], type: WidthType.DXA },
            shading: { fill: "E8F5EF", type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 140, right: 140 },
            children: [
              new Paragraph({ children: [new TextRun({ text: "Decisão adotada", font: "Arial", size: 18, bold: true, color: TEAL })] }),
              new Paragraph({ spacing: { before: 40 }, children: [new TextRun({ text: decisao, font: "Arial", size: 20, color: "1A3D2E" })] })
            ]
          }),
          new TableCell({
            borders,
            width: { size: colW[2], type: WidthType.DXA },
            shading: { fill: "FDF6E3", type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 140, right: 140 },
            children: [
              new Paragraph({ children: [new TextRun({ text: "Alternativa descartada", font: "Arial", size: 18, bold: true, color: AMBER })] }),
              new Paragraph({ spacing: { before: 40 }, children: [new TextRun({ text: alternativa, font: "Arial", size: 20, color: "4A3200" })] })
            ]
          }),
        ]
      })
    ]
  });
}

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
        ]
      }
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [
              new TextRun({ text: "LigadoAI — Implementação Cous  |  pág. ", font: "Arial", size: 18, color: "999999" }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: "999999" }),
            ]
          })
        ]
      })
    },
    children: [

      // ── CAPA ──
      new Paragraph({ spacing: { before: 1440, after: 80 }, children: [new TextRun({ text: "LigadoAI", font: "Arial", size: 64, bold: true, color: GRAY_HEADER })] }),
      new Paragraph({ spacing: { before: 0, after: 60 }, children: [new TextRun({ text: "Cous Terminal Chat", font: "Arial", size: 40, color: TEAL })] }),
      new Paragraph({ spacing: { before: 0, after: 480 }, children: [new TextRun({ text: "Documento de Implementação — Integração PostgreSQL e OpenTracy", font: "Arial", size: 26, color: "666666" })] }),
      new Paragraph({
        spacing: { before: 0, after: 1800 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: TEAL, space: 4 } },
        children: [new TextRun({ text: "Versão 1.0  •  Junho 2026", font: "Arial", size: 20, color: "999999" })]
      }),

      // ── 1. CONTEXTO ──
      h1("1. Contexto e motivação"),
      p("O Cous é um assistente de diagnóstico técnico para máquinas de tatuagem, operado via terminal CLI. A arquitetura original conecta o CLI Python a um backend chamado OpenTracy, que usa DeepSeek como LLM e FAISS para busca vetorial (RAG). A base de conhecimento era composta por arquivos Markdown locais, e as medições físicas dos sensores ESP32-S3 já haviam sido migradas para PostgreSQL."),
      p("Durante a análise da arquitetura, foram identificados três problemas estruturais que motivaram esta implementação:"),
      bullet("Os arquivos Markdown de conhecimento permaneciam apenas no filesystem local — se o servidor mudasse de máquina, o conhecimento se perdia."),
      bullet("Não havia validação de qualidade antes da ingestão de documentos, ao contrário das medições seriais que já tinham um validador."),
      bullet("O OpenTracy não tinha camada de comunicação com o PostgreSQL, criando uma inconsistência entre os dois sistemas."),
      new Paragraph({ spacing: { before: 120 }, children: [] }),

      // ── 2. DECISÕES DE ARQUITETURA ──
      h1("2. Decisões de arquitetura"),
      p("As decisões abaixo foram tomadas com base na análise do código-fonte real de ambos os projetos. Cada uma registra a alternativa descartada e o motivo."),
      new Paragraph({ spacing: { before: 160 }, children: [] }),

      h3("2.1  Eliminação do diretório knowledge/ como persistência"),
      decisionBox(
        "Destino dos .md",
        "Os arquivos Markdown são transitórios: processados, validados e sincronizados para o banco. Não persistem no repositório.",
        "Manter knowledge/ como staging area permanente, crescendo indefinidamente com arquivos de dados no git."
      ),
      new Paragraph({ spacing: { before: 160 }, children: [] }),
      p("O diretório knowledge/ deixa de existir como pasta rastreada pelo git. O técnico cria o .md onde quiser (desktop, pendrive), roda /indexar passando o path, e o arquivo local pode ser descartado após o sync. O repositório passa a versionar apenas o schema de validação e o código, nunca os dados."),
      new Paragraph({ spacing: { before: 160 }, children: [] }),

      h3("2.2  OpenTracy como executor stateless — sem conexão direta ao banco"),
      decisionBox(
        "Acesso ao banco",
        "O OpenTracy não se conecta ao PostgreSQL. O Cous é o dono do conhecimento e alimenta o OpenTracy via HTTP.",
        "Criar pg_store.py dentro do OpenTracy com conexão própria ao banco, acoplando dois sistemas independentes."
      ),
      new Paragraph({ spacing: { before: 160 }, children: [] }),
      p("O OpenTracy foi projetado como runtime stateless — lê arquivos, processa, responde. Adicionar uma conexão de banco quebraria essa responsabilidade única. A solução correta é manter o OpenTracy ignorante do banco e fazer o Cous injetar o corpus via endpoint HTTP."),
      new Paragraph({ spacing: { before: 160 }, children: [] }),

      h3("2.3  Invalidação de cache por evento, não por mtime"),
      decisionBox(
        "Cache do índice FAISS",
        "Invalidação event-driven: o corpus só é recarregado quando o Cous chama /corpus/reload após um /indexar.",
        "Manter checagem de mtime do manifest.jsonl — impossível com PostgreSQL como fonte, causaria recarga a cada requisição."
      ),
      new Paragraph({ spacing: { before: 160 }, children: [] }),

      h3("2.4  Bloqueio assíncrono — run_in_executor"),
      decisionBox(
        "Async vs sync",
        "run_in_executor para a reconstrução do FAISS em memória: não bloqueia o event loop, sem refatorar o _DenseRetriever.",
        "Migrar tudo para asyncpg — correto a longo prazo, mas invasivo demais para o escopo atual."
      ),
      new Paragraph({ spacing: { before: 160 }, children: [] }),

      h3("2.5  Pool de conexão — dois processos, dois pools"),
      decisionBox(
        "Pool de conexão",
        "Como são processos separados, cada um tem seu pool: Cous CLI gerencia o banco, OpenTracy não sabe que ele existe.",
        "Pool compartilhado — só faria sentido se rodassem no mesmo processo, o que não é o caso."
      ),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── 3. ARQUITETURA FINAL ──
      h1("3. Arquitetura final"),
      p("O modelo final separa claramente as responsabilidades: o Cous é o dono do conhecimento e da persistência; o OpenTracy é um executor puro de pipeline de linguagem."),
      new Paragraph({ spacing: { before: 160 }, children: [] }),

      h3("3.1  Fluxo de ingestão de conhecimento"),
      flowTable([
        [
          { text: "Técnico cria .md", fill: GRAY_LIGHT },
          { text: "ValidadorConhecimento", fill: "FDF6E3", bold: true },
          { text: "KnowledgeSyncer → banco", fill: "E8F5EF", bold: true }
        ]
      ]),
      new Paragraph({ spacing: { before: 80 }, children: [] }),
      flowTable([
        [
          { text: "banco (chunks + vetores)", fill: GRAY_LIGHT },
          { text: "CorpusClient → POST /corpus/reload", fill: "E6F1FB", bold: true },
          { text: "FAISS reconstruído em memória", fill: GRAY_LIGHT }
        ]
      ]),
      new Paragraph({ spacing: { before: 160 }, children: [] }),
      p("O arquivo .md nunca precisa existir no servidor. Após o sync, o banco é a única fonte de verdade. O OpenTracy recebe os chunks via HTTP e reconstrói o índice FAISS em memória — sem arquivo em disco, sem conexão de banco."),
      new Paragraph({ spacing: { before: 160 }, children: [] }),

      h3("3.2  Fluxo de startup"),
      p("Quando o Cous inicia, lê todos os chunks ativos do PostgreSQL e chama POST /corpus/reload no OpenTracy. Se o OpenTracy reiniciar de forma independente, o Cous detecta via healthcheck e reinjeta o corpus. O OpenTracy é cold-start safe: sem corpus, retorna [] de documentos e o pipeline segue com o LLM respondendo diretamente."),
      new Paragraph({ spacing: { before: 160 }, children: [] }),

      h3("3.3  Fronteira HTTP entre os projetos"),
      p("A única comunicação nova entre Cous e OpenTracy é um único endpoint:"),
      code("POST /corpus/reload"),
      code("Body: { chunks: [{ id, text, source, vector, metadata }] }"),
      code("Response: 200 OK | { loaded: N, dimension: D }"),
      new Paragraph({ spacing: { before: 120 }, children: [] }),
      p("Todo o resto da comunicação existente (POST /run para diagnóstico) permanece inalterado."),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── 4. MAPA DE ARQUIVOS ──
      h1("4. Mapa completo de mudanças"),

      h3("4.1  Cous CLI"),
      statusTable([
        [{ text: "app/knowledge_syncer.py" }, { text: "NOVO", color: TEAL }, { text: "Recebe conteúdo como string, chunka, embeda e faz upsert dos chunks e vetores em documentos_conhecimento no PostgreSQL. Sem arquivos em disco." }],
        [{ text: "app/validador_conhecimento.py" }, { text: "NOVO", color: TEAL }, { text: "Valida frontmatter YAML, campos obrigatórios (fabricante, modelo, tipo), faixas numéricas coerentes (freq_min < freq_max) e encoding UTF-8. Retorna lista tipada de erros." }],
        [{ text: "app/corpus_client.py" }, { text: "NOVO", color: TEAL }, { text: "Cliente HTTP que lê chunks do banco e chama POST /corpus/reload no OpenTracy. Usado no /indexar e no startup." }],
        [{ text: "app/chat_loop.py" }, { text: "MUDA", color: AMBER }, { text: "Handler do /indexar recebe path do .md, chama ValidadorConhecimento → KnowledgeSyncer → CorpusClient. Duas linhas a mais no final do fluxo existente." }],
        [{ text: "app/startup.py" }, { text: "MUDA", color: AMBER }, { text: "Ao iniciar, lê todos chunks ativos do banco e chama /corpus/reload. Monitora healthcheck do OpenTracy para reinjetar corpus se necessário." }],
        [{ text: "demais módulos" }, { text: "INTOCADO", color: "888888" }, { text: "medicao, auth, config, router, memória, autenticação — nenhuma alteração." }],
      ]),
      new Paragraph({ spacing: { before: 200 }, children: [] }),

      h3("4.2  OpenTracy"),
      statusTable([
        [{ text: "runtime/server.py" }, { text: "MUDA", color: AMBER }, { text: "Ganha um único endpoint novo: POST /corpus/reload. Recebe chunks + vetores, chama CorpusMemoryStore.reload(), retorna 200. O restante das ~1100 linhas não é tocado." }],
        [{ text: "corpora/memory_store.py" }, { text: "NOVO", color: TEAL }, { text: "Singleton em memória. Método reload() recebe chunks e vetores, reconstrói FAISS internamente. Expõe mesma interface do CorpusStore: empty, size, query(). Reconstrução roda em run_in_executor para não bloquear o event loop." }],
        [{ text: "techniques/rag/impl.py" }, { text: "1 LINHA", color: AMBER }, { text: "_load_store() troca CorpusStore.load() por CorpusMemoryStore.instance(). A checagem de mtime desaparece — invalidação é event-driven. execute(), embedder, Document — nada mais muda." }],
        [{ text: "corpora/store.py" }, { text: "INTOCADO", color: "888888" }, { text: "CorpusStore filesystem original permanece. Pode ser usado para desenvolvimento local sem PostgreSQL." }],
        [{ text: "corpora/ingest.py" }, { text: "INTOCADO", color: "888888" }, { text: "Pipeline de ingestão filesystem original permanece. Compatibilidade retroativa preservada." }],
        [{ text: "todo o resto" }, { text: "INTOCADO", color: "888888" }, { text: "executor, pipeline, protocolos, reranking, routing, LLM, traces, harness, compilador, agentes — completamente inalterados." }],
      ]),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── 5. VALIDAÇÃO ──
      h1("5. Validação de conhecimento"),
      p("A validação de documentos segue o mesmo contrato do validador serial de medições — mesma estrutura de erro tipado, mesmos critérios de rejeição. Apenas documentos aprovados seguem para o KnowledgeSyncer."),
      new Paragraph({ spacing: { before: 120 }, children: [] }),

      h3("5.1  Regras de validação"),
      bullet("Frontmatter YAML presente e parseável"),
      bullet("Campos obrigatórios preenchidos: fabricante, modelo, tipo"),
      bullet("Faixas numéricas coerentes: freq_min_hz < freq_max_hz, todos os valores positivos"),
      bullet("Encoding UTF-8 válido"),
      bullet("Conteúdo não vazio após remoção do frontmatter"),
      new Paragraph({ spacing: { before: 120 }, children: [] }),

      h3("5.2  Saída do validador"),
      p("O validador retorna um relatório por arquivo com três possíveis resultados: aprovado (segue para sync), rejeitado (bloqueia o sync com mensagem de erro), ou aviso (sync ocorre mas técnico é alertado). O relatório é exibido no terminal antes de qualquer gravação no banco."),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── 6. SCHEMA DO BANCO ──
      h1("6. Schema PostgreSQL — documentos_conhecimento"),
      p("Tabela análoga a sessoes_medicao, com campos para o frontmatter como JSONB e detecção de mudança por hash de conteúdo."),
      new Paragraph({ spacing: { before: 120 }, children: [] }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 1600, 5360],
        rows: [
          new TableRow({
            tableHeader: true,
            children: ["Coluna", "Tipo", "Descrição"].map((t, i) =>
              new TableCell({
                borders,
                width: { size: [2400, 1600, 5360][i], type: WidthType.DXA },
                shading: { fill: GRAY_HEADER, type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun({ text: t, font: "Arial", size: 20, bold: true, color: WHITE })] })]
              })
            )
          }),
          ...([
            ["id", "UUID PK", "Identificador único do documento"],
            ["conteudo_md", "TEXT", "Conteúdo Markdown completo"],
            ["frontmatter", "JSONB", "Metadados parseados do YAML (fabricante, modelo, tipo, faixas)"],
            ["hash_conteudo", "VARCHAR(64)", "SHA-256 do conteúdo — detecta mudanças para upsert inteligente"],
            ["status_validacao", "VARCHAR(16)", "aprovado | rejeitado | aviso"],
            ["indexado_em", "TIMESTAMPTZ", "Timestamp da última indexação bem-sucedida"],
            ["updated_at", "TIMESTAMPTZ", "Última atualização — usado pelo CorpusMemoryStore para invalidação"],
          ]).map((row, ri) =>
            new TableRow({
              children: row.map((cell, ci) =>
                new TableCell({
                  borders,
                  width: { size: [2400, 1600, 5360][ci], type: WidthType.DXA },
                  shading: { fill: ri % 2 === 0 ? WHITE : GRAY_LIGHT, type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: cell, font: ci < 2 ? "Courier New" : "Arial", size: ci < 2 ? 18 : 20, color: "333333" })] })]
                })
              )
            })
          )
        ]
      }),
      new Paragraph({ spacing: { before: 200 }, children: [] }),

      p("A tabela de chunks — gerada pelo KnowledgeSyncer — armazena cada fragmento com seu vetor:"),
      new Paragraph({ spacing: { before: 120 }, children: [] }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 1600, 5360],
        rows: [
          new TableRow({
            tableHeader: true,
            children: ["Coluna", "Tipo", "Descrição"].map((t, i) =>
              new TableCell({
                borders,
                width: { size: [2400, 1600, 5360][i], type: WidthType.DXA },
                shading: { fill: GRAY_HEADER, type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun({ text: t, font: "Arial", size: 20, bold: true, color: WHITE })] })]
              })
            )
          }),
          ...([
            ["chunk_id", "VARCHAR(32) PK", "Hash SHA-1 do chunk (mesmo formato do ingest.py original)"],
            ["documento_id", "UUID FK", "Referência ao documento pai"],
            ["texto", "TEXT", "Conteúdo do chunk"],
            ["vetor", "FLOAT4[]", "Embedding MiniLM-L6 — 384 dimensões"],
            ["chunk_index", "INT", "Posição do chunk dentro do documento"],
            ["n_chunks", "INT", "Total de chunks do documento"],
            ["metadata", "JSONB", "source, fabricante, modelo — herdados do frontmatter"],
          ]).map((row, ri) =>
            new TableRow({
              children: row.map((cell, ci) =>
                new TableCell({
                  borders,
                  width: { size: [2400, 1600, 5360][ci], type: WidthType.DXA },
                  shading: { fill: ri % 2 === 0 ? WHITE : GRAY_LIGHT, type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: cell, font: ci < 2 ? "Courier New" : "Arial", size: ci < 2 ? 18 : 20, color: "333333" })] })]
                })
              )
            })
          )
        ]
      }),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── 7. IMPACTO NOS TESTES ──
      h1("7. Impacto nos testes existentes"),
      p("A implementação foi desenhada para preservar todos os testes existentes sem alteração:"),
      new Paragraph({ spacing: { before: 100 }, children: [] }),
      bulletMixed([
        { text: "techniques/rag/tests/test_dense.py", font: "Courier New", size: 18, color: BLUE },
        { text: " — usa monkeypatch.setattr para injetar o store diretamente. Nunca passa pelo _load_store() modificado. Zero alterações." }
      ]),
      bulletMixed([
        { text: "corpora/tests/test_ingest_and_store.py", font: "Courier New", size: 18, color: BLUE },
        { text: " — testa o filesystem store que permanece intocado. Zero alterações." }
      ]),
      new Paragraph({ spacing: { before: 120 }, children: [] }),
      p("Novos testes necessários:"),
      bulletMixed([
        { text: "corpora/tests/test_memory_store.py", font: "Courier New", size: 18, color: TEAL },
        { text: " — testa reload(), query() e comportamento de empty store. Mock de chunks e vetores, sem banco." }
      ]),
      bulletMixed([
        { text: "app/tests/test_corpus_client.py", font: "Courier New", size: 18, color: TEAL },
        { text: " — testa serialização do payload e chamada HTTP com mock do OpenTracy." }
      ]),
      bulletMixed([
        { text: "app/tests/test_validador_conhecimento.py", font: "Courier New", size: 18, color: TEAL },
        { text: " — testa casos de aprovação, rejeição e aviso com fixtures de .md válidos e inválidos." }
      ]),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── 8. ORDEM DE IMPLEMENTAÇÃO ──
      h1("8. Ordem de implementação"),
      p("A sequência abaixo respeita as dependências entre os componentes — cada etapa pode ser testada de forma isolada antes de avançar."),
      new Paragraph({ spacing: { before: 120 }, children: [] }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [800, 2800, 5760],
        rows: [
          new TableRow({
            tableHeader: true,
            children: ["Etapa", "Componente", "Critério de conclusão"].map((t, i) =>
              new TableCell({
                borders,
                width: { size: [800, 2800, 5760][i], type: WidthType.DXA },
                shading: { fill: GRAY_HEADER, type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun({ text: t, font: "Arial", size: 20, bold: true, color: WHITE })] })]
              })
            )
          }),
          ...([
            ["1", "Schema documentos_conhecimento + chunks", "Migrações PostgreSQL aplicadas, tabelas criadas"],
            ["2", "corpora/memory_store.py (OpenTracy)", "test_memory_store.py passa; query() retorna hits corretos"],
            ["3", "POST /corpus/reload (server.py)", "curl com payload de teste retorna 200 e FAISS carregado"],
            ["4", "app/validador_conhecimento.py (Cous)", "test_validador_conhecimento.py cobre aprovado/rejeitado/aviso"],
            ["5", "app/knowledge_syncer.py (Cous)", "Upsert no banco por hash funciona; chunks corretos gravados"],
            ["6", "app/corpus_client.py (Cous)", "test_corpus_client.py passa com mock HTTP"],
            ["7", "Integração /indexar no chat_loop.py", "Fluxo E2E: .md → validar → sync → reload → RAG responde"],
            ["8", "Startup reload no Cous", "Restart do OpenTracy seguido de restart do Cous recupera corpus"],
          ]).map((row, ri) =>
            new TableRow({
              children: row.map((cell, ci) =>
                new TableCell({
                  borders,
                  width: { size: [800, 2800, 5760][ci], type: WidthType.DXA },
                  shading: { fill: ri % 2 === 0 ? WHITE : GRAY_LIGHT, type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: cell, font: ci === 0 ? "Arial" : "Arial", size: 20, bold: ci === 0, color: ci === 0 ? GRAY_HEADER : "333333" })] })]
                })
              )
            })
          )
        ]
      }),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── 9. PONTOS DE ATENÇÃO ──
      h1("9. Pontos de atenção na implementação"),

      h3("9.1  Cache do CorpusMemoryStore e concorrência"),
      p("O CorpusMemoryStore é um singleton. O endpoint /corpus/reload substitui o índice FAISS atomicamente — a referência ao store antigo deve ser descartada somente após o novo estar pronto. Usar asyncio.Lock para garantir que uma reconstrução em andamento não seja interrompida por um segundo reload simultâneo."),
      new Paragraph({ spacing: { before: 120 }, children: [] }),

      h3("9.2  Tamanho do payload de reload"),
      p("Com muitos documentos, o payload de chunks + vetores pode crescer. Vetores MiniLM-L6 têm 384 dimensões (float32 = 4 bytes) — 10.000 chunks = ~15MB por reload. Aceitável para o volume atual do Cous. Se o volume crescer, implementar reload incremental (apenas chunks novos ou modificados por hash)."),
      new Paragraph({ spacing: { before: 120 }, children: [] }),

      h3("9.3  Healthcheck e resiliência"),
      p("O corpus_client.py deve verificar o healthcheck do OpenTracy antes de chamar /corpus/reload. Se o OpenTracy estiver indisponível no momento do /indexar, o sync no banco ocorre normalmente e o reload é agendado com retry. O técnico é informado que o corpus será atualizado quando o OpenTracy estiver disponível."),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── 10. O QUE NÃO MUDA ──
      h1("10. O que não muda"),
      p("Esta seção registra explicitamente o que permanece inalterado — importante para delimitar o escopo da implementação."),
      new Paragraph({ spacing: { before: 120 }, children: [] }),
      bullet("Todo o pipeline de medições via serial (validador serial, MedicaoService, snapshots_medicao)"),
      bullet("O protocolo TMA_DATA do firmware ESP32-S3"),
      bullet("O endpoint POST /run do OpenTracy e toda a lógica de pipeline (reranking, routing, generate)"),
      bullet("O CorpusStore filesystem original — pode ser usado em desenvolvimento local sem PostgreSQL via variável de ambiente"),
      bullet("O ingest.py original — mantido para compatibilidade e desenvolvimento local"),
      bullet("Todos os testes existentes do OpenTracy e do Cous"),
      bullet("A interface de autenticação, memória de sessão e roteamento de comandos do Cous CLI"),
      new Paragraph({ spacing: { before: 240 }, children: [] }),

      // ── RODAPÉ ──
      divider(),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 120 },
        children: [new TextRun({ text: "Documento gerado a partir da análise do código-fonte real de LigadoAI-main.zip  •  Junho 2026", font: "Arial", size: 18, color: "999999", italics: true })]
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/mnt/user-data/outputs/implementacao_cous.docx", buffer);
  console.log("OK");
});
