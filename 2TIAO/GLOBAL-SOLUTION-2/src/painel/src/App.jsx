import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [alertas, setAlertas] = useState([]);
  const [matches, setMatches] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");

  const carregarDados = useCallback(async () => {
    try {
      setCarregando(true);
      setErro("");

      const [resAlertas, resMatches] = await Promise.all([
        fetch(`${API_URL}/alertas`),
        fetch(`${API_URL}/matches`),
      ]);

      if (!resAlertas.ok || !resMatches.ok) {
        throw new Error("Não foi possível consultar a API.");
      }

      const dadosAlertas = await resAlertas.json();
      const dadosMatches = await resMatches.json();

      setAlertas(dadosAlertas.alertas || []);
      setMatches(dadosMatches.matches || []);
    } catch (error) {
      setErro(error.message);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      carregarDados();
    }, 0);

    return () => clearTimeout(timer);
  }, [carregarDados]);

  const indicadores = useMemo(() => {
    const aguardando = matches.filter(
      (match) => match.status === "aguardando_aprovacao"
    ).length;

    const confirmados = matches.filter(
      (match) => match.status === "confirmado"
    ).length;

    const rejeitados = matches.filter(
      (match) => match.status === "rejeitado"
    ).length;

    const lojasAfetadas = new Set(
      matches
        .filter((match) => match.loja_id)
        .map((match) => match.loja_id)
    ).size;

    return {
      alertas: alertas.length,
      lojasAfetadas,
      aguardando,
      confirmados,
      rejeitados,
    };
  }, [alertas, matches]);

  async function decidirMatch(matchId, decisao) {
    const acao = decisao === "confirmado" ? "confirmar" : "rejeitar";

    const motivo = window.prompt(
      `Informe o motivo para ${acao} este match:`,
      decisao === "confirmado"
        ? "Evidência conferida pela equipe."
        : "Match descartado após conferência."
    );

    if (motivo === null) {
      return;
    }

    try {
      setMensagem("");
      setErro("");

      const resposta = await fetch(
        `${API_URL}/matches/${matchId}/decisao`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            decisao,
            responsavel: "Equipe da rede",
            motivo,
          }),
        }
      );

      if (!resposta.ok) {
        const detalhe = await resposta.json();
        throw new Error(
          detalhe.detail || "Não foi possível registrar a decisão."
        );
      }

      setMensagem(
        decisao === "confirmado"
          ? "Match confirmado com sucesso."
          : "Match rejeitado com sucesso."
      );

      await carregarDados();
    } catch (error) {
      setErro(error.message);
    }
  }

  function textoRegra(alerta) {
    const regra = alerta.regra_lote || {};

    if (regra.tipo === "lista") {
      return `Lotes: ${(regra.lotes || []).join(", ")}`;
    }

    if (regra.tipo === "sufixo") {
      return `Lotes terminados em: ${regra.sufixo || "-"}`;
    }

    if (regra.tipo === "corte_data") {
      return `Data limite: ${regra.data_limite || "-"}`;
    }

    if (regra.tipo === "todos") {
      return "Todos os lotes";
    }

    return regra.tipo || "Regra não informada";
  }

  function nomeAlerta(alertaId) {
    const alerta = alertas.find(
      (item) => item.alerta_id === alertaId
    );

    if (!alerta) {
      return alertaId;
    }

    return `${alerta.produto || "Produto"} - ${
      alerta.marca || "Marca não informada"
    }`;
  }

  if (carregando) {
    return (
      <main className="estado-central">
        <h1>Recall Seguro</h1>
        <p>Carregando dados...</p>
      </main>
    );
  }

  return (
    <div className="app">
      <header className="topo">
        <div>
          <span className="etiqueta">CitizenTech • Recall de alimentos</span>
          <h1>Painel da rede</h1>
          <p>
            Monitoramento de alertas, lojas afetadas e confirmação humana
            dos matches encontrados.
          </p>
        </div>

        <button className="botao-secundario" onClick={carregarDados}>
          Atualizar dados
        </button>
      </header>

      {erro && <div className="mensagem erro">{erro}</div>}

      {mensagem && (
        <div className="mensagem sucesso">{mensagem}</div>
      )}

      <section className="indicadores">
        <article className="indicador">
          <span>Alertas ativos</span>
          <strong>{indicadores.alertas}</strong>
        </article>

        <article className="indicador">
          <span>Lojas afetadas</span>
          <strong>{indicadores.lojasAfetadas}</strong>
        </article>

        <article className="indicador destaque">
          <span>Aguardando decisão</span>
          <strong>{indicadores.aguardando}</strong>
        </article>

        <article className="indicador">
          <span>Confirmados</span>
          <strong>{indicadores.confirmados}</strong>
        </article>
      </section>

      <section className="secao">
        <div className="titulo-secao">
          <div>
            <span className="etiqueta">Base monitorada</span>
            <h2>Alertas de recall</h2>
          </div>

          <span className="contador">
            {alertas.length} alerta(s)
          </span>
        </div>

        {alertas.length === 0 ? (
          <div className="estado-vazio">
            <h3>Nenhum alerta carregado</h3>
            <p>
              A API está funcionando, mas a memória do backend ainda não
              possui alertas nesta execução.
            </p>
          </div>
        ) : (
          <div className="grade-alertas">
            {alertas.map((alerta) => (
              <article
                className="cartao-alerta"
                key={alerta.alerta_id}
              >
                <div className="linha-cartao">
                  <span className="status status-alerta">
                    Recall ativo
                  </span>

                  <span className="codigo">
                    {alerta.alerta_id}
                  </span>
                </div>

                <h3>{alerta.produto}</h3>
                <p className="marca">{alerta.marca}</p>

                <dl>
                  <div>
                    <dt>Fabricante</dt>
                    <dd>{alerta.fabricante || "-"}</dd>
                  </div>

                  <div>
                    <dt>CNPJ</dt>
                    <dd>{alerta.cnpj || "-"}</dd>
                  </div>

                  <div>
                    <dt>Regra</dt>
                    <dd>{textoRegra(alerta)}</dd>
                  </div>
                </dl>

                {alerta.fonte_url && (
                  <a
                    href={alerta.fonte_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Consultar fonte oficial
                  </a>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="secao">
        <div className="titulo-secao">
          <div>
            <span className="etiqueta">
              Confirmação humana
            </span>
            <h2>Matches encontrados</h2>
          </div>

          <span className="contador">
            {matches.length} match(es)
          </span>
        </div>

        {matches.length === 0 ? (
          <div className="estado-vazio">
            <h3>Nenhum match encontrado</h3>
            <p>
              Quando o motor identificar um recebimento compatível com
              um recall, ele aparecerá aqui para conferência humana.
            </p>
          </div>
        ) : (
          <div className="lista-matches">
            {matches.map((match) => (
              <article
                className="cartao-match"
                key={match.match_id}
              >
                <div className="match-principal">
                  <div>
                    <span
                      className={`status status-${match.status}`}
                    >
                      {match.status}
                    </span>

                    <h3>{nomeAlerta(match.alerta_id)}</h3>

                    <p>
                      Loja:{" "}
                      <strong>{match.loja_id || "-"}</strong>
                    </p>
                  </div>

                  <span className="codigo">
                    {match.match_id}
                  </span>
                </div>

                <div className="evidencia">
                  <h4>Evidência do match</h4>

                  <div className="evidencia-grid">
                    <div>
                      <span>Campo analisado</span>
                      <strong>
                        {match.evidencia?.campo || "-"}
                      </strong>
                    </div>

                    <div>
                      <span>Valor recebido</span>
                      <strong>
                        {String(
                          match.evidencia?.valor_recebimento ??
                            "-"
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>Regra aplicada</span>
                      <strong>
                        {match.regra_aplicada || "-"}
                      </strong>
                    </div>
                  </div>
                </div>

                {match.revisao_manual && (
                  <div className="aviso">
                    Este match requer atenção adicional durante a
                    revisão humana.
                  </div>
                )}

                {match.status === "aguardando_aprovacao" && (
                  <div className="acoes">
                    <button
                      className="botao-confirmar"
                      onClick={() =>
                        decidirMatch(
                          match.match_id,
                          "confirmado"
                        )
                      }
                    >
                      Confirmar match
                    </button>

                    <button
                      className="botao-rejeitar"
                      onClick={() =>
                        decidirMatch(
                          match.match_id,
                          "rejeitado"
                        )
                      }
                    >
                      Rejeitar match
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <footer>
        <p>
          A inteligência artificial auxilia na extração dos dados. A
          decisão de recall é realizada por regras determinísticas e
          confirmada por uma pessoa.
        </p>
      </footer>
    </div>
  );
}

export default App;